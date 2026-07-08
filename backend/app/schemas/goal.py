"""目标相关 Pydantic 模型"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class GoalCreate(BaseModel):
    title: str
    description: str | None = None
    target_value: float | None = None
    unit: str | None = None


class GoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    target_value: float | None = None
    unit: str | None = None


class GoalProgressUpdate(BaseModel):
    current_value: float


class GoalOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    target_value: float | None
    current_value: float
    unit: str | None
    progress_percent: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}