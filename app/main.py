from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import api_router
from app.core.config import settings
from app.database.connection import db_manager
from app.services.storj_services import storj_service
from app.core.logger import get_logger, cleanup_logger
from app.infrastructure.redis.redis_client import redis_client
from app.middleware.rate_limiter import rate_limiter

logger = get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastApi lifecycle."""
    try:
        try:
            logger.info("Initializing application resources")
            await db_manager.connect()
        except ConnectionError as conn_err:
            logger.critical("Connection failed: %s", conn_err, exc_info=True)
            raise

        try:
            storj_service.connect()
        except Exception as e:
            logger.error("Error disconnecting storage: %s", e, exc_info=True)

        logger.info("App started")
        yield

    finally:
        await db_manager.disconnect()
        await redis_client.close()
        await redis_client.connection_pool.disconnect()
        storj_service.disconnect()
        cleanup_logger()


app = FastAPI(lifespan=lifespan)


app.middleware('http')(rate_limiter)


origins = [
    "https://wwww.athenax.co",
    "http://localhost:5173",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix=settings.api_version)

logger.info('Start application')


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
