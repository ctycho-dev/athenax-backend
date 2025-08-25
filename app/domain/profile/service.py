from fastapi import (
    HTTPException,
    status
)
from app.domain.user.repository import UserRepository
from app.domain.profile.repository import ProfileRepository
from app.domain.profile.schema import (
    ProfileCreate,
    ProfileUpdate,
    ProfileOut
)
from app.domain.user.schema import (
    LinkedAccount,
    AuthProvider
)
from app.domain.user.schema import UserOut


class ProfileService:
    """User Service layer."""

    def __init__(
        self,
        repo: ProfileRepository,
        user_repo: UserRepository,
        user: UserOut
    ):

        self.repo = repo
        self.user_repo = user_repo
        self.user = user

    async def get_by_user_id(self, user_id: str) -> ProfileOut | None:
        """
        Get user
        """
        profile = await self.repo.get_by_user_id(user_id)
        return profile

    async def create_profile(
        self,
        data: ProfileCreate,
        # current_user: UserOut
    ) -> ProfileOut:
        """Create user."""

        existing_profile = await self.repo.get_by_user_id(self.user.id)
        if existing_profile:
            await self.repo.delete_by_id(existing_profile.id)

        data.user_id = self.user.id

        if self.user.linked_accounts:
            data = self._populate_socials_from_linked_accounts(
                data,
                self.user.linked_accounts
            )

        profile = await self.repo.create(data)
        if not profile:
            raise ValueError('Profile creation error.')

        updated_user = await self.user_repo.update(
            self.user.id,
            {
                "has_profile": True,
                "account_type": profile.account_type
            }
        )
        if not updated_user:
            raise ValueError('User update failed.')

        return profile

    async def update(
        self,
        user_id: str,
        data: ProfileUpdate
    ) -> ProfileOut:
        """
        Delete a message by its ID.
        """
        updated = await self.repo.update(
            user_id,
            data
        )
        return updated

    async def get_profile_by_user(
        self,
    ) -> ProfileOut | None:
        """Create user."""
        
        profile = await self.repo.get_by_user_id(self.user.id)
        return profile

    def _populate_socials_from_linked_accounts(
        self, 
        profile_data: ProfileCreate, 
        linked_accounts: list[LinkedAccount]
    ) -> ProfileCreate:
        """Extract social information from linked accounts and populate profile data."""
        
        for account in linked_accounts:
            if account.type == AuthProvider.GITHUB and account.username:
                profile_data.github = account.username
            elif account.type == AuthProvider.TWITTER and account.username:
                profile_data.twitter = account.username
            elif account.type == AuthProvider.DISCORD and account.username:
                profile_data.discord = account.username
        
        return profile_data
