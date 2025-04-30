from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi import APIRouter, HTTPException, Depends

from app.infrastructure.repository.wishlist import WishlistRepository
from app.core.dependencies import get_wislist_repo
from app.schemas.wishlist import WishlistIn


router = APIRouter()


@router.get("/")
async def get_wishlish(
    repo: WishlistRepository = Depends(get_wislist_repo)
):
    try:
        data = await repo.get_all()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/")
async def create_wishlish(
    data: WishlistIn,
    repo: WishlistRepository = Depends(get_wislist_repo)
):

    if not data.email or "@" not in data.email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    try:
        await repo.create(data)
        return Response(status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
