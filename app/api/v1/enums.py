from fastapi import APIRouter, Request

from app.enums.enums import ProductSector, ProductStage
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix="/enums", tags=["Enums"])


@router.get("/product-meta")
@limiter.limit("60/minute")
async def get_product_meta(request: Request):
    return {
        "sectors": [e.value for e in ProductSector],
        "stages": [e.value for e in ProductStage],
    }