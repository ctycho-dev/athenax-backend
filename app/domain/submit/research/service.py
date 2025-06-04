# app/services/research_service.py
from app.domain.submit.research.schema import ResearchSubmitSchema
from app.domain.user.schema import UserOut
from app.domain.submit.research.repository import ResearchRepository
from app.exceptions import NotFoundError


class ResearchService:
    def __init__(self, repo: ResearchRepository, user: UserOut):
        self.repo = repo
        self.user = user

    async def get_all(self):
        return await self.repo.get_by_user(self.user.privy_id)

    async def get_by_id(self, research_id: str):
        research = await self.repo.get_by_id(research_id)
        if not research:
            raise NotFoundError("Research not found")
        return research

    async def create(self, data: ResearchSubmitSchema):
        data.user_privy_id = self.user.privy_id
        await self.repo.create(entity=data, current_user=self.user)

    async def update(self, research_id: str, data: ResearchSubmitSchema):
        research = await self.repo.get_by_id(research_id)
        if not research:
            raise NotFoundError("Research not found")
        if research.user_privy_id != self.user.privy_id:
            raise PermissionError("Not authorized to update this research")
        await self.repo.update(research_id, data)
