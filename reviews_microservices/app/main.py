from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.database import get_db

app = FastAPI(
    title="Reviews Microservice",
    description="CRUD API for book reviews (PostgreSQL + Alembic)",
)


@app.get("/")
async def root():
    return {"message": "Reviews Microservice", "docs": "/docs"}


@app.get("/reviews", response_model=List[schemas.ReviewResponse])
async def read_reviews(book_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(models.Review)
    if book_id is not None:
        query = query.filter(models.Review.book_id == book_id)
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/reviews/{review_id}", response_model=schemas.ReviewResponse)
async def read_review(review_id: int, db: AsyncSession = Depends(get_db)):
    review = await db.get(models.Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/reviews", response_model=schemas.ReviewResponse, status_code=201)
async def create_review(review: schemas.ReviewCreate, db: AsyncSession = Depends(get_db)):
    db_review = models.Review(**review.model_dump())
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    return db_review


@app.put("/reviews/{review_id}", response_model=schemas.ReviewResponse)
async def update_review(
    review_id: int, review_update: schemas.ReviewUpdate, db: AsyncSession = Depends(get_db)
):
    db_review = await db.get(models.Review, review_id)
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")

    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_review, field, value)

    await db.commit()
    await db.refresh(db_review)
    return db_review


@app.delete("/reviews/{review_id}", status_code=200)
async def delete_review(review_id: int, db: AsyncSession = Depends(get_db)):
    db_review = await db.get(models.Review, review_id)
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.delete(db_review)
    await db.commit()
    return {"message": "Review deleted successfully"}

