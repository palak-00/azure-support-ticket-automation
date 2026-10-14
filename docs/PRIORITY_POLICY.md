# Azure Support Ticket Priority Policy

This document defines the formal priority policy, SLA targets, team assignment matrix, and automated heuristic rules for ticket triage in the Azure Support Ticket Automation system.

---

## 1. Priority Levels and Service Level Agreements (SLAs)

| Priority | Severity Label | Definition & Impact Criteria | Target First Response | Target Resolution | Escalation Path |
|---|---|---|---|---|---|
| **P1** | **Critical** | Complete outage of production systems, widespread customer-facing impact, urgent security breaches (e.g. root/global admin lockout), or catastrophic financial fraud (> $10k unauthorized charges). | **< 15 minutes** | **< 2 hours** | On-call Incident Commander, Engineering Lead |
| **P2** | **High** | Major degradation of business-critical service without workaround; payment failure risking account suspension within 24h; widespread internal employee authentication blockage. | **< 1 hour** | **< 8 hours** | Tier 2 Support Team Lead |
| **P3** | **Medium** | Moderate operational issue with workaround; single-user access/MFA reset; invoice clarification; quota limit adjustments; pipeline deployment errors. | **< 4 hours** | **< 24 hours** | Support Operations Queue |
| **P4** | **Low** | General technical guidance, architectural recommendations, documentation inquiries, feature requests, compliance certificates (SOC 2, ISO). | **< 24 hours** | **< 72 hours** | Customer Success & Documentation Team |

---

## 2. Category & Team Routing Matrix

| Category | Description | Primary Assigned Team | Fallback / Uncertainty Queue |
|---|---|---|---|
| **Billing** | Invoices, credit card charges, refunds, unexpected billing spikes, tax certificates, subscription suspension due to payment. | `finance-billing-ops` | `triage-review-team` |
| **Technical** | Azure resource failures, AKS/VM crashes, API gateway timeouts, database connection errors, network quota limits, ARM/Terraform errors. | `cloud-infra-eng` | `triage-review-team` |
| **Access** | Microsoft Entra ID (Azure AD), SAML SSO, Multi-Factor Authentication (MFA), RBAC roles, conditional access policies, user permissions. | `iam-security-team` | `triage-review-team` |
| **General** | Roadmap queries, region availability, Service Trust compliance reports, architecture reviews, feature requests, FastTrack partner program. | `customer-success-ops` | `triage-review-team` |

---

## 3. Automated Heuristic Priority Assessment

The automated priority engine evaluates tickets using a multi-factor rule engine:
1. **Critical Keywords Analysis**: Detection of high-urgency tokens (e.g., `"crashloop"`, `"500 error"`, `"unresponsive"`, `"global administrator locked"`, `"unauthorized charges"`, `"fraud"`, `"production offline"`).
2. **Category-Specific Baselines**:
   - Outage + Technical -> **P1**
   - Locked Account + Tenant Admin -> **P1**
   - Fraud / Production Suspension + Billing -> **P1**
   - Pipeline/Quota Error + Workaround -> **P3**
   - Onboarding / Role Assignment -> **P3**
   - Documentation / Architecture / Compliance -> **P4**
3. **Ambiguity / Uncertainty Flag**: When category confidence is below the defined threshold (`< 0.60`) or confidence margin between top candidates is narrow (`< 0.12`), the priority is capped at minimum `P3` and the ticket is routed to `triage-review-team` with `requires_manual_review = true`.
