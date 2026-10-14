"""
SQLAlchemy ORM models for ticket storage and audit state.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, String, Text

from app.database import Base


class Ticket(Base):
    """Support Ticket Entity representing persistent ticket state."""
    __tablename__ = "tickets"

    id = Column(String(64), primary_key=True, index=True)
    message = Column(Text, nullable=False)
    category = Column(String(32), nullable=False, index=True)
    priority = Column(String(8), nullable=False, index=True)
    assigned_team = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False)
    margin = Column(Float, nullable=False, default=0.0)
    summary = Column(Text, nullable=False)
    draft_response = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="CLASSIFIED", index=True)
    is_ambiguous = Column(Boolean, default=False)
    requires_manual_review = Column(Boolean, default=False)
    routing_reason = Column(Text, nullable=True)
    priority_reason = Column(Text, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    approved_by = Column(String(64), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def ticket_id(self) -> str:
        return self.id
