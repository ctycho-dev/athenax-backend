from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import TypeVar
from app.domain.user.repository import UserRepository
from app.domain.user.schema import (
    UserSignupSchema,
    UserCreateDBSchema,
    UserOutSchema,
    UserCredsSchema,
)
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
    def __init__(self, repo: UserRepository, email_service: EmailService):
        self.repo = repo
        self.email_service = email_service
    
    async def get_all(self, db: AsyncSession) -> list[UserOutSchema]:
        return await self.repo.get_all(db)

    async def get_by_id(self, db: AsyncSession, user_id: int) -> UserOutSchema:
        return await self.repo.get_by_id(db, user_id)

    async def delete_by_id(self, db: AsyncSession, current_user: UserOutSchema, user_id: int) -> None:
        await self.repo.delete_by_id(db, user_id)

    async def get_by_email(self, db: AsyncSession, email: str) -> UserCredsSchema | None:
        user = await self.repo.get_by_email(db, email)
        if not user:
            return None
        return UserCredsSchema.model_validate(user)

    async def create_user(self, db: AsyncSession, user: UserSignupSchema) -> UserOutSchema:
        existing_user = await self.repo.get_by_email(db, user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User already exists'
            )

        data = UserCreateDBSchema(
            name=user.name,
            email=user.email,
            password_hash=hash_password(user.password),
            verified=False,
            verification_hash=None,
            reset_hash=None,
            role=user.role,
            external_id=user.external_id,
            lab_id=user.lab_id,
            bio=user.bio,
            organization=user.organization,
        )
        return await self.repo.create(db, data)

    async def signup_user(self, db: AsyncSession, user: UserSignupSchema) -> str:
        """
        Public signup path.
        """
        new_user = await self.create_user(db, user)
        token = await self._issue_verification_token(db, new_user.id)
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
        user = await self.repo.get_by_verification_hash(db, hash_token(token))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )
        verified_user = self._require_user(user)

        updated_user = await self.repo.update(
            db,
            verified_user.id,
            {"verified": True, "verification_hash": None},
        )
        return self._require_user(updated_user)

    async def resend_verification_email(self, db: AsyncSession, email: str) -> str:
        user = await self.repo.get_by_email(db, email)
        if not user:
            return "If an account with that email exists, a verification email has been sent."

        if user.verified:
            return "Email is already verified."

        token = await self._issue_verification_token(db, user.id)
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

    async def reset_password(self, db: AsyncSession, token: str, password: str) -> str:
        user = await self.repo.get_by_reset_hash(db, hash_token(token))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        reset_user = self._require_user(user)

        await self.repo.update(
            db,
            reset_user.id,
            {
                "password_hash": hash_password(password),
                "reset_hash": None,
            },
        )
        return "Password reset successfully."

    async def ensure_login_allowed(self, db: AsyncSession, email: str, password: str) -> UserCredsSchema:
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

    async def _issue_verification_token(self, db: AsyncSession, user_id: int) -> str:
        token = generate_email_token()
        await self.repo.update(
            db,
            user_id,
            {"verification_hash": hash_token(token)},
        )
        return token

    async def _issue_reset_token(self, db: AsyncSession, user_id: int) -> str:
        token = generate_email_token()
        await self.repo.update(
            db,
            user_id,
            {"reset_hash": hash_token(token)},
        )
        return token

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
