from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings


def add_cors_middleware(app: FastAPI):
    origins = []

    if settings.MODE == "dev":
        origins.append("http://localhost:5173")
        origins.append("http://localhost:3543")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
