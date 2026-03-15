"""
Модуль заглушки для микросервиса рекомендаций библиотеки.
"""

from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

# Создаём экземпляр приложения FastAPI
app = FastAPI(
    title="Микросервис рекомендаций библиотеки",
    description="API для получения рекомендаций книг и управления персональными настройками",
    version="3.0.0"
)

# ----- Перечисления (Enums) -----
class IgnoreReason(str, Enum):
    """Причины игнорирования книги"""
    ALREADY_READ = "already_read"
    NOT_INTERESTING = "not_interesting"
    DISLIKE_AUTHOR = "dislike_author"
    OTHER = "other"

class Priority(str, Enum):
    """Приоритет книги в списке чтения"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# ----- Модели данных Pydantic -----
class BookRecommendation(BaseModel):
    """Модель рекомендации книги"""
    id: int
    title: str
    author: str
    author_id: Optional[int] = None
    genre_id: Optional[int] = None
    genre_name: Optional[str] = None
    year: Optional[int] = None
    cover: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None

class IgnoreRequest(BaseModel):
    """Модель запроса на игнорирование книги"""
    book_id: int = Field(..., description="ID книги")
    reason: Optional[IgnoreReason] = Field(None, description="Причина игнорирования")

class IgnoreResponse(BaseModel):
    """Модель ответа после добавления в игнор-лист"""
    message: str
    book_id: int

class ReadingListRequest(BaseModel):
    """Модель запроса на добавление книги в список чтения"""
    book_id: int = Field(..., description="ID книги")
    priority: Priority = Field(Priority.MEDIUM, description="Приоритет")

class ReadingListResponse(BaseModel):
    """Модель ответа после добавления в список чтения"""
    message: str
    book_id: int

class MessageResponse(BaseModel):
    """Общая модель для сообщений"""
    message: str

class IgnoreItem(BaseModel):
    """Модель элемента игнор-листа"""
    book_id: int
    reason: Optional[IgnoreReason] = None
    book: Optional[BookRecommendation] = None

class ReadingListItem(BaseModel):
    """Модель элемента списка чтения"""
    book_id: int
    priority: Priority
    book: Optional[BookRecommendation] = None

# ----- "База данных" -----
# Несколько примеров книг для демонстрации
books_db = {
    1: {"id": 1, "title": "Война и мир", "author": "Лев Толстой", "author_id": 1, "genre_id": 1, "genre_name": "Классика", "year": 1869, "rating": 4.7, "rating_count": 2345},
    2: {"id": 2, "title": "Преступление и наказание", "author": "Фёдор Достоевский", "author_id": 2, "genre_id": 1, "genre_name": "Классика", "year": 1866, "rating": 4.8, "rating_count": 1892},
    3: {"id": 3, "title": "Мастер и Маргарита", "author": "Михаил Булгаков", "author_id": 3, "genre_id": 1, "genre_name": "Классика", "year": 1967, "rating": 4.9, "rating_count": 3120},
}

# Данные пользователей
users_data = {
    42: {
        "ignore": {3: "already_read"},
        "reading": {1: "high", 2: "medium"}
    }
}

# ----- Эндпоинты API -----

@app.get("/")
def root():
    """Корневой эндпоинт для проверки работоспособности"""
    return {
        "message": "Микросервис рекомендаций библиотеки",
        "status": "работает",
        "docs": "/docs"
    }


# 1. GET - популярные книги
@app.get("/recommendations/popular", 
         response_model=List[BookRecommendation],
         summary="Популярные книги",
         description="Возвращает список самых популярных книг")
def get_popular_books(
    limit: int = Query(10, ge=1, le=50, description="Количество книг")
):
    """ЗАГЛУШКА: возвращает пример популярных книг"""
    # Просто возвращаем первые несколько книг из базы
    return list(books_db.values())[:limit]


# 2. GET - новинки
@app.get("/recommendations/new", 
         response_model=List[BookRecommendation],
         summary="Новинки",
         description="Возвращает недавно добавленные книги")
def get_new_books(
    limit: int = Query(10, ge=1, description="Количество книг")
):
    """ЗАГЛУШКА: возвращает пример новых книг"""
    return list(books_db.values())[:limit]


# 3. GET - популярные книги по жанру
@app.get("/recommendations/genre/{genreId}", 
         response_model=List[BookRecommendation],
         summary="Популярное в жанре",
         description="Возвращает самые популярные книги в указанном жанре")
def get_popular_books_by_genre(
    genreId: int = Path(..., description="ID жанра"),
    limit: int = Query(10, ge=1, description="Количество книг"),
    min_rating: float = Query(4.0, ge=0, le=5, description="Минимальный рейтинг")
):
    """ЗАГЛУШКА: возвращает пример книг по жанру"""
    # Просто проверяем, что жанр существует (для примера)
    if genreId > 5:
        raise HTTPException(status_code=404, detail="Жанр с указанным ID не существует")
    
    return list(books_db.values())[:limit]


# 4. GET - популярные книги автора
@app.get("/recommendations/author/{authorId}", 
         response_model=List[BookRecommendation],
         summary="Популярное у автора",
         description="Возвращает самые популярные книги указанного автора")
def get_popular_books_by_author(
    authorId: int = Path(..., description="ID автора"),
    limit: int = Query(5, ge=1, description="Количество книг")
):
    """ЗАГЛУШКА: возвращает пример книг автора"""
    # Проверяем, что автор существует (для примера)
    if authorId > 10:
        raise HTTPException(status_code=404, detail="Автор с указанным ID не найден")
    
    return list(books_db.values())[:limit]


# 5. GET - похожие книги
@app.get("/recommendations/similar/{bookId}", 
         response_model=List[BookRecommendation],
         summary="Похожие книги",
         description="Возвращает книги, похожие на указанную")
def get_similar_books(
    bookId: int = Path(..., description="ID книги"),
    limit: int = Query(5, ge=1, description="Количество книг")
):
    """ЗАГЛУШКА: возвращает пример похожих книг"""
    # Проверяем, что книга существует (для примера)
    if bookId not in books_db:
        raise HTTPException(status_code=404, detail="Книга с указанным ID не существует")
    
    return list(books_db.values())[:limit]


# 6. GET - случайная книга
@app.get("/recommendations/random", 
         response_model=BookRecommendation,
         summary="Случайная книга",
         description="Возвращает одну случайную книгу")
def get_random_book(
    genre_id: Optional[int] = Query(None, description="Ограничить жанром")
):
    """ЗАГЛУШКА: возвращает первую книгу как 'случайную'"""
    # Для заглушки просто возвращаем первую книгу
    return list(books_db.values())[0]


# 7. GET - список игнорируемых книг
@app.get("/user/{userId}/ignore", 
         response_model=List[IgnoreItem],
         summary="Список игнорируемых книг",
         description="Возвращает список книг, которые пользователь игнорирует")
def get_ignore_list(
    userId: int = Path(..., description="ID пользователя"),
    include_book_details: bool = Query(True, description="Включить полную информацию о книгах")
):
    """ЗАГЛУШКА: возвращает пример списка игнорируемых книг"""
    # Проверяем существование пользователя
    if userId not in users_data:
        raise HTTPException(status_code=404, detail="Пользователь с указанным ID не существует")
    
    # Для примера возвращаем одну книгу
    return [
        IgnoreItem(
            book_id=3, 
            reason=IgnoreReason.ALREADY_READ,
            book=books_db[3] if include_book_details else None
        )
    ]


# 8. POST - добавить книгу в игнор-лист
@app.post("/user/{userId}/ignore", 
          response_model=IgnoreResponse, 
          status_code=201,
          summary="Игнорировать книгу",
          description="Добавляет книгу в список игнорируемых")
def add_to_ignore_list(
    userId: int = Path(..., description="ID пользователя"),
    request: IgnoreRequest = None
):
    """ЗАГЛУШКА: имитирует добавление книги в игнор-лист"""
    # Проверяем существование пользователя
    if userId not in users_data:
        raise HTTPException(status_code=404, detail="Пользователь с указанным ID не существует")
    
    # Проверяем существование книги
    if request.book_id not in books_db:
        raise HTTPException(status_code=404, detail="Книга с указанным ID не существует")
    
    return IgnoreResponse(
        message="Книга больше не будет вам рекомендоваться",
        book_id=request.book_id
    )


# 9. DELETE - удалить книгу из игнор-листа
@app.delete("/user/{userId}/ignore",
            response_model=MessageResponse,
            summary="Перестать игнорировать",
            description="Удаляет книгу из списка игнорируемых")
def remove_from_ignore_list(
    userId: int = Path(..., description="ID пользователя"),
    request: IgnoreRequest = None
):
    """ЗАГЛУШКА: имитирует удаление книги из игнор-листа"""
    # Проверяем существование пользователя
    if userId not in users_data:
        raise HTTPException(status_code=404, detail="Пользователь с указанным ID не существует")
    
    # Для заглушки всегда возвращаем успех
    return MessageResponse(message="Книга снова может вам рекомендоваться")


# 10. GET - список чтения пользователя
@app.get("/user/{userId}/reading-list", 
         response_model=List[ReadingListItem],
         summary="Список чтения",
         description="Возвращает список книг, которые пользователь планирует прочитать")
def get_reading_list(
    userId: int = Path(..., description="ID пользователя"),
    include_book_details: bool = Query(True, description="Включить полную информацию о книгах")
):
    """ЗАГЛУШКА: возвращает пример списка чтения"""
    # Проверяем существование пользователя
    if userId not in users_data:
        raise HTTPException(status_code=404, detail="Пользователь с указанным ID не существует")
    
    # Для примера возвращаем две книги
    return [
        ReadingListItem(
            book_id=1, 
            priority=Priority.HIGH,
            book=books_db[1] if include_book_details else None
        ),
        ReadingListItem(
            book_id=2, 
            priority=Priority.MEDIUM,
            book=books_db[2] if include_book_details else None
        )
    ]


# 11. POST - сохранить книгу в "прочитать позже"
@app.post("/user/{userId}/reading-list",
          response_model=ReadingListResponse,
          status_code=201,
          summary="Добавить в список чтения",
          description="Сохраняет книгу в персональный список 'прочитать позже'")
def add_to_reading_list(
    userId: int = Path(..., description="ID пользователя"),
    request: ReadingListRequest = None
):
    """ЗАГЛУШКА: имитирует добавление книги в список чтения"""
    # Проверяем существование пользователя
    if userId not in users_data:
        raise HTTPException(status_code=404, detail="Пользователь с указанным ID не существует")
    
    # Проверяем существование книги
    if request.book_id not in books_db:
        raise HTTPException(status_code=404, detail="Книга с указанным ID не существует")
    
    return ReadingListResponse(
        message="Книга сохранена в список 'прочитать позже'",
        book_id=request.book_id
    )


# 12. DELETE - удалить книгу из "прочитать позже"
@app.delete("/user/{userId}/reading-list",
            response_model=MessageResponse,
            summary="Удалить из списка чтения",
            description="Убирает книгу из списка 'прочитать позже'")
def remove_from_reading_list(
    userId: int = Path(..., description="ID пользователя"),
    request: ReadingListRequest = None
):
    """ЗАГЛУШКА: имитирует удаление книги из списка чтения"""
    # Проверяем существование пользователя
    if userId not in users_data:
        raise HTTPException(status_code=404, detail="Пользователь с указанным ID не существует")
    
    # Для заглушки всегда возвращаем успех
    return MessageResponse(message="Книга удалена из списка чтения")