"""复旦教务外部数据导入 API"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.external import (
    FudanConnectRequest,
    FudanConnectResponse,
    FudanStatusResponse,
    SyncResponse,
)
from app.services.fudan_service import (
    connect_fudan,
    disconnect_fudan,
    get_credential,
    sync_fudan_data,
)
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external", tags=["外部数据"])


@router.post("/fudan/connect", response_model=FudanConnectResponse)
async def connect_fudan_account(
    data: FudanConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """连接复旦教务系统（加密保存密码和 Cookie）"""
    result = await connect_fudan(db, current_user.id, data.student_id, data.password)
    return FudanConnectResponse(success=result["success"], message=result["message"])


@router.get("/fudan/status", response_model=FudanStatusResponse)
async def get_fudan_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看复旦连接状态"""
    credential = await get_credential(db, current_user.id)
    if credential and credential.is_active:
        return FudanStatusResponse(
            connected=True,
            student_id=credential.student_id,
            last_sync_at=credential.last_sync_at,
        )
    return FudanStatusResponse(connected=False)


@router.post("/fudan/sync", response_model=SyncResponse)
async def sync_fudan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    触发复旦数据同步：
    并发抓取课表、考试、eLearning 作业并增量导入
    """
    from app.services.fudan_service import sync_fudan_data as do_sync
    result = await do_sync(db, current_user.id)

    if result["success"]:
        return SyncResponse(
            success=True,
            data=result.get("data"),
            message=result.get("message", "同步完成"),
        )
    else:
        return SyncResponse(success=False, message=result.get("message", "同步失败"))


@router.delete("/fudan/disconnect", response_model=FudanConnectResponse)
async def disconnect_fudan_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """断开复旦教务连接"""
    success = await disconnect_fudan(db, current_user.id)
    return FudanConnectResponse(
        success=success,
        message="已断开复旦连接" if success else "未找到复旦连接",
    )