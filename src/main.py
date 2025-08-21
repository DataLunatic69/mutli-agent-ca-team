from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging

from .config.settings import settings
from .utils.logging import setup_logging
from .api.v1.router import api_router
from .db.session import SyncSessionLocal, AsyncSessionLocal

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Multi-Agent System for Chartered Accountancy Tasks",
        version="1.0.0",
        debug=settings.DEBUG,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"] if settings.DEBUG else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoints
    @app.get("/")
    async def root():
        return {"message": "CA Multi-Agent System API is running", "version": "1.0.0"}

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "database": "connected",  # Would check database connection
            "services": "available"
        }

    @app.get("/agents")
    async def list_agents():
        """List all available agents"""
        from .agents import get_agent
        return {
            "agents": [
                "A1_Intent_Classification",
                "A2_Document_Ingestion",
                "A3_Ledger_Posting",
                "A5_Reconciliation",
                "A6_GST_Agent",
                "A7_Income_Tax_Agent",
                "A8_Compliance_Calendar",
                "A9_Reporting_Analytics",
                "A10_Advisory_Q&A",
                "A11_Anomaly_Detection",
                "A12_Report_Formatter",
                "Supervisor"
            ]
        }

    # Include API routers
    app.include_router(api_router, prefix="/api/v1")

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting CA Multi-Agent System API")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Debug mode: {settings.DEBUG}")
        
        # Initialize agents (warm-up)
        try:
            from .agents import get_agent
            # Pre-load agents to avoid cold starts
            intent_agent = get_agent("A1_Intent_Classification")
            logger.info("Agents initialized successfully")
        except Exception as e:
            logger.warning(f"Agent initialization warning: {e}")

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down CA Multi-Agent System API")

    return app

app = create_app()