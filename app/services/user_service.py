from app.infrastructure.repository.user import UserRepository
from app.schemas.user import UserCreate, UserOut
from app.enums.enums import UserRole


class UserService:
    """User Service layer."""

    def __init__(self, db_repo: UserRepository):

        self.db_repo = db_repo

    async def create_user(self, data: UserCreate) -> UserOut:
        """Create user."""
        try:
            has_bd_account = any(
                account.type == "google_oauth"
                and account.email
                and account.email.endswith('@athenax.co')
                for account in data.linked_accounts
            )

            # Set role to BD if criteria met and current role is USER
            if has_bd_account and data.role == UserRole.USER:
                data.role = UserRole.BD

            new_user = await self.db_repo.create(data)
            if not new_user:
                raise ValueError('User creation error.')
            return new_user
        except Exception as e:
            raise e
