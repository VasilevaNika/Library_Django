import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


def _clean_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None:
        return default
    return value.replace("\ufeff", "").replace("\xa0", "").strip()


def _resolve_database_url() -> str:
    """Та же БД, что у монолита: DATABASE_URL / MAIN_DATABASE_URL, иначе сборка из DB_*."""
    for key in ("DATABASE_URL", "MAIN_DATABASE_URL"):
        raw = os.getenv(key)
        if raw and raw.strip():
            u = raw.strip().replace("\ufeff", "").replace("\xa0", "").strip()
            if u.startswith("postgres://"):
                u = "postgresql://" + u[len("postgres://") :]
            return u
    return (
        f"postgresql://{_clean_env('DB_USER')}:{_clean_env('DB_PASSWORD')}"
        f"@{_clean_env('DB_HOST', 'localhost')}:{_clean_env('DB_PORT', '5432')}"
        f"/{_clean_env('DB_NAME', 'library')}"
    )


DATABASE_URL = _resolve_database_url()

engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"application_name": "reviews_microservice"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
