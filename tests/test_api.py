"""
Integration tests for FastAPI Endpoints.
Covers ingestion, duplicate rejection, validation errors, approval workflow,
and health checks.
"""

import pytest


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["classifier_loaded"] is True


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["status"] == "online"


def test_create_ticket_success(client):
    payload = {
        "ticket_id": "TCK-TEST-001",
        "message": "We were charged $2,500 twice on invoice INV-99012 for Cosmos DB. Please refund."
    }
    response = client.post("/api/v1/tickets", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["ticket_id"] == "TCK-TEST-001"
    assert data["category"] == "Billing"
    assert data["priority"] in ["P1", "P2", "P3", "P4"]
    assert data["assigned_team"] == "finance-billing-ops"
    assert data["status"] == "CLASSIFIED"
    assert "draft_response" in data
    assert len(data["draft_response"]) > 20


def test_reject_duplicate_ticket_id(client):
    payload = {
        "ticket_id": "TCK-DUP-001",
        "message": "Original ticket message describing a database timeout issue."
    }
    # First creation -> success
    r1 = client.post("/api/v1/tickets", json=payload)
    assert r1.status_code == 201

    # Second creation with same ticket_id -> HTTP 409 Conflict
    r2 = client.post("/api/v1/tickets", json=payload)
    assert r2.status_code == 409
    assert "Duplicate ticket ID" in r2.json()["detail"]


def test_reject_invalid_ticket_id_format(client):
    payload = {
        "ticket_id": "invalid ticket id with spaces!",
        "message": "A valid message with more than ten characters."
    }
    response = client.post("/api/v1/tickets", json=payload)
    assert response.status_code == 422


def test_reject_short_message(client):
    payload = {
        "ticket_id": "TCK-SHORT-001",
        "message": "Help"
    }
    response = client.post("/api/v1/tickets", json=payload)
    assert response.status_code == 422


def test_reject_whitespace_message(client):
    payload = {
        "ticket_id": "TCK-SPACE-001",
        "message": "               "
    }
    response = client.post("/api/v1/tickets", json=payload)
    assert response.status_code == 422


def test_get_ticket_by_id(client):
    payload = {
        "ticket_id": "TCK-GET-001",
        "message": "Azure Kubernetes cluster pod crashed with 500 internal server error."
    }
    client.post("/api/v1/tickets", json=payload)

    response = client.get("/api/v1/tickets/TCK-GET-001")
    assert response.status_code == 200
    assert response.json()["ticket_id"] == "TCK-GET-001"


def test_get_nonexistent_ticket_returns_404(client):
    response = client.get("/api/v1/tickets/TCK-DOES-NOT-EXIST")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_approval_workflow_marks_ready(client):
    # Ingest ambiguous ticket -> status PENDING_REVIEW
    payload = {
        "ticket_id": "TCK-AMBIG-TEST",
        "message": "We have an urgent dispute regarding who deployed the billing subscription and why access permissions caused a cluster outage."
    }
    ingest_resp = client.post("/api/v1/tickets", json=payload)
    assert ingest_resp.status_code == 201
    ticket_data = ingest_resp.json()
    assert ticket_data["status"] == "PENDING_REVIEW"
    assert ticket_data["requires_manual_review"] is True

    # Reviewer approves ticket
    approval_payload = {
        "reviewer_id": "lead-engineer-jordan",
        "reviewer_notes": "Verified root cause in audit logs. Approved.",
        "updated_category": "Access",
        "updated_priority": "P2",
        "updated_draft_response": "Dear Customer, our IAM team has resolved your access permission issue."
    }
    approve_resp = client.post("/api/v1/tickets/TCK-AMBIG-TEST/approve", json=approval_payload)
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()

    # Verify state transition to READY
    assert approved_data["status"] == "READY"
    assert approved_data["approved_by"] == "lead-engineer-jordan"
    assert approved_data["category"] == "Access"
    assert approved_data["priority"] == "P2"
    assert approved_data["requires_manual_review"] is False
    assert approved_data["draft_response"] == "Dear Customer, our IAM team has resolved your access permission issue."


def test_rejection_workflow(client):
    payload = {
        "ticket_id": "TCK-SPAM-001",
        "message": "Win a free gift card by clicking this suspicious external link."
    }
    client.post("/api/v1/tickets", json=payload)

    reject_payload = {
        "reviewer_id": "support-lead",
        "rejection_reason": "Spam promotional message, not a valid support ticket."
    }
    reject_resp = client.post("/api/v1/tickets/TCK-SPAM-001/reject", json=reject_payload)
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "REJECTED"


def test_metrics_endpoint(client):
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "accuracy_percentage" in data
    assert data["total_test_samples"] == 10
    assert data["accuracy_percentage"] >= 80.0
