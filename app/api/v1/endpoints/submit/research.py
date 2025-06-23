from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status
)
from fastapi.responses import JSONResponse
from app.middleware.rate_limiter import limiter
from app.domain.submit.research.schema import (
    ResearchSubmitSchema,
    StateUpdateSchema,
    CommentCreateSchema
)
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
    """
    Retrieve all research records.
    """
    try:
        return await service.get_all()
    except Exception as e:
        logger.error("[get_researches] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/user/")
@limiter.limit("100/minute")
async def get_researches_by_user(
    request: Request,
    service: ResearchService = Depends(get_research_service),
):
    """
    Retrieve research records submitted by the current user.
    """
    try:
        return await service.get_by_user()
    except Exception as e:
        logger.error("[get_researches_by_user] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/state/{state}")
@limiter.limit("100/minute")
async def get_researches_by_state(
    request: Request,
    state: str,
    service: ResearchService = Depends(get_research_service),
):
    """
    Retrieve research records filtered by a specific state.
    """
    try:
        return await service.get_by_state(state)
    except Exception as e:
        logger.error("[get_researches_by_state] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{research_id}")
@limiter.limit("100/minute")
async def get_research(
    request: Request,
    research_id: str,
    service: ResearchService = Depends(get_research_service),
):
    """
    Retrieve a specific research record by its ID.
    """
    try:
        return await service.get_by_id(research_id)
    except NotFoundError as e:
        logger.error("[get_research] Not found: %s", research_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("[get_research] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{research_id}")
@limiter.limit("5/minute")
async def update_research(
    request: Request,
    research_id: str,
    data: ResearchSubmitSchema,
    service: ResearchService = Depends(get_research_service),
):
    """
    Update an existing research record.
    """
    try:
        await service.update(research_id, data)
        return JSONResponse(status_code=200, content={"success": True})
    except NotFoundError as e:
        logger.error("[update_research] Not found: %s", research_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except HTTPException as e:
        logger.error("[update_research] HTTP error: %s", e)
        raise
    except Exception as e:
        logger.error("[update_research] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{research_id}/state")
@limiter.limit("5/minute")
async def update_research_state(
    request: Request,
    research_id: str,
    data: StateUpdateSchema,
    service: ResearchService = Depends(get_research_service),
):
    """
    Update the state of a specific research record.
    """
    try:
        await service.update_state(research_id, data.state)
        return JSONResponse(status_code=200, content={"success": True})
    except NotFoundError as e:
        logger.error("[update_research_state] Research not found: %s", research_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("[update_research_state] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/{research_id}/comment")
@limiter.limit("5/minute")
async def add_research_comment(
    request: Request,
    research_id: str,
    data: CommentCreateSchema,
    service: ResearchService = Depends(get_research_service),
):
    """
    Add a comment to a specific research record.
    """
    try:
        await service.add_comment(research_id, data.comment)
        return JSONResponse(status_code=200, content={"success": True})
    except NotFoundError as e:
        logger.error("[add_research_comment] Research not found: %s", research_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("[add_research_comment] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/")
@limiter.limit("10/hour")
async def create_research(
    request: Request,
    data: ResearchSubmitSchema,
    service: ResearchService = Depends(get_research_service),
):
    """
    Create a new research record.
    """
    try:
        await service.create(data)
        return JSONResponse(status_code=201, content={"success": True})
    except ValueError as e:
        logger.error("[create_research] Validation error: %s", e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except HTTPException as e:
        logger.error("[create_research] HTTPException: %s", e)
        raise
    except Exception as e:
        logger.error("[create_research] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
