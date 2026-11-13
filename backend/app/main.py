from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text

from app.api import admin, ai, attachments, auth, batch, inspirations, leases, recycle, sales, sync, transfer, work_logs
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Device, InviteCode


def seed_bootstrap_admin_invite() -> None:
    """空库首次启动创建管理员邀请码；已有管理员后不再自动补发。"""
    with SessionLocal() as db:
        admin_count = db.scalar(select(func.count()).where(Device.role_level == 1, Device.status == 1)) or 0
        if admin_count:
            return
        invite = db.scalar(select(InviteCode).where(InviteCode.invite_code == settings.bootstrap_invite_code))
        if invite is None:
            now = datetime.now()
            invite = InviteCode(
                invite_code=settings.bootstrap_invite_code,
                valid_start=now,
                valid_end=now + timedelta(days=3650),
                max_use_count=10,
                used_count=0,
                role_level=1,
                status=1,
                creator_id="0" * 32,
            )
            db.add(invite)
            db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 本地 SQLite 开发自动建表；生产 MySQL 由 database/init.sql 初始化。
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    seed_bootstrap_admin_invite()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="上海商办租赁/买卖经纪团队内部信息资产库 MVP",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# 上传目录必须存在后再挂载，否则容器首次启动会直接失败。
upload_root = Path(settings.upload_dir)
upload_root.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_root), name="uploads")

for router in [
    auth.router,
    batch.router,
    sales.router,
    leases.router,
    work_logs.router,
    inspirations.router,
    attachments.router,
    ai.router,
    sync.router,
    transfer.router,
    recycle.router,
    admin.router,
]:
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }


@app.get(f"{settings.api_prefix}/health")
def health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "unreachable"})
    return {
        "status": "ok",
        "database": "ok",
        "redis": "optional",
        "server_time": datetime.now().isoformat(timespec="seconds"),
    }
