from fastapi import APIRouter

from app.core.config import settings

from .user import router as user_router
from .university import router as university_router
from .lab import router as lab_router
from .category import router as category_router
from .paper import router as paper_router
from .product import router as product_router
from .enums import router as enums_router

router = APIRouter(
    prefix=settings.api.v1.prefix,
)

router.include_router(user_router)
router.include_router(university_router)
router.include_router(lab_router)
router.include_router(category_router)
router.include_router(paper_router)
router.include_router(product_router)
router.include_router(enums_router)

__all__ = ["router"]
