from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Базовая модель с общими полями
class ReviewBase(BaseModel):
    title: str
    content: Optional[str] = None
    is_published: bool = False


# Модель для создания (без id и служебных полей)
class ReviewCreate(ReviewBase):
    user_id: int = Field(..., ge=1, description="ID пользователя (автор отзыва)")
    book_id: Optional[int] = Field(None, ge=1, description="ID книги в каталоге рекомендаций")

# Модель для обновления (все поля опциональны)
class ReviewUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_published: Optional[bool] = None

# Модель для ответа (со всеми полями)
class ReviewResponse(ReviewBase):
    id: int
    user_id: int
    book_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True  # позволяет создавать Pydantic-модель из ORM-объекта