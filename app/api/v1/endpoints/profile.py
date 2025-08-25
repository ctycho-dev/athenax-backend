from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request
)
from app.middleware.rate_limiter import limiter
from app.core.dependencies import get_current_user
from app.domain.profile.schema import (
    ProfileCreate,
    ProfileOut,
    ProfileUpdate
)
from app.domain.user.model import User
from app.core.logger import get_logger
from app.core.dependencies import get_profile_service
from app.domain.profile.service import ProfileService


logger = get_logger()

router = APIRouter()


@router.post("/", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_profile(
    request: Request,
    data: ProfileCreate,
    service: ProfileService = Depends(get_profile_service)
) -> ProfileOut | None:
    """
    Create a new user after validating authorization.

    Args:
        data: User creation data validated by ProfileCreate schema
        privy_id: The authenticated user's Privy ID obtained from the dependency
        db_repo: User repository instance for database operations

    Returns:
        ProfileOut: The newly created user details

    Raises:
        HTTPException: 
            - 403 if authorization fails
            - 409 if user already exists
            - 500 if there's an unexpected database error
    """
    try:
        return await service.create_profile(data)
    except ValueError as e:
        logger.error('[create_profile] ValueError: %s', e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException as e:
        logger.error('[create_profile] HTTPException: %s', e)
        raise e
    except Exception as e:
        logger.error('[create_profile] Exception: %s', e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user details"
        ) from e


@router.patch("/{profile_id}/")
@limiter.limit("15/minute")
async def update_profile(
    request: Request,
    profile_id: str,
    data: ProfileUpdate,
    _: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """
    Update profile, bio, or social links for the current user.
    Only provided fields will be updated.

    Args:
        data: Fields to update, validated by ProfileUpdate schema.

    Returns:
        ProfileOut: The updated user object.

    Raises:
        HTTPException:
            - 400 for validation errors
            - 404 if user not found
            - 500 for unexpected errors
    """
    try:
        updated_user = await service.update(profile_id, data)
        return updated_user
    except ValueError as e:
        logger.error('[update_profile] ValueError: %s', e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException as e:
        logger.error('[update_profile] HTTPException: %s', e)
        raise e
    except Exception as e:
        logger.error('[update_profile] Exception: %s', e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating user details"
        ) from e


@router.get("/me/")
@limiter.limit("5/minute")
async def get_my_profile(
    request: Request,
    service: ProfileService = Depends(get_profile_service)
) -> ProfileOut | None:
    """
    Create a new user after validating authorization.

    Args:
        data: User creation data validated by ProfileCreate schema
        privy_id: The authenticated user's Privy ID obtained from the dependency
        db_repo: User repository instance for database operations

    Returns:
        ProfileOut: The newly created user details

    Raises:
        HTTPException: 
            - 403 if authorization fails
            - 409 if user already exists
            - 500 if there's an unexpected database error
    """
    try:
        return await service.get_profile_by_user()
    except ValueError as e:
        logger.error('[get_profile_by_user] ValueError: %s', e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException as e:
        logger.error('[get_profile_by_user] HTTPException: %s', e)
        raise e
    except Exception as e:
        logger.error('[get_profile_by_user] Exception: %s', e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching profile details"
        ) from e