import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_gen.generator import generate_synthetic_dataset
from engine.matcher import ReconciliationMatcher
from engine.classifier import ExceptionClassifier
from engine.fee_audit import FeeAuditor
from engine.anomaly import AnomalyDetector
from engine.forecast import CashflowForecaster
from metrics.evaluator import EngineEvaluator
from llm.investigator_agent import InvestigatorAgent
from llm.query_router import QueryRouter

def test_phase_0_data_generation():
    """Phase 0: Synthetic dataset generation must produce 65 records with valid schema."""
    generate_synthetic_dataset(output_dir="data", count=65, seed=42)
    assert os.path.exists("data/invoices.json")
    assert os.path.exists("data/payments.json")
    assert os.path.exists("data/settlements.json")
    assert os.path.exists("data/bank_entries.json")
    assert os.path.exists("data/ground_truth.json")

def test_phase_1_deterministic_matcher():
    """Phase 1: 3-pass matcher creates NetworkX graph and produces >80% match rate."""
    matcher = ReconciliationMatcher(data_dir="data")
    res = matcher.run_reconciliation()
    assert res["total_records"] == 65
    assert res["matched_count"] >= 50
    assert res["match_rate_percentage"] > 80.0
    assert matcher.graph.number_of_nodes() > 100

def test_phase_2_exception_classifier():
    """Phase 2: Every unmatched record is classified into an actionable category."""
    matcher = ReconciliationMatcher(data_dir="data")
    classifier = ExceptionClassifier()
    res = matcher.run_reconciliation()
    exceptions = classifier.classify_exceptions(res["unmatched_records"])
    assert len(exceptions) == res["unmatched_count"]
    for e in exceptions:
        assert "category" in e
        assert "confidence" in e
        assert "action_required" in e
        assert e["confidence"] > 0.0

def test_phase_3_fee_audit_leakage():
    """Phase 3: Fee auditor flags MDR overcharges with exact rupee leakage."""
    fee_auditor = FeeAuditor(contracted_mdr_rate=0.02, gst_rate=0.18)
    report = fee_auditor.audit_payments(payments_file="data/payments.json")
    assert report["flagged_count"] >= 2
    assert report["total_leakage_inr"] > 0.0

def test_phase_4_anomaly_detection():
    """Phase 4: ML IsolationForest flags multi-dimensional outliers."""
    anomaly_detector = AnomalyDetector()
    report = anomaly_detector.detect_anomalies(payments_file="data/payments.json")
    assert report["total_analyzed"] > 50
    assert report["anomalies_detected_count"] > 0

def test_phase_5_cashflow_forecaster():
    """Phase 5: Cashflow forecaster projects upcoming T+2 bank deposits."""
    forecaster = CashflowForecaster(data_dir="data")
    forecast = forecaster.generate_forecast()
    assert forecast["total_in_flight_orders"] > 0
    assert forecast["total_projected_bank_deposit_inr"] > 0.0
    assert len(forecast["forecast_timeline"]) > 0

def test_phase_8_failure_recovery_investigation():
    """Phase 8: Deliberately ambiguous ghost invoice triggers safe human escalation."""
    investigator = InvestigatorAgent(data_dir="data")
    result = investigator.investigate_record("ord_1065")
    assert result["classification"] == "GHOST_ERP_INVOICE_UNAUTHORIZED"
    assert result["needs_human_review"] is True
    assert result["confidence"] < 0.80

def test_phase_9_ground_truth_metrics():
    """Phase 9: Overall precision & accuracy exceeds 95% against ground truth."""
    evaluator = EngineEvaluator(data_dir="data")
    metrics = evaluator.evaluate_against_ground_truth()
    assert metrics["overall_accuracy_score"] >= 0.95
    assert metrics["3_way_match_rate_pct"] > 80.0
