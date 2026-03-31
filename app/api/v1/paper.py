from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_db,
    get_paper_service,
    require_researcher_user,
)
from app.core.config import settings
from app.domain.paper.schema import (
    PaperCreateSchema,
    PaperOutSchema,
    PaperUpdateSchema,
    VoteOutSchema,
    VoteSchema,
)
from app.domain.paper.service import PaperService
from app.domain.user.schema import UserOutSchema
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix=settings.api.v1.paper, tags=["Paper"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PaperOutSchema)
@limiter.limit("30/minute")
async def create_paper(
    request: Request,
    payload: PaperCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_researcher_user),
    service: PaperService = Depends(get_paper_service),
):
    return await service.create(db, payload, current_user=current_user)


@router.get("", response_model=list[PaperOutSchema])
@limiter.limit("60/minute")
async def list_papers(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: PaperService = Depends(get_paper_service),
):
    return await service.list(db, limit=limit, offset=offset)


@router.get("/{paper_id}", response_model=PaperOutSchema)
@limiter.limit("60/minute")
async def get_paper(
    request: Request,
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    service: PaperService = Depends(get_paper_service),
):
    return await service.get_by_id(db, paper_id=paper_id)


@router.patch("/{paper_id}", response_model=PaperOutSchema)
@limiter.limit("30/minute")
async def update_paper(
    request: Request,
    paper_id: int,
    payload: PaperUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: PaperService = Depends(get_paper_service),
):
    return await service.update(db, paper_id=paper_id, data=payload, current_user=current_user)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_paper(
    request: Request,
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: PaperService = Depends(get_paper_service),
):
    await service.delete_by_id(db, paper_id=paper_id, current_user=current_user)


@router.put("/{paper_id}/vote", response_model=VoteOutSchema)
@limiter.limit("60/minute")
async def vote_paper(
    request: Request,
    paper_id: int,
    payload: VoteSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: PaperService = Depends(get_paper_service),
):
    return await service.vote(db, paper_id=paper_id, voted=payload.voted, current_user=current_user)
