"""FastAPI application entry point."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web_backend.core.config import CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS
from web_backend.api import config, model, robots

app = FastAPI(
    title="Humanoid Retargeting API",
    description="Web API for humanoid motion retargeting",
    version="1.0.0"
)

# CORS middleware - use configured origins
cors_origins = os.getenv("CORS_ORIGINS", ",".join(CORS_ORIGINS)).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# Include routers
app.include_router(config.router)
app.include_router(model.router)
app.include_router(robots.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Humanoid Retargeting API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    from web_backend.core.config import BACKEND_HOST, BACKEND_PORT

    uvicorn.run(
        "web_backend.main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=True
    )
