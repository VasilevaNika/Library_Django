from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import httpx
import os

app = FastAPI(title="Review Service", description="Отзывы и рейтинги")

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000")

# Модель отзыва
class Review(BaseModel):
    id: int
    user_id: int
    product: str
    rating: int
    comment: str

class ReviewCreate(BaseModel):
    user_id: int
    product: str
    rating: int
    comment: str

# "БД"
reviews_db = {}
next_id = 1

@app.get("/")
def root():
    return {"service": "review-service", "status": "running"}

@app.get("/reviews", response_model=List[Review])
def get_reviews():
    return list(reviews_db.values())

@app.post("/reviews", response_model=Review)
async def create_review(review: ReviewCreate):
    global next_id

    # 🔹 1. Проверка пользователя через Auth
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{AUTH_SERVICE_URL}/users/{review.user_id}")
            if r.status_code == 404:
                raise HTTPException(status_code=400, detail="User not found")
        except:
            raise HTTPException(status_code=503, detail="Auth service unavailable")

    # 🔹 2. Проверка рейтинга
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    # 🔹 3. Создание отзыва
    new_review = Review(id=next_id, **review.dict())
    reviews_db[next_id] = new_review
    next_id += 1

    # 🔹 4. Отправка уведомления
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notify",
                json={
                    "user_id": review.user_id,
                    "message": f"Вы оставили отзыв на {review.product} с рейтингом {review.rating}",
                    "type": "new_review"
                }
            )
        except:
            print("Notification service unavailable")

    return new_review