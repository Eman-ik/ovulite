import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ovulite:ovulite_dev_password@db:5432/ovulite",
)

# Fallback to local SQLite if running outside Docker and DATABASE_URL points to 'db' host
if "@db" in DATABASE_URL and not os.path.exists("/.dockerenv"):
    DATABASE_URL = "sqlite:///./ovulite_local.db"

engine_args = {
    "pool_pre_ping": True,
}

if "sqlite" in DATABASE_URL:
    # SQLite doesn't support the pool arguments used for Postgres
    engine_args["connect_args"] = {"check_same_thread": False}
else:
    engine_args.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "40")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
    })

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
    **engine_args
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
