# app/api/v1/report.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.report.schema import (
    ReportCreateSchema,
    ReportUpdateSchema,
    ReportOutSchema
)
from app.domain.report.service import ReportService
from app.api.dependencies import get_db, get_report_service
from app.core.logger import get_logger
from app.core.config import settings
from app.middleware.rate_limiter import limiter

logger = get_logger(__name__)

router = APIRouter(prefix=settings.api.v1.report, tags=["Report"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ReportOutSchema)
@limiter.limit("20/minute")
async def create_report(
    request: Request,
    report: ReportCreateSchema,
    db: AsyncSession = Depends(get_db),
    service: ReportService = Depends(get_report_service)
):
    """Create a new report."""
    created_report = await service.create(db, report)
    return created_report


@router.get("/", status_code=status.HTTP_200_OK, response_model=list[ReportOutSchema])
@limiter.limit("60/minute")
async def get_all_reports(
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: ReportService = Depends(get_report_service)
):
    """Retrieve all reports."""
    reports = await service.get_all(db)
    return reports


@router.get("/camera/{camera_id}", status_code=status.HTTP_200_OK, response_model=list[ReportOutSchema])
@limiter.limit("100/minute")
async def get_reports_by_camera_id(
    request: Request,
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    service: ReportService = Depends(get_report_service)
):
    """Retrieve all reports for a specific camera."""
    reports = await service.get_by_camera_id(db, camera_id)
    return reports


@router.get("/{report_id}", status_code=status.HTTP_200_OK, response_model=ReportOutSchema)
@limiter.limit("100/minute")
async def get_report_by_id(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    service: ReportService = Depends(get_report_service)
):
    """Retrieve a single report by ID."""
    report = await service.get_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id {report_id} not found"
        )
    return report


@router.put("/{report_id}", status_code=status.HTTP_200_OK, response_model=ReportOutSchema)
@limiter.limit("20/minute")
async def update_report(
    request: Request,
    report_id: int,
    report_data: ReportUpdateSchema,
    db: AsyncSession = Depends(get_db),
    service: ReportService = Depends(get_report_service)
):
    """Update existing report."""
    updated_report = await service.update(db, report_id, report_data)
    if not updated_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id {report_id} not found"
        )
    return updated_report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_report_by_id(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    service: ReportService = Depends(get_report_service)
):
    """Delete a report by ID."""
    await service.delete_by_id(db, report_id)

