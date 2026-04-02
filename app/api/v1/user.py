from fastapi import (
    APIRouter,
    Depends,
    status,
    Response,
    Request,
    Query,
)
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.rate_limiter import limiter
from app.domain.user.schema import (
    UserSignupSchema,
    UserOutSchema,
    UserWithProfileOutSchema,
    InvestorProfileSchema,
    InvestorProfileOutSchema,
    ResearcherProfileSchema,
    ResearcherProfileOutSchema,
    SponsorProfileSchema,
    SponsorProfileOutSchema,
    CategoryRefSchema,
    UserCategorySetSchema,
    Token,
    MessageSchema,
    EmailTokenSchema,
    EmailRequestSchema,
    PasswordResetSchema,
)
from app.api.dependencies import get_user_service, get_current_user, get_db
from app.domain.user.service import UserService
from app.utils import oauth2
from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix=settings.api.v1.user, tags=["User"])


def _set_access_token_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/"
    )


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[UserOutSchema])
@limiter.limit("100/minute")
async def get_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await user_service.get_all(db, limit=limit, offset=offset)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserOutSchema)
@limiter.limit("5/minute")
async def create_user(
    request: Request,
    data: UserSignupSchema,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.create_user(db, data)


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=MessageSchema)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    data: UserSignupSchema,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    return MessageSchema(message=await user_service.signup_user(db, data))


@router.post("/verify", response_model=UserOutSchema)
@limiter.limit("60/minute")
async def verify(
    request: Request,
    user: UserOutSchema = Depends(get_current_user),
):
    return user


@router.get("/verify-email", response_model=MessageSchema)
@limiter.limit("10/minute")
async def verify_email_link(
    request: Request,
    response: Response,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    logger.info(
        "verify_email_link_request",
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "query_has_token": bool(token),
            "token_len": len(token),
            "token_prefix": token[:8],
            "origin": request.headers.get("origin"),
            "referer": request.headers.get("referer"),
            "cookie_names": list(request.cookies.keys()),
        },
    )
    verified_user = await user_service.verify_email(db, token)
    access_token = oauth2.create_access_token(data={"user_id": str(verified_user.id)})
    _set_access_token_cookie(response, access_token)
    return MessageSchema(message="Email verified successfully.")


@router.post("/verify-email", response_model=MessageSchema)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    response: Response,
    payload: EmailTokenSchema,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    verified_user = await user_service.verify_email(db, payload.token)
    access_token = oauth2.create_access_token(data={"user_id": str(verified_user.id)})
    _set_access_token_cookie(response, access_token)
    return MessageSchema(message="Email verified successfully.")


@router.post("/verify-email/resend", response_model=MessageSchema)
@limiter.limit("5/minute")
async def resend_verification_email(
    request: Request,
    payload: EmailRequestSchema,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    return MessageSchema(
        message=await user_service.resend_verification_email(db, payload.email)
    )


@router.get("/{user_id}", response_model=UserWithProfileOutSchema)
@limiter.limit("60/minute")
async def get_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_user_with_profile(db, user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    await user_service.delete_by_id(db, current_user, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.ensure_login_allowed(
        db,
        user_credentials.username,
        user_credentials.password,
    )
    access_token = oauth2.create_access_token(data={"user_id": str(user.id)})
    _set_access_token_cookie(response, access_token)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password", response_model=MessageSchema)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    payload: EmailRequestSchema,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    return MessageSchema(
        message=await user_service.request_password_reset(db, payload.email)
    )


@router.post("/reset-password", response_model=MessageSchema)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    payload: PasswordResetSchema,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    return MessageSchema(
        message=await user_service.reset_password(db, payload.token, payload.password)
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )
    return {"message": "Logged out successfully"}


# ---------------------------------------------------------------------------
# Investor profile
# ---------------------------------------------------------------------------

@router.post(
    "/{user_id}/investor-profile",
    response_model=InvestorProfileOutSchema,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def upsert_investor_profile(
    request: Request,
    user_id: int,
    data: InvestorProfileSchema,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.upsert_investor_profile(db, user_id, data)


@router.get("/{user_id}/investor-profile", response_model=InvestorProfileOutSchema)
@limiter.limit("60/minute")
async def get_investor_profile(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_investor_profile(db, user_id)


# ---------------------------------------------------------------------------
# Researcher profile
# ---------------------------------------------------------------------------

@router.post(
    "/{user_id}/researcher-profile",
    response_model=ResearcherProfileOutSchema,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def upsert_researcher_profile(
    request: Request,
    user_id: int,
    data: ResearcherProfileSchema,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.upsert_researcher_profile(db, user_id, data)


@router.get("/{user_id}/researcher-profile", response_model=ResearcherProfileOutSchema)
@limiter.limit("60/minute")
async def get_researcher_profile(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_researcher_profile(db, user_id)


# ---------------------------------------------------------------------------
# Sponsor profile
# ---------------------------------------------------------------------------

@router.post(
    "/{user_id}/sponsor-profile",
    response_model=SponsorProfileOutSchema,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def upsert_sponsor_profile(
    request: Request,
    user_id: int,
    data: SponsorProfileSchema,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.upsert_sponsor_profile(db, user_id, data)


@router.get("/{user_id}/sponsor-profile", response_model=SponsorProfileOutSchema)
@limiter.limit("60/minute")
async def get_sponsor_profile(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_sponsor_profile(db, user_id)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@router.post(
    "/{user_id}/categories",
    response_model=list[CategoryRefSchema],
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def set_user_categories(
    request: Request,
    user_id: int,
    data: UserCategorySetSchema,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.set_user_categories(db, user_id, data.category_ids)


@router.get("/{user_id}/categories", response_model=list[CategoryRefSchema])
@limiter.limit("60/minute")
async def get_user_categories(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_user_categories(db, user_id)


@router.delete(
    "/{user_id}/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("20/minute")
async def remove_user_category(
    request: Request,
    user_id: int,
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    await user_service.remove_user_category(db, user_id, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
