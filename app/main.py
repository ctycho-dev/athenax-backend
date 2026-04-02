from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.middleware.logging import AccessLogMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.database.connection import db_manager
from app.api.v1 import router as api_router
# Import models so SQLAlchemy metadata knows about every table before create_all().
from app.domain.product.model import Product, ProductCategory, ProductVote, ProductBookmark, ProductInvestorInterest, ProductComment  # noqa: F401
from app.domain.university.model import University  # noqa: F401
from app.domain.lab.model import Lab, LabCategory  # noqa: F401
from app.domain.paper.model import Paper, PaperCategory, PaperVote  # noqa: F401
from app.exceptions.exceptions import add_exception_handlers
from app.core.logger import (
    get_logger,
    setup_logging
)
from app.middleware.rate_limiter import (
    limiter,
    rate_limit_exceeded_handler
)
from app.middleware.cors import add_cors_middleware


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI application lifecycle."""
    try:
        setup_logging()
        db_manager.init_engine()
        logger.info("Application startup complete")
        yield
    except Exception as e:
        logger.error("lifespan error: %s", e)
        raise
    finally:
        logger.info("Application shutting down")
        await db_manager.close()


app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter

# CORS last = outermost layer
add_cors_middleware(app)

app.add_middleware(AccessLogMiddleware)
app.add_middleware(SlowAPIMiddleware)

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
add_exception_handlers(app)

app.include_router(api_router)


@app.get("/health")
@limiter.limit("5/minute")
async def health_check(request: Request):
    return {"status": "healthy"}
