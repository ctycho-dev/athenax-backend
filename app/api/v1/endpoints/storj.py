import httpx
from urllib.parse import quote
import asyncio
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
    UploadFile
)
from app.infrastructure.storage.storj.service import storj_service
from fastapi.responses import StreamingResponse
from app.domain.submit.audit.schema import AuditSubmitSchema, StoredFile
from app.middleware.rate_limiter import limiter
from app.infrastructure.storage.storj.service import storj_service
from app.infrastructure.storage.cloudflareR2.service import r2_service

from app.core.logger import get_logger
from app.core.config import settings
from app.enums.enums import AppMode

MAX_RETRIES = 2

logger = get_logger()

router = APIRouter()


@router.get("/images/{img_id}/{folder:path}/{filename}")
@limiter.limit("200/minute")
async def proxy_storj_image(
    request: Request,
    img_id: str,
    folder: str,
    filename: str
):
    url = f"https://link.storjshare.io/raw/{img_id}/{folder}/{filename}"
    timeout = httpx.Timeout(10.0)

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "application/octet-stream")
                    return StreamingResponse(response.aiter_bytes(), media_type=content_type)
                else:
                    raise HTTPException(status_code=response.status_code, detail="Failed to fetch image")
        except httpx.ReadTimeout:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)  # wait before retrying
                continue
            else:
                raise HTTPException(status_code=504, detail="Image fetch timed out")


@router.post("/{bucket}")
@limiter.limit("5/minute")
def upload_file(
    request: Request,
    bucket: str,
    file: UploadFile,
):
    try:
        if settings.mode == AppMode.TEST:
            return Response(status_code=status.HTTP_200_OK)

        res = r2_service.upload_file(file, bucket)
        # res = storj_service.upload_file(file, bucket)
        return res
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.post("/download/")
@limiter.limit("15/minute")
async def get_download_url(
    request: Request,
    data: StoredFile
):
    try:
        if settings.mode == AppMode.TEST:
            return Response(status_code=status.HTTP_200_OK)

        file_obj = r2_service.get_storj_file(
        # file_obj = storj_service.get_storj_file(
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
