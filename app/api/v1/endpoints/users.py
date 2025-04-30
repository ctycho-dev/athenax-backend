from fastapi import APIRouter, Depends, HTTPException, Response, status
from app.core.dependencies import get_current_user, get_user_repo
from app.schemas.user import UserCreate, UserOut
from app.infrastructure.repository.user import UserRepository
from app.core.logger import get_logger

logger = get_logger()

router = APIRouter()


@router.get("/me/", response_model=UserOut)
async def get_or_create_user(
    privy_id: str = Depends(get_current_user),
    db_repo: UserRepository = Depends(get_user_repo)
) -> UserOut:
    """
    Get user details for the currently authenticated user.
    
    Args:
        privy_id: The authenticated user's Privy ID obtained from the dependency
        db_repo: User repository instance for database operations
        
    Returns:
        UserOut: The user details if found
        
    Raises:
        HTTPException: 500 if there's an unexpected database error
    """
    try:
        user = await db_repo.get_by_privy_id(privy_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user

    except HTTPException:
        # Re-raise known HTTP exceptions
        raise
    except Exception as e:
        logger.error("Error fetching user %s: %s", privy_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user details"
        ) from e


@router.post("/", response_model=UserOut)
async def create_user(
    data: UserCreate,
    privy_id: str = Depends(get_current_user),
    db_repo: UserRepository = Depends(get_user_repo)
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
        # Authorization check
        if data.privy_id != privy_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Not authorized"
            )

        # Check for existing user
        existing_user = await db_repo.get_by_privy_id(privy_id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists"
            )

        # Create new user
        new_user = await db_repo.create(data)
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
            
        return new_user
        
    except HTTPException:
        # Re-raise known HTTP exceptions
        raise
    except Exception as e:
        logger.error("Error creating user %s: %s", privy_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating user"
        ) from e