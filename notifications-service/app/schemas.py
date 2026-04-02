from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class NotificationType(str, Enum):
    DUE_DATE = "due_date"
    NEW_BOOK = "new_book"
    EVENT = "event"
    FINE = "fine"
    SYSTEM = "system"
    REVIEW = "review"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"


class NotificationStatus(str, Enum):
    ALL = "all"
    UNREAD = "unread"
    READ = "read"


class RelatedData(BaseModel):
    book_id: Optional[int] = None
    book_title: Optional[str] = None
    event_id: Optional[int] = None
    event_name: Optional[str] = None
    fine_amount: Optional[float] = None
    due_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationCreate(BaseModel):
    user_id: int
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channel: NotificationChannel = NotificationChannel.IN_APP
    related_data: Optional[RelatedData] = None


class NotificationFromExternalCreate(BaseModel):
    """
    Данные для создания уведомления на основе ответа публичного API.

    Endpoint сам сделает HTTP-запрос (например JSONPlaceholder) и извлечет title/body.
    """

    user_id: int
    external_post_id: int
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channel: NotificationChannel = NotificationChannel.IN_APP
    related_data: Optional[RelatedData] = None


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: NotificationType
    title: str
    message: str
    created_at: datetime
    read_at: Optional[datetime] = None
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channel: NotificationChannel
    related_data: Optional[RelatedData] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    items: List[NotificationResponse]


class MarkAllReadResponse(BaseModel):
    message: str
    updated_count: int


class StatisticsResponse(BaseModel):
    period: Dict[str, Any]
    total_sent: int
    by_type: Dict[str, int]
    by_channel: Dict[str, int]
    read_rate: float
    average_response_time: Optional[str] = None
    by_priority: Dict[str, int]
