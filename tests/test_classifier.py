"""
Unit tests for AI Ticket Classifier and Uncertainty Routing.
"""

import pytest
from app.services.classifier import get_classifier, CATEGORIES, CATEGORY_TEAM_MAP


@pytest.fixture(scope="module")
def classifier():
    return get_classifier()


def test_classifier_is_trained(classifier):
    assert classifier.is_trained is True
    assert classifier.pipeline is not None


def test_classify_billing_ticket(classifier):
    msg = "We were charged $5,000 twice on invoice INV-29182 for Azure Cosmos DB. Please process a refund."
    res = classifier.predict_with_confidence(msg)
    assert res["category"] == "Billing"
    assert res["confidence"] > 0.40
    assert res["assigned_team"] == "finance-billing-ops"


def test_classify_technical_ticket(classifier):
    msg = "AKS cluster pods are in CrashLoopBackOff and our order gateway is throwing 500 errors."
    res = classifier.predict_with_confidence(msg)
    assert res["category"] == "Technical"
    assert res["confidence"] > 0.40
    assert res["assigned_team"] == "cloud-infra-eng"


def test_classify_access_ticket(classifier):
    msg = "Azure Entra ID global admin cannot log in due to hardware MFA token sync error."
    res = classifier.predict_with_confidence(msg)
    assert res["category"] == "Access"
    assert res["confidence"] > 0.40
    assert res["assigned_team"] == "iam-security-team"


def test_classify_general_ticket(classifier):
    msg = "Where can I find Azure Landing Zones architecture documentation and HIPAA compliance guide?"
    res = classifier.predict_with_confidence(msg)
    assert res["category"] == "General"
    assert res["confidence"] > 0.40
    assert res["assigned_team"] == "customer-success-ops"


def test_ambiguous_ticket_triggers_uncertainty_routing(classifier):
    ambiguous_msg = "We have an urgent dispute regarding who deployed the billing subscription and why access permissions caused a cluster outage."
    res = classifier.predict_with_confidence(ambiguous_msg)
    assert res["is_ambiguous"] is True
    assert res["requires_manual_review"] is True
    assert res["assigned_team"] == "triage-review-team"
    assert "manual review" in res["routing_reason"].lower()
