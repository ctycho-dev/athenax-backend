from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile
from app.services.storj_services import storj_service
from app.core.logger import get_logger


logger = get_logger()

router = APIRouter()

@router.post("/{bucket}")
def upload_file(
    bucket: str,
    file: UploadFile,
):
    try:
        res = storj_service.upload_file(file, bucket)
        return res
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e)) from e