from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="Backend API for TC-Explorer tropical cyclone analysis."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # okay for development; restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict:
    return {
        "message": f"{settings.app_name} is running",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
    }


@app.get("/health")
def app_health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }