from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logger import get_logger
from app.domain.subscriber.repository import SubscriberRepository
from app.domain.subscriber.schema import SubscriberCreateSchema, SubscriberOutSchema
from app.exceptions.exceptions import NotFoundError
from app.infrastructure.email.service import EmailDeliveryError, EmailService

logger = get_logger(__name__)


class SubscriberService:
    def __init__(self, repo: SubscriberRepository, email_service: EmailService) -> None:
        self.repo = repo
        self.email_service = email_service

    async def subscribe(self, db: AsyncSession, data: SubscriberCreateSchema) -> SubscriberOutSchema:
        token = str(uuid.uuid4())
        subscriber = await self.repo.create(db, {"email": str(data.email), "is_active": True, "unsubscribe_token": token})
        await db.commit()
        await db.refresh(subscriber)

        unsubscribe_url = f"{settings.subscriber_unsubscribe_url}?token={token}"
        try:
            await self.email_service.send_subscriber_welcome_email(subscriber.email, unsubscribe_url)
        except EmailDeliveryError:
            logger.warning("subscriber_welcome_email_failed", extra={"email": subscriber.email})

        return SubscriberOutSchema.model_validate(subscriber, from_attributes=True)

    async def unsubscribe_by_id(self, db: AsyncSession, subscriber_id: int) -> None:
        await self.repo.update(db, subscriber_id, {"is_active": False})
        await db.commit()

    async def unsubscribe_by_token(self, db: AsyncSession, token: str) -> None:
        subscriber = await self.repo.get_by_unsubscribe_token(db, token)
        if subscriber is None:
            raise NotFoundError("Subscriber not found")
        await self.repo.update_instance(db, subscriber, {"is_active": False})
        await db.commit()
