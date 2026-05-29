from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_admin_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import AdminAuditLog, Coupon, PaymentOrder, Plan, SongAnalysis, SystemSetting, User
from app.schemas.api import (
    AdminCouponCreate,
    AdminCouponResponse,
    AdminOrderStatusUpdate,
    AdminPlanUpdate,
    AdminPointsUpdate,
    AdminRoleUpdate,
    AdminStatusUpdate,
    OrderResponse,
    PlanResponse,
    SettingResponse,
    SettingUpdate,
    SongAnalysisResponse,
    UserResponse,
)
from app.services.points import apply_points

router = APIRouter(prefix="/admin", tags=["管理者"])


def audit(db: Session, admin_id: int, action: str, target_type: str, target_id: int | None, detail: dict) -> None:
    db.add(
        AdminAuditLog(
            admin_user_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )


@router.get("/users", response_model=list[UserResponse])
def users(
    query: str | None = None,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[User]:
    statement = select(User).order_by(desc(User.created_at)).limit(100)
    if query:
        statement = select(User).where(User.email.like(f"%{query}%")).order_by(desc(User.created_at)).limit(100)
    return list(db.scalars(statement))


@router.get("/users/{user_id}", response_model=UserResponse)
def user_detail(user_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "ユーザーが見つかりません。")
    return user


@router.patch("/users/{user_id}/status", response_model=UserResponse)
def user_status(
    user_id: int,
    payload: AdminStatusUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise AppError(404, "USER_NOT_FOUND", "ユーザーが見つかりません。")
    target.status = payload.status
    audit(db, admin.id, "UPDATE_USER_STATUS", "user", target.id, {"status": payload.status})
    db.commit()
    db.refresh(target)
    return target


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def user_role(
    user_id: int,
    payload: AdminRoleUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise AppError(404, "USER_NOT_FOUND", "ユーザーが見つかりません。")
    target.role = payload.role
    audit(db, admin.id, "UPDATE_USER_ROLE", "user", target.id, {"role": payload.role})
    db.commit()
    db.refresh(target)
    return target


@router.patch("/users/{user_id}/points", response_model=UserResponse)
def adjust_points(
    user_id: int,
    payload: AdminPointsUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> User:
    target = apply_points(
        db,
        user_id,
        payload.points_change,
        "ADMIN_ADJUSTMENT",
        payload.reason,
        "admin_user",
        admin.id,
    )
    audit(
        db,
        admin.id,
        "ADJUST_POINTS",
        "user",
        user_id,
        {"points_change": payload.points_change, "reason": payload.reason},
    )
    db.commit()
    db.refresh(target)
    return target


@router.get("/orders", response_model=list[OrderResponse])
def orders(_: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> list[PaymentOrder]:
    return list(db.scalars(select(PaymentOrder).order_by(desc(PaymentOrder.created_at)).limit(100)))


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def order_status(
    order_id: int,
    payload: AdminOrderStatusUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> PaymentOrder:
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.id == order_id).with_for_update())
    if order is None:
        raise AppError(404, "ORDER_NOT_FOUND", "注文が見つかりません。")
    if payload.status == "PAID":
        if order.status == "PAID":
            raise AppError(409, "ORDER_ALREADY_PAID", "注文は既に支払い済みです。")
        apply_points(
            db,
            order.user_id,
            order.points_granted,
            "POINT_PURCHASE",
            "管理者承認によるポイント購入",
            "payment_order",
            order.id,
        )
        order.paid_at = datetime.utcnow()
    order.status = payload.status
    audit(db, admin.id, "UPDATE_ORDER_STATUS", "payment_order", order.id, {"status": payload.status})
    db.commit()
    db.refresh(order)
    return order


@router.get("/song-analyses", response_model=list[SongAnalysisResponse])
def analyses(_: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> list[SongAnalysis]:
    return list(db.scalars(select(SongAnalysis).order_by(desc(SongAnalysis.created_at)).limit(100)))


@router.get("/audit-logs")
def audit_logs(_: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> list[dict]:
    logs = db.scalars(select(AdminAuditLog).order_by(desc(AdminAuditLog.created_at)).limit(100))
    return [
        {
            "id": item.id,
            "action": item.action,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "detail": item.detail,
            "created_at": item.created_at,
        }
        for item in logs
    ]


@router.get("/settings", response_model=list[SettingResponse])
def settings(_: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> list[SystemSetting]:
    return list(db.scalars(select(SystemSetting).order_by(SystemSetting.setting_key)))


@router.patch("/settings/{setting_key}", response_model=SettingResponse)
def update_setting(
    setting_key: str,
    payload: SettingUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> SystemSetting:
    setting = db.get(SystemSetting, setting_key)
    if setting is None:
        raise AppError(404, "SETTING_NOT_FOUND", "設定項目が見つかりません。")
    setting.setting_value = payload.setting_value
    audit(db, admin.id, "UPDATE_SETTING", "system_setting", None, {"key": setting_key})
    db.commit()
    db.refresh(setting)
    return setting


@router.get("/coupons", response_model=list[AdminCouponResponse])
def coupons(_: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> list[Coupon]:
    return list(db.scalars(select(Coupon).order_by(desc(Coupon.id)).limit(100)))


@router.post("/coupons", response_model=AdminCouponResponse, status_code=201)
def create_coupon(
    payload: AdminCouponCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> Coupon:
    code = payload.code.upper()
    if db.scalar(select(Coupon.id).where(Coupon.code == code)):
        raise AppError(409, "COUPON_ALREADY_EXISTS", "クーポンコードは既に登録されています。")
    coupon = Coupon(
        code=code,
        coupon_type="POINTS",
        value=payload.value,
        expires_at=payload.expires_at,
        max_redemptions=payload.max_redemptions,
    )
    db.add(coupon)
    db.flush()
    audit(db, admin.id, "CREATE_COUPON", "coupon", coupon.id, {"code": code, "value": payload.value})
    db.commit()
    db.refresh(coupon)
    return coupon


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: int,
    payload: AdminPlanUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "プランが見つかりません。")
    for field, value in payload.model_dump().items():
        setattr(plan, field, value)
    audit(db, admin.id, "UPDATE_PLAN", "plan", plan.id, {"name": plan.name})
    db.commit()
    db.refresh(plan)
    return plan
