"""日程业务逻辑"""

import uuid
from datetime import datetime

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event, EventPreparationPeriod
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
            .options(selectinload(Event.preparation_periods))
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
            .options(selectinload(Event.preparation_periods))
        )
        return result.scalar_one_or_none()

    async def create_event(self, data: EventCreate) -> Event:
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
        )
        self.db.add(event)
        await self.db.flush()

        # 添加准备时段
        for period in data.preparation_periods:
            pp = EventPreparationPeriod(
                event_id=event.id,
                start_time=period.start_time,
                end_time=period.end_time,
            )
            self.db.add(pp)

        # 重新加载以获取关联的准备时段
        result = await self.db.execute(
            select(Event)
            .where(Event.id == event.id)
            .options(selectinload(Event.preparation_periods))
        )
        return result.scalar_one()

    async def update_event(self, event_id: uuid.UUID, data: EventUpdate) -> Event | None:
        event = await self.get_event(event_id)
        if not event:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(event, key, value)

        await self.db.flush()
        result = await self.db.execute(
            select(Event)
            .where(Event.id == event.id)
            .options(selectinload(Event.preparation_periods))
        )
        return result.scalar_one()

    async def delete_event(self, event_id: uuid.UUID) -> bool:
        event = await self.get_event(event_id)
        if not event:
            return False
        event.is_deleted = True
        await self.db.flush()
        return True