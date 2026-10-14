"""
Evaluation CLI Script.
Evaluates the classifier against the 10 reserved test set tickets,
prints confusion matrix, precision/recall/F1 metrics, and writes an evaluation report.
"""

import json
import os
import sys

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.evaluator import run_test_set_evaluation


def main():
    print("=" * 70)
    print("   AZURE SUPPORT TICKET AUTOMATION - TEST SET EVALUATION")
    print("=" * 70)

    report = run_test_set_evaluation()

    print(f"\nModel Architecture: {report['model_type']}")
    print(f"Training Set Size : {report['trained_on_samples']} labelled tickets")
    print(f"Reserved Test Set : {report['total_test_samples']} tickets")
    print(f"Correct Predictions: {report['correct_predictions']} / {report['total_test_samples']}")
    print(f"Overall Accuracy  : {report['accuracy_percentage']}%\n")

    print("-" * 70)
    print(f"{'Category':<15} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
    print("-" * 70)
    for cat, metrics in report["per_class_metrics"].items():
        print(f"{cat:<15} {metrics['precision']:<12.3f} {metrics['recall']:<12.3f} {metrics['f1_score']:<12.3f} {metrics['support']:<10}")
    print("-" * 70)

    print("\nConfusion Matrix (Rows: True, Columns: Predicted):")
    cols = list(report["confusion_matrix"].keys())
    corner_label = "True / Pred"
    header = f"{corner_label:<15}" + "".join([f"{c:<12}" for c in cols])
    print(header)
    print("-" * len(header))
    for true_cat in cols:
        row = f"{true_cat:<15}"
        for pred_cat in cols:
            row += f"{report['confusion_matrix'][true_cat][pred_cat]:<12}"
        print(row)

    print("\nIndividual Test Sample Breakdown:")
    print("-" * 70)
    for sample in report["predictions_detail"]:
        status_flag = "PASS" if sample["correct"] else "FAIL"
        ambig_flag = "[UNCERTAIN/ROUTED]" if sample["is_ambiguous"] else "[HIGH CONFIDENCE]"
        print(f"  [{status_flag}] {sample['ticket_id']}: True={sample['true_category']:<10} Pred={sample['predicted_category']:<10} Conf={sample['confidence']:.1%} {ambig_flag}")
    print("-" * 70)

    # Save artifact
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "evaluation_report.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nSaved evaluation metrics to: {output_path}")

    # Return exit code: 0 if accuracy >= 80%, else 1
    if report["accuracy_percentage"] >= 80.0:
        print("\n>>> EVALUATION CRITERIA MET (Accuracy >= 80%) <<<\n")
        sys.exit(0)
    else:
        print("\n>>> EVALUATION CRITERIA FAILED <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
