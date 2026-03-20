from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    status,
    Response,
    Request
)
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.middleware.rate_limiter import limiter
from app.domain.user.schema import (
    UserSignupSchema,
    UserOutSchema,
    Token
)
from app.api.dependencies import get_user_service, get_current_user, get_db
from app.domain.user.service import UserService
from app.utils import oauth2
from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix=settings.api.v1.user, tags=["User"])


@router.get("/", response_model=list[UserOutSchema])
@limiter.limit("100/minute")
async def get_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    users = await user_service.get_all(db)
    return users


@router.get("/{user_id}")
@limiter.limit("60/minute")
async def get_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.get_by_id(db, user_id)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    await user_service.delete_by_id(db, current_user, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserOutSchema)
@limiter.limit("5/minute")
async def create_user(
    request: Request,
    data: UserSignupSchema,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    new_user = await user_service.create_user(db, data)
    return new_user


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=Token)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    response: Response,
    data: UserSignupSchema,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.signup_user(db, data)

    access_token = oauth2.create_access_token(data={"user_id": str(user.id)})

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        path="/"
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post('/verify')
@limiter.limit("60/minute")
async def verify(
    request: Request,
    user: UserOutSchema = Depends(get_current_user)
):
    return user


@router.post('/login', response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.get_by_email(db, user_credentials.username)
    if not user or not oauth2.verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid credentials",
        )

    access_token = oauth2.create_access_token(data={"user_id": str(user.id)})

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        path="/"
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite="lax",
    )
    return {"message": "Logged out successfully"}
