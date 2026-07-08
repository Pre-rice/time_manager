"""特殊日期 API 路由"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.special_date import SpecialDate
from app.schemas.special_date import SpecialDateCreate, SpecialDateOut

router = APIRouter(prefix="/special-dates", tags=["日历标识"])


@router.get("/", response_model=list[SpecialDateOut])
async def list_special_dates(
    year: int | None = Query(None),
    month: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    query = select(SpecialDate).order_by(SpecialDate.date_value)
    if year and month:
        query = query.where(
            SpecialDate.date_value.between(
                date(year, month, 1),
                date(year + (1 if month == 12 else 0), (1 if month == 12 else month + 1), 1),
            )
        )
    elif year:
        query = query.where(
            SpecialDate.date_value.between(date(year, 1, 1), date(year, 12, 31))
        )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=SpecialDateOut, status_code=status.HTTP_201_CREATED)
async def create_special_date(
    data: SpecialDateCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    special_date = SpecialDate(**data.model_dump())
    db.add(special_date)
    await db.flush()
    await db.refresh(special_date)
    return special_date


@router.delete("/{special_date_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_special_date(
    special_date_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    from uuid import UUID

    result = await db.execute(select(SpecialDate).where(SpecialDate.id == UUID(special_date_id)))
    special_date = result.scalar_one_or_none()
    if not special_date:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="特殊日期不存在")
    await db.delete(special_date)
    await db.flush()