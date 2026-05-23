from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import DailyLoginReward, User
from app.schemas.api import LoginRequest, TokenResponse, UserCreate
from app.services.points import apply_points


settings = get_settings()


def register_user(db: Session, payload: UserCreate) -> User:
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
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, payload: LoginRequest) -> TokenResponse:
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
        db.commit()
    except IntegrityError:
        db.rollback()
        user = db.scalar(select(User).where(User.email == payload.email.lower()))
        daily_bonus = 0
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=user,
        daily_bonus_awarded=daily_bonus,
    )
