"""
Микросервис рекомендаций библиотеки.
"""

import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path as FilePath
from typing import List, Optional

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Path, Query, Request, Response
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

logger = logging.getLogger("recommendations-service")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Микросервис рекомендаций библиотеки",
    description="API для получения рекомендаций книг и управления персональными настройками",
    version="3.0.0",
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

def _log_user_action(action: str, user_id: int, payload: dict) -> None:
    logs_dir = FilePath("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "actions.jsonl"
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "payload": payload,
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info(action, extra={"user_id": user_id, "payload": payload})


def _book_to_rec(book: models.Book) -> schemas.BookRecommendation:
    return schemas.BookRecommendation.model_validate(book)


def _parse_ignore_reason(value: Optional[str]) -> Optional[schemas.IgnoreReason]:
    if value is None:
        return None
    try:
        return schemas.IgnoreReason(value)
    except ValueError:
        return schemas.IgnoreReason.OTHER


def _get_user_or_404(db: Session, user_id: int) -> models.LibraryUser:
    user = db.get(models.LibraryUser, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь с указанным ID не существует",
        )
    return user


def _get_book_or_404(db: Session, book_id: int) -> models.Book:
    book = db.get(models.Book, book_id)
    if not book:
        raise HTTPException(
            status_code=404,
            detail="Книга с указанным ID не существует",
        )
    return book


# ---------------------------------------------------------------------------
# Эндпоинты API
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """Корневой эндпоинт для проверки работоспособности"""
    logger.info("health check")
    return {
        "message": "Микросервис рекомендаций библиотеки",
        "status": "работает",
        "docs": "/docs",
        "data": "PostgreSQL",
    }


@app.get(
    "/recommendations/popular",
    response_model=List[schemas.BookRecommendation],
    summary="Популярные книги",
    description="Возвращает список самых популярных книг",
)
def get_popular_books(
    limit: int = Query(10, ge=1, le=50, description="Количество книг"),
    db: Session = Depends(get_db),
):
    logger.info("get_popular_books", extra={"limit": limit})
    q = (
        db.query(models.Book)
        .order_by(models.Book.rating.desc().nulls_last(), models.Book.id)
        .limit(limit)
    )
    return [_book_to_rec(b) for b in q.all()]


@app.get(
    "/recommendations/new",
    response_model=List[schemas.BookRecommendation],
    summary="Новинки",
    description="Возвращает недавно добавленные книги",
)
def get_new_books(
    limit: int = Query(10, ge=1, description="Количество книг"),
    db: Session = Depends(get_db),
):
    logger.info("get_new_books", extra={"limit": limit})
    q = (
        db.query(models.Book)
        .order_by(
            models.Book.created_at.desc().nulls_last(),
            models.Book.id.desc(),
        )
        .limit(limit)
    )
    return [_book_to_rec(b) for b in q.all()]


@app.get(
    "/recommendations/genre/{genreId}",
    response_model=List[schemas.BookRecommendation],
    summary="Популярное в жанре",
    description="Возвращает самые популярные книги в указанном жанре",
)
def get_popular_books_by_genre(
    genreId: int = Path(..., description="ID жанра"),
    limit: int = Query(10, ge=1, description="Количество книг"),
    min_rating: float = Query(4.0, ge=0, le=5, description="Минимальный рейтинг"),
    db: Session = Depends(get_db),
):
    logger.info("get_popular_books_by_genre", extra={"genre_id": genreId, "limit": limit})
    if genreId > 5:
        raise HTTPException(status_code=404, detail="Жанр с указанным ID не существует")
    q = (
        db.query(models.Book)
        .filter(models.Book.genre_id == genreId)
        .filter(models.Book.rating >= min_rating)
        .order_by(models.Book.rating.desc().nulls_last(), models.Book.id)
        .limit(limit)
    )
    rows = q.all()
    if not rows:
        return []
    return [_book_to_rec(b) for b in rows]


@app.get(
    "/recommendations/author/{authorId}",
    response_model=List[schemas.BookRecommendation],
    summary="Популярное у автора",
    description="Возвращает самые популярные книги указанного автора",
)
def get_popular_books_by_author(
    authorId: int = Path(..., description="ID автора"),
    limit: int = Query(5, ge=1, description="Количество книг"),
    db: Session = Depends(get_db),
):
    logger.info("get_popular_books_by_author", extra={"author_id": authorId, "limit": limit})
    if authorId > 10:
        raise HTTPException(status_code=404, detail="Автор с указанным ID не найден")
    q = (
        db.query(models.Book)
        .filter(models.Book.author_id == authorId)
        .order_by(models.Book.rating.desc().nulls_last(), models.Book.id)
        .limit(limit)
    )
    rows = q.all()
    if not rows:
        return []
    return [_book_to_rec(b) for b in rows]


@app.get(
    "/recommendations/similar/{bookId}",
    response_model=List[schemas.BookRecommendation],
    summary="Похожие книги",
    description="Возвращает книги, похожие на указанную",
)
def get_similar_books(
    bookId: int = Path(..., description="ID книги"),
    limit: int = Query(5, ge=1, description="Количество книг"),
    db: Session = Depends(get_db),
):
    logger.info("get_similar_books", extra={"book_id": bookId, "limit": limit})
    base = db.get(models.Book, bookId)
    if not base:
        raise HTTPException(status_code=404, detail="Книга с указанным ID не существует")
    q = (
        db.query(models.Book)
        .filter(models.Book.id != bookId)
        .order_by(models.Book.rating.desc().nulls_last(), models.Book.id)
        .limit(limit)
    )
    return [_book_to_rec(b) for b in q.all()]


@app.get(
    "/recommendations/random",
    response_model=schemas.BookRecommendation,
    summary="Случайная книга",
    description="Возвращает одну случайную книгу",
)
def get_random_book(
    genre_id: Optional[int] = Query(None, description="Ограничить жанром"),
    db: Session = Depends(get_db),
):
    logger.info("get_random_book", extra={"genre_id": genre_id})
    q = db.query(models.Book)
    if genre_id is not None:
        q = q.filter(models.Book.genre_id == genre_id)
    books = q.all()
    if not books:
        raise HTTPException(status_code=404, detail="Нет книг для выдачи")
    return _book_to_rec(random.choice(books))


@app.get(
    "/recommendations/quotes",
    response_model=schemas.QuoteResponse,
    summary="Цитата для чтения",
    description="Получает случайную цитату из публичного API через httpx",
    responses={
        200: {
            "description": "Успешно получена цитата",
            "content": {
                "application/json": {
                    "example": {
                        "source": "jsonplaceholder",
                        "quote_id": 16,
                        "quote": "suscipit nam nisi quo aperiam aut...",
                        "author": "Demo Author",
                        "title": "sint suscipit perspiciatis velit dolorum...",
                    }
                }
            },
        },
        502: {
            "description": "Ошибка внешнего API",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Не удалось получить цитату из внешнего API"
                    }
                }
            },
        },
    },
)
async def get_reading_quote():
    quote_id = random.randint(1, 100)
    url = f"https://jsonplaceholder.typicode.com/posts/{quote_id}"
    logger.info("get_reading_quote", extra={"quote_id": quote_id})
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            "source": "jsonplaceholder",
            "quote_id": data["id"],
            "quote": data["body"],
            "author": "Demo Author",
            "title": data["title"],
        }
    except httpx.HTTPError:
        logger.error("external_api_error", extra={"url": url})
        raise HTTPException(
            status_code=502,
            detail="Не удалось получить цитату из внешнего API",
        )


@app.get(
    "/user/{userId}/ignore",
    response_model=List[schemas.IgnoreItem],
    summary="Список игнорируемых книг",
    description="Возвращает список книг, которые пользователь игнорирует",
)
def get_ignore_list(
    userId: int = Path(..., description="ID пользователя"),
    include_book_details: bool = Query(True, description="Включить полную информацию о книгах"),
    db: Session = Depends(get_db),
):
    logger.info("get_ignore_list", extra={"user_id": userId})
    _get_user_or_404(db, userId)
    rows = (
        db.query(models.IgnoredBook)
        .filter(models.IgnoredBook.user_id == userId)
        .all()
    )
    out: List[schemas.IgnoreItem] = []
    for row in rows:
        book = _book_to_rec(row.book) if include_book_details and row.book else None
        out.append(
            schemas.IgnoreItem(
                book_id=row.book_id,
                reason=_parse_ignore_reason(row.reason),
                book=book,
            )
        )
    return out


@app.post(
    "/user/{userId}/ignore",
    response_model=schemas.IgnoreResponse,
    status_code=201,
    summary="Игнорировать книгу",
    description="Добавляет книгу в список игнорируемых",
)
def add_to_ignore_list(
    userId: int = Path(..., description="ID пользователя"),
    request: schemas.IgnoreRequest = ...,
    background_tasks: BackgroundTasks = ...,
    db: Session = Depends(get_db),
):
    _get_user_or_404(db, userId)
    _get_book_or_404(db, request.book_id)
    reason_val = request.reason.value if request.reason else None
    existing = (
        db.query(models.IgnoredBook)
        .filter_by(user_id=userId, book_id=request.book_id)
        .first()
    )
    if existing:
        existing.reason = reason_val
    else:
        db.add(
            models.IgnoredBook(
                user_id=userId,
                book_id=request.book_id,
                reason=reason_val,
            )
        )
    db.commit()
    background_tasks.add_task(
        _log_user_action,
        "add_to_ignore_list",
        userId,
        {
            "book_id": request.book_id,
            "reason": reason_val,
            "result": "created_or_updated",
        },
    )
    return schemas.IgnoreResponse(
        message="Книга больше не будет вам рекомендоваться",
        book_id=request.book_id,
    )


@app.delete(
    "/user/{userId}/ignore",
    response_model=schemas.MessageResponse,
    summary="Перестать игнорировать",
    description="Удаляет книгу из списка игнорируемых",
)
def remove_from_ignore_list(
    userId: int = Path(..., description="ID пользователя"),
    request: schemas.IgnoreRequest = ...,
    db: Session = Depends(get_db),
):
    _get_user_or_404(db, userId)
    db.query(models.IgnoredBook).filter_by(
        user_id=userId, book_id=request.book_id
    ).delete()
    db.commit()
    return schemas.MessageResponse(message="Книга снова может вам рекомендоваться")


@app.get(
    "/user/{userId}/reading-list",
    response_model=List[schemas.ReadingListItem],
    summary="Список чтения",
    description="Возвращает список книг, которые пользователь планирует прочитать",
)
def get_reading_list(
    userId: int = Path(..., description="ID пользователя"),
    include_book_details: bool = Query(True, description="Включить полную информацию о книгах"),
    db: Session = Depends(get_db),
):
    logger.info("get_reading_list", extra={"user_id": userId})
    _get_user_or_404(db, userId)
    rows = (
        db.query(models.ReadingListEntry)
        .filter(models.ReadingListEntry.user_id == userId)
        .all()
    )
    out: List[schemas.ReadingListItem] = []
    for row in rows:
        try:
            pr = schemas.Priority(row.priority)
        except ValueError:
            pr = schemas.Priority.MEDIUM
        book = _book_to_rec(row.book) if include_book_details and row.book else None
        out.append(
            schemas.ReadingListItem(book_id=row.book_id, priority=pr, book=book)
        )
    return out


@app.post(
    "/user/{userId}/reading-list",
    response_model=schemas.ReadingListResponse,
    status_code=201,
    summary="Добавить в список чтения",
    description="Сохраняет книгу в персональный список 'прочитать позже'",
)
def add_to_reading_list(
    userId: int = Path(..., description="ID пользователя"),
    request: schemas.ReadingListRequest = ...,
    background_tasks: BackgroundTasks = ...,
    db: Session = Depends(get_db),
):
    _get_user_or_404(db, userId)
    _get_book_or_404(db, request.book_id)
    priority_val = request.priority.value
    existing = (
        db.query(models.ReadingListEntry)
        .filter_by(user_id=userId, book_id=request.book_id)
        .first()
    )
    if existing:
        existing.priority = priority_val
    else:
        db.add(
            models.ReadingListEntry(
                user_id=userId,
                book_id=request.book_id,
                priority=priority_val,
            )
        )
    db.commit()
    background_tasks.add_task(
        _log_user_action,
        "add_to_reading_list",
        userId,
        {
            "book_id": request.book_id,
            "priority": priority_val,
            "result": "created_or_updated",
        },
    )
    return schemas.ReadingListResponse(
        message="Книга сохранена в список 'прочитать позже'",
        book_id=request.book_id,
    )


@app.delete(
    "/user/{userId}/reading-list",
    response_model=schemas.MessageResponse,
    summary="Удалить из списка чтения",
    description="Убирает книгу из списка 'прочитать позже'",
)
def remove_from_reading_list(
    userId: int = Path(..., description="ID пользователя"),
    request: schemas.ReadingListRequest = ...,
    db: Session = Depends(get_db),
):
    _get_user_or_404(db, userId)
    db.query(models.ReadingListEntry).filter_by(
        user_id=userId, book_id=request.book_id
    ).delete()
    db.commit()
    return schemas.MessageResponse(message="Книга удалена из списка чтения")
