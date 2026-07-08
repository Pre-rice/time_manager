"""AI 服务封装（LiteLLM）"""

import json
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_api_key
from app.models.ai_config import AIConfig
from app.models.event import Event
from app.models.task import Task


async def get_user_ai_config(db: AsyncSession, user_id: uuid.UUID) -> AIConfig | None:
    """获取用户的 AI 配置"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.user_id == user_id).limit(1)
    )
    return result.scalar_one_or_none()


def build_litellm_params(config: AIConfig) -> dict:
    """构建 LiteLLM 调用参数"""
    api_key = decrypt_api_key(config.encrypted_api_key)
    params = {
        "model": config.model_name,
        "api_key": api_key,
        "temperature": 0.3,
    }
    if config.api_endpoint:
        params["api_base"] = config.api_endpoint
    return params


async def call_llm(
    config: AIConfig, system_prompt: str, user_prompt: str
) -> str:
    """调用 LLM（同步执行，适用短期请求）"""
    from litellm import completion

    params = build_litellm_params(config)
    params["messages"] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = completion(**params)
    return response.choices[0].message.content or ""


async def extract_from_text(
    db: AsyncSession, user_id: uuid.UUID, text: str
) -> list[dict]:
    """自然语言提取日程/待办"""
    config = await get_user_ai_config(db, user_id)
    if not config:
        raise ValueError("请先在设置中配置 AI")

    system_prompt = """你是一个任务提取助手。从用户的自然语言描述中提取日程和待办事项。
返回 JSON 数组，每个元素包含：
- type: "event" 或 "task"
- title: 标题
- start_time: 开始时间 (ISO 格式，如 "2026-07-10T14:00:00")
- end_time: 结束时间 (可选)
- deadline: 截止时间 (可选，仅 task 类型)
- priority: 优先级 0-3 (可选)
- description: 描述 (可选)

只返回 JSON 数组，不要其他文字。"""

    content = await call_llm(config, system_prompt, text)
    # 尝试解析 JSON
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0]
    try:
        items = json.loads(content)
        if isinstance(items, list):
            return items
    except json.JSONDecodeError:
        pass
    return []


async def suggest_time(
    db: AsyncSession, user_id: uuid.UUID, title: str, duration_minutes: int = 60
) -> list[dict]:
    """AI 时间分配建议"""
    config = await get_user_ai_config(db, user_id)
    if not config:
        raise ValueError("请先在设置中配置 AI")

    # 获取用户未来日程
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(Event).where(
            Event.user_id == user_id,
            Event.start_time >= today.isoformat(),
        ).order_by(Event.start_time)
    )
    events = result.scalars().all()

    # 获取待办
    result = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.status != "done",
        )
    )
    tasks = result.scalars().all()

    events_summary = "\n".join(
        [f"- {e.title} ({e.start_time} ~ {e.end_time})" for e in events if e.start_time]
    ) or "无"

    tasks_summary = "\n".join(
        [f"- {t.title} (截止: {t.deadline})" for t in tasks if t.deadline]
    ) or "无"

    system_prompt = f"""你是一个时间管理助手。用户想安排 "{title}"，需要 {duration_minutes} 分钟。

用户的未来日程：
{events_summary}

待办任务：
{tasks_summary}

请分析用户空闲时间，返回建议时间段 JSON 数组：
- start_time: 建议开始时间 (ISO)
- end_time: 建议结束时间 (ISO)
- reason: 建议理由

最多返回 3 个建议，按推荐度排序。只返回 JSON 数组。"""

    content = await call_llm(config, system_prompt, title)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0]
    try:
        items = json.loads(content)
        if isinstance(items, list):
            return items
    except json.JSONDecodeError:
        pass
    return []


async def generate_morning_message(
    db: AsyncSession, user_id: uuid.UUID
) -> str:
    """生成早安消息"""
    config = await get_user_ai_config(db, user_id)
    if not config:
        raise ValueError("请先在设置中配置 AI")

    today_str = date.today().isoformat()

    # 获取今天日程
    result = await db.execute(
        select(Event).where(
            Event.user_id == user_id,
            Event.start_time >= today_str,
            Event.start_time < f"{today_str}T23:59:59",
        ).order_by(Event.start_time)
    )
    events = result.scalars().all()

    # 获取过期/今天到期的待办
    result = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.status != "done",
            Task.deadline <= f"{today_str}T23:59:59",
        )
    )
    tasks = result.scalars().all()

    events_text = "\n".join(
        [f"- {e.title} ({e.start_time or '全天'})" for e in events]
    ) or "今天没有日程安排 🎉"

    tasks_text = "\n".join(
        [f"- {t.title} (优先级: {'无低中高'[t.priority] if t.priority else '无'})" for t in tasks]
    ) or "没有待办截止 👍"

    system_prompt = f"""你是一个温暖的早安助手。今天是 {today_str}。

今天的日程：
{events_text}

待办事项：
{tasks_text}

生成一段简短、人性化的早安提醒消息（200字以内），包含：
1. 温暖的早安问候
2. 今天的日程提醒
3. 待办鼓励
4. 一句加油的话

语气要温暖自然，不要过于机械。"""

    return await call_llm(config, system_prompt, "生成早安消息")