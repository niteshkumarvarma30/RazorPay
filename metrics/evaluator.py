import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.matcher import ReconciliationMatcher
from engine.classifier import ExceptionClassifier
from engine.fee_audit import FeeAuditor
from engine.tax_audit import TaxAuditor

class EngineEvaluator:
    """
    Phase 9: Metrics & Ground-Truth Scoring Engine
    Evaluates precision, recall, F1, match rate, fee leakage, and tax-line anomalies against ground truth.
    """
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.matcher = ReconciliationMatcher(data_dir=data_dir)
        self.classifier = ExceptionClassifier()
        self.fee_auditor = FeeAuditor()
        self.tax_auditor = TaxAuditor()

    def evaluate_against_ground_truth(self, ground_truth_file="data/ground_truth.json"):
        with open(ground_truth_file, "r") as f:
            ground_truth = json.load(f)

        reconciliation_res = self.matcher.run_reconciliation()
        fee_res = self.fee_auditor.audit_payments()
        tax_res = self.tax_auditor.audit_tax_lines()
        exceptions = self.classifier.classify_exceptions(reconciliation_res["unmatched_records"])

        # Map predictions by order_id
        predictions = {}
        for m in reconciliation_res["matched_records"]:
            predictions[m["order_id"]] = "MATCHED"

        for exc in exceptions:
            cat = exc["category"]
            if "FULL_REFUND" in cat:
                predictions[exc["order_id"]] = "FULL_REFUND"
            elif "PARTIAL_REFUND" in cat:
                predictions[exc["order_id"]] = "PARTIAL_REFUND"
            elif "DISPUTE" in cat or "CHARGEBACK" in cat:
                predictions[exc["order_id"]] = "CHARGEBACK_HOLD"
            elif "IN_TRANSIT" in cat:
                predictions[exc["order_id"]] = "SETTLEMENT_IN_TRANSIT"
            elif "UNRESOLVED" in cat:
                predictions[exc["order_id"]] = "UNRESOLVED_REQUIRES_INVESTIGATION"
            else:
                predictions[exc["order_id"]] = "UNMATCHED_OTHER"

        # Calculate Confusion Matrix per Class
        classes = ["MATCHED", "FULL_REFUND", "PARTIAL_REFUND", "CHARGEBACK_HOLD", "SETTLEMENT_IN_TRANSIT", "UNRESOLVED_REQUIRES_INVESTIGATION"]
        
        metrics_by_class = {}
        tp_total = 0
        total_eval = len(ground_truth)

        for c in classes:
            tp = sum(1 for oid, gt in ground_truth.items() if (gt["label"] == c or (c == "MATCHED" and gt["label"] == "MATCHED_BATCH")) and predictions.get(oid) == c)
            fp = sum(1 for oid, pred in predictions.items() if pred == c and (ground_truth[oid]["label"] != c and not (c == "MATCHED" and ground_truth[oid]["label"] == "MATCHED_BATCH")))
            fn = sum(1 for oid, gt in ground_truth.items() if (gt["label"] == c or (c == "MATCHED" and gt["label"] == "MATCHED_BATCH")) and predictions.get(oid) != c)

            precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
            recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0
            f1 = round(2 * (precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0

            metrics_by_class[c] = {
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "precision": precision,
                "recall": recall,
                "f1_score": f1
            }
            tp_total += tp

        # Evaluate Tax Audit specifically
        tax_pred_ids = set(e["order_id"] for e in tax_res["tax_exceptions"])
        tax_gt_ids = set(oid for oid, gt in ground_truth.items() if gt.get("tax_audit", {}).get("status") in ["WRONG_GST_SPLIT", "GST_RATE_MISMATCH", "TDS_MISSING"])
        
        tax_tp = len(tax_pred_ids.intersection(tax_gt_ids))
        tax_fp = len(tax_pred_ids - tax_gt_ids)
        tax_fn = len(tax_gt_ids - tax_pred_ids)
        tax_precision = round(tax_tp / (tax_tp + tax_fp), 4) if (tax_tp + tax_fp) > 0 else 1.0
        tax_recall = round(tax_tp / (tax_tp + tax_fn), 4) if (tax_tp + tax_fn) > 0 else 1.0
        tax_f1 = round(2 * (tax_precision * tax_recall) / (tax_precision + tax_recall), 4) if (tax_precision + tax_recall) > 0 else 0.0

        metrics_by_class["TAX_GST_TDS_AUDIT"] = {
            "true_positives": tax_tp,
            "false_positives": tax_fp,
            "false_negatives": tax_fn,
            "precision": tax_precision,
            "recall": tax_recall,
            "f1_score": tax_f1
        }

        overall_accuracy = round(tp_total / total_eval, 4)

        metrics_summary = {
            "total_transactions_evaluated": total_eval,
            "overall_accuracy_score": overall_accuracy,
            "3_way_match_rate_pct": reconciliation_res["match_rate_percentage"],
            "total_reconciled_count": reconciliation_res["matched_count"],
            "total_exceptions_count": reconciliation_res["unmatched_count"],
            "total_fee_leakage_detected_inr": fee_res["total_leakage_inr"],
            "fee_overcharges_flagged_count": fee_res["flagged_count"],
            "total_gst_leakage_detected_inr": tax_res["total_gst_leakage_inr"],
            "total_tds_leakage_detected_inr": tax_res["total_tds_leakage_inr"],
            "tax_exceptions_flagged_count": tax_res["flagged_count"],
            "class_level_performance": metrics_by_class
        }

        os.makedirs("metrics", exist_ok=True)
        with open("metrics/metrics.json", "w") as f:
            json.dump(metrics_summary, f, indent=2)

        return metrics_summary

if __name__ == "__main__":
    evaluator = EngineEvaluator()
    summary = evaluator.evaluate_against_ground_truth()
    print("Evaluation Complete! Metrics exported to metrics/metrics.json")
    print(json.dumps(summary, indent=2))
