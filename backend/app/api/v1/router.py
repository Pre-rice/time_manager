"""v1 路由汇总"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.goals import router as goals_router
from app.api.v1.special_dates import router as special_dates_router
from app.api.v1.ai_config import router as ai_config_router
from app.api.v1.ai import router as ai_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(events_router)
router.include_router(tasks_router)
router.include_router(goals_router)
router.include_router(special_dates_router)
router.include_router(ai_config_router)
router.include_router(ai_router)
