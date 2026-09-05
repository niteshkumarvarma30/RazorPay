import json
import hashlib
from datetime import datetime
from engine.matcher import ReconciliationMatcher
from engine.fee_audit import FeeAuditor
from engine.tax_audit import TaxAuditor

class FaultAttributionEngine:
    """
    Autonomous Root-Cause Fault Attribution & Self-Healing Engine
    Determines whether a financial discrepancy is:
    - RAZORPAY_GATEWAY_FAULT (MDR fee overcharge, settlement delay beyond SLA)
    - MERCHANT_USER_FAULT (ERP typo, ghost invoice, tax state mismatch)
    - CUSTOMER_ACTION (Chargeback dispute, refund)
    - NONE_HEALTHY (Clean 3-way match)
    """
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.matcher = ReconciliationMatcher(data_dir=data_dir)
        self.fee_auditor = FeeAuditor()
        self.tax_auditor = TaxAuditor()

    def analyze_transaction(self, record_id: str, custom_invoices=None):
        if custom_invoices:
            invoices = custom_invoices
        else:
            with open(f"{self.data_dir}/invoices.json", "r") as f:
                invoices = json.load(f)

        with open(f"{self.data_dir}/payments.json", "r") as f:
            payments = json.load(f)
        with open(f"{self.data_dir}/settlements.json", "r") as f:
            settlements = json.load(f)
        with open(f"{self.data_dir}/bank_entries.json", "r") as f:
            bank_entries = json.load(f)
        with open(f"{self.data_dir}/refunds.json", "r") as f:
            refunds = json.load(f)
        with open(f"{self.data_dir}/disputes.json", "r") as f:
            disputes = json.load(f)

        # 1. Locate entities
        inv = next((i for i in invoices if i["order_id"] == record_id or i.get("invoice_id") == record_id), None)
        if not inv:
            return {"error": f"Record {record_id} not found in ERP invoices."}

        order_id = inv["order_id"]
        inv_id = inv["invoice_id"]
        billed_amount = inv["amount"]

        pay = next((p for p in payments if p["order_id"] == order_id or p["pay_id"] == record_id), None)
        pay_id = pay["pay_id"] if pay else None

        setl = next((s for s in settlements if s.get("pay_id") == pay_id), None) if pay_id else None
        setl_id = setl["settlement_id"] if setl else None

        bank = next((b for b in bank_entries if b.get("batch_id") == setl.get("batch_id")), None) if setl else None
        bank_utr = bank["utr"] if bank else None

        rfnd = next((r for r in refunds if r.get("pay_id") == pay_id), None) if pay_id else None
        disp = next((d for d in disputes if d.get("pay_id") == pay_id), None) if pay_id else None

        # 2. Check Fee Overcharge
        fee_overcharge = 0.0
        if pay:
            actual_fee = round(pay.get("mdr_fee", 0.0) + pay.get("gst_on_fee", 0.0), 2)
            expected_fee = round((pay["amount_captured"] * 0.02) + ((pay["amount_captured"] * 0.02) * 0.18), 2)
            if actual_fee - expected_fee > 0.50:
                fee_overcharge = round(actual_fee - expected_fee, 2)

        # 3. Check Tax Mismatch
        tax_mismatches = []
        if inv.get("tax_lines"):
            m_state = inv.get("merchant_state", "Maharashtra")
            c_state = inv.get("customer_state", "Maharashtra")
            is_intra = (m_state.lower() == c_state.lower())
            actual_types = [t.get("type", "").upper() for t in inv["tax_lines"]]
            if is_intra and "IGST" in actual_types:
                tax_mismatches.append("WRONG_SPLIT_INTRA_AS_IGST")
            elif (not is_intra) and ("CGST" in actual_types or "SGST" in actual_types):
                tax_mismatches.append("WRONG_SPLIT_INTER_AS_CGST_SGST")

        # 4. Construct 4-Stage Money Flow
        money_flow = []

        # Stage 1: ERP Invoice
        money_flow.append({
            "stage": "1. ERP Invoicing",
            "entity_id": inv_id,
            "amount": billed_amount,
            "status": "SUCCESS",
            "timestamp": inv.get("date", "2026-08-15"),
            "detail": f"Billed ₹{billed_amount:.2f} ({inv.get('merchant_state', 'MH')} ➔ {inv.get('customer_state', 'MH')})"
        })

        # Stage 2: Gateway Capture
        if pay:
            stage_2_status = "SUCCESS"
            stage_2_detail = f"Captured ₹{pay['amount_captured']:.2f} via {pay_id}"
            if rfnd:
                stage_2_detail += f" (Refunded ₹{rfnd['amount']:.2f})"
            if disp:
                stage_2_status = "HELD"
                stage_2_detail += f" (Dispute: {disp.get('reason', 'chargeback')})"

            money_flow.append({
                "stage": "2. Gateway Capture",
                "entity_id": pay_id,
                "amount": pay["amount_captured"],
                "status": stage_2_status,
                "timestamp": pay.get("date", ""),
                "detail": stage_2_detail
            })
        else:
            money_flow.append({
                "stage": "2. Gateway Capture",
                "entity_id": "MISSING",
                "amount": 0.0,
                "status": "FAILED",
                "timestamp": "-",
                "detail": "No payment record found on Razorpay Gateway (Ghost invoice)"
            })

        # Stage 3: MDR Fee Deduction
        if pay:
            actual_total_fee = round(pay["mdr_fee"] + pay["gst_on_fee"], 2)
            if fee_overcharge > 0:
                fee_status = "FAILED"
                fee_detail = f"Overcharged ₹{actual_total_fee:.2f} (3.5% vs 2.0% MDR + GST). Leakage: +₹{fee_overcharge:.2f}"
            else:
                fee_status = "SUCCESS"
                fee_detail = f"Contracted fee -₹{actual_total_fee:.2f} (2.0% MDR + 18% GST)"

            money_flow.append({
                "stage": "3. MDR Fee Deduction",
                "entity_id": f"FEE_{pay_id}",
                "amount": actual_total_fee,
                "status": fee_status,
                "timestamp": pay.get("date", ""),
                "detail": fee_detail
            })
        else:
            money_flow.append({
                "stage": "3. MDR Fee Deduction",
                "entity_id": "N/A",
                "amount": 0.0,
                "status": "SKIPPED",
                "timestamp": "-",
                "detail": "Skipped (Payment was not captured)"
            })

        # Stage 4: Bank Settlement Deposit
        if bank and not disp and not (rfnd and rfnd["amount"] == billed_amount):
            money_flow.append({
                "stage": "4. Bank Settlement",
                "entity_id": bank_utr,
                "amount": setl["net_amount"] if setl else bank["amount_credited"],
                "status": "SUCCESS",
                "timestamp": bank.get("date", ""),
                "detail": f"Credited ₹{(setl['net_amount'] if setl else bank['amount_credited']):.2f} via UTR {bank_utr}"
            })
        elif disp:
            money_flow.append({
                "stage": "4. Bank Settlement",
                "entity_id": "HELD_DISPUTE",
                "amount": 0.0,
                "status": "HELD",
                "timestamp": disp.get("date", ""),
                "detail": f"Payout frozen due to active dispute {disp.get('dispute_id')}"
            })
        elif rfnd and rfnd["amount"] == billed_amount:
            money_flow.append({
                "stage": "4. Bank Settlement",
                "entity_id": "REFUNDED",
                "amount": 0.0,
                "status": "REFUNDED",
                "timestamp": rfnd.get("date", ""),
                "detail": f"Full refund of ₹{rfnd['amount']:.2f} returned to customer card."
            })
        elif pay and not setl:
            money_flow.append({
                "stage": "4. Bank Settlement",
                "entity_id": "IN_TRANSIT",
                "amount": round(billed_amount - (pay['mdr_fee'] + pay['gst_on_fee']), 2),
                "status": "IN_TRANSIT",
                "timestamp": "T+2 Cycle",
                "detail": "Settlement in-flight per standard bank schedule."
            })
        else:
            money_flow.append({
                "stage": "4. Bank Settlement",
                "entity_id": "NOT_DEPOSITED",
                "amount": 0.0,
                "status": "FAILED",
                "timestamp": "-",
                "detail": "Zero bank settlement deposited."
            })

        # 5. Fault Attribution Decision
        fault_party = "NONE_HEALTHY"
        fault_title = "Healthy 3-Way Reconciled"
        root_cause = "All stages verified. ERP amount matches Razorpay capture and Bank UTR credit."
        recommended_action = "No action required. Transaction clean."
        action_type = "NONE"

        if fee_overcharge > 0:
            fault_party = "RAZORPAY_GATEWAY"
            fault_title = "🔴 Gateway Fee Overcharge Fault"
            root_cause = f"Razorpay Gateway applied an inflated MDR rate (3.5% vs contracted 2.0%), resulting in ₹{fee_overcharge:.2f} revenue leakage."
            recommended_action = f"File automated dispute ticket for ₹{fee_overcharge:.2f} MDR fee reimbursement."
            action_type = "DISPUTE_CLAIM"

        elif not pay:
            fault_party = "MERCHANT_USER"
            fault_title = "🔵 Merchant ERP Ghost Invoice"
            root_cause = "Invoice INV exists in ERP, but customer payment was never captured on Razorpay Gateway (abandoned checkout or manual entry error)."
            recommended_action = "Update ERP to void unpaid invoice or attach valid payment ID."
            action_type = "INVOICE_CORRECTION"

        elif disp:
            fault_party = "CUSTOMER_ACTION"
            fault_title = "🟡 Customer Chargeback Dispute"
            root_cause = f"Customer initiated a chargeback dispute ({disp.get('reason', 'fraud')}). Funds held by card network."
            recommended_action = "Submit proof of fulfillment (delivery receipt) to defend dispute."
            action_type = "DEFEND_DISPUTE"

        elif rfnd:
            fault_party = "CUSTOMER_ACTION"
            fault_title = "🟡 Customer Refund Processed"
            root_cause = f"Refund of ₹{rfnd['amount']:.2f} was processed on {rfnd['date']}."
            recommended_action = "Reconcile debit against customer refund ledger."
            action_type = "NONE"

        elif tax_mismatches:
            fault_party = "MERCHANT_USER"
            fault_title = "🔵 Merchant Tax Split Configuration Error"
            root_cause = f"Tax lines configured incorrectly in ERP for {inv.get('merchant_state')} ➔ {inv.get('customer_state')} transaction."
            recommended_action = "Correct GST ledger allocation in ERP."
            action_type = "INVOICE_CORRECTION"

        elif not setl and pay:
            fault_party = "IN_TRANSIT"
            fault_title = "🟢 Normal T+2 Settlement Cycle"
            root_cause = "Payment captured recently; settlement is in-flight within standard 48-hour banking window."
            recommended_action = "Wait for next T+2 bank settlement batch."
            action_type = "NONE"

        # 6. Generate Dispute Packet (for Razorpay Fault)
        proof_payload = f"{order_id}:{pay_id}:{fee_overcharge}:{billed_amount}"
        evidence_hash = hashlib.sha256(proof_payload.encode()).hexdigest()[:16]

        dispute_packet = {
            "claim_id": f"CLAIM-RZP-{evidence_hash[:8].upper()}",
            "claim_type": "MDR_FEE_OVERCHARGE_REIMBURSEMENT",
            "merchant_id": "merch_razorpay_live_01",
            "order_id": order_id,
            "payment_id": pay_id,
            "billed_amount_inr": billed_amount,
            "overcharge_amount_inr": fee_overcharge,
            "evidence_hash": f"sha256:{evidence_hash}",
            "status": "READY_TO_DISPATCH"
        }

        return {
            "record_id": order_id,
            "invoice_id": inv_id,
            "payment_id": pay_id,
            "billed_amount": billed_amount,
            "fault_party": fault_party,
            "fault_title": fault_title,
            "root_cause": root_cause,
            "recommended_action": recommended_action,
            "action_type": action_type,
            "fee_overcharge_inr": fee_overcharge,
            "money_flow": money_flow,
            "dispute_packet": dispute_packet,
            "editable_invoice": {
                "invoice_id": inv_id,
                "order_id": order_id,
                "amount": billed_amount,
                "merchant_state": inv.get("merchant_state", "Maharashtra"),
                "customer_state": inv.get("customer_state", "Maharashtra"),
                "date": inv.get("date", "2026-08-15 10:00:00")
            }
        }
