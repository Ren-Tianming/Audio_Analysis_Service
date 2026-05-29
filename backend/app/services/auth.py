from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import DailyLoginReward, RefreshToken, User
from app.schemas.api import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services.points import apply_points

settings = get_settings()


def _utcnow() -> datetime:
    return datetime.utcnow()


def _refresh_expiry() -> datetime:
    return _utcnow() + timedelta(days=settings.refresh_token_expire_days)


def issue_refresh_token(
    db: Session,
    user: User,
    user_agent: str | None,
    ip_address: str | None,
    family_id: str | None = None,
) -> tuple[str, RefreshToken]:
    plain_token = generate_refresh_token()
    model = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(plain_token),
        family_id=family_id or str(uuid4()),
        expires_at=_refresh_expiry(),
        user_agent=user_agent[:255] if user_agent else None,
        ip_address=ip_address[:64] if ip_address else None,
    )
    db.add(model)
    db.flush()
    return plain_token, model


def token_response(
    db: Session,
    user: User,
    daily_bonus_awarded: int,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenResponse:
    refresh_token, _ = issue_refresh_token(db, user, user_agent, ip_address)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
        daily_bonus_awarded=daily_bonus_awarded,
    )


def register_user(
    db: Session,
    payload: UserCreate,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenResponse:
    if payload.password != payload.password_confirmation:
        raise AppError(422, "PASSWORD_CONFIRMATION_MISMATCH", "パスワード確認が一致しません。")
    if db.scalar(select(User.id).where(User.email == payload.email.lower())):
        raise AppError(409, "EMAIL_ALREADY_EXISTS", "メールアドレスは既に登録されています。")
    user = User(
        email=payload.email.lower(),
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    apply_points(
        db,
        user.id,
        settings.registration_bonus,
        "REGISTER_BONUS",
        "新規登録ボーナス",
    )
    response = token_response(db, user, 0, user_agent, ip_address)
    db.commit()
    db.refresh(user)
    return TokenResponse(
        access_token=response.access_token,
        refresh_token=response.refresh_token,
        user=UserResponse.model_validate(user),
        daily_bonus_awarded=0,
    )


def login_user(
    db: Session,
    payload: LoginRequest,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AppError(401, "INVALID_CREDENTIALS", "メールアドレスまたはパスワードが不正です。")
    if user.status != "ACTIVE":
        raise AppError(403, "ACCOUNT_DISABLED", "アカウントは停止されています。")

    today = datetime.now(settings.tokyo_tz).date()
    daily_bonus = 0
    if not db.scalar(
        select(DailyLoginReward.id).where(
            DailyLoginReward.user_id == user.id,
            DailyLoginReward.reward_date == today,
        )
    ):
        db.add(
            DailyLoginReward(
                user_id=user.id,
                reward_date=today,
                points_awarded=settings.daily_login_bonus,
            )
        )
        apply_points(
            db,
            user.id,
            settings.daily_login_bonus,
            "DAILY_LOGIN_BONUS",
            "デイリーログインボーナス",
        )
        daily_bonus = settings.daily_login_bonus
    user.last_login_at = datetime.now(settings.tokyo_tz).replace(tzinfo=None)
    try:
        response = token_response(db, user, daily_bonus, user_agent, ip_address)
        db.commit()
        db.refresh(user)
        return TokenResponse(
            access_token=response.access_token,
            refresh_token=response.refresh_token,
            user=UserResponse.model_validate(user),
            daily_bonus_awarded=daily_bonus,
        )
    except IntegrityError:
        db.rollback()
        user = db.scalar(select(User).where(User.email == payload.email.lower()))
        if user is None:
            raise AppError(401, "INVALID_CREDENTIALS", "メールアドレスまたはパスワードが不正です。") from None
        daily_bonus = 0
        response = token_response(db, user, daily_bonus, user_agent, ip_address)
        db.commit()
        db.refresh(user)
        return TokenResponse(
            access_token=response.access_token,
            refresh_token=response.refresh_token,
            user=UserResponse.model_validate(user),
        )


def revoke_refresh_family(db: Session, user_id: int, family_id: str) -> None:
    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=_utcnow())
    )


def rotate_refresh_token(
    db: Session,
    refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenResponse:
    now = _utcnow()
    model = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(refresh_token)).with_for_update()
    )
    if model is None:
        raise AppError(401, "INVALID_REFRESH_TOKEN", "リフレッシュトークンが無効です。")
    if model.revoked_at is not None:
        revoke_refresh_family(db, model.user_id, model.family_id)
        db.commit()
        raise AppError(401, "REFRESH_TOKEN_REUSED", "リフレッシュトークンは既に失効しています。")
    if model.expires_at <= now:
        model.revoked_at = now
        db.commit()
        raise AppError(401, "REFRESH_TOKEN_EXPIRED", "リフレッシュトークンの有効期限が切れています。")

    user = db.scalar(select(User).where(User.id == model.user_id).with_for_update())
    if user is None or user.status != "ACTIVE":
        model.revoked_at = now
        db.commit()
        raise AppError(403, "ACCOUNT_DISABLED", "アカウントは利用できません。")

    model.revoked_at = now
    next_plain, next_model = issue_refresh_token(db, user, user_agent, ip_address, family_id=model.family_id)
    model.replaced_by_id = next_model.id
    db.commit()
    db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=next_plain,
        user=UserResponse.model_validate(user),
    )


def revoke_refresh_token(db: Session, user_id: int, refresh_token: str) -> None:
    model = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(refresh_token)).with_for_update()
    )
    if model is not None and model.user_id == user_id and model.revoked_at is None:
        model.revoked_at = _utcnow()
    db.commit()


def revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_utcnow())
    )
    db.commit()
