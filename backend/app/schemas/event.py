"""日程相关 Pydantic 模型"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    description: str | None = None
    event_type: str = "event"  # event, class, exam
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_all_day: bool = False
    rrule: str | None = None
    preparation_minutes: int | None = None
    source: str = "manual"
    is_preparation: bool = False
    parent_event_id: str | None = None
    parent_task_id: str | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    event_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_all_day: bool | None = None
    rrule: str | None = None
    preparation_minutes: int | None = None
    source: str | None = None
    is_preparation: bool | None = None
    parent_event_id: str | None = None
    parent_task_id: str | None = None


class EventOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    event_type: str
    start_time: datetime | None
    end_time: datetime | None
    is_all_day: bool
    rrule: str | None
    preparation_minutes: int | None
    source: str | None
    is_preparation: bool
    parent_event_id: uuid.UUID | None
    parent_task_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventRangeQuery(BaseModel):
    start: datetime
    end: datetime