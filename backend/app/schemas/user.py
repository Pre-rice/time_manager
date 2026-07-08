"""用户相关 Pydantic 模型"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    timezone: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}