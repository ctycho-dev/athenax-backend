from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin_user
from app.api.dependencies.services import get_subscriber_service
from app.core.config import settings
from app.domain.subscriber.schema import SubscriberCreateSchema, SubscriberOutSchema
from app.domain.subscriber.service import SubscriberService
from app.domain.user.schema import UserOutSchema
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix=settings.api.v1.subscriber, tags=["Subscriber"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SubscriberOutSchema)
@limiter.limit("10/minute")
async def subscribe(
    request: Request,
    payload: SubscriberCreateSchema,
    db: AsyncSession = Depends(get_db),
    service: SubscriberService = Depends(get_subscriber_service),
):
    return await service.subscribe(db, payload)


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_by_token(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    service: SubscriberService = Depends(get_subscriber_service),
):
    await service.unsubscribe_by_token(db, token)
    return HTMLResponse(
        content="<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                "<h2>You've been unsubscribed.</h2>"
                "<p>You won't receive any more emails from AthenaX.</p>"
                "</body></html>"
    )


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
