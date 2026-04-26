"""
conftest.py – общие фикстуры для тестов reviews-service.

ВАЖНО: DATABASE_URL подменяется на SQLite ДО импорта app.*,
иначе database.py попытается подключиться к PostgreSQL уже при загрузке.
"""

import sys
import os

# Подменяем URL базы данных ДО любых импортов из app/
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import models  # регистрация ORM-моделей в Base


@pytest.fixture
def db_session():
    """Свежая in-memory SQLite БД для каждого теста."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(db_session):
    """
    Тестовый HTTP-клиент FastAPI.
    Подменяем get_db, чтобы запросы шли в тестовую SQLite, а не в PostgreSQL.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Создаёт тестового пользователя (id=1)."""
    user = models.LibraryUser(id=1)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_book(db_session):
    """Создаёт тестовую книгу (id=1)."""
    book = models.Book(id=1, title="Война и мир", author="Лев Толстой")
    db_session.add(book)
    db_session.commit()
    return book


@pytest.fixture
def test_user_and_book(test_user, test_book):
    """Удобная комбинированная фикстура: пользователь + книга."""
    return test_user, test_book


@pytest.fixture
def existing_review(client, test_user):
    """Создаёт один отзыв через API и возвращает его JSON."""
    payload = {
        "title": "Отличная книга",
        "content": "Очень понравилось",
        "is_published": False,
        "user_id": 1,
    }
    resp = client.post("/reviews", json=payload)
    assert resp.status_code == 201
    return resp.json()
