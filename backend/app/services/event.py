"""日程业务逻辑"""

import uuid
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate


class EventService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def list_events(
        self, start: datetime | None = None, end: datetime | None = None
    ) -> list[Event]:
        query = (
            select(Event)
            .where(Event.user_id == self.user_id, Event.is_deleted == False)
            .order_by(Event.start_time.asc().nullslast())
        )
        if start and end:
            query = query.where(
                and_(
                    Event.start_time >= start,
                    Event.start_time <= end,
                )
            )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_event(self, event_id: uuid.UUID) -> Event | None:
        result = await self.db.execute(
            select(Event)
            .where(Event.id == event_id, Event.user_id == self.user_id, Event.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def create_event(self, data: EventCreate) -> Event:
        # 处理 parent_event_id/parent_task_id（前端传的是 str，需转 UUID）
        parent_event_id = uuid.UUID(data.parent_event_id) if data.parent_event_id else None
        parent_task_id = uuid.UUID(data.parent_task_id) if data.parent_task_id else None

        event = Event(
            user_id=self.user_id,
            title=data.title,
            description=data.description,
            event_type=data.event_type,
            start_time=data.start_time,
            end_time=data.end_time,
            is_all_day=data.is_all_day,
            rrule=data.rrule,
            preparation_minutes=data.preparation_minutes,
            source=data.source,
            is_preparation=data.is_preparation,
            parent_event_id=parent_event_id,
            parent_task_id=parent_task_id,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def update_event(self, event_id: uuid.UUID, data: EventUpdate) -> Event | None:
        event = await self.get_event(event_id)
        if not event:
            return None

        update_data = data.model_dump(exclude_unset=True)
        # 处理 parent_event_id/parent_task_id 字符串→UUID 转换
        if 'parent_event_id' in update_data and isinstance(update_data['parent_event_id'], str):
            update_data['parent_event_id'] = uuid.UUID(update_data['parent_event_id']) if update_data['parent_event_id'] else None
        if 'parent_task_id' in update_data and isinstance(update_data['parent_task_id'], str):
            update_data['parent_task_id'] = uuid.UUID(update_data['parent_task_id']) if update_data['parent_task_id'] else None

        for key, value in update_data.items():
            setattr(event, key, value)

        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def delete_event(self, event_id: uuid.UUID) -> bool:
        event = await self.get_event(event_id)
        if not event:
            return False
        event.is_deleted = True
        await self.db.flush()
        return True