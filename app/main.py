"""
Main FastAPI Application Entrypoint.
Initializes database tables, pre-warms the AI classifier, and registers routers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.services.classifier import get_classifier
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown routines."""
    # Initialize DB schema
    init_db()
    # Preload and train/cache AI classifier
    get_classifier()
    yield


app = FastAPI(
    title="PS04 Azure Support Ticket Automation API",
    description=(
        "AI-assisted API that classifies support tickets across Billing, Technical, Access, and General categories, "
        "proposes SLA priorities (P1-P4), routes ambiguous cases to human review, and prepares draft responses "
        "requiring human approval before marking ready. Packaged for Azure App Service."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware for cross-origin integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router, prefix="/api/v1", tags=["Support Tickets"])
# Also mount health directly at root for Azure App Service health probe default path
from app.api.routes import health_check
app.add_api_route("/health", health_check, methods=["GET"], tags=["Health Check"])


@app.get("/", tags=["Root"])
def root():
    """Service landing endpoint with metadata and quick documentation links."""
    return {
        "service": "PS04 Azure Support Ticket Automation API",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "ingest_ticket": "POST /api/v1/tickets",
            "list_tickets": "GET /api/v1/tickets",
            "get_ticket": "GET /api/v1/tickets/{ticket_id}",
            "approve_ticket": "POST /api/v1/tickets/{ticket_id}/approve",
            "reject_ticket": "POST /api/v1/tickets/{ticket_id}/reject",
            "metrics_evaluation": "GET /api/v1/metrics"
        },
        "target_platform": "Azure App Service (Linux Container)",
        "categories": ["Billing", "Technical", "Access", "General"],
        "priority_levels": ["P1 (Critical)", "P2 (High)", "P3 (Medium)", "P4 (Low)"]
    }
