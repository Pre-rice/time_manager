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

    async def _delete_preparation_events(self, event_id: uuid.UUID) -> None:
        """删除某事件关联的所有准备日程"""
        result = await self.db.execute(
            select(Event).where(
                Event.parent_event_id == event_id,
                Event.is_preparation == True,
                Event.is_deleted == False,
            )
        )
        prep_events = list(result.scalars().all())
        for pe in prep_events:
            pe.is_deleted = True

    async def _create_preparation_slots(self, main_event_id: uuid.UUID, slots: list) -> None:
        """为主日程批量创建准备时段日程"""
        main_event = await self.get_event(main_event_id)
        if not main_event:
            return
        for slot in slots:
            prep = Event(
                user_id=self.user_id,
                title=f"准备：{main_event.title}",
                description=f"为「{main_event.title}」做准备",
                event_type=main_event.event_type,
                start_time=slot.start_time,
                end_time=slot.end_time,
                is_all_day=False,
                rrule=None,
                preparation_minutes=0,
                source=main_event.source or "manual",
                is_preparation=True,
                parent_event_id=main_event_id,
                parent_task_id=None,
            )
            self.db.add(prep)

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

        # 如果提供准备时段，自动创建准备日程
        if data.preparation_slots and not data.is_preparation:
            await self._create_preparation_slots(event.id, data.preparation_slots)

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

        # 处理 preparation_slots（不直接 setattr 到 event）
        slots = update_data.pop('preparation_slots', None)

        for key, value in update_data.items():
            setattr(event, key, value)

        await self.db.flush()
        await self.db.refresh(event)

        # 如果提供了准备时段，先删旧的再重建
        if slots is not None and not event.is_preparation:
            await self._delete_preparation_events(event.id)
            if slots:
                await self._create_preparation_slots(event.id, slots)

        return event

    async def delete_event(self, event_id: uuid.UUID) -> bool:
        event = await self.get_event(event_id)
        if not event:
            return False
        event.is_deleted = True

        # 级联删除关联的准备日程
        await self._delete_preparation_events(event.id)

        await self.db.flush()
        return True