from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReviewBase(BaseModel):
    book_id: int = Field(..., ge=1, description="ID книги, на которую отзыв")
    author: str = Field(..., min_length=1, max_length=100)
    rating: int = Field(..., ge=1, le=5, description="Оценка от 1 до 5")
    text: Optional[str] = None
    is_published: bool = True


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    rating: Optional[int] = Field(None, ge=1, le=5)
    text: Optional[str] = None
    is_published: Optional[bool] = None


class ReviewResponse(ReviewBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

