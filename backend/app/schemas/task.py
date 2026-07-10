"""待办相关 Pydantic 模型"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    deadline: datetime | None = None
    is_important: bool = False
    status: str = "todo"
    preparation_minutes: int | None = None
    source: str = "manual"


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    is_important: bool | None = None
    status: str | None = None
    preparation_minutes: int | None = None
    source: str | None = None


class TaskOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    deadline: datetime | None
    is_important: bool
    status: str
    preparation_minutes: int | None
    source: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}