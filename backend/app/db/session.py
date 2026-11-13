from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


# SQLite 仅用于自动化测试；生产默认通过 DATABASE_URL 指向 MySQL 8。
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """每个 HTTP 请求独立使用数据库会话，结束后可靠关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
