"""
Модели отзывов и зеркала таблиц каталога (общая БД с recommendations-service).
"""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# --- Таблицы каталога (те же имена и столбцы, что в recommendations-service) ---


class LibraryUser(Base):
    __tablename__ = "library_users"

    id = Column(Integer, primary_key=True, index=True)
    reading_entries = relationship("ReadingListEntry", back_populates="user")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    author_id = Column(Integer, nullable=True)
    genre_id = Column(Integer, nullable=True)
    genre_name = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    cover = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    rating_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)


class ReadingListEntry(Base):
    __tablename__ = "reading_list_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("library_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id = Column(
        Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    priority = Column(String, nullable=False)

    user = relationship("LibraryUser", back_populates="reading_entries")
    book = relationship("Book")

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_reading_user_book"),
    )


# --- Отзывы ---


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    book_id = Column(Integer, nullable=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
