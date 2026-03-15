from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Базовая модель с общими полями
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

# Модель для создания (без id и служебных полей)
class TaskCreate(TaskBase):
    pass

# Модель для обновления (все поля опциональны)
class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

# Модель для ответа (со всеми полями)
class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # позволяет создавать Pydantic-модель из ORM-объекта
