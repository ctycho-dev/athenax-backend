from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request
)
from app.middleware.rate_limiter import limiter
from app.core.dependencies import get_current_user
from app.domain.user.schema import UserCreate, UserOut
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
    except HTTPException:
        logger.error("Error fetching user %s: %s", current_user.privy_id, e, exc_info=True)
        raise
    except Exception as e:
        logger.error("Error fetching user %s: %s", current_user.privy_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user details"
        ) from e


@router.post("/", response_model=UserOut)
@limiter.limit("5/minute")
async def create_user(
    request: Request,
    data: UserCreate,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
) -> UserOut:
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
        user_dict = serialize(current_user.model_dump())
        return await service.create_user(data, UserOut(**user_dict))
    except HTTPException:
        # Re-raise known HTTP exceptions
        raise
    except Exception as e:
        logger.error("Error creating user %s: %s", current_user.privy_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating user"
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