# PS04 Azure Support Ticket Automation

[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen)](https://github.com/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Azure App Service](https://img.shields.io/badge/Azure-App%20Service-0078D4.svg)](https://azure.microsoft.com/en-us/products/app-service/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-ready, AI-assisted Support Ticket Automation API built with FastAPI, scikit-learn, SQLAlchemy, and Docker. The service ingests incoming cloud support tickets, classifies them across four core domains, assigns SLA-backed priorities (P1-P4), flags ambiguous cases to human review queues, and drafts customer responses requiring human sign-off before dispatch.

---

## 1. Key Capabilities & Requirements Coverage

- **AI Classification & Uncertainty Routing**: Classifies messages into `Billing`, `Technical`, `Access`, and `General`. Routes ambiguous cases with low confidence or high candidate competition to `triage-review-team` with `status = "PENDING_REVIEW"`.
- **Priority Policy Engine**: Maps incidents to **P1 (Critical)**, **P2 (High)**, **P3 (Medium)**, and **P4 (Low)** based on business disruption, security lockouts, and financial risks.
- **Strict Input Validation & Duplicate Protection**: Rejects invalid ticket IDs/messages (HTTP 422) and prevents duplicate ticket ID collisions (HTTP 409).
- **Human-in-the-Loop Approval Workflow**: Draft responses are stored and require reviewer approval via `POST /api/v1/tickets/{id}/approve` before transitioning to `READY`.
- **Reproducible Container Packaging**: Production-grade `Dockerfile` with non-root security (`appuser`), dynamic port binding for Azure App Service (`WEBSITES_PORT=8000`), and built-in health probes.
- **GitHub Actions CI & OIDC Azure Deployment**: Automated CI workflow testing code, evaluating test accuracy, running pytest, and testing container build. Zero-secret deployment workflow using Azure OIDC federated credentials.

---

## 2. Dataset & Priority Policy

### 2.1 Labelled Dataset (30 Fictional Tickets)
The dataset is stored in [`data/tickets_dataset.json`](./data/tickets_dataset.json):
- **Training Set (20 tickets)**: 5 Billing, 5 Technical, 5 Access, 5 General.
- **Reserved Test Set (10 tickets)**: 3 Billing, 3 Technical, 2 Access, 2 General.
- **Test Set Accuracy**: **90.0%** (9/10 correct; the 1 ambiguous multi-intent case is correctly routed to manual triage review).

### 2.2 Priority Policy & SLA Summary
For detailed policy rules, refer to [`docs/PRIORITY_POLICY.md`](./docs/PRIORITY_POLICY.md).

| Priority | SLA Response | SLA Resolution | Criteria & Impact | Primary Team |
|---|---|---|---|---|
| **P1** | **< 15 min** | < 2 hours | Production outage, unresponsive database, global admin lockout, unauthorized fraud (> $10k). | Engineering Lead / `cloud-infra-eng` |
| **P2** | **< 1 hour** | < 8 hours | Major service degradation (504 timeout), subscription suspension risk within 24h, corporate SSO failure. | Tier 2 / `finance-billing-ops` / `iam-security-team` |
| **P3** | **< 4 hours** | < 24 hours | Quota limit reached, role assignment requests, MFA device reset, invoice clarification. | Standard Operations Queue |
| **P4** | **< 24 hours** | < 72 hours | Architecture advice (Landing Zones), HIPAA/SOC 2 compliance inquiries, feature suggestions. | `customer-success-ops` |

---

## 3. Quick Start & Local Execution

### Prerequisites
- Python 3.11+
- Git
- (Optional) Docker

### 3.1 Local Environment Setup
```bash
# 1. Clone repository and navigate to directory
git clone https://github.com/<org>/azure-support-ticket-automation.git
cd azure-support-ticket-automation

# 2. Create virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Run automated test suite
pytest -v --cov=app

# 5. Run test-set evaluation script
python scripts/evaluate.py
```

### 3.2 Run the Automated 5-Check Demonstration
Run the comprehensive verification script which executes all 5 demonstration checks:
```bash
python scripts/demo.py
```
This script exercises:
1. Category assignment on realistic tickets
2. Ambiguous ticket detection & routing to triage review
3. Duplicate ticket ID rejection (HTTP 409)
4. Invalid input rejection (HTTP 422)
5. Approval workflow (Draft -> READY)

### 3.3 Start the Local API Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- Evaluation Metrics: [http://localhost:8000/api/v1/metrics](http://localhost:8000/api/v1/metrics)

---

## 4. Docker Packaging & Local Container Run

### 4.1 Build and Run with Docker
```bash
# Build production Docker image
docker build -t azure-support-ticket-automation:latest .

# Run container on port 8000
docker run -d --name support_ticket_api -p 8000:8000 azure-support-ticket-automation:latest

# Verify container logs
docker logs -f support_ticket_api

# Check container health probe
curl http://localhost:8000/health
```

### 4.2 Run with Docker Compose
```bash
docker compose up -d
docker compose ps
docker compose logs -f
```

---

## 5. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/tickets` | Ingest new ticket, reject duplicates/invalid inputs, classify, compute priority, generate draft response. |
| `GET` | `/api/v1/tickets` | List tickets with optional query filters (`category`, `priority`, `status`, `requires_manual_review`). |
| `GET` | `/api/v1/tickets/{ticket_id}` | Retrieve single ticket state, classification confidence, and draft response. |
| `POST` | `/api/v1/tickets/{ticket_id}/approve` | Reviewer approval. Marks draft response as `READY` for dispatch. |
| `POST` | `/api/v1/tickets/{ticket_id}/reject` | Reject ticket with reason and audit trail. |
| `GET` | `/api/v1/metrics` | Returns test-set accuracy, confusion matrix, precision, recall, and F1 scores. |
| `GET` | `/health` | Azure App Service liveness & readiness health probe. |

---

## 6. GitHub Actions CI/CD & Azure OIDC Configuration

- **Continuous Integration Workflow**: [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)
  - Automatically runs Ruff style checks, model test set evaluation, pytest suite with coverage, and Docker container build verification.
- **Azure Deployment Workflow**: [`.github/workflows/deploy-azure.yml`](./.github/workflows/deploy-azure.yml)
  - Manually triggered (`workflow_dispatch`).
  - Employs zero-secret Microsoft Entra ID (Azure AD) OIDC federated credentials (`azure/login@v2`).
  - Builds and pushes image to Azure Container Registry (ACR) and deploys to Azure App Service (`azure/webapps-deploy@v3`).
  - Follow [`docs/AZURE_CONFIG.md`](./docs/AZURE_CONFIG.md) for full Entra ID federated identity setup.

---

## 7. Project Structure

```
azure-support-ticket-automation/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Automated testing, evaluation & container build CI
│       └── deploy-azure.yml       # Azure App Service OIDC deployment workflow
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application initialization & lifespan
│   ├── database.py                # SQLAlchemy engine & session management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── db_models.py           # SQLAlchemy Ticket entity
│   │   └── schemas.py             # Pydantic schemas with validation
│   ├── services/
│   │   ├── __init__.py
│   │   ├── classifier.py          # AI Classifier, confidence scoring & uncertainty routing
│   │   ├── priority.py            # Priority policy engine & reasoning
│   │   ├── summarizer.py          # Summary & draft response generation
│   │   ├── ticket_service.py      # Core service orchestrating ticket lifecycle
│   │   └── evaluator.py           # Test set evaluation & metrics calculation
│   └── api/
│       ├── __init__.py
│       └── routes.py              # REST API endpoint definitions
├── data/
│   ├── tickets_dataset.json       # 30 labelled tickets (20 train, 10 reserved test)
│   ├── trained_model.joblib       # Serialized AI model artifact
│   └── evaluation_report.json     # Saved test-set performance metrics
├── docs/
│   ├── ARCHITECTURE.md            # System architecture & Mermaid flowcharts
│   ├── AZURE_CONFIG.md            # Azure App Service & Entra ID OIDC setup guide
│   └── PRIORITY_POLICY.md         # Formal priority policy & SLA rules
├── scripts/
│   ├── demo.py                    # Automated end-to-end 5-check demonstration
│   ├── evaluate.py                # Standalone evaluation CLI script
│   └── seed_db.py                 # Database seeder script
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures & isolated in-memory DB
│   ├── test_classifier.py         # Classifier & uncertainty routing unit tests
│   ├── test_priority.py           # Priority policy rule tests
│   ├── test_api.py                # Endpoint integration tests (duplicates, validation, approvals)
│   └── test_evaluation.py         # Test-set accuracy verification (>= 80%)
├── Dockerfile                     # Multi-stage production container definition
├── .dockerignore                  # Docker exclusion rules
├── docker-compose.yml             # Local orchestration file
├── requirements.txt               # Production Python dependencies
├── requirements-dev.txt           # Development and testing dependencies
└── README.md                      # Comprehensive project guide
```
