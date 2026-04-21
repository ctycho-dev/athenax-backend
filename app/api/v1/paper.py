from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_db,
    get_paper_service,
    require_admin_user,
    require_researcher_user,
)
from app.api.dependencies.auth import get_optional_user
from app.core.config import settings
from app.domain.paper.schema import (
    PaperCreateSchema,
    PaperOutSchema,
    PaperUpdateSchema,
    PaperVerificationStatusUpdateSchema,
    VoteOutSchema,
    VoteSchema,
)
from app.enums.enums import PaperStatus, PaperVerificationStatus
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
    verification_status: PaperVerificationStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: PaperService = Depends(get_paper_service),
):
    return await service.list_papers(db, limit=limit, offset=offset, verification_status=verification_status, current_user=current_user)


@router.get("/me", response_model=list[PaperOutSchema])
@limiter.limit("60/minute")
async def list_my_papers(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: PaperStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_researcher_user),
    service: PaperService = Depends(get_paper_service),
):
    return await service.list_papers(db, limit=limit, offset=offset, paper_status=status, current_user=current_user, owner_only=True)


@router.get("/slug/{slug}", response_model=PaperOutSchema)
@limiter.limit("60/minute")
async def get_paper_by_slug(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: PaperService = Depends(get_paper_service),
):
    return await service.get_by_slug(db, slug=slug, current_user=current_user)


@router.get("/{paper_id}", response_model=PaperOutSchema)
@limiter.limit("60/minute")
async def get_paper(
    request: Request,
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: PaperService = Depends(get_paper_service),
):
    return await service.get_by_id(db, paper_id=paper_id, current_user=current_user)


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



@router.patch("/{paper_id}/verification-status", response_model=PaperOutSchema)
@limiter.limit("30/minute")
async def update_paper_verification_status(
    request: Request,
    paper_id: int,
    payload: PaperVerificationStatusUpdateSchema,
    db: AsyncSession = Depends(get_db),
    _: UserOutSchema = Depends(require_admin_user),
    service: PaperService = Depends(get_paper_service),
):
    return await service.update_verification_status(db, paper_id=paper_id, data=payload)


@router.get("/{paper_id}/related", response_model=list[PaperOutSchema])
@limiter.limit("60/minute")
async def get_related_papers(
    request: Request,
    paper_id: int,
    limit: int = 5,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: PaperService = Depends(get_paper_service),
):
    return await service.get_related(db, paper_id=paper_id, limit=limit, offset=offset)


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
