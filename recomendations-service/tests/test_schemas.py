"""
Unit-тесты для Pydantic-схем recomendations-service.

Проверяем валидацию в изоляции — без БД и HTTP.
"""

import pytest
from pydantic import ValidationError

from app.schemas import (
    BookRecommendation,
    IgnoreRequest,
    IgnoreResponse,
    IgnoreReason,
    IgnoreItem,
    ReadingListRequest,
    ReadingListResponse,
    ReadingListItem,
    Priority,
    MessageResponse,
    QuoteResponse,
)


# ── Enum-классы ───────────────────────────────────────────────────────────────

class TestEnums:

    def test_ignore_reason_values(self):
        """Все причины игнорирования присутствуют."""
        assert IgnoreReason.ALREADY_READ == "already_read"
        assert IgnoreReason.NOT_INTERESTING == "not_interesting"
        assert IgnoreReason.DISLIKE_AUTHOR == "dislike_author"
        assert IgnoreReason.OTHER == "other"

    def test_priority_values(self):
        """Все приоритеты списка чтения присутствуют."""
        assert Priority.HIGH == "high"
        assert Priority.MEDIUM == "medium"
        assert Priority.LOW == "low"


# ── BookRecommendation ────────────────────────────────────────────────────────

class TestBookRecommendation:

    def test_valid_minimal(self):
        """Минимальная книга: только обязательные поля."""
        book = BookRecommendation(id=1, title="Мастер и Маргарита", author="Булгаков")
        assert book.id == 1
        assert book.title == "Мастер и Маргарита"
        assert book.author == "Булгаков"
        assert book.genre_id is None
        assert book.rating is None

    def test_valid_full(self):
        """Полное описание книги."""
        book = BookRecommendation(
            id=7,
            title="1984",
            author="Оруэлл",
            author_id=3,
            genre_id=2,
            genre_name="Антиутопия",
            year=1949,
            rating=4.9,
            rating_count=50000,
        )
        assert book.year == 1949
        assert book.rating == 4.9
        assert book.genre_name == "Антиутопия"

    def test_missing_id_raises_error(self):
        """id обязателен."""
        with pytest.raises(ValidationError):
            BookRecommendation(title="Книга", author="Автор")

    def test_missing_title_raises_error(self):
        """title обязателен."""
        with pytest.raises(ValidationError):
            BookRecommendation(id=1, author="Автор")

    def test_missing_author_raises_error(self):
        """author обязателен."""
        with pytest.raises(ValidationError):
            BookRecommendation(id=1, title="Книга")

    def test_optional_fields_default_to_none(self):
        """Все необязательные поля по умолчанию None."""
        book = BookRecommendation(id=1, title="Книга", author="Автор")
        assert book.genre_id is None
        assert book.genre_name is None
        assert book.year is None
        assert book.cover is None
        assert book.rating is None
        assert book.rating_count is None
        assert book.created_at is None


# ── IgnoreRequest ─────────────────────────────────────────────────────────────

class TestIgnoreRequest:

    def test_valid_with_reason(self):
        """Запрос на игнор с указанием причины."""
        req = IgnoreRequest(book_id=5, reason=IgnoreReason.ALREADY_READ)
        assert req.book_id == 5
        assert req.reason == IgnoreReason.ALREADY_READ

    def test_valid_without_reason(self):
        """Причина игнора необязательна."""
        req = IgnoreRequest(book_id=3)
        assert req.book_id == 3
        assert req.reason is None

    def test_missing_book_id_raises_error(self):
        """book_id обязателен."""
        with pytest.raises(ValidationError):
            IgnoreRequest()

    def test_invalid_reason_raises_error(self):
        """Недопустимая причина вызывает ошибку."""
        with pytest.raises(ValidationError):
            IgnoreRequest(book_id=1, reason="hate_it")


# ── IgnoreResponse ────────────────────────────────────────────────────────────

class TestIgnoreResponse:

    def test_valid(self):
        resp = IgnoreResponse(message="Книга игнорирована", book_id=10)
        assert resp.book_id == 10
        assert "игнорирована" in resp.message


# ── IgnoreItem ────────────────────────────────────────────────────────────────

class TestIgnoreItem:

    def test_minimal(self):
        """IgnoreItem только с book_id."""
        item = IgnoreItem(book_id=5)
        assert item.book_id == 5
        assert item.reason is None
        assert item.book is None

    def test_with_reason_and_book(self):
        """IgnoreItem с reason и данными книги."""
        book = BookRecommendation(id=5, title="Тест", author="Автор")
        item = IgnoreItem(book_id=5, reason=IgnoreReason.OTHER, book=book)
        assert item.reason == IgnoreReason.OTHER
        assert item.book.title == "Тест"


# ── ReadingListRequest ────────────────────────────────────────────────────────

class TestReadingListRequest:

    def test_valid_with_default_priority(self):
        """Приоритет по умолчанию — medium."""
        req = ReadingListRequest(book_id=1)
        assert req.book_id == 1
        assert req.priority == Priority.MEDIUM

    def test_valid_high_priority(self):
        req = ReadingListRequest(book_id=2, priority=Priority.HIGH)
        assert req.priority == Priority.HIGH

    def test_missing_book_id_raises_error(self):
        with pytest.raises(ValidationError):
            ReadingListRequest()

    def test_invalid_priority_raises_error(self):
        with pytest.raises(ValidationError):
            ReadingListRequest(book_id=1, priority="very_high")


# ── ReadingListResponse ───────────────────────────────────────────────────────

class TestReadingListResponse:

    def test_valid(self):
        resp = ReadingListResponse(message="Добавлено", book_id=3)
        assert resp.book_id == 3


# ── ReadingListItem ───────────────────────────────────────────────────────────

class TestReadingListItem:

    def test_minimal(self):
        item = ReadingListItem(book_id=1, priority=Priority.LOW)
        assert item.priority == Priority.LOW
        assert item.book is None

    def test_with_book(self):
        book = BookRecommendation(id=1, title="Книга", author="Автор")
        item = ReadingListItem(book_id=1, priority=Priority.HIGH, book=book)
        assert item.book.author == "Автор"


# ── MessageResponse ───────────────────────────────────────────────────────────

class TestMessageResponse:

    def test_valid(self):
        r = MessageResponse(message="Операция выполнена")
        assert r.message == "Операция выполнена"


# ── QuoteResponse ─────────────────────────────────────────────────────────────

class TestQuoteResponse:

    def test_valid(self):
        q = QuoteResponse(
            source="jsonplaceholder",
            quote_id=42,
            quote="Читайте книги",
            author="Demo Author",
            title="Заголовок цитаты",
        )
        assert q.quote_id == 42
        assert q.source == "jsonplaceholder"

    def test_missing_field_raises_error(self):
        with pytest.raises(ValidationError):
            QuoteResponse(source="test", quote_id=1, quote="Текст")
