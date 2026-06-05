from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_category_service,
    get_db,
    get_product_service,
    get_system_user,
    verify_internal_key,
)
from app.core.config import settings
from app.domain.category.schema import CategoryOutSchema
from app.domain.category.service import CategoryService
from app.domain.product.schema import ProductCreateSchema, ProductOutSchema
from app.domain.product.service import ProductService
from app.domain.user.schema import UserOutSchema
from app.middleware.rate_limiter import limiter

# Service-to-service endpoints. The whole router is gated by the shared X-Internal-Key
# secret; records created here are attributed to the seeded system user.
router = APIRouter(
    prefix=settings.api.v1.internal,
    tags=["Internal"],
    dependencies=[Depends(verify_internal_key)],
)


@router.post("/products", status_code=status.HTTP_201_CREATED, response_model=ProductOutSchema)
@limiter.limit("60/minute")
async def create_product(
    request: Request,
    payload: ProductCreateSchema,
    db: AsyncSession = Depends(get_db),
    system_user: UserOutSchema = Depends(get_system_user),
    service: ProductService = Depends(get_product_service),
):
    # Reuses the exact user-submit flow; created_by_id = system user, status PENDING.
    return await service.create(db, payload, current_user=system_user)


@router.get("/categories/by-name", response_model=CategoryOutSchema)
@limiter.limit("60/minute")
async def get_category_by_name(
    request: Request,
    name: str,
    db: AsyncSession = Depends(get_db),
    service: CategoryService = Depends(get_category_service),
):
    return await service.get_by_name(db, name, is_subcategory=False)


@router.get("/subcategories/by-name", response_model=CategoryOutSchema)
@limiter.limit("60/minute")
async def get_subcategory_by_name(
    request: Request,
    name: str,
    db: AsyncSession = Depends(get_db),
    service: CategoryService = Depends(get_category_service),
):
    return await service.get_by_name(db, name, is_subcategory=True)


@router.get("/products/by-name", response_model=ProductOutSchema)
@limiter.limit("60/minute")
async def get_product_by_name(
    request: Request,
    name: str,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
):
    return await service.get_by_name(db, name)
