from datetime import datetime
from beanie.operators import Eq
from beanie import PydanticObjectId

from app.common.base_repository import BaseRepository
from app.domain.article.model import Article
from app.domain.article.schema import ArticleOut, ArticleCreate
from app.domain.user.model import User
from app.enums.enums import ArticleState


class ArticleRepository(BaseRepository[Article, ArticleOut, ArticleCreate]):
    def __init__(self):
        super().__init__(Article, ArticleOut, ArticleCreate)

    async def get_by_user(self, privy_id: str) -> list[ArticleOut]:
        data = await Article.find({"created_by.privy_id": privy_id}).to_list()
        return [ArticleOut(**self._serialize(x.model_dump())) for x in data]

    async def get_by_state(self, state: str) -> list[ArticleOut]:
        data = (
            await Article.find(Eq(Article.state, state))
            .sort("-created_at")
            .to_list()
        )
        return [ArticleOut(**self._serialize(x.model_dump())) for x in data]
