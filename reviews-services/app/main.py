import logging
import os
import time
from typing import List, Optional

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

logger = logging.getLogger("reviews-service")

NOTIFICATIONS_SERVICE_URL = os.getenv(
    "NOTIFICATIONS_SERVICE_URL", "http://localhost:8003"
).rstrip("/")

app = FastAPI(
    title="Reviews Microservice",
    description=(
        "Отзывы; общая БД с каталогом (проверка пользователя и книги в БД). "
        "После отзыва о книге книга попадает в список чтения; уведомление через notifications-service."
    ),
)


def write_log(message: str) -> None:
    """Фоновая задача записи простого лога в файл."""
    time.sleep(0.5)
    with open("app.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


def notify_reading_list_updated(
    *,
    user_id: int,
    book_id: int,
    book_title: str,
    review_title: str,
) -> None:
    """Уведомление: книга добавлена в список чтения после отзыва."""
    url = f"{NOTIFICATIONS_SERVICE_URL}/notifications"
    payload = {
        "user_id": user_id,
        "type": "event",
        "title": "Книга в списке чтения",
        "message": (
            f"«{book_title}» добавлена в ваш список чтения после отзыва «{review_title}»."
        ),
        "priority": "medium",
        "channel": "in_app",
        "related_data": {"book_id": book_id, "book_title": book_title},
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
    except Exception as e:
        logger.warning("notifications-service недоступен: %s", e)


@app.get("/")
def root():
    return {
        "message": "Reviews Microservice",
        "docs": "/docs",
        "status": "running with PostgreSQL (общая БД с recommendations)",
    }


@app.get("/reviews", response_model=List[schemas.ReviewResponse])
def read_reviews(db: Session = Depends(get_db)):
    """Получить список всех отзывов."""
    return db.query(models.Review).all()


@app.get("/reviews/{review_id}", response_model=schemas.ReviewResponse)
def read_review(review_id: int, db: Session = Depends(get_db)):
    """Получить отзыв по ID."""
    review = db.get(models.Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/reviews", response_model=schemas.ReviewResponse, status_code=201)
def create_review(
    review: schemas.ReviewCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Создать отзыв. Пользователь и книга проверяются по общей БД с каталогом.
    Если отзыв опубликован и указана книга — книга добавляется в список чтения
    (reading_list_entries), затем отправляется уведомление.
    """
    if not db.get(models.LibraryUser, review.user_id):
        raise HTTPException(
            status_code=400,
            detail=f"User with id {review.user_id} not found",
        )
    if review.book_id is not None and not db.get(models.Book, review.book_id):
        raise HTTPException(
            status_code=400,
            detail=f"Book with id {review.book_id} not found",
        )

    db_review = models.Review(**review.model_dump())
    db.add(db_review)
    db.flush()

    added_to_reading_list = False
    book_title_for_notify: Optional[str] = None
    if review.is_published and review.book_id is not None:
        book = db.get(models.Book, review.book_id)
        if book is None:
            raise HTTPException(
                status_code=400,
                detail=f"Book with id {review.book_id} not found",
            )
        book_title_for_notify = book.title
        existing = (
            db.query(models.ReadingListEntry)
            .filter_by(user_id=review.user_id, book_id=review.book_id)
            .first()
        )
        if not existing:
            db.add(
                models.ReadingListEntry(
                    user_id=review.user_id,
                    book_id=review.book_id,
                    priority="medium",
                )
            )
            added_to_reading_list = True

    db.commit()
    db.refresh(db_review)

    background_tasks.add_task(
        write_log,
        f"Review created: id={db_review.id}, title={db_review.title}",
    )
    if added_to_reading_list and book_title_for_notify is not None and review.book_id:
        background_tasks.add_task(
            notify_reading_list_updated,
            user_id=review.user_id,
            book_id=review.book_id,
            book_title=book_title_for_notify,
            review_title=db_review.title,
        )
    return db_review


@app.put("/reviews/{review_id}", response_model=schemas.ReviewResponse)
def update_review(
    review_id: int,
    review_update: schemas.ReviewUpdate,
    db: Session = Depends(get_db),
):
    """Обновить существующий отзыв."""
    db_review = db.get(models.Review, review_id)
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")

    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_review, field, value)

    db.commit()
    db.refresh(db_review)
    return db_review


@app.delete("/reviews/{review_id}", status_code=200)
def delete_review(review_id: int, db: Session = Depends(get_db)):
    """Удалить отзыв."""
    db_review = db.get(models.Review, review_id)
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")

    db.delete(db_review)
    db.commit()
    return {"message": "Review deleted successfully"}


@app.get("/external/posts")
async def get_external_posts():
    """Асинхронно получает данные из внешнего API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("https://jsonplaceholder.typicode.com/posts")
        response.raise_for_status()
        return response.json()[:5]
