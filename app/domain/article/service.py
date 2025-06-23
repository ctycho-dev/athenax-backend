from app.domain.article.schema import ArticleCreate, ArticleOut
from app.domain.article.repository import ArticleRepository
from app.domain.user.model import User
from app.enums.enums import ArticleState
from app.exceptions import NotFoundError


class ArticleService:
    def __init__(self, repo: ArticleRepository, user: User | None):
        self.repo = repo
        self.user = user

    async def get_all(self) -> list[ArticleOut]:
        return await self.repo.get_all()

    async def get_by_user(self) -> list[ArticleOut]:
        if not self.user:
            raise ValueError("User context required")
        return await self.repo.get_by_user(self.user.privy_id)

    async def get_by_state(self, state: str) -> list[ArticleOut]:
        return await self.repo.get_by_state(state)

    async def get_by_id(self, article_id: str) -> ArticleOut:
        article = await self.repo.get_by_id(article_id)
        if not article:
            raise NotFoundError(f"Article with ID {article_id} not found")
        return article

    async def create(self, data: ArticleCreate) -> ArticleOut:
        if not self.user:
            raise ValueError("User context required")
        return await self.repo.create(entity=data, current_user=self.user)
