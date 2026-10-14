"""
Ticket Summarization and Human-Review Draft Response Generator.
Produces succinct incident summaries and enterprise-grade draft responses
tailored to the ticket's category, priority, and specific context.
"""

from typing import Dict, Any, Optional
import re


def generate_summary(message: str, category: str, priority: str) -> str:
    """
    Generates a concise 1-2 sentence executive summary from the customer message.
    """
    # Clean up whitespace
    text = " ".join(message.strip().split())

    # Detect entity keywords
    invoices = re.findall(r"\bINV-[A-Za-z0-9]+\b", text)
    subs = re.findall(r"\bSUB-[A-Za-z0-9]+\b", text)
    errors = re.findall(r"\b(?:HTTP\s*)?(?:500|504|AADSTS\w+)\b", text)
    amounts = re.findall(r"\$[\d,]+(?:\.\d+)?", text)

    details = []
    if invoices:
        details.append(f"Invoice: {', '.join(invoices)}")
    if subs:
        details.append(f"Subscription: {', '.join(subs)}")
    if errors:
        details.append(f"Error Code: {', '.join(errors)}")
    if amounts:
        details.append(f"Amount: {', '.join(amounts)}")

    detail_str = f" ({'; '.join(details)})" if details else ""

    # Generate category-tailored synthesis
    first_sentence = text.split(".")[0].strip()
    if len(first_sentence) > 130:
        first_sentence = first_sentence[:127] + "..."

    summary = f"[{category} | {priority}] {first_sentence}.{detail_str}"
    return summary


def generate_draft_response(
    ticket_id: str,
    message: str,
    category: str,
    priority: str,
    assigned_team: str,
    is_ambiguous: bool = False
) -> str:
    """
    Constructs a professional, context-aware draft response for support engineer review.
    """
    greeting = f"Hello,\n\nThank you for contacting Azure Support. We have received your request (Reference: {ticket_id}) and our {assigned_team} has been notified."

    # SLA commitment
    sla_map = {
        "P1": "Because this has been prioritized as a Critical (P1) incident, our engineering team is actively investigating under our 15-minute response SLA.",
        "P2": "We have marked this as High Priority (P2) and our team is actively reviewing your case under our 1-hour SLA.",
        "P3": "This case is prioritized as Medium (P3), and our operations team will provide updates within 4 hours.",
        "P4": "This inquiry is prioritized as Standard (P4), and our support team will respond within 24 hours."
    }
    sla_text = sla_map.get(priority, "Our support team is reviewing your ticket promptly.")

    # Category-specific guidance
    guidance = ""
    if category == "Billing":
        guidance = (
            "Our Finance & Billing Operations team is checking your billing profile and charge records. "
            "If this concerns an unauthorized transaction or payment hold, our team will temporarily protect your "
            "subscriptions while reviewing line items and processing any required credits."
        )
    elif category == "Technical":
        guidance = (
            "Our Cloud Infrastructure Engineering team is analyzing platform telemetry and regional health metrics. "
            "If you have correlation IDs, resource IDs, or timestamped application logs from Azure Monitor, "
            "please attach them to expedite root-cause analysis."
        )
    elif category == "Access":
        guidance = (
            "Our Identity & Access Management (IAM) team has received your access or authentication inquiry. "
            "For security reasons, privilege escalations, MFA resets, and role assignments undergo identity verification "
            "in accordance with enterprise security policy."
        )
    else:  # General
        guidance = (
            "Our Customer Success team is reviewing your documentation or advisory request. "
            "We will connect you with the appropriate resources, architecture guidelines, or regional contacts."
        )

    # Uncertainty note if flagged
    review_warning = ""
    if is_ambiguous:
        review_warning = (
            "\n[Note: This ticket involves cross-domain elements and is currently undergoing initial human triage "
            "to ensure the most qualified specialist handles your case.]"
        )

    closing = (
        "Best regards,\n"
        f"Azure Support Operations ({assigned_team})\n"
        "Microsoft Cloud Services"
    )

    draft = f"{greeting}\n\n{sla_text}\n\n{guidance}{review_warning}\n\n{closing}"
    return draft
