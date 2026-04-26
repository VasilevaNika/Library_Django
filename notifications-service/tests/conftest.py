"""
conftest.py – общие фикстуры для тестов notifications-service.

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
from app import models  # регистрация ORM-модели Notification


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
    """Тестовый HTTP-клиент с подменой зависимости get_db."""
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
def notification_payload():
    """Корректные данные для создания уведомления."""
    return {
        "user_id": 42,
        "type": "new_book",
        "title": "Новая книга в библиотеке",
        "message": "Добавлена книга «Мастер и Маргарита»",
        "priority": "medium",
        "channel": "in_app",
    }


@pytest.fixture
def existing_notification(client, notification_payload):
    """Создаёт уведомление через API и возвращает его JSON."""
    resp = client.post("/notifications", json=notification_payload)
    assert resp.status_code == 201
    return resp.json()
