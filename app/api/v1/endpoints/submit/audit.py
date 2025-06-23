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
    CommentCreateSchema,
    StateUpdateSchema
)
from app.core.dependencies import get_audit_service
from app.core.logger import get_logger
from app.core.config import settings
from app.enums.enums import AppMode
from app.domain.submit.audit.service import AuditService


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
        request (Request): Incoming HTTP request.
        service (AuditService): Injected audit service.

    Returns:
        List[AuditOut]: List of all audits.

    Raises:
        HTTPException: 500 Internal Server Error on unexpected failure.
    """
    try:
        return await service.get_all()
    except Exception as e:
        logger.error("[get_audits] Unexpected error: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) from e


@router.get("/user/")
@limiter.limit("100/minute")
async def get_audits_by_user(
    request: Request,
    service: AuditService = Depends(get_audit_service),
):
    """
    Retrieve audit records submitted by the current user.

    Args:
        request (Request): Incoming HTTP request.
        service (AuditService): Injected audit service.

    Returns:
        List[AuditOut]: List of audits by the user.

    Raises:
        HTTPException: 500 Internal Server Error on unexpected failure.
    """
    try:
        return await service.get_by_user()
    except Exception as e:
        logger.error("[get_audits_by_user] Unexpected error: %s", e)
        raise HTTPException(
            status_code=500,
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
    Retrieve audit records filtered by a specific state.

    Args:
        request (Request): Incoming HTTP request.
        state (str): The audit state to filter by.
        service (AuditService): Injected audit service.

    Returns:
        List[AuditOut]: List of audits matching the given state.

    Raises:
        HTTPException: 500 Internal Server Error on unexpected failure.
    """
    try:
        return await service.get_by_state(state)
    except Exception as e:
        logger.error("[get_audits_by_state] Unexpected error: %s", e)
        raise HTTPException(
            status_code=500,
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
    Retrieve a specific audit record by its ID.

    Args:
        request (Request): Incoming HTTP request.
        audit_id (str): UUID of the audit.
        service (AuditService): Injected audit service.

    Returns:
        AuditOut: The requested audit record.

    Raises:
        HTTPException: 404 if audit not found.
        HTTPException: 500 Internal Server Error on unexpected failure.
    """
    try:
        return await service.get_by_id(audit_id)
    except NotFoundError as e:
        logger.error("[get_audit] Audit not found: %s", audit_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("[get_audit] Unexpected error: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) from e


@router.patch("/{audit_id}/state")
@limiter.limit("5/minute")
async def update_audit_state(
    request: Request,
    audit_id: str,
    data: StateUpdateSchema,
    service: AuditService = Depends(get_audit_service),
):
    """
    Update the state of a specific audit record.

    Args:
        audit_id (str): UUID of the audit.
        data (StateUpdateSchema): New state value.
        service (AuditService): Injected audit service.

    Returns:
        JSONResponse: {"success": True} on success.

    Raises:
        HTTPException: 404 if audit not found.
        HTTPException: 500 Internal Server Error on unexpected failure.
    """
    try:
        await service.update_state(audit_id, data.state)
        return JSONResponse(status_code=200, content={"success": True})
    except NotFoundError as e:
        logger.error("[update_audit_state] Audit not found: %s", audit_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("[update_audit_state] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/{audit_id}/comment")
@limiter.limit("5/minute")
async def add_audit_comment(
    request: Request,
    audit_id: str,
    data: CommentCreateSchema,
    service: AuditService = Depends(get_audit_service),
):
    """
    Add a comment to a specific audit record.

    Args:
        request (Request): Incoming HTTP request.
        audit_id (str): UUID of the audit.
        data (CommentCreateSchema): Comment payload.
        service (AuditService): Injected audit service.

    Returns:
        JSONResponse: {"success": True} on success.

    Raises:
        HTTPException: 404 if audit not found.
        HTTPException: 500 Internal Server Error on unexpected failure.
    """
    try:
        await service.add_comment(audit_id, data.comment)
        return JSONResponse(status_code=200, content={"success": True})
    except NotFoundError as e:
        logger.error("[add_audit_comment] Audit not found: %s", audit_id)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("[add_audit_comment] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{audit_id}")
@limiter.limit("5/minute")
async def update_audit(
    request: Request,
    audit_id: str,
    data: AuditSubmitSchema,
    service: AuditService = Depends(get_audit_service),
):
    """
    Update an existing audit record. Only the audit owner may perform this operation.

    Args:
        request (Request): Incoming HTTP request.
        audit_id (str): UUID of the audit.
        data (AuditSubmitSchema): Updated audit data.
        service (AuditService): Injected audit service.

    Returns:
        JSONResponse: {"success": True} on success.

    Raises:
        HTTPException: 401 if unauthorized.
        HTTPException: 404 if audit not found.
        HTTPException: 422 on validation error.
        HTTPException: 500 Internal Server Error on unexpected failure.
    """
    try:
        await service.update(audit_id, data)
        return JSONResponse(status_code=200, content={"success": True})
    except ValueError as e:
        logger.error("[update_audit] Validation error: %s", e)
        raise HTTPException(
            status_code=422,
            detail=str(e)
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[update_audit] Unexpected error: %s", e)
        raise HTTPException(
            status_code=500,
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
        request (Request): Incoming HTTP request.
        data (AuditSubmitSchema): Payload for the new audit.
        service (AuditService): Injected audit service.

    Returns:
        JSONResponse: {"success": True} on success.

    Raises:
        HTTPException: 422 on validation error.
        HTTPException: 500 Internal Server Error on unexpected failure.
    """
    try:
        if settings.mode == AppMode.TEST:
            return Response(status_code=200)

        await service.create(data)
        return JSONResponse(status_code=200, content={"success": True})
    except ValueError as e:
        logger.error("[create_audit] Validation error: %s", e)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException as e:
        logger.error("[create_audit] HTTPException: %s", e)
        raise
    except Exception as e:
        logger.error("[create_audit] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
