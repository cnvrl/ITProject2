"""Main FastAPI application for TC-Explorer 2.0."""

from fastapi import FastAPI

from app.api.routes import router as api_router


app = FastAPI(
    title="TC-Explorer 2.0 API",
    version="0.1.0",
    description="Backend API for tropical cyclone data exploration.",
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    #Return a simple message showing that the API is running.
    return {"message": "TC-Explorer 2.0 API is running"}