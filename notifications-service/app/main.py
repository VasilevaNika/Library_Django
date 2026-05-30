"""
Микросервис уведомлений онлайн-библиотеки (FastAPI + PostgreSQL).
"""

import json
import logging
import time
from datetime import date, datetime, timezone
from typing import List, Optional

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app import models, schemas
from app.database import get_db
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY

# ---------------------------------------------------------------------------
# Структурированное логирование (JSON)
# ---------------------------------------------------------------------------

_LOG_RESERVED = {
    'args', 'created', 'exc_info', 'exc_text', 'filename', 'funcName',
    'levelname', 'levelno', 'lineno', 'message', 'module', 'msecs', 'msg',
    'name', 'pathname', 'process', 'processName', 'relativeCreated',
    'stack_info', 'thread', 'threadName', 'taskName',
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _LOG_RESERVED and not key.startswith('_'):
                log_entry[key] = value
        return json.dumps(log_entry, ensure_ascii=False, default=str)


_handler = logging.StreamHandler()
_handler.setFormatter(JSONFormatter())
logging.root.handlers = [_handler]
logging.root.setLevel(logging.INFO)

logger = logging.getLogger("notifications-service")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

DEMO_USER_ID = 789

app = FastAPI(
    title="API уведомлений онлайн-библиотеки",
    description="API для управления уведомлениями читателей онлайн-библиотеки",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Middleware: сбор метрик Prometheus
# ---------------------------------------------------------------------------

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        return response


app.add_middleware(MetricsMiddleware)


# ---------------------------------------------------------------------------
# Эндпоинт для Prometheus
# ---------------------------------------------------------------------------

@app.get("/metrics", include_in_schema=False)
async def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Тестовые эндпоинты для проверки observability
# ---------------------------------------------------------------------------

@app.get("/test/error", tags=["test"])
async def test_error():
    """Тестовый эндпоинт — всегда возвращает 500 (для проверки error rate)."""
    logger.error("test_error endpoint called", extra={"test": True})
    raise HTTPException(status_code=500, detail="Тестовая ошибка")


@app.get("/test/slow", tags=["test"])
def test_slow():
    """Тестовый эндпоинт — отвечает 2 секунды (для проверки latency)."""
    logger.info("test_slow endpoint called — sleeping 2s", extra={"test": True})
    time.sleep(2)
    return {"status": "ok", "message": "Медленный ответ после 2 секунд"}


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def log_notification_created(
    *,
    user_id: int,
    notification_id: int,
    notification_type: str,
    channel: str,
):
    logger.info(
        "notification_created",
        extra={
            "user_id": user_id,
            "notification_id": notification_id,
            "notification_type": notification_type,
            "channel": channel,
        },
    )


def _notification_to_response(n: models.Notification) -> schemas.NotificationResponse:
    payload = {
        "id": n.id,
        "user_id": n.user_id,
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "created_at": n.created_at,
        "read_at": n.read_at,
        "priority": n.priority,
        "channel": n.channel,
        "related_data": n.related_data,
    }
    return schemas.NotificationResponse.model_validate(payload)


def _filter_notifications(
    db: Session,
    *,
    user_id: Optional[int] = None,
    status: schemas.NotificationStatus = schemas.NotificationStatus.ALL,
    notification_type: Optional[schemas.NotificationType] = None,
) -> List[models.Notification]:
    q = db.query(models.Notification)
    if user_id is not None:
        q = q.filter(models.Notification.user_id == user_id)
    if status == schemas.NotificationStatus.READ:
        q = q.filter(models.Notification.read_at.isnot(None))
    elif status == schemas.NotificationStatus.UNREAD:
        q = q.filter(models.Notification.read_at.is_(None))
    if notification_type is not None:
        q = q.filter(models.Notification.type == notification_type.value)
    return q.all()


# ---------------------------------------------------------------------------
# Обработчик ошибок
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    if exc.status_code == 404:
        detail = exc.detail
        if isinstance(detail, dict):
            err = detail.get("error", "Ресурс не найден")
        else:
            err = str(detail)
        return JSONResponse(
            status_code=404,
            content={"error": err, "code": 404},
        )
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": detail.get("error", str(detail)), "code": exc.status_code},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(detail), "code": exc.status_code},
    )


# ---------------------------------------------------------------------------
# Эндпоинты API
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    logger.info("health check")
    return {
        "message": "API уведомлений онлайн-библиотеки V2",
        "status": "running with PostgreSQL",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/notifications/statistics", response_model=schemas.StatisticsResponse)
def get_statistics(
    db: Session = Depends(get_db),
    from_date: Optional[date] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Конец периода (YYYY-MM-DD)"),
):
    logger.info("get_statistics", extra={"from_date": str(from_date), "to_date": str(to_date)})
    if not to_date:
        to_date = date.today()
    if not from_date:
        from_date = date(to_date.year, to_date.month, 1)

    all_rows = db.query(models.Notification).all()
    filtered: List[models.Notification] = []
    for n in all_rows:
        nd = n.created_at.date() if n.created_at else None
        if nd is not None and from_date <= nd <= to_date:
            filtered.append(n)

    total = len(filtered)
    if total == 0:
        return schemas.StatisticsResponse(
            period={"from": from_date, "to": to_date},
            total_sent=0,
            by_type={},
            by_channel={},
            read_rate=0,
            average_response_time=None,
            by_priority={},
        )

    by_type: dict[str, int] = {}
    by_channel: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for n in filtered:
        by_type[n.type] = by_type.get(n.type, 0) + 1
        by_channel[n.channel] = by_channel.get(n.channel, 0) + 1
        by_priority[n.priority] = by_priority.get(n.priority, 0) + 1

    read_count = sum(1 for n in filtered if n.read_at is not None)
    read_rate = (read_count / total) * 100

    return schemas.StatisticsResponse(
        period={"from": from_date, "to": to_date},
        total_sent=total,
        by_type=by_type,
        by_channel=by_channel,
        read_rate=round(read_rate, 1),
        average_response_time="2.5 hours",
        by_priority=by_priority,
    )


@app.get("/notifications", response_model=schemas.NotificationListResponse)
def get_notifications(
    db: Session = Depends(get_db),
    user_id: Optional[int] = Query(
        None,
        description=(
            "Только уведомления этого пользователя. "
            "Не передавать — вернуться все пользователи. "
            f"Для демо как в заглушке: {DEMO_USER_ID}"
        ),
    ),
    status: schemas.NotificationStatus = Query(
        schemas.NotificationStatus.ALL,
        description="Фильтр по статусу прочтения",
    ),
    type: Optional[schemas.NotificationType] = Query(
        None,
        description="Фильтр по типу уведомления",
    ),
    limit: int = Query(20, ge=1, le=100, description="Количество на странице"),
    offset: int = Query(0, ge=0, description="Смещение"),
):
    logger.info("get_notifications", extra={"user_id": user_id, "status": str(status), "limit": limit})
    user_notifications = _filter_notifications(
        db,
        user_id=user_id,
        status=status,
        notification_type=type,
    )
    user_notifications.sort(
        key=lambda x: x.created_at.timestamp() if x.created_at else 0.0,
        reverse=True,
    )
    total = len(user_notifications)
    unread_count = sum(1 for n in user_notifications if n.read_at is None)
    page = user_notifications[offset : offset + limit]
    return schemas.NotificationListResponse(
        total=total,
        unread_count=unread_count,
        items=[_notification_to_response(n) for n in page],
    )


@app.post("/notifications/read-all", response_model=schemas.MarkAllReadResponse)
def mark_all_as_read(db: Session = Depends(get_db)):
    logger.info("mark_all_as_read", extra={"user_id": DEMO_USER_ID})
    now = datetime.now(timezone.utc)
    rows = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == DEMO_USER_ID,
            models.Notification.read_at.is_(None),
        )
        .all()
    )
    updated_count = 0
    for n in rows:
        n.read_at = now
        updated_count += 1
    db.commit()
    return schemas.MarkAllReadResponse(
        message="Все уведомления отмечены как прочитанные",
        updated_count=updated_count,
    )


@app.post("/notifications", response_model=schemas.NotificationResponse, status_code=201)
def create_notification(
    notification: schemas.NotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    data = notification.model_dump(mode="json")
    related_data = data.pop("related_data", None)
    db_n = models.Notification(**data, related_data=related_data, read_at=None)
    db.add(db_n)
    db.commit()
    db.refresh(db_n)
    logger.info(
        "notification_created",
        extra={
            "notification_id": db_n.id,
            "user_id": db_n.user_id,
            "notification_type": str(db_n.type),
            "channel": str(db_n.channel),
        },
    )
    background_tasks.add_task(
        log_notification_created,
        user_id=db_n.user_id,
        notification_id=db_n.id,
        notification_type=str(db_n.type),
        channel=str(db_n.channel),
    )
    return _notification_to_response(db_n)


@app.get(
    "/notifications/from-external",
    response_model=schemas.NotificationResponse,
    status_code=201,
)
async def create_notification_from_external(
    user_id: int = Query(..., ge=1, description="Пользователь, для которого создаётся уведомление"),
    external_post_id: int = Query(..., ge=1, description="ID поста в JSONPlaceholder"),
    type: schemas.NotificationType = Query(..., description="Тип уведомления"),
    priority: schemas.NotificationPriority = Query(
        schemas.NotificationPriority.MEDIUM, description="Приоритет уведомления"
    ),
    channel: schemas.NotificationChannel = Query(
        schemas.NotificationChannel.IN_APP, description="Канал уведомления"
    ),
    db: Session = Depends(get_db),
):
    logger.info(
        "create_notification_from_external",
        extra={"user_id": user_id, "external_post_id": external_post_id},
    )
    url = f"https://jsonplaceholder.typicode.com/posts/{external_post_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        external_data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("external_api_error", extra={"url": url, "status": e.response.status_code})
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Внешний API вернул ошибку",
                "code": 502,
                "external_status": e.response.status_code,
            },
        )
    except (httpx.RequestError, ValueError):
        logger.error("external_api_request_error", extra={"url": url})
        raise HTTPException(
            status_code=502,
            detail={"error": "Ошибка запроса к внешнему API", "code": 502},
        )

    if not isinstance(external_data, dict) or not external_data:
        raise HTTPException(
            status_code=404,
            detail={"error": "Внешний элемент не найден", "code": 404, "external_post_id": external_post_id},
        )

    title = external_data.get("title") or "External item"
    message = external_data.get("body") or ""
    if not message:
        raise HTTPException(
            status_code=404,
            detail={"error": "Внешний элемент не содержит body", "code": 404, "external_post_id": external_post_id},
        )

    db_n = models.Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        priority=priority,
        channel=channel,
        related_data=None,
        read_at=None,
    )
    db.add(db_n)
    db.commit()
    db.refresh(db_n)
    return _notification_to_response(db_n)


@app.get("/notifications/{notification_id}", response_model=schemas.NotificationResponse)
def get_notification(notification_id: int, db: Session = Depends(get_db)):
    logger.info("get_notification", extra={"notification_id": notification_id})
    n = db.get(models.Notification, notification_id)
    if not n:
        raise HTTPException(
            status_code=404,
            detail={"error": "Уведомление не найдено", "code": 404},
        )
    return _notification_to_response(n)


@app.patch("/notifications/{notification_id}/read", response_model=schemas.NotificationResponse)
def mark_notification_as_read(notification_id: int, db: Session = Depends(get_db)):
    logger.info("mark_notification_as_read", extra={"notification_id": notification_id})
    n = db.get(models.Notification, notification_id)
    if not n:
        raise HTTPException(
            status_code=404,
            detail={"error": "Уведомление не найдено", "code": 404},
        )
    if n.read_at is not None:
        return _notification_to_response(n)
    n.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(n)
    return _notification_to_response(n)


@app.delete("/notifications/{notification_id}", status_code=204)
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    logger.info("delete_notification", extra={"notification_id": notification_id})
    n = db.get(models.Notification, notification_id)
    if not n:
        raise HTTPException(
            status_code=404,
            detail={"error": "Уведомление не найдено", "code": 404},
        )
    db.delete(n)
    db.commit()
    return Response(status_code=204)
