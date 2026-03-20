import asyncio

from app.core.config import settings
from app.database.connection import db_manager
from app.domain.user.repository import UserRepository
from app.domain.user.schema import UserCreateSchema
from app.enums.enums import UserRole
from app.utils.oauth2 import (
    hash_password
)


async def main():
    try:
        db_manager.init_engine()

        async with db_manager.session_scope() as session:
            user_repo = UserRepository()

            data = UserCreateSchema(
                email=settings.ADMIN_LOGIN,
                password=hash_password(settings.ADMIN_PWD),
                role=UserRole.ADMIN,
            )
            admin = await user_repo.create(session, data)
        print(f"✅ Admin user ready: {admin.email}")
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
