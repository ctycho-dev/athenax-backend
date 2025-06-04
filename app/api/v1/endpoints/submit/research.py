from fastapi import (
    APIRouter, Depends, HTTPException,
    Request, status
)
from fastapi.responses import JSONResponse
from app.middleware.rate_limiter import limiter
from app.domain.submit.research.schema import ResearchSubmitSchema
from app.domain.submit.research.service import ResearchService
from app.core.dependencies import get_research_service
from app.exceptions import NotFoundError
from app.core.logger import get_logger

logger = get_logger()
router = APIRouter()


@router.get("/")
@limiter.limit("100/minute")
async def get_researches(
    request: Request,
    service: ResearchService = Depends(get_research_service),
):
    try:
        return await service.get_all()
    except Exception as e:
        logger.error("Unexpected error in get_researches: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{research_id}")
@limiter.limit("100/minute")
async def get_research(
    request: Request,
    research_id: str,
    service: ResearchService = Depends(get_research_service),
):
    try:
        return await service.get_by_id(research_id)
    except NotFoundError as e:
        logger.error(e)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Unexpected error in get_research: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{research_id}")
@limiter.limit("5/minute")
async def update_research(
    request: Request,
    research_id: str,
    data: ResearchSubmitSchema,
    service: ResearchService = Depends(get_research_service),
):
    try:
        await service.update(research_id, data)
        return JSONResponse(status_code=200, content={"success": True})
    except NotFoundError as e:
        logger.error("Not found in update_research: %s", e)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except HTTPException as e:
        logger.error("Unauthorized or HTTP error in update_research: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error in update_research: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/")
@limiter.limit("10/hour")
async def create_research(
    request: Request,
    data: ResearchSubmitSchema,
    service: ResearchService = Depends(get_research_service),
):
    try:
        await service.create(data)
        return JSONResponse(status_code=201, content={"success": True})
    except Exception as e:
        logger.error("Unexpected error in create_research: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
