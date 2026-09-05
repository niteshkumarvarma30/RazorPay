import json

class TaxAuditor:
    """
    Tax-Line (GST & Section 194-O TDS) Auditor
    Audits invoice line items against Indian GST regulations:
    - Intra-State: Split as CGST (9%) + SGST (9%)
    - Inter-State: Charged as IGST (18%)
    - Section 194-O: 1% TDS on gross e-commerce sales value
    """
    def __init__(self, standard_gst_rate=0.18, tds_rate=0.01, merchant_state="Maharashtra", tolerance=0.50):
        self.standard_gst_rate = standard_gst_rate
        self.tds_rate = tds_rate
        self.merchant_state = merchant_state
        self.tolerance = tolerance

    def audit_tax_lines(self, invoices_file="data/invoices.json", custom_invoices=None):
        if custom_invoices is not None:
            invoices = custom_invoices
        else:
            with open(invoices_file, "r") as f:
                invoices = json.load(f)

        exceptions = []
        total_gst_leakage_inr = 0.0
        total_tds_leakage_inr = 0.0

        for inv in invoices:
            order_id = inv["order_id"]
            inv_id = inv["invoice_id"]
            amount = inv["amount"]
            m_state = inv.get("merchant_state", self.merchant_state)
            c_state = inv.get("customer_state", self.merchant_state)
            actual_tax_lines = inv.get("tax_lines", [])
            actual_tds = inv.get("tds_deducted", 0.0)

            is_intra = (m_state.lower() == c_state.lower())

            # 1. Compute Expected GST Breakdown
            expected_tax_lines = []
            expected_total_gst = round(amount * self.standard_gst_rate, 2)

            if is_intra:
                cgst = round(amount * (self.standard_gst_rate / 2.0), 2)
                sgst = round(amount * (self.standard_gst_rate / 2.0), 2)
                expected_tax_lines = [
                    {"type": "CGST", "rate": self.standard_gst_rate / 2.0, "amount": cgst},
                    {"type": "SGST", "rate": self.standard_gst_rate / 2.0, "amount": sgst}
                ]
            else:
                igst = expected_total_gst
                expected_tax_lines = [
                    {"type": "IGST", "rate": self.standard_gst_rate, "amount": igst}
                ]

            # 2. Compute Expected TDS (Section 194-O)
            expected_tds = round(amount * self.tds_rate, 2)

            # 3. Analyze Actual Tax Lines
            actual_types = [t.get("type", "").upper() for t in actual_tax_lines]
            actual_total_gst = round(sum(t.get("amount", 0.0) for t in actual_tax_lines), 2)

            is_flagged = False
            mismatch_types = []
            tax_leakage = 0.0
            tds_leakage = 0.0
            recommendation = []

            # Check Split Type
            if is_intra and "IGST" in actual_types:
                is_flagged = True
                mismatch_types.append("WRONG_GST_SPLIT")
                recommendation.append("Reallocate IGST ledger to CGST (9%) + SGST (9%) for intra-state sale.")
            elif (not is_intra) and ("CGST" in actual_types or "SGST" in actual_types):
                is_flagged = True
                mismatch_types.append("WRONG_GST_SPLIT")
                recommendation.append("Reallocate CGST/SGST ledger to IGST (18%) for inter-state sale.")

            # Check Rate Mismatch / Undercollection
            gst_delta = round(expected_total_gst - actual_total_gst, 2)
            if gst_delta > self.tolerance:
                is_flagged = True
                mismatch_types.append("GST_RATE_MISMATCH")
                tax_leakage += gst_delta
                recommendation.append(f"Undercollected GST of ₹{gst_delta} (applied lower rate vs standard 18%).")

            # Check TDS Missing / Under-deducted
            tds_delta = round(expected_tds - actual_tds, 2)
            if tds_delta > self.tolerance:
                is_flagged = True
                mismatch_types.append("TDS_194O_MISSING")
                tds_leakage += tds_delta
                recommendation.append(f"Section 194-O TDS missing: Deduct 1% (₹{tds_delta}) on gross order value.")

            if is_flagged:
                total_gst_leakage_inr += tax_leakage
                total_tds_leakage_inr += tds_leakage
                exceptions.append({
                    "order_id": order_id,
                    "invoice_id": inv_id,
                    "amount_billed": amount,
                    "merchant_state": m_state,
                    "customer_state": c_state,
                    "transaction_type": "Intra-State" if is_intra else "Inter-State",
                    "mismatch_categories": mismatch_types,
                    "actual_tax_lines": actual_tax_lines,
                    "expected_tax_lines": expected_tax_lines,
                    "actual_total_gst": actual_total_gst,
                    "expected_total_gst": expected_total_gst,
                    "gst_leakage_inr": tax_leakage,
                    "actual_tds": actual_tds,
                    "expected_tds": expected_tds,
                    "tds_leakage_inr": tds_leakage,
                    "action_required": " | ".join(recommendation)
                })

        return {
            "total_gst_leakage_inr": round(total_gst_leakage_inr, 2),
            "total_tds_leakage_inr": round(total_tds_leakage_inr, 2),
            "flagged_count": len(exceptions),
            "tax_exceptions": exceptions,
            "compliance_standards": {
                "standard_gst_rate": f"{self.standard_gst_rate * 100}%",
                "tds_194o_rate": f"{self.tds_rate * 100}%",
                "default_merchant_state": self.merchant_state
            }
        }
