from fastapi import (
    HTTPException,
    status
)
from app.domain.user.repository import UserRepository
from app.domain.user.schema import UserCreate, UserOut
from app.enums.enums import UserRole
from app.utils.serialize import serialize


class UserService:
    """User Service layer."""

    def __init__(self, repo: UserRepository):

        self.repo = repo

    async def get_user_by_privy_id(self, privy_id: str) -> UserOut:
        """
        Get user
        """
        user = await self.repo.get_by_privy_id(privy_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user_dict = serialize(user.model_dump())
        return UserOut(**user_dict)

    async def create_user(
        self,
        data: UserCreate,
        current_user: UserOut
    ) -> UserOut:
        """Create user."""
        try:
            # Authorization check
            if data.privy_id != current_user.privy_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Not authorized"
                )

            # Check for existing user
            existing_user = await self.get_user_by_privy_id(current_user.privy_id)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already exists"
                )

            # Check user role
            has_bd_account = any(
                account.type == "google_oauth"
                and account.email
                and account.email.endswith('@athenax.co')
                for account in data.linked_accounts
            )

            # Set role to BD if criteria met and current role is USER
            if has_bd_account and data.role == UserRole.USER:
                data.role = UserRole.BD

            new_user = await self.repo.create(data)
            if not new_user:
                raise ValueError('User creation error.')
            return new_user
        except Exception as e:
            raise e
