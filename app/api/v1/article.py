from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_article_service, get_db, require_admin_user
from app.common.permissions import is_admin
from app.api.dependencies.auth import get_optional_user
from app.api.dependencies.integrations import get_redis_client
from app.infrastructure.redis.client import RedisClient
from app.common.cache_keys import ARTICLE_DETAIL_PREFIX, ARTICLE_DETAIL_TTL, ARTICLE_LIST_PREFIX, ARTICLE_LIST_TTL
from app.common.cache_utils import cached_detail, cached_list
from app.core.config import settings
from app.domain.article.schema import ArticleCreateSchema, ArticleOutSchema, ArticleSummarySchema, ArticleUpdateSchema
from app.domain.article.service import ArticleService
from app.domain.user.schema import UserOutSchema
from app.enums.enums import ArticleStatus, ArticleType
from app.infrastructure.redis.client import RedisClient
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix=settings.api.v1.article, tags=["Article"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ArticleOutSchema)
@limiter.limit("30/minute")
async def create_article(
    request: Request,
    payload: ArticleCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ArticleService = Depends(get_article_service),
):
    return await service.create(db, payload, current_user=current_user)


@router.get("", response_model=list[ArticleSummarySchema])
@limiter.limit("60/minute")
async def list_articles(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: ArticleStatus | None = None,
    article_type: ArticleType | None = Query(default=None, alias="articleType"),
    tag: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: ArticleService = Depends(get_article_service),
    redis: RedisClient = Depends(get_redis_client),
):
    if current_user is None or not is_admin(current_user):
        return await cached_list(
            redis,
            key=f"{ARTICLE_LIST_PREFIX}:{article_type}:{tag}:{limit}:{offset}",
            ttl=ARTICLE_LIST_TTL,
            schema_class=ArticleSummarySchema,
            fetch_fn=lambda: service.list_articles(db, limit=limit, offset=offset, status=status, article_type=article_type, tag=tag, current_user=current_user),
        )
    return await service.list_articles(db, limit=limit, offset=offset, status=status, article_type=article_type, tag=tag, current_user=current_user)


@router.get("/slug/{slug}", response_model=ArticleOutSchema)
@limiter.limit("60/minute")
async def get_article_by_slug(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: ArticleService = Depends(get_article_service),
    redis: RedisClient = Depends(get_redis_client),
):
    if current_user is None or not is_admin(current_user):
        return await cached_detail(
            redis,
            key=f"{ARTICLE_DETAIL_PREFIX}:{slug}",
            ttl=ARTICLE_DETAIL_TTL,
            schema_class=ArticleOutSchema,
            fetch_fn=lambda: service.get_by_slug(db, slug=slug, current_user=current_user),
        )
    return await service.get_by_slug(db, slug=slug, current_user=current_user)


@router.get("/{article_id}", response_model=ArticleOutSchema)
@limiter.limit("60/minute")
async def get_article(
    request: Request,
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema | None = Depends(get_optional_user),
    service: ArticleService = Depends(get_article_service),
):
    return await service.get_by_id(db, article_id=article_id, current_user=current_user)


@router.patch("/{article_id}", response_model=ArticleOutSchema)
@limiter.limit("30/minute")
async def update_article(
    request: Request,
    article_id: int,
    payload: ArticleUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ArticleService = Depends(get_article_service),
):
    return await service.update(db, article_id=article_id, data=payload, current_user=current_user)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_article(
    request: Request,
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserOutSchema = Depends(require_admin_user),
    service: ArticleService = Depends(get_article_service),
):
    await service.delete_by_id(db, article_id=article_id, current_user=current_user)
