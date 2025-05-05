from fastapi import APIRouter
from app.api.v1.endpoints import (
    audit,
    research,
    user,
    email,
    storj,
    wishlist
)

api_router = APIRouter()

api_router.include_router(
    audit.router,
    prefix="/audit",
    tags=["Audit"]
)

api_router.include_router(
    research.router,
    prefix="/research",
    tags=["Research"]
)

api_router.include_router(
    user.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    email.router,
    prefix="/email",
    tags=["Email"]
)

api_router.include_router(
    storj.router,
    prefix="/s3",
    tags=["Data storage"]
)

api_router.include_router(
    wishlist.router,
    prefix="/wishlist",
    tags=["Wishlist"]
)
