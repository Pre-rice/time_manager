"""复旦教务系统登录凭证（加密存储 UIS 密码）"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class FudanCredential(BaseModel):
    __tablename__ = "fudan_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    cookies: Mapped[str | None] = mapped_column(Text, nullable=True)  # 加密存储的登录 Cookie
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="fudan_credentials")