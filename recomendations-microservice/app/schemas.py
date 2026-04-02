"""
Pydantic-схемы микросервиса рекомендаций (как в docker-practice/main.py).
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class IgnoreReason(str, Enum):
    """Причины игнорирования книги"""

    ALREADY_READ = "already_read"
    NOT_INTERESTING = "not_interesting"
    DISLIKE_AUTHOR = "dislike_author"
    OTHER = "other"


class Priority(str, Enum):
    """Приоритет книги в списке чтения"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BookRecommendation(BaseModel):
    """Модель рекомендации книги"""

    id: int
    title: str
    author: str
    author_id: Optional[int] = None
    genre_id: Optional[int] = None
    genre_name: Optional[str] = None
    year: Optional[int] = None
    cover: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None

    class Config:
        from_attributes = True


class IgnoreRequest(BaseModel):
    """Запрос на игнорирование / снятие игнора книги"""

    book_id: int = Field(..., description="ID книги")
    reason: Optional[IgnoreReason] = Field(None, description="Причина игнорирования")


class IgnoreResponse(BaseModel):
    """Ответ после добавления в игнор-лист"""

    message: str
    book_id: int


class ReadingListRequest(BaseModel):
    """Запрос на добавление / удаление из списка чтения"""

    book_id: int = Field(..., description="ID книги")
    priority: Priority = Field(Priority.MEDIUM, description="Приоритет")


class ReadingListResponse(BaseModel):
    """Ответ после добавления в список чтения"""

    message: str
    book_id: int


class MessageResponse(BaseModel):
    """Общая модель для сообщений"""

    message: str


class IgnoreItem(BaseModel):
    """Элемент игнор-листа"""

    book_id: int
    reason: Optional[IgnoreReason] = None
    book: Optional[BookRecommendation] = None


class ReadingListItem(BaseModel):
    """Элемент списка чтения"""

    book_id: int
    priority: Priority
    book: Optional[BookRecommendation] = None


class QuoteResponse(BaseModel):
    """Ответ асинхронного эндпоинта с цитатой"""

    source: str
    quote_id: int
    quote: str
    author: str
    title: str
