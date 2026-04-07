from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

from dotenv import load_dotenv

load_dotenv()


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
        f"postgresql://{os.getenv('DB_USER', '')}:{os.getenv('DB_PASSWORD', '')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME', 'library')}"
    )


DATABASE_URL = _resolve_database_url()

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
