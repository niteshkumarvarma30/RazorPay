import pytest
from engine.fault_attribution import FaultAttributionEngine

def test_fault_attribution_overcharge_razorpay_fault():
    """
    Tests that MDR overcharged transactions (ord_1063) are attributed to RAZORPAY_GATEWAY.
    """
    fa = FaultAttributionEngine(data_dir="data")
    res = fa.analyze_transaction("ord_1063")

    assert res["fault_party"] == "RAZORPAY_GATEWAY"
    assert res["action_type"] == "DISPUTE_CLAIM"
    assert res["fee_overcharge_inr"] > 0
    assert "dispute_packet" in res
    assert res["dispute_packet"]["claim_type"] == "MDR_FEE_OVERCHARGE_REIMBURSEMENT"

def test_fault_attribution_ghost_invoice_merchant_fault():
    """
    Tests that ghost ERP invoices without gateway captures (ord_1065) are attributed to MERCHANT_USER.
    """
    fa = FaultAttributionEngine(data_dir="data")
    res = fa.analyze_transaction("ord_1065")

    assert res["fault_party"] == "MERCHANT_USER"
    assert res["action_type"] == "INVOICE_CORRECTION"
    assert "editable_invoice" in res

def test_money_flow_stages_structure():
    """
    Tests that the 4-step money flow pipeline contains all necessary financial milestones.
    """
    fa = FaultAttributionEngine(data_dir="data")
    res = fa.analyze_transaction("ord_1001")

    assert len(res["money_flow"]) == 4
    stages = [s["stage"] for s in res["money_flow"]]
    assert "1. ERP Invoicing" in stages
    assert "2. Gateway Capture" in stages
    assert "3. MDR Fee Deduction" in stages
    assert "4. Bank Settlement" in stages
    assert res["fault_party"] == "NONE_HEALTHY"
