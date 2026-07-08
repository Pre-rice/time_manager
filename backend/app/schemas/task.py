"""待办相关 Pydantic 模型"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskPreparationPeriodCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class TaskPreparationPeriodOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    deadline: datetime | None = None
    priority: int = 0
    preparation_minutes: int | None = None
    preparation_periods: list[TaskPreparationPeriodCreate] = []


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    priority: int | None = None
    status: str | None = None
    preparation_minutes: int | None = None


class TaskOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    deadline: datetime | None
    priority: int
    status: str
    preparation_minutes: int | None
    view_type: str
    source: str | None
    created_at: datetime
    updated_at: datetime
    preparation_periods: list[TaskPreparationPeriodOut] = []

    model_config = {"from_attributes": True}