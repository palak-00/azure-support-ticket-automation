"""
Hybrid Semantic Classifier for Azure Support Tickets.
Combines TF-IDF n-gram vectorization with calibrated linear probability modeling
and domain-specific semantic heuristics for high-precision categorization and
calibrated confidence estimation.
"""

import json
import os
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# Target categories
CATEGORIES = ["Billing", "Technical", "Access", "General"]

# Default team routing map
CATEGORY_TEAM_MAP = {
    "Billing": "finance-billing-ops",
    "Technical": "cloud-infra-eng",
    "Access": "iam-security-team",
    "General": "customer-success-ops"
}

# Domain semantic lexicon for confidence calibration & intent alignment
DOMAIN_LEXICON = {
    "Billing": [
        "invoice", "charge", "charged", "refund", "credit", "card", "payment",
        "overdue", "spending", "limit", "cost", "costs", "pricing", "vat", "tax",
        "subscription", "decommissioned", "bandwidth", "fraud", "fraudulent",
        "billing", "egress", "unauthorized charges", "exemption"
    ],
    "Technical": [
        "aks", "kubernetes", "crashloopbackoff", "500", "504", "gateway",
        "timeout", "sql", "database", "latency", "autoscaling", "ingress",
        "terraform", "vnet", "peering", "quota", "ssl", "handshake", "tls",
        "front door", "unresponsive", "outage", "cpu", "throttling",
        "packet loss", "arm", "deployment", "pipeline", "function app",
        "virtual machine", "vm", "crash", "bug", "cluster"
    ],
    "Access": [
        "entra", "active directory", "azure ad", "global administrator", "admin",
        "locked", "token", "contributor", "reader", "role", "rbac", "sso",
        "saml", "reply url", "aadsts", "authenticator", "mfa", "audit",
        "guest", "permissions", "conditional access", "identity", "credential",
        "password", "access denied", "host pool"
    ],
    "General": [
        "architecture", "landing zone", "best practices", "hipaa", "roadmap",
        "general availability", "ga date", "sweden central", "renewal",
        "cloud solutions architect", "soc 2", "iso 27001", "compliance",
        "portal ui", "feature request", "fasttrack", "partner program",
        "documentation", "how to", "guidance", "contact"
    ]
}

# Uncertainty routing thresholds (calibrated for 4-class classification)
CONFIDENCE_THRESHOLD = 0.38
MARGIN_THRESHOLD = 0.10


class TicketClassifier:
    """
    AI Ticket Classifier with Calibrated Probabilities and Uncertainty Routing.
    """

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path
        self.pipeline: Pipeline | None = None
        self.is_trained = False

        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def _build_pipeline(self) -> Pipeline:
        return Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                token_pattern=r"(?u)\b\w[\w-]*\b",
                stop_words="english",
                min_df=1
            )),
            ("clf", LogisticRegression(
                C=5.0,
                solver="lbfgs",
                max_iter=500,
                random_state=42,
                class_weight="balanced"
            ))
        ])

    def train(self, texts: list[str], labels: list[str]) -> None:
        """Train pipeline on labelled ticket texts."""
        self.pipeline = self._build_pipeline()
        self.pipeline.fit(texts, labels)
        self.is_trained = True

    def save(self, path: str) -> None:
        """Serialize pipeline to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        joblib.dump(self.pipeline, path)
        self.model_path = path

    def load(self, path: str) -> None:
        """Load serialized pipeline from disk."""
        self.pipeline = joblib.load(path)
        self.is_trained = True
        self.model_path = path

    def _compute_lexicon_scores(self, text: str) -> tuple[dict[str, float], bool]:
        """Compute lexicon matching density for each category."""
        text_lower = text.lower()
        scores: dict[str, float] = {cat: 0.0 for cat in CATEGORIES}

        for cat, keywords in DOMAIN_LEXICON.items():
            matches = sum(1.0 for kw in keywords if kw in text_lower)
            scores[cat] = matches

        total = sum(scores.values())
        if total > 0:
            for cat in scores:
                scores[cat] = scores[cat] / total
            return scores, True
        return {cat: 0.25 for cat in CATEGORIES}, False

    def predict_with_confidence(self, text: str) -> dict[str, Any]:
        """
        Classifies input message, returns category, confidence scores,
        candidate ranking, and uncertainty routing analysis.
        """
        if not self.is_trained or self.pipeline is None:
            raise RuntimeError("Classifier has not been trained or loaded yet.")

        # ML model probability estimation
        ml_probs_arr = self.pipeline.predict_proba([text])[0]
        classes = list(self.pipeline.classes_)
        ml_probs: dict[str, float] = {
            cls: float(prob) for cls, prob in zip(classes, ml_probs_arr)
        }

        # Domain lexicon prior
        lex_probs, has_matches = self._compute_lexicon_scores(text)

        combined_scores: dict[str, float] = {}
        if has_matches:
            # Blend 70% model and 30% domain semantic keywords
            for cat in CATEGORIES:
                combined_scores[cat] = (0.70 * ml_probs.get(cat, 0.0)) + (0.30 * lex_probs.get(cat, 0.0))
        else:
            for cat in CATEGORIES:
                combined_scores[cat] = ml_probs.get(cat, 0.0)

        # Re-normalize
        sum_scores = sum(combined_scores.values())
        if sum_scores > 0:
            for cat in combined_scores:
                combined_scores[cat] = round(combined_scores[cat] / sum_scores, 4)

        # Sort candidates descending
        sorted_candidates = sorted(
            combined_scores.items(), key=lambda item: item[1], reverse=True
        )

        top_category, top_confidence = sorted_candidates[0]
        second_category, second_confidence = sorted_candidates[1]
        margin = top_confidence - second_confidence

        # Uncertainty Routing Decision
        is_ambiguous = False
        routing_reason = "High confidence classification"
        assigned_team = CATEGORY_TEAM_MAP[top_category]

        if top_confidence < CONFIDENCE_THRESHOLD:
            is_ambiguous = True
            routing_reason = (
                f"Low confidence ({top_confidence:.1%}) below threshold ({CONFIDENCE_THRESHOLD:.1%}). "
                f"Routed to manual review queue."
            )
            assigned_team = "triage-review-team"
        elif margin < MARGIN_THRESHOLD:
            is_ambiguous = True
            routing_reason = (
                f"High category competition between '{top_category}' ({top_confidence:.1%}) "
                f"and '{second_category}' ({second_confidence:.1%}) with margin {margin:.1%} < {MARGIN_THRESHOLD:.1%}. "
                f"Routed to manual review queue."
            )
            assigned_team = "triage-review-team"

        return {
            "category": top_category,
            "confidence": round(float(top_confidence), 4),
            "margin": round(float(margin), 4),
            "is_ambiguous": is_ambiguous,
            "requires_manual_review": is_ambiguous,
            "routing_reason": routing_reason,
            "assigned_team": assigned_team,
            "candidate_probabilities": {
                cat: round(float(score), 4) for cat, score in sorted_candidates
            }
        }


# Singleton classifier instance management
_global_classifier: TicketClassifier | None = None


def get_classifier(model_path: str | None = None) -> TicketClassifier:
    """Return shared classifier instance, training if necessary."""
    global _global_classifier
    if _global_classifier is not None and _global_classifier.is_trained:
        return _global_classifier

    # Default model path
    if model_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, "data", "trained_model.joblib")

    classifier = TicketClassifier()
    if os.path.exists(model_path):
        classifier.load(model_path)
    else:
        # Load dataset and train
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dataset_path = os.path.join(base_dir, "data", "tickets_dataset.json")
        with open(dataset_path, "r", encoding="utf-8") as f:
            tickets = json.load(f)

        train_texts = [t["message"] for t in tickets if t["split"] == "train"]
        train_labels = [t["category"] for t in tickets if t["split"] == "train"]
        classifier.train(train_texts, train_labels)
        classifier.save(model_path)

    _global_classifier = classifier
    return _global_classifier
