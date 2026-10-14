"""
Pydantic Schemas for Request Validation and Response Serialization.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import re
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TicketCreate(BaseModel):
    """Payload for ticket ingestion and automated triage."""
    ticket_id: str = Field(
        ...,
        description="Unique identifier for the support ticket (e.g. TCK-1001)",
        examples=["TCK-1001"]
    )
    message: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Ticket message text describing the customer's issue",
        examples=["Production AKS cluster node is down and returning HTTP 500 errors to customers."]
    )

    @field_validator("ticket_id")
    @classmethod
    def validate_ticket_id(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[A-Za-z0-9-_]{3,50}$", v):
            raise ValueError(
                "ticket_id must be 3-50 characters long and contain only letters, numbers, hyphens, and underscores."
            )
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("message must contain at least 10 non-whitespace characters.")
        return v


class TicketApprovalRequest(BaseModel):
    """Payload for human reviewer approval of draft response."""
    reviewer_id: str = Field(
        ...,
        min_length=2,
        max_length=64,
        description="Identifier of support engineer or lead approving the ticket",
        examples=["engineer-alex"]
    )
    reviewer_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional notes recorded during human triage review"
    )
    updated_draft_response: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=5000,
        description="Optional edited draft response before marking ready"
    )
    updated_category: Optional[str] = Field(
        default=None,
        description="Optional category override (Billing, Technical, Access, General)"
    )
    updated_priority: Optional[str] = Field(
        default=None,
        description="Optional priority override (P1, P2, P3, P4)"
    )


class TicketRejectionRequest(BaseModel):
    """Payload for rejecting an invalid or spam ticket."""
    reviewer_id: str = Field(..., min_length=2, max_length=64)
    rejection_reason: str = Field(..., min_length=5, max_length=500)


class CandidateProbabilities(BaseModel):
    Billing: float
    Technical: float
    Access: float
    General: float


class TicketResponse(BaseModel):
    """Response schema for classified and stored support tickets."""
    ticket_id: str
    message: str
    category: str
    priority: str
    assigned_team: str
    confidence: float
    margin: float
    summary: str
    draft_response: str
    status: str
    is_ambiguous: bool
    requires_manual_review: bool
    routing_reason: Optional[str] = None
    priority_reason: Optional[str] = None
    reviewer_notes: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccuracyMetrics(BaseModel):
    """Model evaluation metrics on test dataset."""
    total_test_samples: int
    accuracy_percentage: float
    accuracy_ratio: str
    per_class_metrics: Dict[str, Dict[str, float]]
    confusion_matrix: Dict[str, Dict[str, int]]
    model_type: str
    trained_on_samples: int
    priority_policy_summary: Dict[str, str]


class HealthResponse(BaseModel):
    """Service health and diagnostics response."""
    status: str
    service: str
    version: str
    database: str
    classifier_loaded: bool
