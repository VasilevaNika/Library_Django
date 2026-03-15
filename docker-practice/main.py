"""
Модуль заглушки для микросервиса уведомлений онлайн-библиотеки.
Демонстрирует базовую структуру FastAPI-приложения с CRUD операциями для уведомлений.
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

# Создаём экземпляр приложения FastAPI
app = FastAPI(
    title="API уведомлений онлайн-библиотеки",
    description="API для управления уведомлениями читателей онлайн-библиотеки",
    version="1.0.0"
)

# ----- Перечисления (Enums) для полей с фиксированными значениями -----

class NotificationType(str, Enum):
    DUE_DATE = "due_date"
    NEW_BOOK = "new_book"
    EVENT = "event"
    FINE = "fine"
    SYSTEM = "system"

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


# ----- Модели данных Pydantic -----

class RelatedData(BaseModel):
    """Дополнительные данные уведомления"""
    book_id: Optional[int] = None
    book_title: Optional[str] = None
    event_id: Optional[int] = None
    event_name: Optional[str] = None
    fine_amount: Optional[float] = None
    due_date: Optional[date] = None

class Notification(BaseModel):
    """Полная модель уведомления (используется для ответов)"""
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

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

class NotificationCreate(BaseModel):
    """Модель для создания уведомления (используется для запросов)"""
    user_id: int
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channel: NotificationChannel = NotificationChannel.IN_APP
    related_data: Optional[RelatedData] = None


# ----- "База данных" в памяти (для заглушки) -----

# Генерируем тестовые данные
def generate_test_notifications():
    notifications = {}
    
    # Текущее время для создания уведомлений
    now = datetime.now()
    
    # Уведомление 1: просрочка возврата книги (не прочитано)
    notifications[1] = Notification(
        id=1,
        user_id=789,
        type=NotificationType.DUE_DATE,
        title="Верните книгу",
        message="Книгу 'Война и мир' необходимо вернуть до 25.03.2024",
        created_at=now,
        read_at=None,
        priority=NotificationPriority.HIGH,
        channel=NotificationChannel.EMAIL,
        related_data=RelatedData(
            book_id=42,
            book_title="Война и мир",
            due_date=date(2024, 3, 25)
        )
    )
    
    # Уведомление 2: новое поступление (прочитано)
    notifications[2] = Notification(
        id=2,
        user_id=789,
        type=NotificationType.NEW_BOOK,
        title="Новое поступление",
        message="В библиотеку поступила книга 'Мастер и Маргарита'",
        created_at=now,
        read_at=now,
        priority=NotificationPriority.MEDIUM,
        channel=NotificationChannel.PUSH,
        related_data=RelatedData(
            book_id=43,
            book_title="Мастер и Маргарита"
        )
    )
    
    # Уведомление 3: мероприятие (не прочитано)
    notifications[3] = Notification(
        id=3,
        user_id=789,
        type=NotificationType.EVENT,
        title="Лекция о Толстом",
        message="Приглашаем на лекцию о творчестве Льва Толстого 30 марта",
        created_at=now,
        read_at=None,
        priority=NotificationPriority.LOW,
        channel=NotificationChannel.IN_APP,
        related_data=RelatedData(
            event_id=15,
            event_name="Лекция о Толстом"
        )
    )
    
    # Уведомление 4: штраф (не прочитано)
    notifications[4] = Notification(
        id=4,
        user_id=790,
        type=NotificationType.FINE,
        title="Штраф за просрочку",
        message="Начислен штраф за просрочку возврата книги в размере 100.50 руб.",
        created_at=now,
        read_at=None,
        priority=NotificationPriority.URGENT,
        channel=NotificationChannel.SMS,
        related_data=RelatedData(
            book_id=44,
            book_title="Преступление и наказание",
            fine_amount=100.50,
            due_date=date(2024, 3, 20)
        )
    )
    
    # Уведомление 5: системное (прочитано)
    notifications[5] = Notification(
        id=5,
        user_id=791,
        type=NotificationType.SYSTEM,
        title="Обновление системы",
        message="Библиотека обновила правила пользования",
        created_at=now,
        read_at=now,
        priority=NotificationPriority.MEDIUM,
        channel=NotificationChannel.EMAIL,
        related_data=None
    )
    
    return notifications

# Словарь с уведомлениями
notifications_db = generate_test_notifications()

# Счётчик для следующего ID
next_id = max(notifications_db.keys()) + 1 if notifications_db else 1


# ----- Вспомогательные функции -----

def filter_notifications(
    user_id: Optional[int] = None,
    status: NotificationStatus = NotificationStatus.ALL,
    notification_type: Optional[NotificationType] = None
) -> List[Notification]:
    """Фильтрация уведомлений по различным критериям"""
    filtered = list(notifications_db.values())
    
    # Фильтр по пользователю (для демо используем фиксированный user_id=789)
    if user_id:
        filtered = [n for n in filtered if n.user_id == user_id]
    
    # Фильтр по статусу прочтения
    if status == NotificationStatus.READ:
        filtered = [n for n in filtered if n.read_at is not None]
    elif status == NotificationStatus.UNREAD:
        filtered = [n for n in filtered if n.read_at is None]
    
    # Фильтр по типу
    if notification_type:
        filtered = [n for n in filtered if n.type == notification_type]
    
    return filtered


# ----- Эндпоинты API -----

@app.get("/")
def root():
    """Корневой эндпоинт для проверки работоспособности"""
    return {
        "message": "API уведомлений онлайн-библиотеки V2",
        "status": "running",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/notifications")
def get_notifications(
    status: NotificationStatus = Query(NotificationStatus.ALL, description="Фильтр по статусу прочтения"),
    type: Optional[NotificationType] = Query(None, description="Фильтр по типу уведомления"),
    limit: int = Query(20, ge=1, le=100, description="Количество уведомлений на странице"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации")
):
    """
    Получить уведомления для текущего пользователя.
    Возвращает список уведомлений с пагинацией.
    """
    # В демо-версии используем фиксированного пользователя
    current_user_id = 789
    
    # Получаем все уведомления пользователя с фильтрацией
    user_notifications = filter_notifications(
        user_id=current_user_id,
        status=status,
        notification_type=type
    )
    
    # Сортируем по дате создания (новые сначала)
    user_notifications.sort(key=lambda x: x.created_at, reverse=True)
    
    # Общее количество до пагинации
    total = len(user_notifications)
    
    # Количество непрочитанных
    unread_count = len([n for n in user_notifications if n.read_at is None])
    
    # Применяем пагинацию
    paginated_items = user_notifications[offset:offset + limit]
    
    return {
        "total": total,
        "unread_count": unread_count,
        "items": paginated_items
    }


@app.post("/notifications", response_model=Notification, status_code=201)
def create_notification(notification: NotificationCreate):
    """
    Отправить новое уведомление.
    Создаёт уведомление для указанного пользователя.
    """
    global next_id
    
    # Проверяем существование пользователя (для демо всегда успешно)
    # В реальном API здесь был бы запрос к сервису пользователей
    
    # Создаём новое уведомление
    new_notification = Notification(
        id=next_id,
        created_at=datetime.now(),
        read_at=None,
        **notification.dict()
    )
    
    # Сохраняем в "базу данных"
    notifications_db[next_id] = new_notification
    
    # Увеличиваем счётчик
    next_id += 1
    
    return new_notification


@app.get("/notifications/{notification_id}", response_model=Notification)
def get_notification(notification_id: int):
    """
    Получить конкретное уведомление по ID.
    """
    if notification_id not in notifications_db:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Уведомление не найдено",
                "code": 404
            }
        )
    
    return notifications_db[notification_id]


@app.patch("/notifications/{notification_id}/read", response_model=Notification)
def mark_notification_as_read(notification_id: int):
    """
    Отметить уведомление как прочитанное.
    """
    if notification_id not in notifications_db:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Уведомление не найдено",
                "code": 404
            }
        )
    
    notification = notifications_db[notification_id]
    
    # Если уже прочитано, просто возвращаем
    if notification.read_at is not None:
        return notification
    
    # Отмечаем как прочитанное
    notification.read_at = datetime.now()
    notifications_db[notification_id] = notification
    
    return notification


@app.delete("/notifications/{notification_id}", status_code=204)
def delete_notification(notification_id: int):
    """
    Удалить уведомление.
    """
    if notification_id not in notifications_db:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Уведомление не найдено",
                "code": 404
            }
        )
    
    del notifications_db[notification_id]
    return None  # status_code 204 не возвращает тело ответа


@app.post("/notifications/read-all")
def mark_all_as_read():
    """
    Отметить все уведомления пользователя как прочитанные.
    """
    # В демо-версии используем фиксированного пользователя
    current_user_id = 789
    
    updated_count = 0
    
    for notification in notifications_db.values():
        if notification.user_id == current_user_id and notification.read_at is None:
            notification.read_at = datetime.now()
            updated_count += 1
    
    return {
        "message": "Все уведомления отмечены как прочитанные",
        "updated_count": updated_count
    }


@app.get("/notifications/statistics")
def get_statistics(
    from_date: Optional[date] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Конец периода (YYYY-MM-DD)")
):
    """
    Получить статистику по уведомлениям за период.
    """
    # Если даты не указаны, берём последние 30 дней
    if not to_date:
        to_date = date.today()
    if not from_date:
        from_date = date(to_date.year, to_date.month, 1)  # первое число месяца
    
    # Фильтруем уведомления по дате
    filtered_notifications = []
    for notification in notifications_db.values():
        notification_date = notification.created_at.date()
        if from_date <= notification_date <= to_date:
            filtered_notifications.append(notification)
    
    total = len(filtered_notifications)
    
    if total == 0:
        return {
            "period": {"from": from_date, "to": to_date},
            "total_sent": 0,
            "by_type": {},
            "by_channel": {},
            "read_rate": 0,
            "by_priority": {}
        }
    
    # Статистика по типам
    by_type = {}
    for notification in filtered_notifications:
        by_type[notification.type.value] = by_type.get(notification.type.value, 0) + 1
    
    # Статистика по каналам
    by_channel = {}
    for notification in filtered_notifications:
        by_channel[notification.channel.value] = by_channel.get(notification.channel.value, 0) + 1
    
    # Статистика по приоритетам
    by_priority = {}
    for notification in filtered_notifications:
        by_priority[notification.priority.value] = by_priority.get(notification.priority.value, 0) + 1
    
    # Процент прочитанных
    read_count = len([n for n in filtered_notifications if n.read_at is not None])
    read_rate = (read_count / total) * 100
    
    return {
        "period": {"from": from_date, "to": to_date},
        "total_sent": total,
        "by_type": by_type,
        "by_channel": by_channel,
        "read_rate": round(read_rate, 1),
        "average_response_time": "2.5 hours",  # Заглушка
        "by_priority": by_priority
    }


# ----- Обработчики ошибок -----

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Кастомный обработчик для соответствия спецификации"""
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={
                "error": str(exc.detail) if isinstance(exc.detail, str) else exc.detail.get("error", "Ресурс не найден"),
                "code": 404
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail), "code": exc.status_code}
    )