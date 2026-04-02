"""
Опциональные функции доступа к БД для уведомлений.
Основная логика сейчас в app.main.
"""

from sqlalchemy.orm import Session

from app import models


def get_notification(db: Session, notification_id: int):
    return db.get(models.Notification, notification_id)
