"""待办业务逻辑"""

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.event import Event
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def list_tasks(self) -> list[Task]:
        result = await self.db.execute(
            select(Task)
            .where(Task.user_id == self.user_id, Task.is_deleted == False)
            .order_by(Task.deadline.asc().nullslast())
        )
        return list(result.scalars().all())

    async def get_task(self, task_id: uuid.UUID) -> Task | None:
        result = await self.db.execute(
            select(Task)
            .where(Task.id == task_id, Task.user_id == self.user_id, Task.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def _create_preparation_for_task(self, task: Task) -> Event | None:
        """为待办创建准备日程"""
        if not task.preparation_minutes or task.preparation_minutes <= 0:
            return None
        if not task.deadline:
            return None
        prep_start = task.deadline - timedelta(minutes=task.preparation_minutes)
        prep_event = Event(
            user_id=self.user_id,
            title=f"准备：{task.title}",
            description=f"为待办「{task.title}」做准备",
            event_type="event",
            start_time=prep_start,
            end_time=task.deadline,
            is_all_day=False,
            preparation_minutes=0,
            source=task.source or "manual",
            is_preparation=True,
            parent_event_id=None,
            parent_task_id=task.id,
        )
        self.db.add(prep_event)
        await self.db.flush()
        await self.db.refresh(prep_event)
        return prep_event

    async def _delete_preparation_for_task(self, task_id: uuid.UUID) -> None:
        """删除某待办关联的所有准备日程"""
        result = await self.db.execute(
            select(Event).where(
                Event.parent_task_id == task_id,
                Event.is_preparation == True,
                Event.is_deleted == False,
            )
        )
        prep_events = list(result.scalars().all())
        for pe in prep_events:
            pe.is_deleted = True
        await self.db.flush()

    async def create_task(self, data: TaskCreate) -> Task:
        task = Task(
            user_id=self.user_id,
            title=data.title,
            description=data.description,
            deadline=data.deadline,
            is_important=data.is_important,
            status=data.status,
            preparation_minutes=data.preparation_minutes,
            source=data.source,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)

        # 如果设置了准备时间且截止时间存在，自动创建准备日程
        if data.deadline and data.preparation_minutes and data.preparation_minutes > 0:
            await self._create_preparation_for_task(task)

        return task

    async def update_task(self, task_id: uuid.UUID, data: TaskUpdate) -> Task | None:
        task = await self.get_task(task_id)
        if not task:
            return None

        # 记录变化前状态
        old_prep_minutes = task.preparation_minutes
        old_deadline = task.deadline

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)

        await self.db.flush()
        await self.db.refresh(task)

        # 如果 deadline 或 preparation_minutes 变化，更新准备日程
        new_prep = task.preparation_minutes or 0
        old_prep = old_prep_minutes or 0
        need_update_prep = (
            new_prep != old_prep
            or (new_prep > 0 and task.deadline != old_deadline)
        )
        if need_update_prep:
            await self._delete_preparation_for_task(task.id)
            if new_prep > 0 and task.deadline:
                await self._create_preparation_for_task(task)

        return task

    async def delete_task(self, task_id: uuid.UUID) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        task.is_deleted = True

        # 级联删除关联的准备日程
        await self._delete_preparation_for_task(task.id)

        await self.db.flush()
        return True