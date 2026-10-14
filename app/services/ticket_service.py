"""
Core Ticket Service coordinating classification, priority assignment,
summarization, persistence, duplicate checking, and human review approvals.
"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.db_models import Ticket
from app.models.schemas import (
    TicketApprovalRequest,
    TicketCreate,
    TicketRejectionRequest,
)
from app.services.classifier import CATEGORY_TEAM_MAP, get_classifier
from app.services.priority import determine_priority
from app.services.summarizer import generate_draft_response, generate_summary


class TicketService:
    """Service layer managing support ticket business workflow."""

    def __init__(self, db: Session):
        self.db = db
        self.classifier = get_classifier()

    def create_ticket(self, payload: TicketCreate) -> Ticket:
        """
        Ingest, validate, classify, compute priority, generate response,
        and persist new ticket. Rejects duplicate ticket IDs.
        """
        # 1. Duplicate Check
        existing = self.db.query(Ticket).filter(Ticket.id == payload.ticket_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate ticket ID: Ticket with ID '{payload.ticket_id}' already exists."
            )

        # 2. Automated AI Classification & Uncertainty Routing
        classification = self.classifier.predict_with_confidence(payload.message)
        category = classification["category"]
        confidence = classification["confidence"]
        margin = classification["margin"]
        is_ambiguous = classification["is_ambiguous"]
        requires_manual_review = classification["requires_manual_review"]
        routing_reason = classification["routing_reason"]
        assigned_team = classification["assigned_team"]

        # 3. Automated Priority Policy Assessment
        priority, priority_reason = determine_priority(category, payload.message)

        # If ambiguous, escalate priority or ensure triage visibility
        if is_ambiguous and priority == "P4":
            priority = "P3"
            priority_reason += " (Escalated to P3 due to category ambiguity requiring triage)."

        # 4. Incident Summary & Draft Response Generation
        summary = generate_summary(payload.message, category, priority)
        draft_response = generate_draft_response(
            ticket_id=payload.ticket_id,
            message=payload.message,
            category=category,
            priority=priority,
            assigned_team=assigned_team,
            is_ambiguous=is_ambiguous
        )

        # 5. Determine Initial Workflow State
        initial_status = "PENDING_REVIEW" if requires_manual_review else "CLASSIFIED"

        ticket = Ticket(
            id=payload.ticket_id,
            message=payload.message,
            category=category,
            priority=priority,
            assigned_team=assigned_team,
            confidence=confidence,
            margin=margin,
            summary=summary,
            draft_response=draft_response,
            status=initial_status,
            is_ambiguous=is_ambiguous,
            requires_manual_review=requires_manual_review,
            routing_reason=routing_reason,
            priority_reason=priority_reason,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def get_ticket(self, ticket_id: str) -> Ticket:
        """Retrieve ticket by unique ID."""
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket not found: Ticket with ID '{ticket_id}' does not exist."
            )
        return ticket

    def list_tickets(
        self,
        category: str | None = None,
        priority: str | None = None,
        status_filter: str | None = None,
        requires_manual_review: bool | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[Ticket]:
        """List tickets with optional query filters."""
        query = self.db.query(Ticket)
        if category:
            query = query.filter(Ticket.category == category)
        if priority:
            query = query.filter(Ticket.priority == priority)
        if status_filter:
            query = query.filter(Ticket.status == status_filter)
        if requires_manual_review is not None:
            query = query.filter(Ticket.requires_manual_review == requires_manual_review)

        return query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()

    def approve_ticket(self, ticket_id: str, request: TicketApprovalRequest) -> Ticket:
        """
        Review and approve a draft response.
        Transitions ticket status to READY for dispatch.
        """
        ticket = self.get_ticket(ticket_id)

        if ticket.status == "REJECTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve rejected ticket '{ticket_id}'. Ticket must be re-opened first."
            )

        if request.updated_draft_response:
            ticket.draft_response = request.updated_draft_response

        if request.updated_category:
            ticket.category = request.updated_category
            ticket.assigned_team = CATEGORY_TEAM_MAP.get(request.updated_category, ticket.assigned_team)

        if request.updated_priority:
            ticket.priority = request.updated_priority

        ticket.reviewer_notes = request.reviewer_notes
        ticket.approved_by = request.reviewer_id
        ticket.approved_at = datetime.utcnow()
        ticket.status = "READY"  # Requirement: require approval before marking draft ready
        ticket.requires_manual_review = False
        ticket.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def reject_ticket(self, ticket_id: str, request: TicketRejectionRequest) -> Ticket:
        """Mark ticket as rejected with audit notes."""
        ticket = self.get_ticket(ticket_id)
        ticket.status = "REJECTED"
        ticket.reviewer_notes = f"Rejected by {request.reviewer_id}: {request.rejection_reason}"
        ticket.requires_manual_review = False
        ticket.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(ticket)
        return ticket
