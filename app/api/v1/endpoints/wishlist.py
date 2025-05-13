from fastapi import (
    APIRouter, Depends, HTTPException,
    Response, Request, status
)
from app.middleware.rate_limiter import limiter
from app.infrastructure.repository.wishlist import WishlistRepository
from app.core.dependencies import get_wislist_repo
from app.schemas.wishlist import WishlistIn
from app.core.config import settings
from app.enums.enums import AppMode


router = APIRouter()


@router.get("/")
@limiter.limit("100/minute")
async def get_wishlish(
    request: Request,
    repo: WishlistRepository = Depends(get_wislist_repo)
):
    try:
        data = await repo.get_all()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/")
@limiter.limit("5/minute")
async def create_wishlish(
    request: Request,
    data: WishlistIn,
    repo: WishlistRepository = Depends(get_wislist_repo)
):

    if not data.email or "@" not in data.email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    try:
        if settings.mode == AppMode.TEST:
            return Response(status_code=status.HTTP_200_OK)
        await repo.create(data)
        return Response(status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
