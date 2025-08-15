from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request
)
from app.middleware.rate_limiter import limiter
from app.core.dependencies import get_current_user
from app.domain.user.schema import (
    UserCreate,
    UserOut,
    UserUpdate
)
from app.domain.user.model import User
from app.core.logger import get_logger
from app.core.dependencies import get_user_service
from app.domain.user.service import UserService
from app.utils.serialize import serialize

logger = get_logger()

router = APIRouter()


@router.get("/me/", response_model=UserOut)
@limiter.limit("30/minute")
async def get_user(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """
    Get user details for the currently authenticated user.
    """
    try:
        user_dict = serialize(current_user.model_dump())
        return UserOut(**user_dict)
    except ValueError as e:
        logger.error('[get_user] ValueError: %s', e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException as e:
        logger.error('[get_user] HTTPException: %s', e)
        raise e
    except Exception as e:
        logger.error('[get_user] Exception: %s', e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user details"
        ) from e


@router.post("/", response_model=UserOut)
@limiter.limit("5/minute")
async def create_user(
    request: Request,
    data: UserCreate,
    # current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
) -> UserOut | None:
    """
    Create a new user after validating authorization.

    Args:
        data: User creation data validated by UserCreate schema
        privy_id: The authenticated user's Privy ID obtained from the dependency
        db_repo: User repository instance for database operations

    Returns:
        UserOut: The newly created user details

    Raises:
        HTTPException: 
            - 403 if authorization fails
            - 409 if user already exists
            - 500 if there's an unexpected database error
    """
    try:
        return await service.create_user(data)
    except ValueError as e:
        logger.error('[create_user] ValueError: %s', e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException as e:
        logger.error('[create_user] HTTPException: %s', e)
        raise e
    except Exception as e:
        logger.error('[create_user] Exception: %s', e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user details"
        ) from e


@router.patch("/")
@limiter.limit("15/minute")
async def update_user(
    request: Request,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
):
    """
    Update profile, bio, or social links for the current user.
    Only provided fields will be updated.

    Args:
        data: Fields to update, validated by UserUpdate schema.

    Returns:
        UserOut: The updated user object.

    Raises:
        HTTPException:
            - 400 for validation errors
            - 404 if user not found
            - 500 for unexpected errors
    """
    try:
        updated_user = await service.update(str(current_user.id), data)
        return updated_user
    except ValueError as e:
        logger.error('[update_user] ValueError: %s', e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException as e:
        logger.error('[update_user] HTTPException: %s', e)
        raise e
    except Exception as e:
        logger.error('[update_user] Exception: %s', e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating user details"
        ) from e


# from fastapi.security import OAuth2PasswordRequestForm
# from datetime import timedelta

# @router.post("/login/password")
# async def login_with_password(
#     form_data: OAuth2PasswordRequestForm = Depends(),
#     db_repo: UserRepository = Depends(get_user_repo)
# ) -> dict:
#     """
#     Authenticate with email/password
    
#     Args:
#         form_data: Standard OAuth2 form with username=email
#         db_repo: User repository
        
#     Returns:
#         dict: Access token and user info
        
#     Raises:
#         HTTPException: 401 for invalid credentials
#     """
#     try:
#         # 1. Find user by email
#         user = await db_repo.get_by_email(form_data.username)
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid credentials"
#             )

#         # 2. Verify password
#         if not user.verify_password(form_data.password):
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid credentials"
#             )

#         # 3. Check email verification
#         if not user.email_verified:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Email not verified"
#             )

#         # 4. Update login stats
#         user.last_login_at = datetime.now()
#         user.login_count += 1
#         await user.save()

#         # 5. Generate token
#         access_token = create_access_token(
#             data={"sub": user.email},
#             expires_delta=timedelta(minutes=30)
            
#         return {
#             "access_token": access_token,
#             "token_type": "bearer",
#             "user": UserOut.from_orm(user)
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error("Login error: %s", e)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Login failed"
#         )