from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False, class_=Session)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        # Loại bỏ query param ?pgbouncer=true của Prisma vì psycopg2 không nhận diện
        if "?pgbouncer=true" in url:
            url = url.replace("?pgbouncer=true", "")
        elif "&pgbouncer=true" in url:
            url = url.replace("&pgbouncer=true", "")
        _engine = create_engine(url, pool_pre_ping=True)
        SessionLocal.configure(bind=_engine)
    return _engine


def get_db() -> Generator[Session, None, None]:
    get_engine()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
