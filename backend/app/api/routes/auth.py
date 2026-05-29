from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.api import (
    LoginRequest,
    Message,
    PasswordChange,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.auth import (
    login_user,
    register_user,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["認証"])


def client_metadata(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    return user_agent, ip_address


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user_agent, ip_address = client_metadata(request)
    return register_user(db, payload, user_agent, ip_address)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user_agent, ip_address = client_metadata(request)
    return login_user(db, payload, user_agent, ip_address)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user_agent, ip_address = client_metadata(request)
    return rotate_refresh_token(db, payload.refresh_token, user_agent, ip_address)


@router.post("/logout", response_model=Message)
def logout(
    payload: RefreshRequest | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    if payload is not None:
        revoke_refresh_token(db, user.id, payload.refresh_token)
    return Message(message="ログアウトしました。クライアント側のトークンを破棄してください。")


@router.post("/logout-all", response_model=Message)
def logout_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Message:
    revoke_all_refresh_tokens(db, user.id)
    return Message(message="すべての端末のセッションをログアウトしました。")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/password", response_model=Message)
def change_password(
    payload: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    if not verify_password(payload.current_password, user.hashed_password):
        raise AppError(401, "INVALID_CREDENTIALS", "現在のパスワードが不正です。")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return Message(message="パスワードを更新しました。")
