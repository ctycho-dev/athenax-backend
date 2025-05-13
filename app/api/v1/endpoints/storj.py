from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, UploadFile
from app.middleware.rate_limiter import limiter
from app.services.storj_services import storj_service
from app.core.logger import get_logger
from app.core.config import settings
from app.enums.enums import AppMode


logger = get_logger()

router = APIRouter()


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

        res = storj_service.upload_file(file, bucket)
        return res
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e