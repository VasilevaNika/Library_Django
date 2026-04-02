from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class LibraryUser(Base):
    """Пользователь библиотеки (ID совпадает с внешней системой)."""

    __tablename__ = "library_users"

    id = Column(Integer, primary_key=True, index=True)

    ignored_books = relationship("IgnoredBook", back_populates="user", cascade="all, delete-orphan")
    reading_entries = relationship("ReadingListEntry", back_populates="user", cascade="all, delete-orphan")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    author_id = Column(Integer, nullable=True, index=True)
    genre_id = Column(Integer, nullable=True, index=True)
    genre_name = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    cover = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    rating_count = Column(Integer, nullable=True)


class IgnoredBook(Base):
    __tablename__ = "ignored_books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("library_users.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String, nullable=True)

    user = relationship("LibraryUser", back_populates="ignored_books")
    book = relationship("Book")

    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uq_ignored_user_book"),)


class ReadingListEntry(Base):
    __tablename__ = "reading_list_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("library_users.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    priority = Column(String, nullable=False)

    user = relationship("LibraryUser", back_populates="reading_entries")
    book = relationship("Book")

    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uq_reading_user_book"),)
