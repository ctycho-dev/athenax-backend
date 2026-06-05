import secrets

from fastapi import (
    HTTPException,
    status,
    Request,
    Header,
    Depends
)
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from app.core.config import settings
from app.domain.user.schema import UserOutSchema
from app.domain.user.repository import UserRepository
from app.enums.enums import UserRole, SYSTEM_USER_EMAIL
from app.exceptions.exceptions import NotFoundError
from app.api.dependencies.db import get_db
from app.middleware.logging import set_user_email
from app.utils.oauth2 import verify_access_token


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserOutSchema:
    """Get current user from an HTTP-only cookie."""
    user_repo = UserRepository()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception
    try:
        token_data = verify_access_token(token, credentials_exception)
        user_id = token_data.id
        if user_id is None:
            raise credentials_exception

        # Fetch the user from the repository
        user = await user_repo.get_by_id(db, int(user_id))

        if not user.verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email is not verified",
            )

        request.state.user = user.id
        set_user_email(user.email, request)

        return user
    except (JWTError, NotFoundError, ValueError) as exc:
        raise credentials_exception from exc


def require_roles(*roles: UserRole, detail: str = "Not enough permissions"):
    allowed_roles = set(roles)
    async def dependency(
        current_user: UserOutSchema = Depends(get_current_user),
    ) -> UserOutSchema:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        return current_user
    return dependency


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserOutSchema | None:
    """Soft authentication dependency for public endpoints that behave differently based on who is asking.
    when no valid session is present — allowing the endpoint to remain publicly accessible.

    Used on the product list endpoint so the service can apply role-based filtering:
      - None (unauthenticated) or non-admin → approved products only
      - Admin → can filter by any status or retrieve all products
    """
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


async def verify_internal_key(x_internal_key: str | None = Header(default=None)) -> None:
    """Gate internal service-to-service endpoints with the shared X-Internal-Key secret."""
    expected = settings.auth.internal_api_key
    # Reject when the key is unconfigured so endpoints never open up by accident.
    if not expected or not x_internal_key or not secrets.compare_digest(x_internal_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal key",
        )


async def get_system_user(db: AsyncSession = Depends(get_db)) -> UserOutSchema:
    """Resolve the seeded system user that owns records created via internal endpoints."""
    user = await UserRepository().get_by_email(db, SYSTEM_USER_EMAIL)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System user not provisioned",
        )
    return UserOutSchema.model_validate(user, from_attributes=True)


require_admin_user = require_roles(UserRole.ADMIN, UserRole.BD, detail="Admin role required")
require_researcher_user = require_roles(UserRole.RESEARCHER, UserRole.ADMIN, UserRole.BD, detail="Researcher role required")
require_founder_or_admin = require_roles(UserRole.FOUNDER, UserRole.ADMIN, UserRole.BD, detail="Founder or admin role required")
require_investor_user = require_roles(UserRole.INVESTOR, detail="Investor role required")
