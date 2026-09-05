import json

class FeeAuditor:
    """
    Phase 3: Fee Audit Layer & Revenue Leakage Detector
    Recomputes contracted MDR% + 18% GST fee per transaction, catches gateway overcharges.
    """
    def __init__(self, contracted_mdr_rate=0.02, gst_rate=0.18, tolerance=0.50):
        self.mdr_rate = contracted_mdr_rate
        self.gst_rate = gst_rate
        self.tolerance = tolerance

    def audit_payments(self, payments_file="data/payments.json"):
        with open(payments_file, "r") as f:
            payments = json.load(f)

        flagged_transactions = []
        total_leakage_inr = 0.0

        for pay in payments:
            amount = pay["amount_captured"]
            actual_mdr = pay["mdr_fee"]
            actual_gst = pay["gst_on_fee"]
            actual_total_fee = round(actual_mdr + actual_gst, 2)

            expected_mdr = round(amount * self.mdr_rate, 2)
            expected_gst = round(expected_mdr * self.gst_rate, 2)
            expected_total_fee = round(expected_mdr + expected_gst, 2)

            delta = round(actual_total_fee - expected_total_fee, 2)

            if delta > self.tolerance:
                total_leakage_inr += delta
                flagged_transactions.append({
                    "pay_id": pay["pay_id"],
                    "order_id": pay["order_id"],
                    "amount_captured": amount,
                    "actual_fee_charged": actual_total_fee,
                    "contracted_expected_fee": expected_total_fee,
                    "overcharge_leakage_inr": delta,
                    "effective_mdr_charged_pct": round((actual_mdr / amount) * 100, 2),
                    "contracted_mdr_pct": round(self.mdr_rate * 100, 2),
                    "date": pay["date"]
                })

        return {
            "total_leakage_inr": round(total_leakage_inr, 2),
            "flagged_count": len(flagged_transactions),
            "flagged_transactions": flagged_transactions,
            "contracted_terms": {
                "mdr_rate": f"{self.mdr_rate * 100}%",
                "gst_rate": f"{self.gst_rate * 100}%"
            }
        }
