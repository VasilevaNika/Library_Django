from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),
    )

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, nullable=False, index=True)
    author = Column(String(100), nullable=False)
    rating = Column(Integer, nullable=False)
    text = Column(Text, nullable=True)
    is_published = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

