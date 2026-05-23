from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import generate_api_key
from app.models import (
    ApiKey,
    ApiUsageLog,
    Coupon,
    CouponRedemption,
    PaymentOrder,
    Plan,
    PointPackage,
    Subscription,
    User,
)
from app.schemas.api import (
    ApiKeyCreate,
    ApiKeyIssued,
    ApiKeyResponse,
    CouponRedeem,
    Message,
    OrderCreate,
    OrderResponse,
    PackageResponse,
    PlanResponse,
    SubscriptionCreate,
)
from app.services.points import apply_points


router = APIRouter(tags=["商用機能"])


@router.get("/pricing/packages", response_model=list[PackageResponse])
def packages(db: Session = Depends(get_db)) -> list[PointPackage]:
    return list(db.scalars(select(PointPackage).where(PointPackage.is_active.is_(True))))


@router.get("/plans", response_model=list[PlanResponse])
def plans(db: Session = Depends(get_db)) -> list[Plan]:
    return list(db.scalars(select(Plan).where(Plan.is_active.is_(True))))


@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    payload: OrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentOrder:
    package = db.get(PointPackage, payload.package_id)
    if package is None or not package.is_active:
        raise AppError(404, "PACKAGE_NOT_FOUND", "ポイントパックが見つかりません。")
    order = PaymentOrder(
        user_id=user.id,
        package_id=package.id,
        amount=package.price,
        currency=package.currency,
        points_granted=package.points,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders", response_model=list[OrderResponse])
def orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PaymentOrder]:
    return list(
        db.scalars(
            select(PaymentOrder)
            .where(PaymentOrder.user_id == user.id)
            .order_by(desc(PaymentOrder.created_at))
        )
    )


@router.post("/orders/{order_id}/mock-pay", response_model=OrderResponse)
def mock_pay(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentOrder:
    order = db.scalar(
        select(PaymentOrder)
        .where(PaymentOrder.id == order_id, PaymentOrder.user_id == user.id)
        .with_for_update()
    )
    if order is None:
        raise AppError(404, "ORDER_NOT_FOUND", "注文が見つかりません。")
    if order.status == "PAID":
        raise AppError(409, "ORDER_ALREADY_PAID", "注文は既に支払い済みです。")
    if order.status != "PENDING":
        raise AppError(409, "ORDER_NOT_PAYABLE", "この注文は支払処理できません。")
    order.status = "PAID"
    order.paid_at = datetime.utcnow()
    apply_points(
        db,
        user.id,
        order.points_granted,
        "POINT_PURCHASE",
        "ポイントパック購入",
        "payment_order",
        order.id,
    )
    db.commit()
    db.refresh(order)
    return order


@router.post("/subscriptions", response_model=Message, status_code=201)
def subscribe(
    payload: SubscriptionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    plan = db.get(Plan, payload.plan_id)
    if plan is None or not plan.is_active:
        raise AppError(404, "PLAN_NOT_FOUND", "プランが見つかりません。")
    now = datetime.utcnow()
    db.add(
        Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status="ACTIVE",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
    )
    db.commit()
    return Message(message=f"{plan.name} プランを開始しました。")


@router.post("/coupons/redeem", response_model=Message)
def redeem_coupon(
    payload: CouponRedeem,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    coupon = db.scalar(select(Coupon).where(Coupon.code == payload.code.upper(), Coupon.is_active.is_(True)))
    if coupon is None or (coupon.expires_at and coupon.expires_at < datetime.utcnow()):
        raise AppError(404, "COUPON_NOT_AVAILABLE", "利用可能なクーポンが見つかりません。")
    if db.scalar(
        select(CouponRedemption.id).where(
            CouponRedemption.coupon_id == coupon.id,
            CouponRedemption.user_id == user.id,
        )
    ):
        raise AppError(409, "COUPON_ALREADY_REDEEMED", "このクーポンは既に利用済みです。")
    if coupon.max_redemptions is not None:
        count = db.scalar(
            select(func.count()).select_from(CouponRedemption).where(CouponRedemption.coupon_id == coupon.id)
        )
        if count >= coupon.max_redemptions:
            raise AppError(409, "COUPON_LIMIT_REACHED", "クーポンの利用上限に達しました。")
    if coupon.coupon_type != "POINTS":
        raise AppError(409, "COUPON_NOT_SUPPORTED", "現在はポイント付与型のみ利用できます。")
    db.add(CouponRedemption(coupon_id=coupon.id, user_id=user.id))
    apply_points(db, user.id, coupon.value, "COUPON_REWARD", "クーポン利用", "coupon", coupon.id)
    db.commit()
    return Message(message=f"クーポンを利用し、{coupon.value}ポイントを付与しました。")


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ApiKey]:
    return list(
        db.scalars(select(ApiKey).where(ApiKey.user_id == user.id).order_by(desc(ApiKey.created_at)))
    )


@router.get("/api-keys/usage")
def api_key_usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(ApiUsageLog, ApiKey.key_prefix)
        .join(ApiKey, ApiKey.id == ApiUsageLog.api_key_id)
        .where(ApiKey.user_id == user.id)
        .order_by(desc(ApiUsageLog.created_at))
        .limit(100)
    ).all()
    return [
        {
            "id": usage.id,
            "key_prefix": prefix,
            "endpoint": usage.endpoint,
            "status_code": usage.status_code,
            "points_cost": usage.points_cost,
            "created_at": usage.created_at,
        }
        for usage, prefix in rows
    ]


@router.post("/api-keys", response_model=ApiKeyIssued, status_code=201)
def issue_api_key(
    payload: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyIssued:
    plain_key, prefix, key_hash = generate_api_key()
    model = ApiKey(user_id=user.id, name=payload.name, key_prefix=prefix, key_hash=key_hash)
    db.add(model)
    db.commit()
    db.refresh(model)
    response = ApiKeyResponse.model_validate(model).model_dump()
    return ApiKeyIssued(**response, api_key=plain_key)


@router.delete("/api-keys/{key_id}", response_model=Message)
def revoke_api_key(
    key_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    key = db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id))
    if key is None:
        raise AppError(404, "API_KEY_NOT_FOUND", "APIキーが見つかりません。")
    key.status = "REVOKED"
    db.commit()
    return Message(message="APIキーを無効化しました。")
