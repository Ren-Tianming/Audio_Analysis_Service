from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token, hash_api_key
from app.models import ApiKey, User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError(401, "UNAUTHORIZED", "ログインが必要です。")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise AppError(401, "INVALID_TOKEN", "認証トークンが無効です。") from None
    user = db.get(User, user_id)
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "ユーザーが存在しません。")
    if user.status != "ACTIVE":
        raise AppError(403, "ACCOUNT_DISABLED", "アカウントは停止されています。")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise AppError(403, "FORBIDDEN", "管理者権限が必要です。")
    return user


def get_api_or_current_user(
    api_key_value: str | None = Header(default=None, alias="X-API-Key"),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if api_key_value:
        key = db.scalar(
            select(ApiKey).where(
                ApiKey.key_hash == hash_api_key(api_key_value),
                ApiKey.status == "ACTIVE",
            )
        )
        if key is None:
            raise AppError(401, "INVALID_API_KEY", "APIキーが無効です。")
        user = db.get(User, key.user_id)
        if user is None or user.status != "ACTIVE":
            raise AppError(403, "ACCOUNT_DISABLED", "アカウントは利用できません。")
        return user
    return get_current_user(credentials, db)
