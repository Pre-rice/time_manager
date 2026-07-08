"""AI 相关 Pydantic 模型"""

from pydantic import BaseModel


class AIConfigCreate(BaseModel):
    provider: str = "openai"
    api_endpoint: str | None = None
    api_key: str
    model_name: str = "gpt-4o-mini"


class AIConfigUpdate(BaseModel):
    provider: str | None = None
    api_endpoint: str | None = None
    api_key: str | None = None
    model_name: str | None = None


class AIConfigResponse(BaseModel):
    id: str
    provider: str
    api_endpoint: str | None = None
    model_name: str
    # api_key 不返回


class ExtractRequest(BaseModel):
    text: str


class ExtractItem(BaseModel):
    type: str  # event, task
    title: str
    start_time: str | None = None
    end_time: str | None = None
    deadline: str | None = None
    priority: int | None = None
    description: str | None = None


class ExtractResponse(BaseModel):
    items: list[ExtractItem]


class SuggestTimeRequest(BaseModel):
    title: str
    duration_minutes: int = 60
    preferred_days: list[str] | None = None  # "2026-07-10"


class SuggestTimeItem(BaseModel):
    start_time: str
    end_time: str
    reason: str


class SuggestTimeResponse(BaseModel):
    suggestions: list[SuggestTimeItem]


class MorningMessageResponse(BaseModel):
    message: str
    date: str