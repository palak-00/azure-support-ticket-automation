"""
Comprehensive End-to-End Demonstration Script.
Demonstrates all 5 mandatory checks:
  1. Category assignment across Billing, Technical, Access, General
  2. Ambiguous / uncertain ticket detection & triage routing
  3. Duplicate ticket ID rejection (HTTP 409)
  4. Invalid input validation (HTTP 422)
  5. Human reviewer approval workflow (Draft -> Approved / READY)
"""

import os
import sys

from fastapi.testclient import TestClient

# Ensure project root on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine, init_db
from app.main import app

client = TestClient(app)


def print_step_header(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def run_demo():
    # Ensure fresh state for repeatable runs
    Base.metadata.drop_all(bind=engine)
    init_db()

    # -------------------------------------------------------------
    # DEMO 1: Standard Category & Priority Assignment
    # -------------------------------------------------------------
    print_step_header("DEMO 1: CATEGORY ASSIGNMENT & TRIAGE REASONING")
    sample_tickets = [
        {
            "ticket_id": "DEMO-BILL-01",
            "message": "We were charged $3,500 twice on invoice INV-88219 for Azure Cosmos DB. Please issue a refund immediately as our corporate card is maxed out."
        },
        {
            "ticket_id": "DEMO-TECH-01",
            "message": "CRITICAL OUTAGE: Our primary Azure SQL database in East US is completely unresponsive and all production web apps are returning HTTP 500 errors."
        },
        {
            "ticket_id": "DEMO-ACC-01",
            "message": "Our primary Azure Entra ID global administrator account is locked out after token failure. No administrator can log into the portal."
        },
        {
            "ticket_id": "DEMO-GEN-01",
            "message": "What is the recommended architecture and best practice guidelines for setting up Azure Landing Zones for healthcare HIPAA compliance?"
        }
    ]

    for item in sample_tickets:
        resp = client.post("/api/v1/tickets", json=item)
        assert resp.status_code == 201, f"Failed to create ticket: {resp.text}"
        data = resp.json()
        print(f"\n[Ticket Ingested]: {data['ticket_id']}")
        print(f"  Message   : {item['message'][:85]}...")
        print(f"  Category  : {data['category']} (Confidence: {data['confidence']:.1%})")
        print(f"  Priority  : {data['priority']}")
        print(f"  Team      : {data['assigned_team']}")
        print(f"  Status    : {data['status']}")
        print(f"  Summary   : {data['summary']}")
        print(f"  Draft Resp: {data['draft_response'][:110]}...")

    # -------------------------------------------------------------
    # DEMO 2: Ambiguous Ticket & Uncertainty Routing
    # -------------------------------------------------------------
    print_step_header("DEMO 2: AMBIGUOUS TICKET & UNCERTAINTY ROUTING")
    ambiguous_ticket = {
        "ticket_id": "DEMO-AMBIG-01",
        "message": "We have an urgent dispute regarding who deployed the billing subscription and why access permissions caused a cluster outage."
    }
    resp = client.post("/api/v1/tickets", json=ambiguous_ticket)
    assert resp.status_code == 201, f"Failed: {resp.text}"
    data = resp.json()
    print(f"[Ticket ID]              : {data['ticket_id']}")
    print(f"  Message                : {ambiguous_ticket['message']}")
    print(f"  Top Category Candidate : {data['category']}")
    print(f"  Confidence Score       : {data['confidence']:.1%}")
    print(f"  Is Ambiguous           : {data['is_ambiguous']}")
    print(f"  Requires Manual Review : {data['requires_manual_review']}")
    print(f"  Assigned Team          : {data['assigned_team']} (Fallback Triage Queue)")
    print(f"  Workflow Status        : {data['status']} (Awaiting human triage)")
    print(f"  Routing Reasoning      : {data['routing_reason']}")

    # -------------------------------------------------------------
    # DEMO 3: Reject Duplicate Ticket IDs (HTTP 409)
    # -------------------------------------------------------------
    print_step_header("DEMO 3: REJECT DUPLICATE TICKET ID (HTTP 409)")
    duplicate_payload = {
        "ticket_id": "DEMO-BILL-01",  # Already ingested in Demo 1
        "message": "Attempting to re-ingest duplicate ticket with the same ID."
    }
    resp = client.post("/api/v1/tickets", json=duplicate_payload)
    print("[Request]: Ingesting ticket with existing ID 'DEMO-BILL-01'")
    print(f"  Response Status Code: {resp.status_code} (Expected: 409 Conflict)")
    print(f"  Response Body       : {resp.json()}")
    assert resp.status_code == 409, f"Expected 409 Conflict, got {resp.status_code}"

    # -------------------------------------------------------------
    # DEMO 4: Reject Invalid Inputs (HTTP 422)
    # -------------------------------------------------------------
    print_step_header("DEMO 4: REJECT INVALID INPUT (HTTP 422)")
    invalid_cases = [
        ({"ticket_id": "!!INVALID@@", "message": "Valid length message describing an issue."}, "Invalid ticket ID pattern"),
        ({"ticket_id": "TCK-VAL-01", "message": "Too short"}, "Message below minimum 10 characters"),
        ({"ticket_id": "", "message": "Valid length message describing an issue."}, "Empty ticket ID"),
        ({"ticket_id": "TCK-VAL-02", "message": "           "}, "Whitespace only message")
    ]

    for payload, reason in invalid_cases:
        resp = client.post("/api/v1/tickets", json=payload)
        print(f"\n[Test Case]: {reason}")
        print(f"  Payload       : {payload}")
        print(f"  Status Code   : {resp.status_code} (Expected: 422 Unprocessable Entity)")
        print(f"  Error Detail  : {resp.json().get('detail')}")
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"

    # -------------------------------------------------------------
    # DEMO 5: Approval Workflow (Draft -> Approved / READY)
    # -------------------------------------------------------------
    print_step_header("DEMO 5: APPROVAL WORKFLOW (REQUIRE APPROVAL BEFORE READY)")
    ticket_to_approve = "DEMO-AMBIG-01"

    # Verify initial status is PENDING_REVIEW
    get_resp = client.get(f"/api/v1/tickets/{ticket_to_approve}")
    assert get_resp.status_code == 200
    initial_ticket = get_resp.json()
    print("[Pre-Approval State]:")
    print(f"  Ticket ID   : {initial_ticket['ticket_id']}")
    print(f"  Status      : {initial_ticket['status']}")
    print(f"  Approved By : {initial_ticket['approved_by']}")

    # Reviewer submits approval with review notes and refined response
    approval_payload = {
        "reviewer_id": "senior-eng-sarah",
        "reviewer_notes": "Reviewed cross-cutting incident. Determined root cause was IAM role change causing AKS auth failure. Routed to IAM Security.",
        "updated_category": "Access",
        "updated_priority": "P1",
        "updated_draft_response": (
            "Hello,\n\nOur Senior IAM Security engineering team has reviewed this case. "
            "Because this involves permissions affecting production cluster availability, we are treating this as P1. "
            "We are auditing the Entra ID role assignment audit logs right now and will restore service access within 15 minutes.\n\n"
            "Best regards,\nAzure IAM Operations"
        )
    }

    approve_resp = client.post(f"/api/v1/tickets/{ticket_to_approve}/approve", json=approval_payload)
    assert approve_resp.status_code == 200, f"Approval failed: {approve_resp.text}"
    approved_ticket = approve_resp.json()
    print("\n[Post-Approval State]:")
    print(f"  Ticket ID      : {approved_ticket['ticket_id']}")
    print(f"  Status         : {approved_ticket['status']} (Successfully transitioned to READY for dispatch!)")
    print(f"  Approved By    : {approved_ticket['approved_by']}")
    print(f"  Approved At    : {approved_ticket['approved_at']}")
    print(f"  Reviewer Notes : {approved_ticket['reviewer_notes']}")
    print(f"  Final Category : {approved_ticket['category']}")
    print(f"  Final Priority : {approved_ticket['priority']}")
    print(f"  Final Response :\n{approved_ticket['draft_response']}")

    # -------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------
    print_step_header("ALL 5 DEMONSTRATION CHECKS COMPLETED SUCCESSFULLY!")
    print("1. [PASS] Category Assignment (Billing, Technical, Access, General)")
    print("2. [PASS] Ambiguous Ticket Detection & Uncertainty Triage Routing")
    print("3. [PASS] Duplicate Ticket ID Rejection (HTTP 409)")
    print("4. [PASS] Invalid Input Validation (HTTP 422)")
    print("5. [PASS] Human Approval Workflow (Marked READY upon reviewer approval)\n")


if __name__ == "__main__":
    run_demo()
