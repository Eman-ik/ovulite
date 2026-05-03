import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ovulite:ovulite_dev_password@db:5432/ovulite",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "40")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
    echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a database session and closes after use."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
