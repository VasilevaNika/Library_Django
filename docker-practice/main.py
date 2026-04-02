from fastapi import FastAPI, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from enum import Enum
import uvicorn
from collections import defaultdict
import random

# Инициализация приложения
app = FastAPI(
    title="API для отзывов на книги",
    description="Сервис рейтингов и отзывов на книги",
    version="1.0.0"
)

# === Модели данных ===
class ReviewStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class ReviewSort(str, Enum):
    newest = "newest"
    oldest = "oldest"
    highest_rating = "highest_rating"
    lowest_rating = "lowest_rating"
    most_helpful = "most_helpful"

class ReportReason(str, Enum):
    spam = "spam"
    offensive = "offensive"
    irrelevant = "irrelevant"
    other = "other"

class RatingTrend(str, Enum):
    rising = "rising"
    falling = "falling"
    stable = "stable"

# Pydantic модели для запросов
class ReviewCreate(BaseModel):
    user_id: int = Field(..., example=12345)
    rating: int = Field(..., ge=1, le=5, example=5)
    title: Optional[str] = Field(None, example="Шедевр на все времена")
    text: str = Field(..., example="Эта книга изменила моё представление о литературе...")
    anonymous: bool = Field(default=False)

class HelpfulVote(BaseModel):
    user_id: int = Field(..., example=12345)

class ReviewResponse(BaseModel):
    user_id: int = Field(..., example=67890)
    text: str = Field(..., example="Спасибо за отзыв! Рады, что книга вам понравилась.")

class ReviewReport(BaseModel):
    user_id: int
    reason: ReportReason
    comment: Optional[str] = None

# Модели для ответов
class ReviewOut(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    rating: int
    title: Optional[str] = None
    text: str
    helpful_votes: int = 0
    status: ReviewStatus = ReviewStatus.pending
    anonymous: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    responses_count: int = 0

class ReviewsListResponse(BaseModel):
    book_id: int
    total_reviews: int
    average_rating: float
    rating_distribution: Dict[str, int]
    reviews: List[ReviewOut]

class RatingStatsResponse(BaseModel):
    book_id: int
    total_reviews: int
    average_rating: float
    monthly_stats: List[Dict]
    rating_trend: RatingTrend

# === Имитация базы данных (в памяти) ===
# Структура: {book_id: {review_id: review_data}}
reviews_db = defaultdict(dict)

# Структура для полезных голосов: {review_id: set(user_ids)}
helpful_votes_db = defaultdict(set)

# Структура для ответов: {review_id: [responses]}
responses_db = defaultdict(list)

# Структура для жалоб: {review_id: [reports]}
reports_db = defaultdict(list)

# Счетчики для ID
review_counter = 1000
response_counter = 500

# Пример пользователей
users_db = {
    12345: {"name": "Иван Петров"},
    67890: {"name": "Издательство ABC"},
    11111: {"name": "Мария Сидорова"},
    22222: {"name": "Петр Иванов"}
}

# === Вспомогательные функции ===
def get_next_review_id():
    global review_counter
    review_counter += 1
    return review_counter

def get_next_response_id():
    global response_counter
    response_counter += 1
    return response_counter

def calculate_rating_stats(book_id: int):
    reviews = reviews_db[book_id]
    if not reviews:
        return {
            "total_reviews": 0,
            "average_rating": 0.0,
            "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        }
    
    ratings = [review["rating"] for review in reviews.values()]
    total = len(ratings)
    avg = sum(ratings) / total
    
    distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for rating in ratings:
        distribution[str(rating)] += 1
    
    return {
        "total_reviews": total,
        "average_rating": round(avg, 2),
        "rating_distribution": distribution
    }

# === Эндпоинты ===

# 1. Создать отзыв
@app.post("/books/{bookId}/reviews", 
          status_code=status.HTTP_201_CREATED,
          summary="Создать отзыв",
          description="Добавляет новый отзыв на книгу")
async def create_review(
    bookId: int = Path(..., example=67890),
    review: ReviewCreate = None
):
    # Проверка, не оставлял ли пользователь уже отзыв
    for rev_id, rev_data in reviews_db[bookId].items():
        if rev_data["user_id"] == review.user_id:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "Конфликт",
                    "message": "Пользователь уже оставил отзыв на эту книгу"
                }
            )
    
    review_id = get_next_review_id()
    
    reviews_db[bookId][review_id] = {
        "id": review_id,
        "user_id": review.user_id,
        "rating": review.rating,
        "title": review.title,
        "text": review.text,
        "anonymous": review.anonymous,
        "helpful_votes": 0,
        "status": "pending",
        "created_at": datetime.now(),
        "updated_at": None
    }
    
    return {
        "review_id": review_id,
        "status": "pending_moderation"
    }

# 2. Получить отзывы на книгу
@app.get("/books/{bookId}/reviews",
         response_model=ReviewsListResponse,
         summary="Отзывы на книгу",
         description="Возвращает список отзывов для указанной книги")
async def get_reviews(
    bookId: int = Path(..., example=67890),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    sort: ReviewSort = Query(ReviewSort.newest),
    rating: Optional[int] = Query(None, ge=1, le=5)
):
    if bookId not in reviews_db:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Не найдено",
                "message": f"Книга с ID {bookId} не найдена"
            }
        )
    
    # Получаем все отзывы для книги
    all_reviews = list(reviews_db[bookId].values())
    
    # Фильтр по рейтингу
    if rating:
        all_reviews = [r for r in all_reviews if r["rating"] == rating]
    
    # Сортировка
    if sort == ReviewSort.newest:
        all_reviews.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort == ReviewSort.oldest:
        all_reviews.sort(key=lambda x: x["created_at"])
    elif sort == ReviewSort.highest_rating:
        all_reviews.sort(key=lambda x: x["rating"], reverse=True)
    elif sort == ReviewSort.lowest_rating:
        all_reviews.sort(key=lambda x: x["rating"])
    elif sort == ReviewSort.most_helpful:
        all_reviews.sort(key=lambda x: x["helpful_votes"], reverse=True)
    
    # Пагинация
    start = (page - 1) * limit
    end = start + limit
    paginated_reviews = all_reviews[start:end]
    
    # Добавляем имена пользователей
    for review in paginated_reviews:
        if not review["anonymous"] and review["user_id"] in users_db:
            review["user_name"] = users_db[review["user_id"]]["name"]
        review["responses_count"] = len(responses_db[review["id"]])
    
    stats = calculate_rating_stats(bookId)
    
    return {
        "book_id": bookId,
        "total_reviews": len(all_reviews),
        "average_rating": stats["average_rating"],
        "rating_distribution": stats["rating_distribution"],
        "reviews": paginated_reviews
    }

# 3. Удалить отзыв
@app.delete("/reviews/{reviewId}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Удалить отзыв",
            description="Удаляет отзыв (только автор или модератор)")
async def delete_review(
    reviewId: int = Path(...),
    user_id: int = Query(..., description="ID пользователя, выполняющего удаление")
):
    # Ищем отзыв во всех книгах
    for book_id, reviews in reviews_db.items():
        if reviewId in reviews:
            # Проверка прав (упрощенно: модераторы имеют ID > 90000)
            is_moderator = user_id > 90000
            is_author = reviews[reviewId]["user_id"] == user_id
            
            if not (is_moderator or is_author):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Доступ запрещен",
                        "message": "Недостаточно прав для удаления отзыва"
                    }
                )
            
            # Удаляем отзыв и связанные данные
            del reviews_db[book_id][reviewId]
            if reviewId in helpful_votes_db:
                del helpful_votes_db[reviewId]
            if reviewId in responses_db:
                del responses_db[reviewId]
            if reviewId in reports_db:
                del reports_db[reviewId]
            
            return None
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Не найдено",
            "message": f"Отзыв с ID {reviewId} не найден"
        }
    )

# 4. Отметить отзыв как полезный
@app.post("/reviews/{reviewId}/helpful",
          summary="Отметить отзыв как полезный",
          description="Добавляет голос пользователя за полезность отзыва")
async def mark_helpful(
    reviewId: int = Path(...),
    vote: HelpfulVote = None
):
    # Ищем отзыв
    found = False
    for book_id, reviews in reviews_db.items():
        if reviewId in reviews:
            found = True
            break
    
    if not found:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Не найдено",
                "message": f"Отзыв с ID {reviewId} не найден"
            }
        )
    
    # Проверяем, не голосовал ли пользователь уже
    if vote.user_id in helpful_votes_db[reviewId]:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Конфликт",
                "message": "Пользователь уже отметил этот отзыв как полезный"
            }
        )
    
    helpful_votes_db[reviewId].add(vote.user_id)
    
    # Обновляем счетчик в отзыве
    for book_id, reviews in reviews_db.items():
        if reviewId in reviews:
            reviews[reviewId]["helpful_votes"] = len(helpful_votes_db[reviewId])
            break
    
    return {
        "helpful_votes": len(helpful_votes_db[reviewId])
    }

# 5. Убрать отметку полезности
@app.delete("/reviews/{reviewId}/helpful",
            summary="Убрать отметку полезности",
            description="Удаляет голос пользователя за полезность отзыва")
async def unmark_helpful(
    reviewId: int = Path(...),
    user_id: int = Query(...)
):
    if user_id not in helpful_votes_db[reviewId]:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Не найдено",
                "message": "Голос пользователя не найден"
            }
        )
    
    helpful_votes_db[reviewId].remove(user_id)
    
    # Обновляем счетчик в отзыве
    for book_id, reviews in reviews_db.items():
        if reviewId in reviews:
            reviews[reviewId]["helpful_votes"] = len(helpful_votes_db[reviewId])
            break
    
    return {
        "helpful_votes": len(helpful_votes_db[reviewId])
    }

# 6. Ответить на отзыв
@app.post("/reviews/{reviewId}/responses",
          status_code=status.HTTP_201_CREATED,
          summary="Ответить на отзыв",
          description="Добавляет ответ от автора книги или модератора")
async def add_response(
    reviewId: int = Path(...),
    response: ReviewResponse = None
):
    # Проверяем существование отзыва
    found = False
    for book_id, reviews in reviews_db.items():
        if reviewId in reviews:
            found = True
            break
    
    if not found:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Не найдено",
                "message": f"Отзыв с ID {reviewId} не найден"
            }
        )
    
    response_id = get_next_response_id()
    response_data = {
        "id": response_id,
        "review_id": reviewId,
        "user_id": response.user_id,
        "text": response.text,
        "created_at": datetime.now()
    }
    
    responses_db[reviewId].append(response_data)
    
    return {
        "response_id": response_id
    }

# 7. Статистика по книге
@app.get("/books/{bookId}/rating/stats",
         response_model=RatingStatsResponse,
         summary="Статистика рейтинга книги",
         description="Детальная статистика по оценкам книги")
async def get_rating_stats(
    bookId: int = Path(..., example=67890)
):
    stats = calculate_rating_stats(bookId)
    
    if stats["total_reviews"] == 0:
        return {
            "book_id": bookId,
            "total_reviews": 0,
            "average_rating": 0.0,
            "monthly_stats": [],
            "rating_trend": "stable"
        }
    
    # Генерируем месячную статистику (для демо)
    monthly_stats = []
    now = datetime.now()
    for i in range(3):
        month = (now - timedelta(days=30*i)).strftime("%Y-%m")
        monthly_stats.append({
            "month": month,
            "reviews_count": random.randint(1, 10),
            "average_rating": round(random.uniform(3.5, 5.0), 2)
        })
    
    # Определяем тренд
    if len(monthly_stats) >= 2:
        if monthly_stats[0]["average_rating"] > monthly_stats[1]["average_rating"]:
            trend = "rising"
        elif monthly_stats[0]["average_rating"] < monthly_stats[1]["average_rating"]:
            trend = "falling"
        else:
            trend = "stable"
    else:
        trend = "stable"
    
    return {
        "book_id": bookId,
        "total_reviews": stats["total_reviews"],
        "average_rating": stats["average_rating"],
        "monthly_stats": monthly_stats,
        "rating_trend": trend
    }

# 8. Жалобы на отзывы
@app.post("/reviews/{reviewId}/reports",
          status_code=status.HTTP_201_CREATED,
          summary="Пожаловаться на отзыв",
          description="Отправить жалобу на некорректный отзыв")
async def report_review(
    reviewId: int = Path(...),
    report: ReviewReport = None
):
    # Проверяем существование отзыва
    found = False
    for book_id, reviews in reviews_db.items():
        if reviewId in reviews:
            found = True
            break
    
    if not found:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Не найдено",
                "message": f"Отзыв с ID {reviewId} не найден"
            }
        )
    
    report_data = {
        "user_id": report.user_id,
        "reason": report.reason,
        "comment": report.comment,
        "created_at": datetime.now()
    }
    
    reports_db[reviewId].append(report_data)
    
    return {"status": "reported"}

# Дополнительный эндпоинт для создания тестовых данных
@app.post("/debug/populate", include_in_schema=False)
async def populate_test_data():
    """Заполняет базу тестовыми данными"""
    test_reviews = [
        {
            "user_id": 12345,
            "rating": 5,
            "title": "Шедевр на все времена",
            "text": "Эта книга изменила моё представление о литературе...",
            "anonymous": False
        },
        {
            "user_id": 11111,
            "rating": 4,
            "title": "Очень интересно",
            "text": "Отличная книга, рекомендую!",
            "anonymous": False
        },
        {
            "user_id": 22222,
            "rating": 3,
            "text": "Неплохо, но могло быть лучше",
            "anonymous": True
        }
    ]
    
    for review in test_reviews:
        await create_review(67890, ReviewCreate(**review))
    
    return {"message": "Test data created"}

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Book Reviews API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)