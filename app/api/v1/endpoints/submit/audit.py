from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status
)
from fastapi.responses import JSONResponse

from app.middleware.rate_limiter import limiter
from app.exceptions import NotFoundError
from app.domain.submit.audit.schema import (
    AuditSubmitSchema,
    CommentCreateSchema
)
from app.core.dependencies import get_audit_service
from app.core.logger import get_logger
from app.core.config import settings
from app.enums.enums import AppMode
from app.domain.submit.audit.service import AuditService
from app.enums.enums import ReportState


logger = get_logger()
router = APIRouter()


@router.get("/")
@limiter.limit("100/minute")
async def get_audits(
    request: Request,
    service: AuditService = Depends(get_audit_service)
):
    """
    Retrieve all audit records.

    Args:
        request (Request): Incoming HTTP request
        service (AuditService): Injected audit service with repo and user context

    Returns:
        List[AuditOut]: List of audit records

    Raises:
        HTTPException: 500 Internal Server Error on unexpected failure
    """
    try:
        return await service.get_all()
    except Exception as e:
        logger.error("Unexpected error in get_audits: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@router.get("/user/")
@limiter.limit("100/minute")
async def get_audits_by_user(
    request: Request,
    service: AuditService = Depends(get_audit_service),
):
    """
    Retrieve all audit records associated with the authenticated user.

    Args:
        request (Request): Incoming HTTP request
        service (AuditService): Audit service instance
        current_user (UserOut): Currently authenticated user

    Returns:
        List[AuditOut]: User-specific audit records

    Raises:
        HTTPException: 500 Internal Server Error on unexpected failure
    """
    try:
        return await service.get_by_user()
    except Exception as e:
        logger.error("Unexpected error in get_audits_by_user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e
    

@router.get("/state/{state}")
@limiter.limit("100/minute")
async def get_audits_by_state(
    request: Request,
    state: str,
    service: AuditService = Depends(get_audit_service),
):
    """
    Retrieve all audit records in a specific state, sorted from newest to oldest.

    Args:
        request (Request): Incoming HTTP request
        state (ReportState): State to filter audits by
        service (AuditService): Audit service instance

    Returns:
        List[AuditOut]: Audit records matching the given state

    Raises:
        HTTPException: 500 Internal Server Error on unexpected failure
    """
    try:
        return await service.get_by_state(state)
    except Exception as e:
        logger.error("Unexpected error in get_audits_by_state: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e

@router.get("/{audit_id}")
@limiter.limit("100/minute")
async def get_audit(
    request: Request,
    audit_id: str,
    service: AuditService = Depends(get_audit_service),
):
    """
    Retrieve a specific audit record by ID.

    Args:
        request (Request): Incoming HTTP request
        audit_id (str): UUID of the audit record
        service (AuditService): Audit service instance

    Returns:
        AuditOut: Audit record matching the given ID

    Raises:
        HTTPException: 404 if not found
        HTTPException: 500 Internal Server Error on unexpected failure
    """
    try:
        return await service.get_by_id(audit_id)
    except NotFoundError as e:
        logger.error("Audit not found: %s", audit_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in get_audit: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


# @router.patch("/{audit_id}/state")
# @limiter.limit("5/minute")
# async def update_audit_state(
#     audit_id: str,
#     data: StateUpdateSchema,
#     service: AuditService = Depends(get_audit_service),
# ):
#     try:
#         await service.update_state(audit_id, data.state)
#         return JSONResponse(status_code=200, content={"success": True})
#     except NotFoundError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         logger.error("Error updating state: %s", e)
#         raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{audit_id}/comment")
@limiter.limit("5/minute")
async def add_audit_comment(
    request: Request,
    audit_id: str,
    data: CommentCreateSchema,
    service: AuditService = Depends(get_audit_service),
):
    try:
        await service.add_comment(audit_id, data.comment)
        return JSONResponse(status_code=200, content={"success": True})
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error adding comment: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{audit_id}")
@limiter.limit("5/minute")
async def update_audit(
    request: Request,
    audit_id: str,
    data: AuditSubmitSchema,
    service: AuditService = Depends(get_audit_service),
):
    """
    Update an existing audit record.

    Only the owner of the audit can perform the update.

    Args:
        request (Request): Incoming HTTP request
        audit_id (str): UUID of the audit to update
        data (AuditSubmitSchema): New data to update
        service (AuditService): Audit service instance
        current_user (UserOut): Currently authenticated user

    Returns:
        JSONResponse: { "success": True } on success

    Raises:
        HTTPException: 401 if not authorized
        HTTPException: 404 if audit not found
        HTTPException: 422 on validation error
        HTTPException: 500 Internal Server Error on unexpected failure
    """
    try:
        await service.update(audit_id, data)
        return JSONResponse(status_code=200, content={"success": True})
    except ValueError as e:
        logger.error("Validation error in update_audit: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in update_audit: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e


@router.post("/")
@limiter.limit("10/hour")
async def create_audit(
    request: Request,
    data: AuditSubmitSchema,
    service: AuditService = Depends(get_audit_service),
):
    """
    Create a new audit record.

    Args:
        request (Request): Incoming HTTP request
        data (AuditSubmitSchema): Data for the new audit
        service (AuditService): Audit service instance
        current_user (UserOut): Currently authenticated user

    Returns:
        JSONResponse: { "success": True } on success

    Raises:
        HTTPException: 422 on validation error
        HTTPException: 500 Internal Server Error on unexpected failure
    """
    try:
        if settings.mode == AppMode.TEST:
            return Response(status_code=status.HTTP_200_OK)

        await service.create(data)
        return JSONResponse(status_code=200, content={"success": True})
    except ValueError as e:
        logger.error("Validation error in create_audit: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in create_audit: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e
