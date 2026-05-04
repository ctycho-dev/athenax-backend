from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_db,
    get_product_service,
)
from app.api.dependencies.services import get_storage_service
from app.common.storage import R2StorageService
from app.api.dependencies.auth import get_optional_user, require_admin_user, require_investor_user
from app.common.schema import PaginatedSchema
from app.core.config import settings
from app.domain.product.schema import (
    BookmarkSchema,
    CommentCreateSchema,
    CommentOutSchema,
    CommentPinSchema,
    CommentUpdateSchema,
    InvestorInterestSchema,
    ProductCreateSchema,
    ProductListSchema,
    ProductOutSchema,
    ProductReleaseStatsSchema,
    ProductStatusUpdateSchema,
    ProductSummarySchema,
    ProductUpdateSchema,
    ToggleOutSchema,
    VoteSchema,
    ProductLinkCreateSchema, ProductLinkUpdateSchema, ProductLinkOutSchema,
    ProductMediaCreateSchema, ProductMediaUpdateSchema, ProductMediaOutSchema,
    TeamMemberCreateSchema, TeamMemberUpdateSchema, TeamMemberStatusUpdateSchema, TeamMemberOutSchema,
    ProductBackerCreateSchema, ProductBackerOutSchema,
    ProductVoiceCreateSchema, ProductVoiceUpdateSchema, ProductVoiceOutSchema,
    BountyCreateSchema, BountyUpdateSchema, BountyOutSchema,
)
from app.enums.enums import ProductDateFilter, ProductSortBy, ProductStage, ProductStatus
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
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.create(db, payload, current_user=current_user)


@router.get("", response_model=PaginatedSchema[ProductListSchema])
@limiter.limit("60/minute")
async def list_products(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: ProductStatus | None = None,
    category_id: int | None = None,
    date_filter: ProductDateFilter | None = None,
    sort_by: ProductSortBy | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.list(
        db, limit=limit, offset=offset, status=status, current_user=current_user,
        category_id=category_id, date_filter=date_filter, sort_by=sort_by,
    )


@router.get("/stats", response_model=ProductReleaseStatsSchema)
@limiter.limit("60/minute")
async def get_product_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
):
    return await service.get_release_stats(db)


@router.get("/me", response_model=PaginatedSchema[ProductListSchema])
@limiter.limit("60/minute")
async def list_my_products(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: ProductStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.list(db, limit=limit, offset=offset, status=status, current_user=current_user, owner_only=True)


@router.get("/me/voted", response_model=list[ProductSummarySchema])
@limiter.limit("60/minute")
async def list_voted_products(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_voted(db, limit=limit, offset=offset, current_user=current_user)


@router.get("/me/bookmarked", response_model=list[ProductSummarySchema])
@limiter.limit("60/minute")
async def list_bookmarked_products(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_bookmarked(db, limit=limit, offset=offset, current_user=current_user)


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
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.get_by_id(db, product_id=product_id, current_user=current_user)


@router.patch("/{product_id}", response_model=ProductOutSchema)
@limiter.limit("30/minute")
async def update_product(
    request: Request,
    product_id: int,
    payload: ProductUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update(db, product_id=product_id, data=payload, current_user=current_user)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_product(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
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


@router.patch("/{product_id}/comments/{comment_id}/pin", response_model=CommentOutSchema)
@limiter.limit("30/minute")
async def pin_comment(
    request: Request,
    product_id: int,
    comment_id: int,
    payload: CommentPinSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.pin_comment(db, product_id=product_id, comment_id=comment_id, data=payload, current_user=current_user)


# -------------------------
# Product Links
# -------------------------

@router.get("/{product_id}/links", response_model=list[ProductLinkOutSchema])
@limiter.limit("60/minute")
async def list_links(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_links(db, product_id=product_id)


@router.post("/{product_id}/links", status_code=status.HTTP_201_CREATED, response_model=ProductLinkOutSchema)
@limiter.limit("30/minute")
async def create_link(
    request: Request,
    product_id: int,
    payload: ProductLinkCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.create_link(db, product_id=product_id, data=payload, current_user=current_user)


@router.patch("/{product_id}/links/{link_id}", response_model=ProductLinkOutSchema)
@limiter.limit("30/minute")
async def update_link(
    request: Request,
    product_id: int,
    link_id: int,
    payload: ProductLinkUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update_link(db, product_id=product_id, link_id=link_id, data=payload, current_user=current_user)


@router.delete("/{product_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_link(
    request: Request,
    product_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    await service.delete_link(db, product_id=product_id, link_id=link_id, current_user=current_user)


# -------------------------
# Product Media
# -------------------------

@router.get("/{product_id}/media", response_model=list[ProductMediaOutSchema])
@limiter.limit("60/minute")
async def list_media(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_media(db, product_id=product_id)


@router.post("/{product_id}/media", status_code=status.HTTP_201_CREATED, response_model=ProductMediaOutSchema)
@limiter.limit("30/minute")
async def create_media(
    request: Request,
    product_id: int,
    payload: ProductMediaCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.create_media(db, product_id=product_id, data=payload, current_user=current_user)


@router.post("/{product_id}/media/upload", status_code=status.HTTP_201_CREATED, response_model=ProductMediaOutSchema)
@limiter.limit("10/minute")
async def upload_media(
    request: Request,
    product_id: int,
    file: UploadFile = File(...),
    sort_order: int | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
    storage: R2StorageService = Depends(get_storage_service),
):
    return await service.upload_media(
        db,
        product_id=product_id,
        file=file,
        sort_order=sort_order,
        current_user=current_user,
        storage=storage,
    )


@router.patch("/{product_id}/media/{media_id}", response_model=ProductMediaOutSchema)
@limiter.limit("30/minute")
async def update_media(
    request: Request,
    product_id: int,
    media_id: int,
    payload: ProductMediaUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update_media(db, product_id=product_id, media_id=media_id, data=payload, current_user=current_user)


@router.delete("/{product_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_media(
    request: Request,
    product_id: int,
    media_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    await service.delete_media(db, product_id=product_id, media_id=media_id, current_user=current_user)


# -------------------------
# Product Team
# -------------------------

@router.get("/{product_id}/team", response_model=list[TeamMemberOutSchema])
@limiter.limit("60/minute")
async def list_team(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_team(db, product_id=product_id, current_user=current_user)


@router.post("/{product_id}/team", status_code=status.HTTP_201_CREATED, response_model=TeamMemberOutSchema)
@limiter.limit("30/minute")
async def create_team_member(
    request: Request,
    product_id: int,
    payload: TeamMemberCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.create_team_member(db, product_id=product_id, data=payload, current_user=current_user)


@router.patch("/{product_id}/team/{member_id}", response_model=TeamMemberOutSchema)
@limiter.limit("30/minute")
async def update_team_member(
    request: Request,
    product_id: int,
    member_id: int,
    payload: TeamMemberUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update_team_member(db, product_id=product_id, member_id=member_id, data=payload, current_user=current_user)


@router.patch("/{product_id}/team/{member_id}/status", response_model=TeamMemberOutSchema)
@limiter.limit("30/minute")
async def update_team_member_status(
    request: Request,
    product_id: int,
    member_id: int,
    payload: TeamMemberStatusUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update_team_member_status(db, product_id=product_id, member_id=member_id, data=payload, current_user=current_user)


@router.delete("/{product_id}/team/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_team_member(
    request: Request,
    product_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    await service.delete_team_member(db, product_id=product_id, member_id=member_id, current_user=current_user)


# -------------------------
# Product Backers
# -------------------------

@router.get("/{product_id}/backers", response_model=list[ProductBackerOutSchema])
@limiter.limit("60/minute")
async def list_backers(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_backers(db, product_id=product_id)


@router.post("/{product_id}/backers", status_code=status.HTTP_201_CREATED, response_model=ProductBackerOutSchema)
@limiter.limit("30/minute")
async def create_backer(
    request: Request,
    product_id: int,
    payload: ProductBackerCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.create_backer(db, product_id=product_id, data=payload, current_user=current_user)


@router.delete("/{product_id}/backers/{backer_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_backer(
    request: Request,
    product_id: int,
    backer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    await service.delete_backer(db, product_id=product_id, backer_id=backer_id, current_user=current_user)


# -------------------------
# Product Voices
# -------------------------

@router.get("/{product_id}/voices", response_model=list[ProductVoiceOutSchema])
@limiter.limit("60/minute")
async def list_voices(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_voices(db, product_id=product_id)


@router.post("/{product_id}/voices", status_code=status.HTTP_201_CREATED, response_model=ProductVoiceOutSchema)
@limiter.limit("30/minute")
async def create_voice(
    request: Request,
    product_id: int,
    payload: ProductVoiceCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.create_voice(db, product_id=product_id, data=payload, current_user=current_user)


@router.patch("/{product_id}/voices/{voice_id}", response_model=ProductVoiceOutSchema)
@limiter.limit("30/minute")
async def update_voice(
    request: Request,
    product_id: int,
    voice_id: int,
    payload: ProductVoiceUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update_voice(db, product_id=product_id, voice_id=voice_id, data=payload, current_user=current_user)


@router.delete("/{product_id}/voices/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_voice(
    request: Request,
    product_id: int,
    voice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    await service.delete_voice(db, product_id=product_id, voice_id=voice_id, current_user=current_user)


# -------------------------
# Bounties
# -------------------------

@router.get("/{product_id}/bounties", response_model=list[BountyOutSchema])
@limiter.limit("60/minute")
async def list_bounties(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_bounties(db, product_id=product_id)


@router.post("/{product_id}/bounties", status_code=status.HTTP_201_CREATED, response_model=BountyOutSchema)
@limiter.limit("30/minute")
async def create_bounty(
    request: Request,
    product_id: int,
    payload: BountyCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.create_bounty(db, product_id=product_id, data=payload, current_user=current_user)


@router.patch("/{product_id}/bounties/{bounty_id}", response_model=BountyOutSchema)
@limiter.limit("30/minute")
async def update_bounty(
    request: Request,
    product_id: int,
    bounty_id: int,
    payload: BountyUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update_bounty(db, product_id=product_id, bounty_id=bounty_id, data=payload, current_user=current_user)


@router.delete("/{product_id}/bounties/{bounty_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_bounty(
    request: Request,
    product_id: int,
    bounty_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ProductService = Depends(get_product_service),
):
    await service.delete_bounty(db, product_id=product_id, bounty_id=bounty_id, current_user=current_user)
