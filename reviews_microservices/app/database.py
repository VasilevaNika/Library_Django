from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Формируем строку подключения
def _clean_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None:
        return default
    return value.replace("\ufeff", "").replace("\xa0", "").strip()


DB_USER = _clean_env("DB_USER")
DB_PASSWORD = _clean_env("DB_PASSWORD")
DB_NAME = _clean_env("DB_NAME")
DB_HOST = "localhost"  # так как БД в контейнере на том же хосте
DB_PORT = "5432"

DATABASE_URL = URL.create(
    "postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
    query={"application_name": "reviews_microservice"},
)

# Создаём engine (двигатель) - фабрика соединений
engine = create_engine(DATABASE_URL, echo=True)  # echo=True для отладки SQL-запросов

# Создаём SessionLocal - фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()

# Зависимость для получения сессии БД в эндпоинтах
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()