"""
FastAPI Route Definitions for Azure Support Ticket Automation API.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import (
    TicketCreate,
    TicketResponse,
    TicketApprovalRequest,
    TicketRejectionRequest,
    HealthResponse
)
from app.services.ticket_service import TicketService
from app.services.evaluator import run_test_set_evaluation

router = APIRouter()


@router.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and Classify Support Ticket",
    description="Accepts ticket ID and message, performs AI triage, calculates priority, generates draft response, and stores ticket state."
)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db)
) -> TicketResponse:
    """Ingest a support ticket, reject duplicates/invalid input, classify, and prepare draft response."""
    service = TicketService(db)
    ticket = service.create_ticket(payload)
    return ticket


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
    summary="Get Ticket Details",
    description="Fetch a stored ticket by its unique ticket ID."
)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db)
) -> TicketResponse:
    """Retrieve details, classification, and draft response of an existing ticket."""
    service = TicketService(db)
    return service.get_ticket(ticket_id)


@router.get(
    "/tickets",
    response_model=List[TicketResponse],
    summary="List Support Tickets",
    description="Query stored tickets with optional status, category, and review requirement filters."
)
def list_tickets(
    category: Optional[str] = Query(None, description="Filter by category (Billing, Technical, Access, General)"),
    priority: Optional[str] = Query(None, description="Filter by priority (P1, P2, P3, P4)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (CLASSIFIED, PENDING_REVIEW, READY, REJECTED)"),
    requires_manual_review: Optional[bool] = Query(None, description="Filter by manual review flag"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
) -> List[TicketResponse]:
    """List tickets with filtering."""
    service = TicketService(db)
    return service.list_tickets(
        category=category,
        priority=priority,
        status_filter=status_filter,
        requires_manual_review=requires_manual_review,
        limit=limit,
        offset=offset
    )


@router.post(
    "/tickets/{ticket_id}/approve",
    response_model=TicketResponse,
    summary="Approve Ticket Draft Response",
    description="Human reviewer sign-off. Transitions ticket status to READY for dispatch."
)
def approve_ticket(
    ticket_id: str,
    request: TicketApprovalRequest,
    db: Session = Depends(get_db)
) -> TicketResponse:
    """Approve a ticket draft response and mark state as READY."""
    service = TicketService(db)
    return service.approve_ticket(ticket_id, request)


@router.post(
    "/tickets/{ticket_id}/reject",
    response_model=TicketResponse,
    summary="Reject Support Ticket",
    description="Mark ticket as REJECTED with reviewer notes."
)
def reject_ticket(
    ticket_id: str,
    request: TicketRejectionRequest,
    db: Session = Depends(get_db)
) -> TicketResponse:
    """Reject invalid ticket."""
    service = TicketService(db)
    return service.reject_ticket(ticket_id, request)


@router.get(
    "/metrics",
    summary="Model Accuracy & Test Set Evaluation",
    description="Reports classification accuracy, confusion matrix, and per-class metrics on the reserved 10 test tickets."
)
def get_metrics() -> Dict[str, Any]:
    """Retrieve test set accuracy and evaluation metrics."""
    return run_test_set_evaluation()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Health probe for container readiness and Azure App Service liveness checks."
)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Returns application health status, database connectivity, and classifier state."""
    db_ok = True
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    from app.services.classifier import get_classifier
    clf = get_classifier()

    return HealthResponse(
        status="healthy" if db_ok and clf.is_trained else "degraded",
        service="azure-support-ticket-automation",
        version="1.0.0",
        database="connected" if db_ok else "disconnected",
        classifier_loaded=clf.is_trained
    )
