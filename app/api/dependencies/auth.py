from fastapi import (
    HTTPException,
    status,
    Request,
    Depends
)
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from app.domain.user.schema import UserOutSchema
from app.domain.user.repository import UserRepository
from app.enums.enums import UserRole
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

        request.state.user = user.id
        set_user_email(user.email, request)

        return user
    except (JWTError, NotFoundError, ValueError) as exc:
        raise credentials_exception from exc


async def require_admin_user(
    current_user: UserOutSchema = Depends(get_current_user),
) -> UserOutSchema:
    """Require an authenticated admin user."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
