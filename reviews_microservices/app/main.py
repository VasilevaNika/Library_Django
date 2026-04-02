from typing import List

import time

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

app = FastAPI(
    title="Reviews Microservice",
    description="CRUD API for reviews with PostgreSQL",
)


def write_log(message: str) -> None:
    """Фоновая задача записи простого лога в файл."""
    time.sleep(0.5)
    with open("app.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


@app.get("/")
def root():
    return {
        "message": "Reviews Microservice",
        "docs": "/docs",
        "status": "running with PostgreSQL",
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
    """Создать новый отзыв."""
    db_review = models.Review(**review.model_dump())
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    background_tasks.add_task(
        write_log,
        f"Review created: id={db_review.id}, title={db_review.title}",
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
