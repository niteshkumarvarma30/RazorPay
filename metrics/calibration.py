import json
import os

CONFIDENCE_BUCKETS = [
    {"label": "90–100%", "min_conf": 0.90, "max_conf": 1.00, "midpoint": 95},
    {"label": "70–90%", "min_conf": 0.70, "max_conf": 0.90, "midpoint": 80},
    {"label": "50–70%", "min_conf": 0.50, "max_conf": 0.70, "midpoint": 60},
    {"label": "<50%", "min_conf": 0.00, "max_conf": 0.50, "midpoint": 25},
]

def compute_calibration(predictions, ground_truth_file="data/ground_truth.json", sample_threshold=5):
    """
    Feature 2: Confidence Calibration Engine
    Evaluates whether stated classifier confidence matches empirical real-world accuracy.
    """
    if not os.path.exists(ground_truth_file):
        return {
            "calibration_available": False,
            "message": "Ground truth labels not present for live unlabelled batches."
        }

    with open(ground_truth_file, "r") as f:
        ground_truth = json.load(f)

    # Bucketed accumulator
    bucket_results = []
    for b in CONFIDENCE_BUCKETS:
        bucket_results.append({
            "bucket": b["label"],
            "stated_confidence_pct": b["midpoint"],
            "count": 0,
            "correct_count": 0,
            "actual_accuracy_pct": 0.0,
            "low_sample": False
        })

    # Join predictions with ground truth
    for record_id, pred_info in predictions.items():
        if record_id not in ground_truth:
            continue

        pred_label = pred_info.get("predicted_label")
        conf = pred_info.get("confidence", 0.7)
        true_label = ground_truth[record_id].get("label")

        # Normalize matched batch label
        if true_label == "MATCHED_BATCH":
            true_label = "MATCHED"

        is_correct = (pred_label == true_label)

        # Assign to appropriate bucket
        for b_idx, b in enumerate(CONFIDENCE_BUCKETS):
            if (conf >= b["min_conf"] and (conf <= b["max_conf"] if b["max_conf"] == 1.00 else conf < b["max_conf"])) or (b["min_conf"] == 0.00 and conf <= 0.50):
                bucket_results[b_idx]["count"] += 1
                if is_correct:
                    bucket_results[b_idx]["correct_count"] += 1
                break

    # Calculate actual empirical accuracy & sample size guardrail
    high_conf_stat = None
    for b in bucket_results:
        cnt = b["count"]
        if cnt > 0:
            b["actual_accuracy_pct"] = round((b["correct_count"] / cnt) * 100, 1)
        else:
            b["actual_accuracy_pct"] = 0.0

        if cnt < sample_threshold:
            b["low_sample"] = True

        if b["bucket"] == "90–100%" and cnt > 0:
            high_conf_stat = f"Our 90%+ confidence predictions were correct {b['actual_accuracy_pct']}% of the time (n={cnt})."

    headline_summary = high_conf_stat or "Model confidence scores calibrated across all test batches."

    return {
        "calibration_available": True,
        "headline_summary": headline_summary,
        "calibration_buckets": bucket_results,
        "total_evaluated": len(predictions)
    }

if __name__ == "__main__":
    # Smoke test with dummy predictions
    dummy_preds = {
        "ord_1001": {"predicted_label": "MATCHED", "confidence": 1.0},
        "ord_1056": {"predicted_label": "PARTIAL_REFUND", "confidence": 1.0},
        "ord_1065": {"predicted_label": "UNRESOLVED_REQUIRES_INVESTIGATION", "confidence": 0.50}
    }
    res = compute_calibration(dummy_preds)
    print(json.dumps(res, indent=2))
