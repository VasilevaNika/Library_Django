"""
Unit-тесты для Pydantic-схем notifications-service.

Тестируем валидацию данных в изоляции: без БД, без HTTP-сервера.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas import (
    NotificationCreate,
    NotificationResponse,
    NotificationListResponse,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    NotificationStatus,
    RelatedData,
    MarkAllReadResponse,
    StatisticsResponse,
)


# ── Enum-классы ───────────────────────────────────────────────────────────────

class TestEnums:

    def test_notification_types_exist(self):
        """Все нужные типы уведомлений присутствуют в enum."""
        assert NotificationType.DUE_DATE == "due_date"
        assert NotificationType.NEW_BOOK == "new_book"
        assert NotificationType.EVENT == "event"
        assert NotificationType.FINE == "fine"
        assert NotificationType.SYSTEM == "system"
        assert NotificationType.REVIEW == "review"

    def test_notification_priorities_exist(self):
        """Все приоритеты присутствуют."""
        assert NotificationPriority.LOW == "low"
        assert NotificationPriority.MEDIUM == "medium"
        assert NotificationPriority.HIGH == "high"
        assert NotificationPriority.URGENT == "urgent"

    def test_notification_channels_exist(self):
        """Все каналы доставки присутствуют."""
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.PUSH == "push"
        assert NotificationChannel.SMS == "sms"
        assert NotificationChannel.IN_APP == "in_app"

    def test_notification_status_values(self):
        """Статусы для фильтрации присутствуют."""
        assert NotificationStatus.ALL == "all"
        assert NotificationStatus.UNREAD == "unread"
        assert NotificationStatus.READ == "read"


# ── NotificationCreate ────────────────────────────────────────────────────────

class TestNotificationCreate:

    def test_valid_minimal(self):
        """Минимально необходимые поля."""
        n = NotificationCreate(
            user_id=1,
            type=NotificationType.NEW_BOOK,
            title="Новинка",
            message="Появилась новая книга",
        )
        assert n.user_id == 1
        assert n.type == NotificationType.NEW_BOOK
        assert n.priority == NotificationPriority.MEDIUM   # значение по умолчанию
        assert n.channel == NotificationChannel.IN_APP     # значение по умолчанию
        assert n.related_data is None

    def test_valid_full(self):
        """Все поля переданы явно."""
        n = NotificationCreate(
            user_id=99,
            type=NotificationType.FINE,
            title="Штраф",
            message="У вас задолженность",
            priority=NotificationPriority.URGENT,
            channel=NotificationChannel.EMAIL,
        )
        assert n.priority == NotificationPriority.URGENT
        assert n.channel == NotificationChannel.EMAIL

    def test_missing_user_id_raises_error(self):
        """user_id обязателен."""
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(
                type="new_book",
                title="Тест",
                message="Сообщение",
            )
        fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert "user_id" in fields

    def test_missing_type_raises_error(self):
        """type обязателен."""
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(user_id=1, title="Тест", message="Сообщение")
        fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert "type" in fields

    def test_missing_title_raises_error(self):
        """title обязателен."""
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(user_id=1, type="new_book", message="Сообщение")
        fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert "title" in fields

    def test_missing_message_raises_error(self):
        """message обязателен."""
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(user_id=1, type="new_book", title="Заголовок")
        fields = [e["loc"][0] for e in exc_info.value.errors()]
        assert "message" in fields

    def test_invalid_type_raises_error(self):
        """Недопустимое значение type вызывает ошибку."""
        with pytest.raises(ValidationError):
            NotificationCreate(
                user_id=1,
                type="unknown_type",
                title="Тест",
                message="Сообщение",
            )

    def test_invalid_priority_raises_error(self):
        """Недопустимое значение priority вызывает ошибку."""
        with pytest.raises(ValidationError):
            NotificationCreate(
                user_id=1,
                type="new_book",
                title="Тест",
                message="Сообщение",
                priority="super_urgent",
            )

    def test_invalid_channel_raises_error(self):
        """Недопустимое значение channel вызывает ошибку."""
        with pytest.raises(ValidationError):
            NotificationCreate(
                user_id=1,
                type="new_book",
                title="Тест",
                message="Сообщение",
                channel="telegram",
            )


# ── RelatedData ───────────────────────────────────────────────────────────────

class TestRelatedData:

    def test_empty_related_data(self):
        """RelatedData может быть полностью пустым."""
        rd = RelatedData()
        assert rd.book_id is None
        assert rd.book_title is None
        assert rd.event_id is None
        assert rd.fine_amount is None
        assert rd.due_date is None

    def test_with_book_data(self):
        """RelatedData с данными книги."""
        rd = RelatedData(book_id=5, book_title="Анна Каренина")
        assert rd.book_id == 5
        assert rd.book_title == "Анна Каренина"

    def test_with_fine_data(self):
        """RelatedData с суммой штрафа."""
        rd = RelatedData(fine_amount=150.0)
        assert rd.fine_amount == 150.0


# ── NotificationResponse ──────────────────────────────────────────────────────

class TestNotificationResponse:

    def test_valid_response(self):
        """NotificationResponse принимает все обязательные поля."""
        now = datetime.now()
        r = NotificationResponse(
            id=1,
            user_id=42,
            type=NotificationType.NEW_BOOK,
            title="Заголовок",
            message="Текст",
            created_at=now,
            priority=NotificationPriority.MEDIUM,
            channel=NotificationChannel.IN_APP,
        )
        assert r.id == 1
        assert r.read_at is None          # по умолчанию не прочитано
        assert r.related_data is None

    def test_read_at_optional(self):
        """read_at опционален."""
        now = datetime.now()
        r = NotificationResponse(
            id=2,
            user_id=1,
            type="system",
            title="Тест",
            message="Текст",
            created_at=now,
            channel="in_app",
        )
        assert r.read_at is None


# ── MarkAllReadResponse ───────────────────────────────────────────────────────

class TestMarkAllReadResponse:

    def test_valid(self):
        r = MarkAllReadResponse(message="Все прочитаны", updated_count=5)
        assert r.message == "Все прочитаны"
        assert r.updated_count == 5
