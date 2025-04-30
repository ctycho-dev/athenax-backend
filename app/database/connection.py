from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.database.models.wishlist import WishlistCollection
from app.database.models.audit import AuditForm
from app.database.models.research import ResearchForm
from app.database.models.user import User


class DatabaseManager:

    def __init__(self):
        self.client = None

    async def connect(self):
        """
        Initialize the database connection and Beanie.
        """
        self.client = AsyncIOMotorClient(
            host=settings.MONGO_HOST,
            port=settings.MONGO_PORT,
            username=settings.MONGO_INITDB_ROOT_USERNAME,
            password=settings.MONGO_INITDB_ROOT_PASSWORD,
        )
        await init_beanie(
            database=self.client.get_database(settings.MONGO_INITDB_DATABASE),
            document_models=[
                WishlistCollection,
                AuditForm,
                ResearchForm,
                User
            ],
        )

    async def disconnect(self):
        """
        Close the database connection.
        """
        if self.client:
            self.client.close()

    def get_client(self):
        """
        Get client.
        """
        return self.client


db_manager = DatabaseManager()
