"""
Unit tests for Priority Policy Engine and Reasoning.
"""

import pytest
from app.services.priority import determine_priority


def test_priority_p1_outage():
    priority, reason = determine_priority("Technical", "CRITICAL OUTAGE: Primary SQL database is completely unresponsive.")
    assert priority == "P1"
    assert "<15m SLA" in reason


def test_priority_p1_fraud():
    priority, reason = determine_priority("Billing", "Unauthorized charges exceeding $15,000 appeared on our corporate credit card. This is fraudulent!")
    assert priority == "P1"
    assert "Critical impact" in reason


def test_priority_p2_gateway_timeout():
    priority, reason = determine_priority("Technical", "Azure Function App order-processor is failing with 504 Gateway Timeout.")
    assert priority == "P2"
    assert "<1h SLA" in reason


def test_priority_p3_quota():
    priority, reason = determine_priority("Technical", "Deployment pipeline failed due to VnetPeeringLimitReached quota limit.")
    assert priority == "P3"
    assert "<4h SLA" in reason


def test_priority_p4_guidance():
    priority, reason = determine_priority("General", "Can you provide the SOC 2 Type II compliance reports and ISO 27001 certificates?")
    assert priority == "P4"
    assert "<24h SLA" in reason
