from fastapi import APIRouter

from app.core.config import settings

from .user import router as user_router
from .university import router as university_router
from .lab import router as lab_router

router = APIRouter(
    prefix=settings.api.v1.prefix,
)

router.include_router(user_router)
router.include_router(university_router)
router.include_router(lab_router)

__all__ = ["router"]
