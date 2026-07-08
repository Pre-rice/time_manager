"""AI 核心功能 API（文本提取、时间建议、早安消息）"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.ai import (
    ExtractRequest,
    ExtractResponse,
    ExtractItem,
    MorningMessageResponse,
    SuggestTimeRequest,
    SuggestTimeResponse,
    SuggestTimeItem,
)
from app.services.ai_service import (
    extract_from_text,
    generate_morning_message,
    suggest_time,
)

router = APIRouter(prefix="/ai", tags=["AI 功能"])


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    req: ExtractRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从自然语言中提取日程/待办"""
    try:
        items = await extract_from_text(db, current_user.id, req.text)
        return ExtractResponse(
            items=[ExtractItem(**item) for item in items]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 调用失败: {str(e)}")


@router.post("/suggest-time", response_model=SuggestTimeResponse)
async def suggest_time_endpoint(
    req: SuggestTimeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 时间分配建议"""
    try:
        suggestions = await suggest_time(
            db, current_user.id, req.title, req.duration_minutes
        )
        return SuggestTimeResponse(
            suggestions=[SuggestTimeItem(**s) for s in suggestions]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 调用失败: {str(e)}")


@router.get("/morning-message", response_model=MorningMessageResponse)
async def morning_message(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成早安消息"""
    try:
        from datetime import date
        message = await generate_morning_message(db, current_user.id)
        return MorningMessageResponse(
            message=message,
            date=date.today().isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 调用失败: {str(e)}")