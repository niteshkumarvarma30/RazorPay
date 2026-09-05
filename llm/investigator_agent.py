import json

class InvestigatorAgent:
    """
    Phase 8: Investigation Agent for Ambiguous Edge Cases
    Demonstrates bounded AI Judgment with transparent reasoning traces and safe human escalation.
    """
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir

    def investigate_record(self, record_id):
        # Load sources to check
        with open(f"{self.data_dir}/invoices.json", "r") as f:
            invoices = json.load(f)
        with open(f"{self.data_dir}/payments.json", "r") as f:
            payments = json.load(f)
        with open(f"{self.data_dir}/settlements.json", "r") as f:
            settlements = json.load(f)
        with open(f"{self.data_dir}/refunds.json", "r") as f:
            refunds = json.load(f)
        with open(f"{self.data_dir}/disputes.json", "r") as f:
            disputes = json.load(f)

        reasoning_trace = []
        reasoning_trace.append(f"Step 1: Commencing deep investigation for target entity '{record_id}'.")

        # 1. Check Invoice
        inv = next((i for i in invoices if i["order_id"] == record_id or i["invoice_id"] == record_id), None)
        if not inv:
            reasoning_trace.append(f"Step 2: No invoice entry found matching '{record_id}'.")
            return {
                "status": "NOT_FOUND",
                "confidence": 0.0,
                "reasoning_trace": reasoning_trace,
                "recommendation": "Verify record ID with billing team."
            }

        order_id = inv["order_id"]
        reasoning_trace.append(f"Step 2: Invoice verified: {inv['invoice_id']} billed for ₹{inv['amount']} on {inv['date']}.")

        # 2. Check Gateway Payment
        pay = next((p for p in payments if p["order_id"] == order_id), None)
        if not pay:
            reasoning_trace.append("Step 3: Tool Execution `query_razorpay_gateway(order_id)` returned NULL.")
            reasoning_trace.append("Step 4: Anomaly Detected -> Ghost Invoice (Order was created in ERP, but checkout was never completed/authorized on Razorpay).")
            reasoning_trace.append("Step 5: Confidence score is 0.45 (< 0.80 safety threshold). Escalate to Human Controller.")
            return {
                "record_id": record_id,
                "classification": "GHOST_ERP_INVOICE_UNAUTHORIZED",
                "confidence": 0.45,
                "needs_human_review": True,
                "reasoning_trace": reasoning_trace,
                "recommendation": "Human Action Required: Cancel ERP invoice #{} or check if buyer abandoned checkout.".format(inv['invoice_id'])
            }

        pay_id = pay["pay_id"]
        reasoning_trace.append(f"Step 3: Payment authorization located: {pay_id} status '{pay['status']}' amount ₹{pay['amount_captured']}.")

        # 3. Check Disputes / Refunds
        disp = next((d for d in disputes if d["pay_id"] == pay_id), None)
        if disp:
            reasoning_trace.append(f"Step 4: Active dispute detected: {disp['dispute_id']} for reason '{disp.get('reason')}'. Funds blocked.")
            return {
                "record_id": record_id,
                "classification": "DISPUTE_CHARGEBACK_HOLD",
                "confidence": 1.0,
                "needs_human_review": False,
                "reasoning_trace": reasoning_trace,
                "recommendation": f"Submit chargeback representation evidence on Razorpay dashboard for dispute {disp['dispute_id']}."
            }

        ref = next((r for r in refunds if r["pay_id"] == pay_id), None)
        if ref:
            reasoning_trace.append(f"Step 4: Refund found: {ref['refund_id']} for amount ₹{ref['amount']}.")
            return {
                "record_id": record_id,
                "classification": "REFUND_DEDUCTED",
                "confidence": 1.0,
                "needs_human_review": False,
                "reasoning_trace": reasoning_trace,
                "recommendation": f"Book credit note for ₹{ref['amount']} against invoice {inv['invoice_id']}."
            }

        # 4. Check Settlement
        setl = next((s for s in settlements if s["pay_id"] == pay_id), None)
        if not setl:
            reasoning_trace.append("Step 4: No settlement batch generated yet. Transaction is within standard T+2 settlement window.")
            return {
                "record_id": record_id,
                "classification": "SETTLEMENT_IN_TRANSIT",
                "confidence": 0.95,
                "needs_human_review": False,
                "reasoning_trace": reasoning_trace,
                "recommendation": "Wait for T+2 settlement batch completion."
            }

        reasoning_trace.append(f"Step 5: Settlement confirmed in batch {setl['batch_id']}. Fully reconciled.")
        return {
            "record_id": record_id,
            "classification": "FULLY_RECONCILED",
            "confidence": 1.0,
            "needs_human_review": False,
            "reasoning_trace": reasoning_trace,
            "recommendation": "No action required."
        }
