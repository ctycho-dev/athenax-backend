from fastapi import (
    HTTPException,
    status
)
from app.domain.user.repository import UserRepository
from app.domain.user.schema import (
    UserCreate,
    UserOut,
    UserUpdate
)
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
        # current_user: UserOut
    ) -> UserOut:
        """Create user."""
        try:
            # Set email if not set but found in linked accounts
            if not getattr(data, "email", None):
                email_from_linked = None
                for account in data.linked_accounts:
                    # Prefer a non-null email in the linked_account (OAuth or otherwise)
                    if getattr(account, "email", None):
                        email_from_linked = account.email
                        break
                    # Fallback: for "email" provider, check 'address'
                    if account.type == "email" and getattr(account, "address", None):
                        email_from_linked = account.address
                        break
                if email_from_linked:
                    data.email = email_from_linked
            
            # Business logic for role
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
    
    async def update(
        self,
        user_id: str,
        data: UserUpdate
    ) -> UserOut:
        """
        Delete a message by its ID.
        """
        updated = await self.repo.update(
            user_id,
            data
        )
        return updated
    # async def delete_user(
    #     self,
    #     user_id_to_delete: str,
    #     current_user: UserOut
    # ) -> None:
    #     """
    #     Delete user.

    #     Rules:
    #         1. Users cannot delete themselves
    #         2. Superadmins can delete anyone
    #         3. Admins can only delete users from their own company
    #         4. Regular users cannot delete anyone

    #     Args:
    #         user_id_to_delete (int): The ID of the user to delete.
    #         current_user (UserOut): The currently authenticated user (from dependency).

    #     Raises:
    #         HTTPException: 
    #             - 403 Forbidden if user doesn't have permission
    #             - 404 Not Found if user doesn't exist
    #             - 500 Internal Server Error for unexpected errors
    #     """
    #     try:
    #         # Check permissions
    #         if user_id_to_delete == current_user.id:
    #             raise HTTPException(
    #                 status_code=status.HTTP_403_FORBIDDEN,
    #                 detail="Cannot delete yourself"
    #             )

    #         # Get the user to delete
    #         user = await self.repo.get_by_id(str(user_id_to_delete))
    #         if not user:
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="User not found"
    #             )

    #         if not (current_user.role == Role.SUPERADMIN or
    #                 (current_user.role == Role.ADMIN and user.company_id == current_user.company_id)):
    #             raise HTTPException(
    #                 status_code=status.HTTP_403_FORBIDDEN,
    #                 detail="Insufficient permissions to delete this user"
    #             )

    #         # ws_repo = get_ws_repo()

    #         # # Delete related Workspaces
    #         # workspaces = await ws_repo.get_by_user(user_id_to_delete)
    #         # for ws in workspaces:
    #         #     await ws_repo.delete_by_id(ws.id)

    #         await self.repo.delete_by_id(user_id_to_delete)
    #     except Exception as e:
    #         raise e