import pytest
import os
import json
from engine.tax_audit import TaxAuditor

def test_tax_audit_detection_accuracy():
    """
    Tests that TaxAuditor accurately flags:
    1. WRONG_GST_SPLIT (Inter-state billed with CGST/SGST)
    2. GST_RATE_MISMATCH (12% vs standard 18%)
    3. TDS_194O_MISSING (0% vs 1% Section 194-O TDS)
    And has 0 false positives on clean invoices.
    """
    auditor = TaxAuditor(standard_gst_rate=0.18, tds_rate=0.01, merchant_state="Maharashtra")
    res = auditor.audit_tax_lines(invoices_file="data/invoices.json")

    assert res["flagged_count"] == 3
    assert res["total_gst_leakage_inr"] > 0
    assert res["total_tds_leakage_inr"] > 0

    exceptions_by_id = {e["order_id"]: e for e in res["tax_exceptions"]}
    
    # Check Anomaly 1: ord_1040
    assert "ord_1040" in exceptions_by_id
    assert "WRONG_GST_SPLIT" in exceptions_by_id["ord_1040"]["mismatch_categories"]
    assert exceptions_by_id["ord_1040"]["transaction_type"] == "Inter-State"

    # Check Anomaly 2: ord_1041
    assert "ord_1041" in exceptions_by_id
    assert "GST_RATE_MISMATCH" in exceptions_by_id["ord_1041"]["mismatch_categories"]
    assert exceptions_by_id["ord_1041"]["gst_leakage_inr"] > 0

    # Check Anomaly 3: ord_1042
    assert "ord_1042" in exceptions_by_id
    assert "TDS_194O_MISSING" in exceptions_by_id["ord_1042"]["mismatch_categories"]
    assert exceptions_by_id["ord_1042"]["tds_leakage_inr"] > 0

def test_tax_audit_intra_inter_calculation():
    """
    Unit test for custom tax calculation inputs.
    """
    auditor = TaxAuditor(standard_gst_rate=0.18, tds_rate=0.01, merchant_state="Maharashtra")
    
    # 1. Clean Intra-State
    clean_intra = [{
        "order_id": "test_intra",
        "invoice_id": "INV-INTRA-1",
        "amount": 1000.0,
        "merchant_state": "Maharashtra",
        "customer_state": "Maharashtra",
        "tax_lines": [
            {"type": "CGST", "rate": 0.09, "amount": 90.0},
            {"type": "SGST", "rate": 0.09, "amount": 90.0}
        ],
        "tds_deducted": 10.0
    }]
    res = auditor.audit_tax_lines(custom_invoices=clean_intra)
    assert res["flagged_count"] == 0

    # 2. Clean Inter-State
    clean_inter = [{
        "order_id": "test_inter",
        "invoice_id": "INV-INTER-1",
        "amount": 1000.0,
        "merchant_state": "Maharashtra",
        "customer_state": "Karnataka",
        "tax_lines": [
            {"type": "IGST", "rate": 0.18, "amount": 180.0}
        ],
        "tds_deducted": 10.0
    }]
    res_inter = auditor.audit_tax_lines(custom_invoices=clean_inter)
    assert res_inter["flagged_count"] == 0
