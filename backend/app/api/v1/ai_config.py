"""AI 配置 API"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.crypto import encrypt_api_key
from app.core.database import get_db
from app.models.ai_config import AIConfig
from app.models.user import User
from app.schemas.ai import AIConfigCreate, AIConfigResponse, AIConfigUpdate

router = APIRouter(prefix="/ai/config", tags=["AI 配置"])


@router.get("/", response_model=AIConfigResponse | None)
async def get_ai_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户的 AI 配置（不返回 api_key）"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.user_id == current_user.id).limit(1)
    )
    config = result.scalar_one_or_none()
    if not config:
        return None
    return AIConfigResponse(
        id=str(config.id),
        provider=config.provider,
        api_endpoint=config.api_endpoint,
        model_name=config.model_name,
    )


@router.put("/", response_model=AIConfigResponse)
async def upsert_ai_config(
    data: AIConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建或更新 AI 配置"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.user_id == current_user.id).limit(1)
    )
    config = result.scalar_one_or_none()

    encrypted_key = encrypt_api_key(data.api_key)

    if config:
        config.provider = data.provider
        config.api_endpoint = data.api_endpoint
        config.encrypted_api_key = encrypted_key
        config.model_name = data.model_name
    else:
        config = AIConfig(
            user_id=current_user.id,
            provider=data.provider,
            api_endpoint=data.api_endpoint,
            encrypted_api_key=encrypted_key,
            model_name=data.model_name,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return AIConfigResponse(
        id=str(config.id),
        provider=config.provider,
        api_endpoint=config.api_endpoint,
        model_name=config.model_name,
    )


@router.patch("/", response_model=AIConfigResponse)
async def update_ai_config(
    data: AIConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部分更新 AI 配置"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.user_id == current_user.id).limit(1)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="未找到 AI 配置")

    if data.provider is not None:
        config.provider = data.provider
    if data.api_endpoint is not None:
        config.api_endpoint = data.api_endpoint
    if data.api_key is not None:
        config.encrypted_api_key = encrypt_api_key(data.api_key)
    if data.model_name is not None:
        config.model_name = data.model_name

    await db.commit()
    await db.refresh(config)

    return AIConfigResponse(
        id=str(config.id),
        provider=config.provider,
        api_endpoint=config.api_endpoint,
        model_name=config.model_name,
    )


@router.delete("/", status_code=204)
async def delete_ai_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除 AI 配置"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.user_id == current_user.id).limit(1)
    )
    config = result.scalar_one_or_none()
    if config:
        await db.delete(config)
        await db.commit()