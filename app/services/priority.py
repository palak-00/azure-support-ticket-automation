"""
Priority Policy Engine and Reasoning Module.
Assigns P1-P4 priority ratings based on impact severity, business continuity risk,
and urgency signals in accordance with docs/PRIORITY_POLICY.md.
"""

from typing import Dict, Any, Tuple
import re

P1_SIGNALS = [
    r"\boutage\b",
    r"\bcritical outage\b",
    r"\bcrashloop\b",
    r"\bunresponsive\b",
    r"\bglobal administrator .*locked\b",
    r"\bunauthorized charges\b",
    r"\bfraud\b",
    r"\bfraudulent\b",
    r"\bproduction .*paused\b",
    r"\bproduction .*disabled\b",
    r"\b500 (internal server|errors)\b",
    r"\bdown for all\b",
    r"\bcompletely unresponsive\b"
]

P2_SIGNALS = [
    r"\b504\b",
    r"\bgateway timeout\b",
    r"\bssl handshake\b",
    r"\bspending limit cap\b",
    r"\bsubscription .*suspended\b",
    r"\bsso .*stopped working\b",
    r"\baadsts50011\b",
    r"\bconditional access .*blocks\b",
    r"\bthrottling\b",
    r"\bpacket loss\b",
    r"\bcharge failed\b",
    r"\bduplicate charge\b",
    r"\bhigh latency\b",
    r"\bsevere\b"
]

P3_SIGNALS = [
    r"\bquota\b",
    r"\bpeering\b",
    r"\bcontributor role\b",
    r"\breader (permissions|role)\b",
    r"\bmfa reset\b",
    r"\bauthenticator\b",
    r"\binvoice .*surge\b",
    r"\binvoiced for .*decommissioned\b",
    r"\bbreakdown\b",
    r"\bresourcegroupnotfound\b",
    r"\bpipeline fails\b",
    r"\bconnection pool\b"
]

P4_SIGNALS = [
    r"\barchitecture\b",
    r"\blanding zones?\b",
    r"\bbest practices\b",
    r"\bhipaa\b",
    r"\bprojected general availability\b",
    r"\bga date\b",
    r"\bsoc 2\b",
    r"\biso 27001\b",
    r"\bcompliance\b",
    r"\bfeature enhancement\b",
    r"\bdocumentation\b",
    r"\bpricing tiers?\b",
    r"\bpartner program\b",
    r"\bfasttrack\b",
    r"\btax exemption\b",
    r"\baudit user role\b",
    r"\bwhere can i find\b",
    r"\bhow to\b"
]


def determine_priority(category: str, message: str) -> Tuple[str, str]:
    """
    Evaluates ticket text and category to determine priority (P1-P4)
    and provides clear human-readable policy reasoning.
    """
    text = message.lower()

    # Check P1 Critical
    for pattern in P1_SIGNALS:
        if re.search(pattern, text):
            match_str = re.search(pattern, text).group(0)
            return (
                "P1",
                f"Critical impact: detected urgent signal '{match_str}'. "
                f"Production outage, critical account lock, or major unauthorized charge requires <15m SLA response."
            )

    # Check P2 High
    for pattern in P2_SIGNALS:
        if re.search(pattern, text):
            match_str = re.search(pattern, text).group(0)
            return (
                "P2",
                f"High severity: detected operational disruption signal '{match_str}'. "
                f"Affects critical workflows, authentication, or carries imminent suspension risk (<1h SLA)."
            )

    # Check P3 Medium
    for pattern in P3_SIGNALS:
        if re.search(pattern, text):
            match_str = re.search(pattern, text).group(0)
            return (
                "P3",
                f"Medium severity: detected localized operational request '{match_str}'. "
                f"Workaround available or single-user scope (<4h SLA)."
            )

    # Check P4 Low
    for pattern in P4_SIGNALS:
        if re.search(pattern, text):
            match_str = re.search(pattern, text).group(0)
            return (
                "P4",
                f"Low severity: detected informational, roadmap, compliance, or feature request '{match_str}'. "
                f"Standard advisory turnaround (<24h SLA)."
            )

    # Category-based fallback heuristic
    fallback_map = {
        "Technical": ("P3", "Default technical incident rating pending deeper telemetry diagnosis."),
        "Billing": ("P3", "Standard billing review query pending invoice reconciliation."),
        "Access": ("P3", "Identity and access modification request subject to standard review."),
        "General": ("P4", "Informational consultation ticket with standard advisory SLA.")
    }

    return fallback_map.get(category, ("P3", "Standard operational priority assignment."))
