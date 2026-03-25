from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db,
    get_university_service,
    require_admin_user,
)
from app.core.config import settings
from app.domain.university.schema import (
    UniversityCreateSchema,
    UniversityOutSchema,
    UniversityUpdateSchema,
)
from app.domain.university.service import UniversityService
from app.domain.user.schema import UserOutSchema
from app.middleware.rate_limiter import limiter


router = APIRouter(prefix=settings.api.v1.university, tags=["University"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UniversityOutSchema)
@limiter.limit("30/minute")
async def create_university(
    request: Request,
    payload: UniversityCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: UniversityService = Depends(get_university_service),
):
    return await service.create(db, payload, current_user=current_user)


@router.get("", response_model=list[UniversityOutSchema])
@limiter.limit("60/minute")
async def list_universities(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: UniversityService = Depends(get_university_service),
):
    return await service.list(db, limit=limit, offset=offset)


@router.get("/{university_id}", response_model=UniversityOutSchema)
@limiter.limit("60/minute")
async def get_university(
    request: Request,
    university_id: int,
    db: AsyncSession = Depends(get_db),
    service: UniversityService = Depends(get_university_service),
):
    return await service.get_by_id(db, university_id=university_id)


@router.patch("/{university_id}", response_model=UniversityOutSchema)
@limiter.limit("30/minute")
async def update_university(
    request: Request,
    university_id: int,
    payload: UniversityUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: UniversityService = Depends(get_university_service),
):
    return await service.update(
        db,
        university_id=university_id,
        data=payload,
        current_user=current_user,
    )


@router.delete("/{university_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_university(
    request: Request,
    university_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: UniversityService = Depends(get_university_service),
):
    await service.delete_by_id(db, university_id=university_id, current_user=current_user)
