from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_db,
    get_product_service,
)
from app.api.dependencies.auth import get_optional_user, require_admin_user, require_founder_or_admin, require_investor_user
from app.core.config import settings
from app.domain.product.schema import (
    BookmarkSchema,
    CommentCreateSchema,
    CommentOutSchema,
    CommentUpdateSchema,
    InvestorInterestSchema,
    ProductCreateSchema,
    ProductListSchema,
    ProductOutSchema,
    ProductStatusUpdateSchema,
    ProductUpdateSchema,
    ToggleOutSchema,
    VoteSchema,
)
from app.enums.enums import ProductStage, ProductStatus
from app.domain.product.service import ProductService
from app.domain.user.schema import UserOutSchema
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix=settings.api.v1.product, tags=["Product"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProductOutSchema)
@limiter.limit("30/minute")
async def create_product(
    request: Request,
    payload: ProductCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_founder_or_admin),
    service: ProductService = Depends(get_product_service),
):
    return await service.create(db, payload, current_user=current_user)


@router.get("", response_model=list[ProductListSchema])
@limiter.limit("60/minute")
async def list_products(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: ProductStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.list(db, limit=limit, offset=offset, status=status, current_user=current_user)


@router.get("/me", response_model=list[ProductListSchema])
@limiter.limit("60/minute")
async def list_my_products(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: ProductStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_founder_or_admin),
    service: ProductService = Depends(get_product_service),
):
    return await service.list(db, limit=limit, offset=offset, status=status, current_user=current_user, owner_only=True)


@router.get("/slug/{slug}", response_model=ProductOutSchema)
@limiter.limit("60/minute")
async def get_product_by_slug(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.get_by_slug(db, slug=slug, current_user=current_user)


@router.get("/{product_id}", response_model=ProductOutSchema)
@limiter.limit("60/minute")
async def get_product(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
):
    return await service.get_by_id(db, product_id=product_id)


@router.patch("/{product_id}", response_model=ProductOutSchema)
@limiter.limit("30/minute")
async def update_product(
    request: Request,
    product_id: int,
    payload: ProductUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_founder_or_admin),
    service: ProductService = Depends(get_product_service),
):
    return await service.update(db, product_id=product_id, data=payload, current_user=current_user)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_product(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_founder_or_admin),
    service: ProductService = Depends(get_product_service),
):
    await service.delete_by_id(db, product_id=product_id, current_user=current_user)


@router.patch("/{product_id}/status", response_model=ProductOutSchema)
@limiter.limit("30/minute")
async def update_product_status(
    request: Request,
    product_id: int,
    payload: ProductStatusUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update_status(db, product_id=product_id, data=payload, current_user=current_user)


@router.put("/{product_id}/vote", response_model=ToggleOutSchema)
@limiter.limit("60/minute")
async def toggle_vote(
    request: Request,
    product_id: int,
    payload: VoteSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.toggle_vote(db, product_id=product_id, toggled=payload.voted, current_user=current_user)


@router.put("/{product_id}/bookmark", response_model=ToggleOutSchema)
@limiter.limit("60/minute")
async def toggle_bookmark(
    request: Request,
    product_id: int,
    payload: BookmarkSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.toggle_bookmark(db, product_id=product_id, toggled=payload.bookmarked, current_user=current_user)


@router.put("/{product_id}/interest", response_model=ToggleOutSchema)
@limiter.limit("60/minute")
async def toggle_investor_interest(
    request: Request,
    product_id: int,
    payload: InvestorInterestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_investor_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.toggle_investor_interest(db, product_id=product_id, toggled=payload.interested, current_user=current_user)


@router.get("/{product_id}/comments", response_model=list[CommentOutSchema])
@limiter.limit("60/minute")
async def list_comments(
    request: Request,
    product_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_comments(db, product_id=product_id, limit=limit, offset=offset)


@router.post("/{product_id}/comments", status_code=status.HTTP_201_CREATED, response_model=CommentOutSchema)
@limiter.limit("30/minute")
async def create_comment(
    request: Request,
    product_id: int,
    payload: CommentCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.create_comment(db, product_id=product_id, data=payload, current_user=current_user)


@router.patch("/{product_id}/comments/{comment_id}", response_model=CommentOutSchema)
@limiter.limit("30/minute")
async def update_comment(
    request: Request,
    product_id: int,
    comment_id: int,
    payload: CommentUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update_comment(db, product_id=product_id, comment_id=comment_id, data=payload, current_user=current_user)


@router.delete("/{product_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_comment(
    request: Request,
    product_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    await service.delete_comment(db, product_id=product_id, comment_id=comment_id, current_user=current_user)
