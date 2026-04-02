from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Notification(Base):
    """Уведомление читателя онлайн-библиотеки."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(String(32), nullable=False)
    title = Column(String(512), nullable=False)
    message = Column(String(4096), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    priority = Column(String(16), nullable=False, server_default="medium")
    channel = Column(String(32), nullable=False)
    # JSON: book_id, book_title, event_id, event_name, fine_amount, due_date (ISO string)
    related_data = Column(JSON, nullable=True)
