from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin_user
from app.api.dependencies.auth import get_optional_user
from app.api.dependencies.services import get_broadcast_service
from app.core.config import settings
from app.domain.broadcast.schema import (
    BroadcastCreateSchema,
    BroadcastOutSchema,
    BroadcastSummarySchema,
    BroadcastUpdateSchema,
)
from app.domain.broadcast.service import BroadcastService
from app.domain.user.schema import UserOutSchema
from app.enums.enums import BroadcastStatus, BroadcastType
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix=settings.api.v1.broadcast, tags=["Broadcast"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BroadcastOutSchema)
@limiter.limit("30/minute")
async def create_broadcast(
    request: Request,
    payload: BroadcastCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.create(db, payload, current_user=current_user)


@router.get("", response_model=list[BroadcastSummarySchema])
@limiter.limit("60/minute")
async def list_broadcasts(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: BroadcastStatus | None = None,
    broadcast_type: BroadcastType | None = Query(default=None, alias="broadcastType"),
    tag: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.list_broadcasts(
        db, limit=limit, offset=offset, status=status,
        broadcast_type=broadcast_type, tag=tag, current_user=current_user,
    )


@router.get("/slug/{slug}", response_model=BroadcastOutSchema)
@limiter.limit("60/minute")
async def get_broadcast_by_slug(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.get_by_slug(db, slug=slug, current_user=current_user)


@router.get("/{broadcast_id}", response_model=BroadcastOutSchema)
@limiter.limit("60/minute")
async def get_broadcast(
    request: Request,
    broadcast_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.get_by_id(db, broadcast_id=broadcast_id, current_user=current_user)


@router.patch("/{broadcast_id}", response_model=BroadcastOutSchema)
@limiter.limit("30/minute")
async def update_broadcast(
    request: Request,
    broadcast_id: int,
    payload: BroadcastUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.update(db, broadcast_id=broadcast_id, data=payload, current_user=current_user)


@router.delete("/{broadcast_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_broadcast(
    request: Request,
    broadcast_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: BroadcastService = Depends(get_broadcast_service),
):
    await service.delete_by_id(db, broadcast_id=broadcast_id, current_user=current_user)
