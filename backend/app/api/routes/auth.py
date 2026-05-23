from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.api import LoginRequest, Message, PasswordChange, TokenResponse, UserCreate, UserResponse
from app.services.auth import login_user, register_user


router = APIRouter(prefix="/auth", tags=["認証"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    user = register_user(db, payload)
    return TokenResponse(access_token=create_access_token(user.id, user.role), user=user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return login_user(db, payload)


@router.post("/logout", response_model=Message)
def logout(_: User = Depends(get_current_user)) -> Message:
    return Message(message="ログアウトしました。クライアント側のトークンを破棄してください。")


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
