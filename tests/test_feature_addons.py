import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.razorpay_live_adapter import RazorpayLiveAdapter
from metrics.calibration import compute_calibration, CONFIDENCE_BUCKETS
from engine.matcher import ReconciliationMatcher
from engine.classifier import ExceptionClassifier

def test_feature_1_live_adapter_schema_conformance():
    """Feature 1: Live adapter returns merged dataset with required schema and source tags."""
    adapter = RazorpayLiveAdapter(ttl_seconds=60, data_dir="data")
    data, timestamp, fetched_fresh = adapter.fetch_live_and_merged_data()

    assert "invoices" in data
    assert "payments" in data
    assert "settlements" in data
    assert "bank_entries" in data
    assert len(data["payments"]) >= 65
    assert data["total_count"] >= 65

    # Assert source tagging exists
    live_records = [p for p in data["payments"] if p.get("source") == "live"]
    synth_records = [p for p in data["payments"] if p.get("source") == "synthetic"]
    assert len(synth_records) >= 60

    # Test TTL Caching: Second call should return cached data without refetching
    data2, timestamp2, fetched_fresh2 = adapter.fetch_live_and_merged_data(force_refresh=False)
    assert fetched_fresh2 is False

def test_feature_2_confidence_calibration_accuracy():
    """Feature 2: Confidence calibration accurately calculates accuracy per bucket and sample size guardrails."""
    matcher = ReconciliationMatcher(data_dir="data")
    classifier = ExceptionClassifier()

    rec_res = matcher.run_reconciliation()
    exceptions = classifier.classify_exceptions(rec_res["unmatched_records"])

    # Build predictions dict
    predictions = {}
    for m in rec_res["matched_records"]:
        predictions[m["order_id"]] = {"predicted_label": "MATCHED", "confidence": 1.0}

    for exc in exceptions:
        cat = exc["category"]
        conf = exc.get("confidence", 0.7)
        if "FULL_REFUND" in cat:
            label = "FULL_REFUND"
        elif "PARTIAL_REFUND" in cat:
            label = "PARTIAL_REFUND"
        elif "DISPUTE" in cat or "CHARGEBACK" in cat:
            label = "CHARGEBACK_HOLD"
        elif "IN_TRANSIT" in cat:
            label = "SETTLEMENT_IN_TRANSIT"
        elif "UNRESOLVED" in cat:
            label = "UNRESOLVED_REQUIRES_INVESTIGATION"
        else:
            label = "OTHER"

        predictions[exc["order_id"]] = {"predicted_label": label, "confidence": conf}

    calibration = compute_calibration(predictions, ground_truth_file="data/ground_truth.json")

    assert calibration["calibration_available"] is True
    assert "headline_summary" in calibration
    assert len(calibration["calibration_buckets"]) == len(CONFIDENCE_BUCKETS)

    # 90-100% bucket must have high empirical accuracy
    high_bucket = next(b for b in calibration["calibration_buckets"] if b["bucket"] == "90–100%")
    assert high_bucket["count"] >= 50
    assert high_bucket["actual_accuracy_pct"] >= 95.0
    assert high_bucket["low_sample"] is False

    # Low sample bucket check (<50% bucket has 1 unresolvable case)
    low_bucket = next(b for b in calibration["calibration_buckets"] if b["bucket"] == "<50%")
    assert low_bucket["low_sample"] is True
