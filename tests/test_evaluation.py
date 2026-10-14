"""
Test Suite Verification for Test-Set Classification Accuracy.
Ensures model meets target accuracy on the reserved 10-ticket evaluation set.
"""

from app.services.evaluator import run_test_set_evaluation


def test_reserved_test_set_accuracy():
    report = run_test_set_evaluation()
    accuracy = report["accuracy_percentage"]

    # Target threshold is at least 80%
    assert accuracy >= 80.0, f"Expected accuracy >= 80%, but got {accuracy}%"
    assert report["total_test_samples"] == 10
    assert report["trained_on_samples"] == 20

    # Ensure all 4 categories are present in per-class metrics
    for cat in ["Billing", "Technical", "Access", "General"]:
        assert cat in report["per_class_metrics"]
        assert report["per_class_metrics"][cat]["support"] > 0
