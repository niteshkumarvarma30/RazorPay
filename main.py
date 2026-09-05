import os
import sys
import json
import hashlib
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from engine.matcher import ReconciliationMatcher
from engine.classifier import ExceptionClassifier
from engine.fee_audit import FeeAuditor
from engine.tax_audit import TaxAuditor
from engine.anomaly import AnomalyDetector
from engine.forecast import CashflowForecaster
from engine.fault_attribution import FaultAttributionEngine
from llm.query_router import QueryRouter
from llm.investigator_agent import InvestigatorAgent
from metrics.evaluator import EngineEvaluator
from metrics.calibration import compute_calibration
from ingestion.razorpay_live_adapter import RazorpayLiveAdapter

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Razorpay AI Finance Controller",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
matcher = ReconciliationMatcher()
classifier = ExceptionClassifier()
fee_auditor = FeeAuditor()
tax_auditor = TaxAuditor()
anomaly_detector = AnomalyDetector()
forecaster = CashflowForecaster()
query_router = QueryRouter()
investigator = InvestigatorAgent()
evaluator = EngineEvaluator()
live_adapter = RazorpayLiveAdapter(ttl_seconds=60)
fault_engine = FaultAttributionEngine()

class ChatRequest(BaseModel):
    query: str

class InvestigateRequest(BaseModel):
    record_id: str

class DisputeClaimRequest(BaseModel):
    order_id: str
    claim_type: str
    overcharge_amount_inr: float
    evidence_hash: str

class ReverifyInvoiceRequest(BaseModel):
    order_id: str
    invoice_id: str
    amount: float
    customer_state: str = "Maharashtra"
    merchant_state: str = "Maharashtra"
    pay_id: str = None

# API Endpoints
@app.get("/api/reconcile")
def get_reconciliation(mode: str = Query("synthetic", enum=["synthetic", "live"]), refresh: bool = False):
    """
    Returns 3-way reconciliation results.
    If mode='live', ingests live payments from Razorpay test API and tags records.
    """
    data_freshness = "Batch Static"
    is_live = False
    
    if mode == "live":
        merged_data, timestamp, fresh = live_adapter.fetch_live_and_merged_data(force_refresh=refresh)
        data_freshness = f"Live Razorpay Test API — last refreshed at {timestamp}"
        is_live = True
        active_matcher = ReconciliationMatcher(custom_data=merged_data)
    else:
        active_matcher = matcher

    res = active_matcher.run_reconciliation()
    classified_exceptions = classifier.classify_exceptions(res["unmatched_records"])
    fee_report = fee_auditor.audit_payments()

    # Add source tagging to matched records
    live_pay_ids = set()
    if is_live and "merged_data" in locals():
        live_pay_ids = set(p["pay_id"] for p in merged_data.get("payments", []) if p.get("source") == "live")
        live_order_ids = set(p.get("order_id") for p in merged_data.get("payments", []) if p.get("source") == "live")
    else:
        live_order_ids = set()

    live_records = []
    synthetic_records = []
    for m in res["matched_records"]:
        is_rec_live = is_live and (
            m.get("pay_id") in live_pay_ids or 
            m.get("order_id") in live_order_ids or
            "live" in str(m.get("order_id", "")).lower() or 
            "live" in str(m.get("pay_id", "")).lower() or
            str(m.get("invoice_id", "")).startswith("INV-LIVE")
        )
        m["source"] = "live" if is_rec_live else "synthetic"
        if is_rec_live:
            live_records.append(m)
        else:
            synthetic_records.append(m)

    # In live mode, put live records at the top so they are immediately visible
    ordered_matched = live_records + synthetic_records

    return {
        "mode": mode,
        "data_freshness": data_freshness,
        "is_live": is_live,
        "summary": {
            "total_records": res["total_records"],
            "matched_count": res["matched_count"],
            "unmatched_count": res["unmatched_count"],
            "match_rate_percentage": res["match_rate_percentage"],
            "total_fee_leakage_inr": fee_report["total_leakage_inr"],
            "overcharge_count": fee_report["flagged_count"],
            "live_records_count": len(live_records)
        },
        "matched_records": ordered_matched,
        "exceptions": classified_exceptions
    }

@app.get("/api/calibration")
def get_confidence_calibration():
    """
    Feature 2: Returns confidence calibration analysis against ground truth.
    """
    res = matcher.run_reconciliation()
    exceptions = classifier.classify_exceptions(res["unmatched_records"])

    predictions = {}
    for m in res["matched_records"]:
        predictions[m["order_id"]] = {"predicted_label": "MATCHED", "confidence": 1.0}

    for exc in exceptions:
        cat = exc["category"]
        conf = exc.get("confidence", 0.70)
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

    calibration_data = compute_calibration(predictions, ground_truth_file="data/ground_truth.json")
    return calibration_data

@app.post("/api/chat")
def chat_with_controller(req: ChatRequest):
    if not req.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    response = query_router.process_query(req.query)
    return response

@app.get("/api/forecast")
def get_cashflow_forecast():
    return forecaster.generate_forecast()

@app.get("/api/fee-audit")
def get_fee_audit():
    return fee_auditor.audit_payments()

@app.get("/api/tax-audit")
def get_tax_audit():
    """
    Returns Tax-Line (GST & Section 194-O TDS) Audit Report.
    """
    return tax_auditor.audit_tax_lines()

@app.get("/api/anomalies")
def get_anomalies():
    return anomaly_detector.detect_anomalies()

@app.get("/api/metrics")
def get_metrics():
    return evaluator.evaluate_against_ground_truth()

@app.get("/api/evidence/{record_id}")
def get_evidence_graph(record_id: str, mode: str = "synthetic"):
    """
    Returns NetworkX subgraph evidence for a record ID, supporting both synthetic and live API records.
    """
    # If live mode or live record, check live matcher first
    if "live" in record_id or mode == "live":
        merged_data, _, _ = live_adapter.fetch_live_and_merged_data(force_refresh=False)
        live_matcher = ReconciliationMatcher(custom_data=merged_data)
        subgraph = live_matcher.get_subgraph_evidence(record_id)
        if "error" not in subgraph:
            return subgraph

    # Check default static matcher
    subgraph = matcher.get_subgraph_evidence(record_id)
    if "error" not in subgraph:
        return subgraph

    # Fallback check live matcher in case record is live
    merged_data, _, _ = live_adapter.fetch_live_and_merged_data(force_refresh=False)
    live_matcher = ReconciliationMatcher(custom_data=merged_data)
    subgraph = live_matcher.get_subgraph_evidence(record_id)
    if "error" not in subgraph:
        return subgraph

    raise HTTPException(status_code=404, detail=subgraph.get("error", f"Record {record_id} not found."))

@app.post("/api/investigate")
def investigate_record(req: InvestigateRequest):
    result = investigator.investigate_record(req.record_id)
    return result

@app.get("/api/fault-attribution/{record_id}")
def get_fault_attribution(record_id: str):
    """
    Returns Root-Cause Fault Attribution, 4-Stage Money Flow Timeline, and Resolution Action.
    """
    res = fault_engine.analyze_transaction(record_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.post("/api/dispute-claim")
def submit_dispute_claim(req: DisputeClaimRequest):
    """
    Simulates automated 1-click dispute dispatch to Razorpay Merchant Reimbursement Desk.
    """
    claim_id = f"CLAIM-RZP-{hashlib.sha256(f'{req.order_id}:{datetime.now().isoformat()}'.encode()).hexdigest()[:8].upper()}"
    return {
        "success": True,
        "claim_id": claim_id,
        "order_id": req.order_id,
        "amount_inr": req.overcharge_amount_inr,
        "status": "DISPATCHED_TO_RAZORPAY",
        "message": f"Dispute ticket {claim_id} dispatched to Razorpay Merchant Resolution Desk. Reimbursement credited within 48h SLA."
    }

@app.post("/api/reverify-invoice")
def reverify_invoice(req: ReverifyInvoiceRequest):
    """
    Accepts corrected merchant invoice data, updates ledger, and runs instant self-healing re-verification.
    """
    with open("data/invoices.json", "r") as f:
        invoices = json.load(f)

    found = False
    for inv in invoices:
        if inv["order_id"] == req.order_id:
            inv["amount"] = req.amount
            inv["invoice_id"] = req.invoice_id
            inv["customer_state"] = req.customer_state
            inv["merchant_state"] = req.merchant_state
            found = True
            break

    if not found:
        invoices.append({
            "order_id": req.order_id,
            "invoice_id": req.invoice_id,
            "amount": req.amount,
            "customer_id": "cust_reverify",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "merchant_state": req.merchant_state,
            "customer_state": req.customer_state
        })

    with open("data/invoices.json", "w") as f:
        json.dump(invoices, f, indent=2)

    # If pay_id provided or ghost invoice fix, also pair with a simulated capture payment if needed
    if req.pay_id:
        with open("data/payments.json", "r") as f:
            payments = json.load(f)
        with open("data/settlements.json", "r") as f:
            settlements = json.load(f)
        with open("data/bank_entries.json", "r") as f:
            bank_entries = json.load(f)

        if not any(p["order_id"] == req.order_id for p in payments):
            fee = round((req.amount * 0.02) + ((req.amount * 0.02) * 0.18), 2)
            net = round(req.amount - fee, 2)
            batch_id = f"batch_healed_{req.order_id}"
            utr = f"UTR8899{hashlib.sha256(req.order_id.encode()).hexdigest()[:8].upper()}"

            payments.append({
                "pay_id": req.pay_id,
                "order_id": req.order_id,
                "amount_captured": req.amount,
                "mdr_fee": round(req.amount * 0.02, 2),
                "gst_on_fee": round((req.amount * 0.02) * 0.18, 2),
                "status": "captured",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            settlements.append({
                "settlement_id": f"setl_{req.pay_id}",
                "pay_id": req.pay_id,
                "net_amount": net,
                "batch_id": batch_id,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            bank_entries.append({
                "utr": utr,
                "batch_id": batch_id,
                "amount_credited": net,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            with open("data/payments.json", "w") as f:
                json.dump(payments, f, indent=2)
            with open("data/settlements.json", "w") as f:
                json.dump(settlements, f, indent=2)
            with open("data/bank_entries.json", "w") as f:
                json.dump(bank_entries, f, indent=2)

    # Re-run matcher
    new_matcher = ReconciliationMatcher(data_dir="data")
    match_res = new_matcher.run_reconciliation()
    is_matched = any(m["order_id"] == req.order_id for m in match_res["matched_records"])

    return {
        "success": True,
        "order_id": req.order_id,
        "reconciled": is_matched,
        "status": "MATCHED" if is_matched else "EXAMINED",
        "message": "Invoice corrected and self-healed in reconciliation graph." if is_matched else "Invoice updated."
    }

# Serve static dashboard
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_dashboard():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
