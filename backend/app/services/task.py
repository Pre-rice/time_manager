"""待办业务逻辑"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
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
        return task

    async def update_task(self, task_id: uuid.UUID, data: TaskUpdate) -> Task | None:
        task = await self.get_task(task_id)
        if not task:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def delete_task(self, task_id: uuid.UUID) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        task.is_deleted = True
        await self.db.flush()
        return True