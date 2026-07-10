"""日程模型"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Event(BaseModel):
    __tablename__ = "events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(
        String(20), default="event", nullable=False
    )  # event, class, exam
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rrule: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 重复规则
    preparation_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # manual, fudan, feishu
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 准备日程字段：替代原 EventPreparationPeriod 子表
    is_preparation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "(parent_event_id IS NULL OR parent_task_id IS NULL)",
            name="ck_event_preparation_parent_mutex"
        ),
    )

    user = relationship("User", back_populates="events")
    # parent_event 引用的父日程
    parent_event = relationship("Event", remote_side="Event.id", backref="preparation_children")