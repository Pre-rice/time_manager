"""AI 提示词模板模型"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AITemplate(BaseModel):
    __tablename__ = "ai_templates"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)  # extract, suggest, morning
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)