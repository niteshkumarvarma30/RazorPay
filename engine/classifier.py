class ExceptionClassifier:
    """
    Phase 2: Rule-based Exception Classifier
    Classifies unmatched records into actionable financial categories with confidence scores.
    """
    def __init__(self):
        pass

    def classify_exceptions(self, unmatched_records):
        classified = []

        for rec in unmatched_records:
            status = rec.get("status")
            amount = rec.get("discrepancy_amount", rec.get("amount_billed", 0))
            evidence_ids = rec.get("evidence_ids", [])
            order_id = rec.get("order_id")

            if status == "FULL_REFUND":
                classified.append({
                    "order_id": order_id,
                    "invoice_id": rec.get("invoice_id"),
                    "category": "FULL_REFUND_PROCESSED",
                    "confidence": 1.0,
                    "discrepancy_inr": amount,
                    "action_required": "Auto-adjust ledger: Debit Sales Returns, Credit Accounts Receivable.",
                    "explanation": rec.get("reason"),
                    "evidence_ids": evidence_ids
                })

            elif status == "PARTIAL_REFUND":
                classified.append({
                    "order_id": order_id,
                    "invoice_id": rec.get("invoice_id"),
                    "category": "PARTIAL_REFUND_DEDUCTION",
                    "confidence": 1.0,
                    "discrepancy_inr": amount,
                    "action_required": "Auto-adjust ledger: Book partial credit note against original invoice.",
                    "explanation": rec.get("reason"),
                    "evidence_ids": evidence_ids
                })

            elif status == "CHARGEBACK_HOLD":
                classified.append({
                    "order_id": order_id,
                    "invoice_id": rec.get("invoice_id"),
                    "category": "DISPUTE_CHARGEBACK_HOLD",
                    "confidence": 1.0,
                    "discrepancy_inr": amount,
                    "action_required": "Escalate to Risk Ops: Upload proof of delivery to Razorpay Dispute Dashboard within 5 business days.",
                    "explanation": rec.get("reason"),
                    "evidence_ids": evidence_ids
                })

            elif status == "SETTLEMENT_IN_TRANSIT":
                classified.append({
                    "order_id": order_id,
                    "invoice_id": rec.get("invoice_id"),
                    "category": "SETTLEMENT_IN_TRANSIT",
                    "confidence": 0.95,
                    "discrepancy_inr": amount,
                    "action_required": "No action needed: Auto-reconciliation scheduled for next T+2 batch settlement run.",
                    "explanation": rec.get("reason"),
                    "evidence_ids": evidence_ids
                })

            elif status == "MISSING_PAYMENT_RECORD":
                classified.append({
                    "order_id": order_id,
                    "invoice_id": rec.get("invoice_id"),
                    "category": "UNRESOLVED_REQUIRES_INVESTIGATION",
                    "confidence": 0.50,
                    "discrepancy_inr": amount,
                    "action_required": "Human Review Required: Invoice logged in ERP without corresponding gateway authorization.",
                    "explanation": rec.get("reason"),
                    "evidence_ids": evidence_ids
                })

            else:
                classified.append({
                    "order_id": order_id,
                    "invoice_id": rec.get("invoice_id"),
                    "category": "GENERAL_UNMATCHED_VARIANCE",
                    "confidence": 0.70,
                    "discrepancy_inr": amount,
                    "action_required": "Finance audit required.",
                    "explanation": rec.get("reason", "Unknown discrepancy"),
                    "evidence_ids": evidence_ids
                })

        return classified
