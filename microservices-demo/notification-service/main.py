"""
Notification Service — заглушка для уведомлений.
Получает уведомления от других сервисов и "отправляет" их (пишет в лог).
"""

from fastapi import FastAPI
from pydantic import BaseModel
import logging

# Настраиваем логирование, чтобы видеть уведомления
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Service", description="Отправка уведомлений")

class Notification(BaseModel):
    user_id: int
    message: str
    type: str  # например: "welcome", "new_post", "post_deleted"

@app.get("/")
def root():
    return {
        "service": "notification-service",
        "status": "running"
    }

@app.post("/notify")
def send_notification(notification: Notification):
    """
    Получить уведомление и "отправить" его.
    В реальном проекте здесь была бы отправка email/push.
    В заглушке просто пишем в лог.
    """
    logger.info(f"NOTIFICATION: user={notification.user_id}, type={notification.type}, message={notification.message}")
    return {
        "status": "sent",
        "notification": notification
    }
