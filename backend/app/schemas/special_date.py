"""特殊日期 Pydantic 模型"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class SpecialDateCreate(BaseModel):
    name: str
    date_value: date
    date_type: str = "holiday"
    description: str | None = None
    is_recurring: bool = True


class SpecialDateOut(BaseModel):
    id: uuid.UUID
    name: str
    date_value: date
    date_type: str
    description: str | None
    is_recurring: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}