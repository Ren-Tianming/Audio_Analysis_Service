from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, commercial, songs, users
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.errors import AppError, app_error_handler
from app.services.bootstrap import seed_master_data


settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("rythm_music_analys")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        logger.info("開発用テーブルとマスターデータを初期化しました。")
    with SessionLocal() as db:
        seed_master_data(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.3.0",
    description="音源解析 SaaS の商用化雛形 API",
    lifespan=lifespan,
)
app.add_exception_handler(AppError, app_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(songs.router, prefix=settings.api_prefix)
app.include_router(commercial.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": "1.3.0"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "RyThM_Music_Analys API", "docs": "/docs", "health": "/health"}
