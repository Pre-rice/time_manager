"""待办模型"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Task(BaseModel):
    __tablename__ = "tasks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=无, 1=低, 2=中, 3=高
    status: Mapped[str] = mapped_column(
        String(20), default="todo", nullable=False
    )  # todo, in_progress, done, cancelled
    preparation_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_type: Mapped[str] = mapped_column(
        String(20), default="deadline", nullable=False
    )  # deadline, priority, remaining
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="tasks")
    preparation_periods = relationship(
        "TaskPreparationPeriod", back_populates="task", cascade="all, delete-orphan"
    )


class TaskPreparationPeriod(BaseModel):
    """待办的明确准备时间段"""

    __tablename__ = "task_preparation_periods"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    task = relationship("Task", back_populates="preparation_periods")