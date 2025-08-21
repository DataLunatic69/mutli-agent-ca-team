from fastapi import FastAPI
from .src.ca_multi_agent.config.settings import settings
from .src.ca_multi_agent.api.v1.router import api_router

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
    )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {"message": "CA Multi-Agent System API is running"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app

app = create_app()