from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings


def add_cors_middleware(app: FastAPI):
    origins = [o.strip() for o in settings.cors_origin.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
