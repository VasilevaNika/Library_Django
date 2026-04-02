"""
Auth Service — заглушка для демонстрации взаимодействия микросервисов.
Отвечает за пользователей и JWT-токены.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="Auth Service", description="Управление пользователями")

# Модели данных
class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool = True

class UserCreate(BaseModel):
    username: str
    email: str

# "База данных" в памяти
users_db = {
    1: User(id=1, username="alice", email="alice@example.com"),
    2: User(id=2, username="bob", email="bob@example.com"),
}
next_id = 3

@app.get("/")
def root():
    return {
        "service": "auth-service",
        "status": "running",
        "endpoints": ["GET /users", "GET /users/{id}", "POST /users", "DELETE /users/{id}"]
    }

@app.get("/users", response_model=List[User])
def get_users():
    """Получить всех пользователей"""
    return list(users_db.values())

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    """Получить пользователя по ID"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id]

@app.post("/users", response_model=User, status_code=201)
def create_user(user: UserCreate):
    """Создать нового пользователя"""
    global next_id
    new_user = User(id=next_id, **user.dict())
    users_db[next_id] = new_user
    next_id += 1
    return new_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    """Удалить пользователя"""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    del users_db[user_id]
    return {"message": "User deleted"}
