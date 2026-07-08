"""节日、生日等特殊日期模型"""

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SpecialDate(BaseModel):
    __tablename__ = "special_dates"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_value: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    date_type: Mapped[str] = mapped_column(
        String(20), default="holiday", nullable=False
    )  # holiday, birthday, custom
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(default=True, nullable=False)