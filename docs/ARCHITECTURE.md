# System Architecture & Design Documentation

## 1. High-Level Architecture

The **Azure Support Ticket Automation** service is designed as an asynchronous, resilient, AI-assisted triage backend. It accepts raw ticket descriptions, validates input schemas, classifies incidents into four core cloud categories, determines SLA urgency, extracts diagnostic parameters, prepares contextual draft responses, and enforces human-in-the-loop sign-off before dispatch.

```mermaid
flowchart TD
    subgraph Client ["Client / Azure Portal / Webhooks"]
        req["POST /api/v1/tickets"]
        approve["POST /api/v1/tickets/{id}/approve"]
    end

    subgraph Validation ["Validation & Deduplication Layer"]
        v_id{"Regex ID Validation"}
        v_msg{"Message Length Check"}
        dup_chk{"Duplicate ID Check (SQLite)"}
    end

    subgraph AI_Engine ["AI & Priority Engine"]
        tfidf["TF-IDF (1,2 n-grams) Vectorizer"]
        clf["Calibrated Logistic Regression"]
        lex["Domain Semantic Intent Scorer"]
        ensemble["Hybrid Posterior Calibrator"]
        uncertainty{"Confidence >= 0.38 & Margin >= 0.10?"}
        priority_eng["Priority Policy Evaluator (P1-P4)"]
        summary_eng["Entity Extraction & Summarizer"]
        draft_eng["Contextual Draft Generator"]
    end

    subgraph Storage ["Persistence & State Machine"]
        db[("SQLite Database / ORM")]
        state_classified["State: CLASSIFIED"]
        state_review["State: PENDING_REVIEW"]
        state_ready["State: READY"]
    end

    req --> v_id
    v_id -->|Invalid| err422["HTTP 422 Unprocessable Entity"]
    v_id -->|Valid| v_msg
    v_msg -->|Too Short| err422
    v_msg -->|Valid| dup_chk
    dup_chk -->|Exists| err409["HTTP 409 Conflict"]
    dup_chk -->|New| tfidf

    tfidf --> clf
    v_msg --> lex
    clf --> ensemble
    lex --> ensemble
    ensemble --> uncertainty

    uncertainty -->|Yes| team_std["Assigned Team: Dedicated Queue"]
    uncertainty -->|No (Ambiguous)| team_triage["Assigned Team: triage-review-team"]
    
    ensemble --> priority_eng
    priority_eng --> summary_eng
    summary_eng --> draft_eng

    team_std --> state_classified
    team_triage --> state_review
    draft_eng --> db

    approve -->|Human Reviewer Sign-Off| state_ready
    state_ready --> db
```

---

## 2. Key Architectural Components

### 2.1 AI Classification & Uncertainty Routing
- **Vector Space Representation**: `TfidfVectorizer` extracting word unigrams and bigrams (`ngram_range=(1, 2)`), sublinear term frequency scaling, and stopword filtering.
- **Probabilistic Learner**: Multinomial Logistic Regression (`solver='lbfgs'`, class weighting balanced).
- **Domain Lexicon Prior**: Domain-specific lexicon covering Microsoft Azure terminology (AKS, Cosmos DB, Entra ID, SAML SSO, Landing Zones, etc.).
- **Uncertainty Gate**:
  - `CONFIDENCE_THRESHOLD = 0.38` (calibrated for 4-class multiclass distribution)
  - `MARGIN_THRESHOLD = 0.10`
  - Tickets failing the uncertainty criteria are flagged with `is_ambiguous = true`, routed to `triage-review-team`, and assigned `PENDING_REVIEW` state.

### 2.2 Priority Policy Engine
- Evaluates operational disruption, financial risk, and system scope according to formal policies.
- Recognizes critical tokens:
  - `P1 (Critical)`: Production outage, unresponsive database, AKS CrashLoop, global admin lockout, unauthorized credit card charges.
  - `P2 (High)`: Gateway timeouts (504), SSL errors, subscription suspended, SSO failure.
  - `P3 (Medium)`: Quota limits, role assignments (Contributor, Reader), invoice queries, MFA resets.
  - `P4 (Low)`: Advisory, HIPAA architecture, compliance documentation (SOC 2, ISO), feature enhancement requests.

### 2.3 Ticket State Machine
```
   [Incoming Ticket]
           │
           ▼
    Validation Check ───(Fail)───► [HTTP 422 / 409]
           │ (Pass)
           ▼
    AI Classification
           │
     ┌─────┴───────────────┐
     ▼                     ▼
[CLASSIFIED]        [PENDING_REVIEW] (if ambiguous)
     │                     │
     └─────────┬───────────┘
               │
               ▼
      [Reviewer Action]
         │           │
   (Approve)      (Reject)
         │           │
         ▼           ▼
      [READY]    [REJECTED]
```

### 2.4 Entity-Aware Response & Summary Generator
- Automatically scans customer messages for Azure entities (`INV-*`, `SUB-*`, `HTTP 500/504`, dollar values).
- Generates a 1-sentence executive summary with structured metadata.
- Prepares a formal, courteous draft response with appropriate SLA commitments, team contacts, and tailored diagnostic prompts.
