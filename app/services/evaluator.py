"""
Model Evaluation and Metrics Module.
Calculates test set accuracy, per-class metrics, confusion matrix,
and priority policy statistics on the reserved test set.
"""

import os
import json
from typing import Dict, Any, List
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from app.services.classifier import get_classifier, CATEGORIES


def run_test_set_evaluation() -> Dict[str, Any]:
    """
    Evaluates the classifier on the reserved test tickets in data/tickets_dataset.json.
    Returns structured accuracy metrics, confusion matrix, and performance stats.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(base_dir, "data", "tickets_dataset.json")

    with open(dataset_path, "r", encoding="utf-8") as f:
        tickets = json.load(f)

    test_tickets = [t for t in tickets if t["split"] == "test"]
    train_tickets = [t for t in tickets if t["split"] == "train"]

    classifier = get_classifier()

    y_true: List[str] = []
    y_pred: List[str] = []
    predictions_detail: List[Dict[str, Any]] = []

    for t in test_tickets:
        pred_result = classifier.predict_with_confidence(t["message"])
        y_true.append(t["category"])
        y_pred.append(pred_result["category"])

        predictions_detail.append({
            "ticket_id": t["ticket_id"],
            "true_category": t["category"],
            "predicted_category": pred_result["category"],
            "confidence": pred_result["confidence"],
            "is_ambiguous": pred_result["is_ambiguous"],
            "correct": t["category"] == pred_result["category"]
        })

    acc = accuracy_score(y_true, y_pred)
    acc_pct = round(acc * 100.0, 2)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=CATEGORIES)
    cm_dict: Dict[str, Dict[str, int]] = {}
    for i, true_cat in enumerate(CATEGORIES):
        cm_dict[true_cat] = {}
        for j, pred_cat in enumerate(CATEGORIES):
            cm_dict[true_cat][pred_cat] = int(cm[i][j])

    # Per-class report
    report = classification_report(
        y_true, y_pred, labels=CATEGORIES, output_dict=True, zero_division=0
    )

    per_class: Dict[str, Dict[str, float]] = {}
    for cat in CATEGORIES:
        if cat in report:
            per_class[cat] = {
                "precision": round(report[cat]["precision"], 3),
                "recall": round(report[cat]["recall"], 3),
                "f1_score": round(report[cat]["f1-score"], 3),
                "support": int(report[cat]["support"])
            }

    correct_count = sum(1 for p in predictions_detail if p["correct"])
    total_count = len(test_tickets)

    return {
        "total_test_samples": total_count,
        "correct_predictions": correct_count,
        "accuracy_percentage": acc_pct,
        "accuracy_ratio": f"{correct_count}/{total_count}",
        "per_class_metrics": per_class,
        "confusion_matrix": cm_dict,
        "predictions_detail": predictions_detail,
        "model_type": "TF-IDF (1,2-grams) + Calibrated Logistic Regression + Azure Domain Semantics",
        "trained_on_samples": len(train_tickets),
        "priority_policy_summary": {
            "P1": "Critical production outage, security lockout, or financial fraud (<15m SLA)",
            "P2": "High degradation of business workflow or payment suspension (<1h SLA)",
            "P3": "Medium operational request with workaround (<4h SLA)",
            "P4": "Low advisory, roadmap, or documentation inquiry (<24h SLA)"
        }
    }
