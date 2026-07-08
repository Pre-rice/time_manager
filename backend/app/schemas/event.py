"""日程相关 Pydantic 模型"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class EventPreparationPeriodCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class EventPreparationPeriodOut(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    title: str
    description: str | None = None
    event_type: str = "event"  # event, class, exam
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_all_day: bool = False
    rrule: str | None = None
    preparation_minutes: int | None = None
    preparation_periods: list[EventPreparationPeriodCreate] = []


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    event_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_all_day: bool | None = None
    rrule: str | None = None
    postponed: bool | None = None
    preparation_minutes: int | None = None


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
    postponed: bool
    preparation_minutes: int | None
    source: str | None
    created_at: datetime
    updated_at: datetime
    preparation_periods: list[EventPreparationPeriodOut] = []

    model_config = {"from_attributes": True}


class EventRangeQuery(BaseModel):
    start: datetime
    end: datetime