from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin_user
from app.api.dependencies.services import get_subscriber_service
from app.core.config import settings
from app.domain.subscriber.schema import SubscriberCreateSchema
from app.domain.subscriber.service import SubscriberService
from app.domain.user.schema import UserOutSchema
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix=settings.api.v1.subscriber, tags=["Subscriber"])


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def subscribe(
    request: Request,
    payload: SubscriberCreateSchema,
    db: AsyncSession = Depends(get_db),
    service: SubscriberService = Depends(get_subscriber_service),
) -> None:
    await service.subscribe(db, payload)


@router.get("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_by_token(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    service: SubscriberService = Depends(get_subscriber_service),
) -> None:
    await service.unsubscribe_by_token(db, token)


@router.delete("/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def unsubscribe_by_id(
    request: Request,
    subscriber_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: SubscriberService = Depends(get_subscriber_service),
):
    await service.unsubscribe_by_id(db, subscriber_id)
