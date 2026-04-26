"""
Unit-тесты для Pydantic-схем reviews-service.

Проверяем валидацию данных в изоляции — без базы данных и сервера.
Каждый тест проверяет одно конкретное правило модели.
"""

import pytest
from pydantic import ValidationError

from app.schemas import ReviewCreate, ReviewUpdate, ReviewResponse


# ── ReviewCreate ──────────────────────────────────────────────────────────────

class TestReviewCreate:

    def test_valid_minimal(self):
        """Минимальный корректный отзыв: только обязательные поля."""
        review = ReviewCreate(title="Хорошая книга", user_id=1)

        assert review.title == "Хорошая книга"
        assert review.user_id == 1
        assert review.content is None        # необязательное поле → None по умолчанию
        assert review.is_published is False  # значение по умолчанию
        assert review.book_id is None        # необязательное поле

    def test_valid_full(self):
        """Все поля заполнены корректно."""
        review = ReviewCreate(
            title="Шедевр",
            content="Детальный разбор произведения",
            is_published=True,
            user_id=5,
            book_id=10,
        )

        assert review.title == "Шедевр"
        assert review.content == "Детальный разбор произведения"
        assert review.is_published is True
        assert review.user_id == 5
        assert review.book_id == 10

    def test_missing_title_raises_error(self):
        """Поле title обязательно — без него должна быть ошибка валидации."""
        with pytest.raises(ValidationError) as exc_info:
            ReviewCreate(user_id=1)

        errors = exc_info.value.errors()
        fields_with_errors = [e["loc"][0] for e in errors]
        assert "title" in fields_with_errors

    def test_missing_user_id_raises_error(self):
        """Поле user_id обязательно."""
        with pytest.raises(ValidationError) as exc_info:
            ReviewCreate(title="Без автора")

        errors = exc_info.value.errors()
        fields_with_errors = [e["loc"][0] for e in errors]
        assert "user_id" in fields_with_errors

    def test_user_id_must_be_positive(self):
        """user_id должен быть >= 1 (Field ge=1)."""
        with pytest.raises(ValidationError):
            ReviewCreate(title="Тест", user_id=0)

    def test_user_id_negative_raises_error(self):
        """Отрицательный user_id недопустим."""
        with pytest.raises(ValidationError):
            ReviewCreate(title="Тест", user_id=-5)

    def test_book_id_must_be_positive_if_given(self):
        """book_id >= 1 если передан (Field ge=1)."""
        with pytest.raises(ValidationError):
            ReviewCreate(title="Тест", user_id=1, book_id=0)

    def test_book_id_can_be_none(self):
        """book_id — необязательное поле, None допустим."""
        review = ReviewCreate(title="Без книги", user_id=1, book_id=None)
        assert review.book_id is None

    def test_is_published_defaults_to_false(self):
        """is_published по умолчанию False."""
        review = ReviewCreate(title="Тест", user_id=1)
        assert review.is_published is False

    def test_is_published_can_be_true(self):
        """is_published=True принимается корректно."""
        review = ReviewCreate(title="Тест", user_id=1, is_published=True)
        assert review.is_published is True


# ── ReviewUpdate ──────────────────────────────────────────────────────────────

class TestReviewUpdate:

    def test_empty_update_is_valid(self):
        """ReviewUpdate без полей — валидный объект (частичное обновление)."""
        update = ReviewUpdate()

        assert update.title is None
        assert update.content is None
        assert update.is_published is None

    def test_update_only_title(self):
        """Можно обновить только title."""
        update = ReviewUpdate(title="Новое название")

        assert update.title == "Новое название"
        assert update.content is None
        assert update.is_published is None

    def test_update_only_published(self):
        """Можно изменить только статус публикации."""
        update = ReviewUpdate(is_published=True)

        assert update.is_published is True
        assert update.title is None
        assert update.content is None

    def test_update_all_fields(self):
        """Можно обновить все поля сразу."""
        update = ReviewUpdate(
            title="Обновлённый заголовок",
            content="Новый текст",
            is_published=True,
        )

        assert update.title == "Обновлённый заголовок"
        assert update.content == "Новый текст"
        assert update.is_published is True

    def test_update_content_to_none(self):
        """Можно явно передать None (сброс значения)."""
        update = ReviewUpdate(content=None)
        assert update.content is None


# ── ReviewResponse ────────────────────────────────────────────────────────────

class TestReviewResponse:

    def test_valid_response(self):
        """ReviewResponse принимает полный набор полей."""
        from datetime import datetime

        response = ReviewResponse(
            id=1,
            title="Тестовый отзыв",
            content="Содержание",
            is_published=True,
            user_id=2,
            book_id=3,
            created_at=datetime.now(),
        )

        assert response.id == 1
        assert response.title == "Тестовый отзыв"
        assert response.user_id == 2
        assert response.book_id == 3

    def test_response_book_id_optional(self):
        """book_id в ответе необязателен."""
        from datetime import datetime

        response = ReviewResponse(
            id=1,
            title="Без книги",
            is_published=False,
            user_id=1,
            created_at=datetime.now(),
        )

        assert response.book_id is None
