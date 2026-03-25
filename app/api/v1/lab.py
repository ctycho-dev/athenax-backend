from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db, get_lab_service
from app.core.config import settings
from app.domain.lab.schema import LabCreateSchema, LabOutSchema, LabUpdateSchema
from app.domain.lab.service import LabService
from app.domain.user.schema import UserOutSchema
from app.middleware.rate_limiter import limiter


router = APIRouter(prefix=settings.api.v1.lab, tags=["Lab"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=LabOutSchema)
@limiter.limit("30/minute")
async def create_lab(
    request: Request,
    payload: LabCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: LabService = Depends(get_lab_service),
):
    return await service.create(db, payload, current_user=current_user)


@router.get("", response_model=list[LabOutSchema])
@limiter.limit("60/minute")
async def list_labs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _current_user: UserOutSchema = Depends(get_current_user),
    service: LabService = Depends(get_lab_service),
):
    return await service.list(db, limit=limit, offset=offset)


@router.get("/{lab_id}", response_model=LabOutSchema)
@limiter.limit("60/minute")
async def get_lab(
    request: Request,
    lab_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: UserOutSchema = Depends(get_current_user),
    service: LabService = Depends(get_lab_service),
):
    return await service.get_by_id(db, lab_id=lab_id)


@router.patch("/{lab_id}", response_model=LabOutSchema)
@limiter.limit("30/minute")
async def update_lab(
    request: Request,
    lab_id: int,
    payload: LabUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: LabService = Depends(get_lab_service),
):
    return await service.update(
        db,
        lab_id=lab_id,
        data=payload,
        current_user=current_user,
    )


@router.delete("/{lab_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_lab(
    request: Request,
    lab_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(get_current_user),
    service: LabService = Depends(get_lab_service),
):
    await service.delete_by_id(db, lab_id=lab_id, current_user=current_user)
