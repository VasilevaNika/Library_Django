"""
conftest.py – общие фикстуры для тестов recomendations-service.

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
from app import models  # регистрация Book, LibraryUser, IgnoredBook, ReadingListEntry


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
    """Тестовый HTTP-клиент FastAPI с тестовой БД."""
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
    """Тестовый пользователь (id=10)."""
    user = models.LibraryUser(id=10)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_book(db_session):
    """Тестовая книга с genre_id=1 и author_id=1."""
    book = models.Book(
        id=1,
        title="Преступление и наказание",
        author="Достоевский",
        genre_id=1,
        author_id=1,
        rating=4.8,
    )
    db_session.add(book)
    db_session.commit()
    return book


@pytest.fixture
def two_books(db_session):
    """Две тестовые книги для проверки списков и сортировки."""
    book1 = models.Book(id=1, title="Книга 1", author="Автор 1", genre_id=1, author_id=1, rating=4.5)
    book2 = models.Book(id=2, title="Книга 2", author="Автор 2", genre_id=1, author_id=1, rating=4.0)
    db_session.add_all([book1, book2])
    db_session.commit()
    return [book1, book2]
