"""外部数据导入的请求/响应模型"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class FudanConnectRequest(BaseModel):
    """连接复旦教务系统请求"""
    student_id: str = Field(..., description="复旦学号")
    password: str = Field(..., description="UIS 密码")


class FudanConnectResponse(BaseModel):
    """连接结果"""
    success: bool
    message: str


class FudanStatusResponse(BaseModel):
    """连接状态"""
    connected: bool
    student_id: str | None = None
    last_sync_at: datetime | None = None


class ParsedEvent(BaseModel):
    """解析出的日程"""
    title: str
    start_time: str  # ISO 格式
    end_time: str | None = None
    location: str | None = None
    description: str | None = None
    event_type: str = "class"  # class, exam
    rrule: str | None = None  # 重复规则（课表用）


class ParsedTask(BaseModel):
    """解析出的待办"""
    title: str
    deadline: str | None = None  # ISO 格式
    description: str | None = None
    priority: int = 1


class SyncResult(BaseModel):
    """同步结果"""
    events_created: int
    events_updated: int
    tasks_created: int
    tasks_updated: int
    errors: list[str] = []


class SyncResponse(BaseModel):
    """同步响应"""
    success: bool
    data: SyncResult | None = None
    message: str = ""