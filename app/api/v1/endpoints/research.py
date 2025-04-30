from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse, JSONResponse

from app.exceptions import NotFoundError
from app.services.storj_services import storj_service
from app.schemas.research import ResearchFormSchema, StoredFile
from app.infrastructure.repository.research import ResearchRepository
from app.core.dependencies import get_research_repo, get_current_user
from app.core.logger import get_logger


logger = get_logger()

router = APIRouter()


@router.get("/")
async def get_researches(
    repo: ResearchRepository = Depends(get_research_repo),
    privy_id: str = Depends(get_current_user),
):
    try:
        response = await repo.get_by_user(privy_id)
        # response = await repo.get_all()
        return response
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{research_id}")
async def get_research(
    research_id: str,
    repo: ResearchRepository = Depends(get_research_repo),
    _: str = Depends(get_current_user),
):
    try:
        response = await repo.get_by_id(research_id)
        return response
    except NotFoundError as e:
        logger.error(e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.patch("/{research_id}")
async def update_research(
    research_id: str,
    data: ResearchFormSchema,
    repo: ResearchRepository = Depends(get_research_repo),
    privy_id: str = Depends(get_current_user),
):
    try:
        audit = await repo.get_by_id(research_id)
        if not audit:
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Not Found'
            )
        if audit.user_privy_id != privy_id:
            return HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Not Authorized'
            )
        await repo.update(research_id, data)
        return JSONResponse(
            status_code=200,
            content={"success": True}
        )
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/")
async def create_research(
    data: ResearchFormSchema,
    repo: ResearchRepository = Depends(get_research_repo),
    privy_id: str = Depends(get_current_user),
):
    try:
        data.user_privy_id = privy_id
        await repo.create(data)
        return JSONResponse(
            status_code=200,
            content={"success": True}
        )
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/download/")
async def get_download_url(
    data: StoredFile
):
    try:
        file_obj = storj_service.get_storj_file(
            bucket=data.bucket,
            key=data.key,
        )

        # Encode the filename for HTTP headers
        encoded_filename = quote(data.original_filename.encode('utf-8'))
        return StreamingResponse(
            file_obj['Body'].iter_chunks(),  # Stream chunks directly
            media_type=data.content_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except HTTPException as e:
        logger.error('Error: %s', e)
        raise e
    except Exception as e:
        logger.error('Error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))
