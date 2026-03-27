from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Type, TypeVar

from app.domain.user.model import User
from app.domain.user.repository import ProfileRepository
from app.domain.user.repository import (
    UserRepository,
    InvestorProfileRepository,
    ResearcherProfileRepository,
    SponsorProfileRepository,
    UserCategoryRepository,
)
from app.domain.user.schema import (
    CategoryRefSchema,
    InvestorProfileOutSchema,
    InvestorProfileSchema,
    ResearcherProfileOutSchema,
    ResearcherProfileSchema,
    SponsorProfileOutSchema,
    SponsorProfileSchema,
    UserSignupSchema,
    UserCreateDBSchema,
    UserOutSchema,
    UserCredsSchema,
    UserWithProfileOutSchema,
)
from app.enums.enums import TokenType
from app.core.logger import get_logger
from app.infrastructure.email.service import EmailService, EmailDeliveryError
from app.utils.oauth2 import (
    hash_password,
    verify_password,
    generate_email_token,
    hash_token,
)


logger = get_logger(__name__)
TUser = TypeVar("TUser")


class UserService:
    def __init__(
        self,
        repo: UserRepository,
        email_service: EmailService,
        investor_profile_repo: InvestorProfileRepository,
        researcher_profile_repo: ResearcherProfileRepository,
        sponsor_profile_repo: SponsorProfileRepository,
        user_category_repo: UserCategoryRepository,
    ):
        self.repo = repo
        self.email_service = email_service
        self.investor_profile_repo = investor_profile_repo
        self.researcher_profile_repo = researcher_profile_repo
        self.sponsor_profile_repo = sponsor_profile_repo
        self.user_category_repo = user_category_repo

    async def get_all(self, db: AsyncSession, limit: int = 50, offset: int = 0) -> list[User]:
        return await self.repo.get_all(db, limit=limit, offset=offset)

    async def get_by_id(self, db: AsyncSession, user_id: int) -> User:
        return await self.repo.get_by_id(db, user_id)

    async def delete_by_id(
        self, db: AsyncSession, current_user: UserOutSchema, user_id: int
    ) -> None:
        await self.repo.delete_by_id(db, user_id)
        await db.commit()

    async def get_by_email(
        self, db: AsyncSession, email: str
    ) -> UserCredsSchema | None:
        user = await self.repo.get_by_email(db, email)
        if not user:
            return None
        return UserCredsSchema.model_validate(user)

    async def create_user(
        self, db: AsyncSession, user: UserSignupSchema
    ) -> UserOutSchema:
        existing_user = await self.repo.get_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists",
            )
        data = UserCreateDBSchema(
            name=user.name,
            email=user.email,
            password_hash=hash_password(user.password),
            verified=False,
            role=user.role,
            external_id=user.external_id,
        )
        return await self.repo.create(db, data)

    async def signup_user(self, db: AsyncSession, user: UserSignupSchema) -> str:
        """
        Public signup. Creates user and optional role-specific profile
        in a single transaction.
        """
        new_user = await self.create_user(db, user)

        if user.investor_profile is not None:
            await self._upsert_profile(db, self.investor_profile_repo, new_user.id, user.investor_profile, InvestorProfileOutSchema)
        if user.researcher_profile is not None:
            await self._upsert_profile(db, self.researcher_profile_repo, new_user.id, user.researcher_profile, ResearcherProfileOutSchema)
        if user.sponsor_profile is not None:
            await self._upsert_profile(db, self.sponsor_profile_repo, new_user.id, user.sponsor_profile, SponsorProfileOutSchema)

        token = await self._issue_verification_token(db, new_user.id)
        await db.commit()
        try:
            await self.email_service.send_verification_email(
                new_user.email,
                new_user.name,
                token,
            )
        except EmailDeliveryError:
            logger.warning(
                "verification_email_delivery_failed",
                extra={"email": new_user.email, "user_id": new_user.id},
            )
            return (
                "Signup successful, but we could not send the verification email right now. "
                "Please try the resend verification endpoint later."
            )
        return "Signup successful. Please verify your email."

    async def verify_email(self, db: AsyncSession, token: str) -> UserOutSchema:
        user = await self.repo.get_by_token_hash(db, hash_token(token), TokenType.VERIFICATION)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )
        verified_user = self._require_user(user)
        updated_user = await self.repo.update(
            db,
            verified_user.id,
            {"verified": True, "token_hash": None, "token_type": None},
        )
        await db.commit()
        return self._require_user(updated_user)

    async def resend_verification_email(
        self, db: AsyncSession, email: str
    ) -> str:
        user = await self.repo.get_by_email(db, email)
        if not user:
            return "If an account with that email exists, a verification email has been sent."
        if user.verified:
            return "Email is already verified."
        token = await self._issue_verification_token(db, user.id)
        await db.commit()
        try:
            await self.email_service.send_verification_email(
                user.email,
                user.name,
                token,
            )
        except EmailDeliveryError:
            logger.warning(
                "verification_email_resend_failed",
                extra={"email": user.email, "user_id": user.id},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not send verification email right now. Please try again later.",
            )
        return "Verification email has been sent."

    async def request_password_reset(self, db: AsyncSession, email: str) -> str:
        user = await self.repo.get_by_email(db, email)
        if not user:
            return "If an account with that email exists, a password reset email has been sent."
        token = await self._issue_reset_token(db, user.id)
        await db.commit()
        try:
            await self.email_service.send_password_reset_email(
                user.email,
                user.name,
                token,
            )
        except EmailDeliveryError:
            logger.warning(
                "password_reset_email_delivery_failed",
                extra={"email": user.email, "user_id": user.id},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not send password reset email right now. Please try again later.",
            )
        return "Password reset email has been sent."

    async def reset_password(
        self, db: AsyncSession, token: str, password: str
    ) -> str:
        user = await self.repo.get_by_token_hash(db, hash_token(token), TokenType.RESET)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        reset_user = self._require_user(user)
        await self.repo.update(
            db,
            reset_user.id,
            {"password_hash": hash_password(password), "token_hash": None, "token_type": None},
        )
        await db.commit()
        return "Password reset successfully."

    async def ensure_login_allowed(
        self, db: AsyncSession, email: str, password: str
    ) -> UserCredsSchema:
        user = await self.repo.get_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid credentials",
            )
        if not user.verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email is not verified",
            )
        if not self._verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid credentials",
            )
        return UserCredsSchema.model_validate(user)

    # ------------------------------------------------------------------
    # Profile methods
    # ------------------------------------------------------------------

    async def upsert_investor_profile(
        self, db: AsyncSession, user_id: int, data: InvestorProfileSchema
    ) -> InvestorProfileOutSchema:
        result = await self._upsert_profile(
            db, self.investor_profile_repo, user_id, data, InvestorProfileOutSchema
        )
        await db.commit()
        return result

    async def get_investor_profile(
        self, db: AsyncSession, user_id: int
    ) -> InvestorProfileOutSchema:
        return await self._get_profile(
            db, self.investor_profile_repo, user_id, InvestorProfileOutSchema, "Investor profile not found"
        )

    async def upsert_researcher_profile(
        self, db: AsyncSession, user_id: int, data: ResearcherProfileSchema
    ) -> ResearcherProfileOutSchema:
        result = await self._upsert_profile(
            db, self.researcher_profile_repo, user_id, data, ResearcherProfileOutSchema
        )
        await db.commit()
        return result

    async def get_researcher_profile(
        self, db: AsyncSession, user_id: int
    ) -> ResearcherProfileOutSchema:
        return await self._get_profile(
            db, self.researcher_profile_repo, user_id, ResearcherProfileOutSchema, "Researcher profile not found"
        )

    async def upsert_sponsor_profile(
        self, db: AsyncSession, user_id: int, data: SponsorProfileSchema
    ) -> SponsorProfileOutSchema:
        result = await self._upsert_profile(
            db, self.sponsor_profile_repo, user_id, data, SponsorProfileOutSchema
        )
        await db.commit()
        return result

    async def get_sponsor_profile(
        self, db: AsyncSession, user_id: int
    ) -> SponsorProfileOutSchema:
        return await self._get_profile(
            db, self.sponsor_profile_repo, user_id, SponsorProfileOutSchema, "Sponsor profile not found"
        )

    async def set_user_categories(
        self, db: AsyncSession, user_id: int, category_ids: list[int]
    ) -> list[CategoryRefSchema]:
        entries = await self.user_category_repo.set_categories(db, user_id, category_ids)
        await db.commit()
        return [CategoryRefSchema(category_id=e.category_id) for e in entries]

    async def get_user_categories(
        self, db: AsyncSession, user_id: int
    ) -> list[CategoryRefSchema]:
        entries = await self.user_category_repo.get_by_user_id(db, user_id)
        return [CategoryRefSchema(category_id=e.category_id) for e in entries]

    async def remove_user_category(
        self, db: AsyncSession, user_id: int, category_id: int
    ) -> None:
        await self.user_category_repo.remove_category(db, user_id, category_id)
        await db.commit()

    async def get_user_with_profile(
        self, db: AsyncSession, user_id: int
    ) -> UserWithProfileOutSchema:
        user = await self.repo.get_by_id(db, user_id)
        investor = await self.investor_profile_repo.get_by_user_id(db, user_id)
        researcher = await self.researcher_profile_repo.get_by_user_id(db, user_id)
        sponsor = await self.sponsor_profile_repo.get_by_user_id(db, user_id)
        categories = await self.user_category_repo.get_by_user_id(db, user_id)

        return UserWithProfileOutSchema(
            **UserOutSchema.model_validate(user, from_attributes=True).model_dump(),
            investor_profile=InvestorProfileOutSchema.model_validate(
                investor, from_attributes=True
            ) if investor else None,
            researcher_profile=ResearcherProfileOutSchema.model_validate(
                researcher, from_attributes=True
            ) if researcher else None,
            sponsor_profile=SponsorProfileOutSchema.model_validate(
                sponsor, from_attributes=True
            ) if sponsor else None,
            categories=[CategoryRefSchema(category_id=c.category_id) for c in categories],
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _issue_verification_token(self, db: AsyncSession, user_id: int) -> str:
        return await self._issue_token(db, user_id, TokenType.VERIFICATION)

    async def _issue_reset_token(self, db: AsyncSession, user_id: int) -> str:
        return await self._issue_token(db, user_id, TokenType.RESET)

    async def _issue_token(self, db: AsyncSession, user_id: int, token_type: TokenType) -> str:
        token = generate_email_token()
        await self.repo.update(db, user_id, {"token_hash": hash_token(token), "token_type": token_type})
        return token

    async def _upsert_profile(
        self,
        db: AsyncSession,
        repo: ProfileRepository[Any],
        user_id: int,
        data: Any,
        out_schema: Type[Any],
    ) -> Any:
        profile = await repo.upsert(db, user_id, data.model_dump())
        return out_schema.model_validate(profile, from_attributes=True)

    async def _get_profile(
        self,
        db: AsyncSession,
        repo: ProfileRepository[Any],
        user_id: int,
        out_schema: Type[Any],
        not_found_detail: str,
    ) -> Any:
        profile = await repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail
            )
        return out_schema.model_validate(profile, from_attributes=True)

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        return verify_password(password, password_hash)

    @staticmethod
    def _require_user(user: TUser | None) -> TUser:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
