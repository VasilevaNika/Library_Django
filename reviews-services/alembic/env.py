from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL
from alembic import context
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project path for imports
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv(Path(__file__).parent.parent / ".env")


def _clean_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None:
        return default
    return value.replace("\ufeff", "").replace("\xa0", "").strip()

from app.database import Base
from app.models import Book, LibraryUser, ReadingListEntry, Review  # noqa: F401

config = context.config

# Build database URL from environment (общая БД с recommendations; отдельная таблица версий Alembic)
_db_host = _clean_env("DB_HOST", "localhost")
_db_port = int(_clean_env("DB_PORT", "5432"))
DATABASE_URL = URL.create(
    "postgresql+psycopg2",
    username=_clean_env("DB_USER"),
    password=_clean_env("DB_PASSWORD"),
    host=_db_host,
    port=_db_port,
    database=_clean_env("DB_NAME"),
    query={"application_name": "reviews_microservice_alembic"},
)
config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.render_as_string(hide_password=False),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="alembic_version_reviews",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version_reviews",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
