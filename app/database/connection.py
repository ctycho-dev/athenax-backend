from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.domain.wishlist.model import WishlistCollection
from app.domain.submit.audit.model import AuditSubmit
from app.domain.submit.research.model import ResearchSubmit
from app.domain.article.model import Article
from app.domain.user.model import User


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
                AuditSubmit,
                ResearchSubmit,
                User,
                Article
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
