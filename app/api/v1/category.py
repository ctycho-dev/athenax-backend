from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin_user
from app.api.dependencies.services import get_category_service
from app.core.config import settings
from app.domain.category.schema import CategoryCreateSchema, CategoryOutSchema, CategoryUpdateSchema
from app.domain.category.service import CategoryService
from app.domain.user.schema import UserOutSchema
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix=settings.api.v1.category, tags=["Category"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CategoryOutSchema)
@limiter.limit("30/minute")
async def create_category(
    request: Request,
    payload: CategoryCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: CategoryService = Depends(get_category_service),
):
    return await service.create(db, payload, current_user=current_user)


@router.get("", response_model=list[CategoryOutSchema])
@limiter.limit("60/minute")
async def list_categories(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: CategoryService = Depends(get_category_service),
):
    return await service.list(db, limit=limit, offset=offset)


@router.get("/{category_id}", response_model=CategoryOutSchema)
@limiter.limit("60/minute")
async def get_category(
    request: Request,
    category_id: int,
    db: AsyncSession = Depends(get_db),
    service: CategoryService = Depends(get_category_service),
):
    return await service.get_by_id(db, category_id=category_id)


@router.patch("/{category_id}", response_model=CategoryOutSchema)
@limiter.limit("30/minute")
async def update_category(
    request: Request,
    category_id: int,
    payload: CategoryUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: CategoryService = Depends(get_category_service),
):
    return await service.update(db, category_id=category_id, data=payload, current_user=current_user)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_category(
    request: Request,
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: CategoryService = Depends(get_category_service),
):
    await service.delete_by_id(db, category_id=category_id, current_user=current_user)
