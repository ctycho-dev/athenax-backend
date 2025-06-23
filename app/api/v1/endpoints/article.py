from typing import List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request
)
from fastapi.responses import JSONResponse
from app.domain.article.service import ArticleService
from app.domain.article.schema import ArticleCreate, ArticleOut
from app.middleware.rate_limiter import limiter
from app.core.dependencies import (
    get_article_service_with_auth,
    get_article_service_optional
)
from app.enums.enums import AppMode
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger()
router = APIRouter()


@router.get("/", response_model=List[ArticleOut])
@limiter.limit("100/minute")
async def get_articles(
    request: Request,
    service: ArticleService = Depends(get_article_service_optional),
):
    try:
        return await service.get_all()
    except Exception as e:
        logger.error("[get_articles] %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/", response_model=List[ArticleOut])
@limiter.limit("100/minute")
async def get_articles_by_user(
    request: Request,
    service: ArticleService = Depends(get_article_service_with_auth),
):
    try:
        return await service.get_by_user()
    except Exception as e:
        logger.error("[get_articles_by_user] %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/state/{state}", response_model=List[ArticleOut])
@limiter.limit("100/minute")
async def get_articles_by_state(
    request: Request,
    state: str,
    service: ArticleService = Depends(get_article_service_with_auth),
):
    try:
        return await service.get_by_state(state)
    except Exception as e:
        logger.error("[get_articles_by_state] %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{article_id}", response_model=ArticleOut)
@limiter.limit("100/minute")
async def get_article(
    request: Request,
    article_id: str,
    service: ArticleService = Depends(get_article_service_with_auth),
):
    try:
        return await service.get_by_id(article_id)
    except Exception as e:
        logger.error("[get_article] %s", e)
        raise HTTPException(status_code=404, detail="Article not found")


@router.post("/", status_code=200)
@limiter.limit("10/hour")
async def create_article(
    request: Request,
    data: ArticleCreate,
    service: ArticleService = Depends(get_article_service_with_auth),
):
    try:
        if settings.mode == AppMode.TEST:
            return JSONResponse(status_code=200, content={"success": True})
        await service.create(data)
        return JSONResponse(status_code=200, content={"success": True})
    except Exception as e:
        logger.error("[create_article] %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
