"""目标业务逻辑"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalUpdate, GoalProgressUpdate


class GoalService:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    async def list_goals(self) -> list[Goal]:
        result = await self.db.execute(
            select(Goal)
            .where(Goal.user_id == self.user_id)
            .order_by(Goal.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_goal(self, goal_id: uuid.UUID) -> Goal | None:
        result = await self.db.execute(
            select(Goal).where(Goal.id == goal_id, Goal.user_id == self.user_id)
        )
        return result.scalar_one_or_none()

    async def create_goal(self, data: GoalCreate) -> Goal:
        goal = Goal(
            user_id=self.user_id,
            title=data.title,
            description=data.description,
            target_value=data.target_value,
            unit=data.unit,
        )
        self.db.add(goal)
        await self.db.flush()
        await self.db.refresh(goal)
        return goal

    async def update_goal(self, goal_id: uuid.UUID, data: GoalUpdate) -> Goal | None:
        goal = await self.get_goal(goal_id)
        if not goal:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(goal, key, value)

        await self.db.flush()
        await self.db.refresh(goal)
        return goal

    async def update_progress(self, goal_id: uuid.UUID, data: GoalProgressUpdate) -> Goal | None:
        goal = await self.get_goal(goal_id)
        if not goal:
            return None

        goal.current_value = data.current_value
        if goal.target_value and goal.target_value > 0:
            goal.progress_percent = min(int((data.current_value / goal.target_value) * 100), 100)
        else:
            goal.progress_percent = 0

        await self.db.flush()
        await self.db.refresh(goal)
        return goal

    async def delete_goal(self, goal_id: uuid.UUID) -> bool:
        goal = await self.get_goal(goal_id)
        if not goal:
            return False
        await self.db.delete(goal)
        await self.db.flush()
        return True