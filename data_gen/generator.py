import json
import os
import random
from datetime import datetime, timedelta

def generate_synthetic_dataset(output_dir="data", count=65, seed=42):
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    invoices = []
    payments = []
    settlements = []
    bank_entries = []
    refunds = []
    disputes = []
    ground_truth = {}

    base_date = datetime(2026, 8, 15, 10, 0, 0)
    
    # Contracted MDR rate = 2.0% (0.02), GST on MDR = 18% (0.18) -> Effective rate = 2.36% (0.0236)
    CONTRACTED_MDR_RATE = 0.02
    GST_RATE = 0.18
    TDS_RATE = 0.01
    MERCHANT_STATE = "Maharashtra"
    OTHER_STATES = ["Karnataka", "Delhi", "Tamil Nadu", "Gujarat", "Telangana"]

    # We will define standard categories:
    # 1. CLEAN_MATCH (45 records)
    # 2. BATCH_SETTLEMENT (6 records grouped into 2 bank UTRs)
    # 3. SETTLEMENT_IN_TRANSIT (4 records within last 2 days)
    # 4. PARTIAL_REFUND (3 records)
    # 5. FULL_REFUND (2 records)
    # 6. CHARGEBACK_HOLD (2 records)
    # 7. FEE_MISCALCULATION / LEAKAGE (2 records)
    # 8. DELIBERATELY_AMBIGUOUS (1 record)
    
    # Track batch settlement groupings
    batch_1_settlements = []
    batch_2_settlements = []

    for i in range(1, count + 1):
        order_id = f"ord_{1000 + i}"
        inv_id = f"INV-2026-{1000 + i}"
        cust_id = f"cust_{random.randint(100, 999)}"
        amount = round(random.choice([499, 799, 999, 1299, 1499, 1999, 2499, 3999, 4999, 8999]), 2)
        
        # Stagger transaction dates over 15 days (Aug 15 to Aug 30, 2026)
        day_offset = (i % 14)
        hour_offset = random.randint(1, 12)
        tx_date = base_date + timedelta(days=day_offset, hours=hour_offset)
        
        # Standard fee calculation
        expected_mdr = round(amount * CONTRACTED_MDR_RATE, 2)
        expected_gst = round(expected_mdr * GST_RATE, 2)
        total_fee = round(expected_mdr + expected_gst, 2)
        net_amount = round(amount - total_fee, 2)

        # Indian GST & TDS Tax Breakdown
        # Even indices = Intra-State (Maharashtra -> Maharashtra)
        # Odd indices = Inter-State (Maharashtra -> Other States)
        is_intra_state = (i % 2 == 0)
        customer_state = MERCHANT_STATE if is_intra_state else OTHER_STATES[i % len(OTHER_STATES)]
        
        expected_tds = round(amount * TDS_RATE, 2)
        tds_deducted = expected_tds
        
        if is_intra_state:
            tax_lines = [
                {"type": "CGST", "rate": 0.09, "amount": round(amount * 0.09, 2)},
                {"type": "SGST", "rate": 0.09, "amount": round(amount * 0.09, 2)}
            ]
        else:
            tax_lines = [
                {"type": "IGST", "rate": 0.18, "amount": round(amount * 0.18, 2)}
            ]

        tax_anomaly_type = "CLEAN"
        tax_leakage = 0.0

        # Plant 3 specific tax anomalies on records 40, 41, 42
        if i == 40:
            # Planted Anomaly 1: Wrong GST Split Type
            # Inter-state sale (Maharashtra -> Karnataka) mistakenly billed with CGST + SGST instead of IGST
            customer_state = "Karnataka"
            tax_lines = [
                {"type": "CGST", "rate": 0.09, "amount": round(amount * 0.09, 2)},
                {"type": "SGST", "rate": 0.09, "amount": round(amount * 0.09, 2)}
            ]
            tax_anomaly_type = "WRONG_GST_SPLIT"
            tax_leakage = 0.0 # Compliance violation (wrong tax ledger allocation)

        elif i == 41:
            # Planted Anomaly 2: Incorrect GST Rate (12% charged instead of standard 18%)
            customer_state = "Delhi"
            actual_tax = round(amount * 0.12, 2)
            expected_tax = round(amount * 0.18, 2)
            tax_lines = [
                {"type": "IGST", "rate": 0.12, "amount": actual_tax}
            ]
            tax_anomaly_type = "GST_RATE_MISMATCH"
            tax_leakage = round(expected_tax - actual_tax, 2)

        elif i == 42:
            # Planted Anomaly 3: Missing Section 194-O TDS Deduction (0% instead of 1%)
            tds_deducted = 0.0
            tax_anomaly_type = "TDS_MISSING"
            tax_leakage = expected_tds

        # Invoice record (extended with tax fields)
        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": amount,
            "date": tx_date.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_id": cust_id,
            "merchant_state": MERCHANT_STATE,
            "customer_state": customer_state,
            "tax_lines": tax_lines,
            "tds_deducted": tds_deducted
        })

        pay_id = f"pay_{os.urandom(4).hex()}"

        # Assign scenario based on index
        if i <= 45:
            # 1. Clean 3-Way Match
            payments.append({
                "pay_id": pay_id,
                "order_id": order_id,
                "amount_captured": amount,
                "mdr_fee": expected_mdr,
                "gst_on_fee": expected_gst,
                "status": "captured",
                "date": tx_date.strftime("%Y-%m-%d %H:%M:%S")
            })

            settlement_id = f"setl_{os.urandom(4).hex()}"
            settle_date = tx_date + timedelta(days=2) # T+2 settlement
            batch_id = f"batch_{settle_date.strftime('%Y%m%d')}_{i}"
            utr = f"UTR{random.randint(100000000000, 999999999999)}"

            settlements.append({
                "settlement_id": settlement_id,
                "pay_id": pay_id,
                "net_amount": net_amount,
                "batch_id": batch_id,
                "date": settle_date.strftime("%Y-%m-%d %H:%M:%S")
            })

            bank_entries.append({
                "utr": utr,
                "batch_id": batch_id,
                "amount_credited": net_amount,
                "date": settle_date.strftime("%Y-%m-%d %H:%M:%S")
            })

            ground_truth[order_id] = {
                "label": "MATCHED",
                "reason": "Clean 3-way reconciliation verified across ERP, Razorpay, and Bank UTR.",
                "discrepancy_amount": 0.0,
                "tax_audit": {
                    "status": tax_anomaly_type,
                    "tax_leakage": tax_leakage
                }
            }

        elif 46 <= i <= 48:
            # 2. Batch settlement 1 (3 transactions bundled into 1 Bank credit)
            payments.append({
                "pay_id": pay_id,
                "order_id": order_id,
                "amount_captured": amount,
                "mdr_fee": expected_mdr,
                "gst_on_fee": expected_gst,
                "status": "captured",
                "date": tx_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            settlement_id = f"setl_{os.urandom(4).hex()}"
            settle_date = tx_date + timedelta(days=2)
            batch_id = "batch_20260828_GRP1"
            
            settlements.append({
                "settlement_id": settlement_id,
                "pay_id": pay_id,
                "net_amount": net_amount,
                "batch_id": batch_id,
                "date": settle_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            batch_1_settlements.append((net_amount, settle_date))
            ground_truth[order_id] = {
                "label": "MATCHED_BATCH",
                "reason": "Many-to-one batch settlement reconciled via subset-sum matching.",
                "discrepancy_amount": 0.0,
                "tax_audit": {
                    "status": "CLEAN",
                    "tax_leakage": 0.0
                }
            }

        elif 49 <= i <= 51:
            # 2. Batch settlement 2 (3 transactions bundled into 1 Bank credit)
            payments.append({
                "pay_id": pay_id,
                "order_id": order_id,
                "amount_captured": amount,
                "mdr_fee": expected_mdr,
                "gst_on_fee": expected_gst,
                "status": "captured",
                "date": tx_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            settlement_id = f"setl_{os.urandom(4).hex()}"
            settle_date = tx_date + timedelta(days=2)
            batch_id = "batch_20260829_GRP2"
            
            settlements.append({
                "settlement_id": settlement_id,
                "pay_id": pay_id,
                "net_amount": net_amount,
                "batch_id": batch_id,
                "date": settle_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            batch_2_settlements.append((net_amount, settle_date))
            ground_truth[order_id] = {
                "label": "MATCHED_BATCH",
                "reason": "Many-to-one batch settlement reconciled via subset-sum matching.",
                "discrepancy_amount": 0.0,
                "tax_audit": {
                    "status": "CLEAN",
                    "tax_leakage": 0.0
                }
            }

        elif 52 <= i <= 55:
            # 3. Settlement In-Transit (Recent transactions within T+2 window, not yet paid to bank)
            recent_date = datetime(2026, 8, 30, 14, 30) - timedelta(hours=random.randint(2, 28))
            invoices[-1]["date"] = recent_date.strftime("%Y-%m-%d %H:%M:%S")
            payments.append({
                "pay_id": pay_id,
                "order_id": order_id,
                "amount_captured": amount,
                "mdr_fee": expected_mdr,
                "gst_on_fee": expected_gst,
                "status": "captured",
                "date": recent_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            # No settlement or bank entry yet!
            ground_truth[order_id] = {
                "label": "SETTLEMENT_IN_TRANSIT",
                "reason": "Transaction captured within last 48h; settlement is in-transit per standard T+2 bank cycle.",
                "discrepancy_amount": net_amount,
                "tax_audit": {
                    "status": "CLEAN",
                    "tax_leakage": 0.0
                }
            }

        elif 56 <= i <= 58:
            # 4. Partial Refund
            refund_amount = round(amount * 0.5, 2)
            payments.append({
                "pay_id": pay_id,
                "order_id": order_id,
                "amount_captured": amount,
                "mdr_fee": expected_mdr,
                "gst_on_fee": expected_gst,
                "status": "captured",
                "date": tx_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            refund_id = f"rfnd_{os.urandom(4).hex()}"
            refund_date = tx_date + timedelta(days=1)
            refunds.append({
                "refund_id": refund_id,
                "pay_id": pay_id,
                "amount": refund_amount,
                "date": refund_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            settlement_id = f"setl_{os.urandom(4).hex()}"
            adjusted_net = round(net_amount - refund_amount, 2)
            settle_date = tx_date + timedelta(days=2)
            batch_id = f"batch_{settle_date.strftime('%Y%m%d')}_{i}"
            utr = f"UTR{random.randint(100000000000, 999999999999)}"

            settlements.append({
                "settlement_id": settlement_id,
                "pay_id": pay_id,
                "net_amount": adjusted_net,
                "batch_id": batch_id,
                "date": settle_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            bank_entries.append({
                "utr": utr,
                "batch_id": batch_id,
                "amount_credited": adjusted_net,
                "date": settle_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            ground_truth[order_id] = {
                "label": "PARTIAL_REFUND",
                "reason": f"Partial refund of ₹{refund_amount} deducted from settlement amount.",
                "discrepancy_amount": refund_amount,
                "tax_audit": {
                    "status": "CLEAN",
                    "tax_leakage": 0.0
                }
            }

        elif 59 <= i <= 60:
            # 5. Full Refund
            payments.append({
                "pay_id": pay_id,
                "order_id": order_id,
                "amount_captured": amount,
                "mdr_fee": expected_mdr,
                "gst_on_fee": expected_gst,
                "status": "refunded",
                "date": tx_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            refund_id = f"rfnd_{os.urandom(4).hex()}"
            refund_date = tx_date + timedelta(days=1)
            refunds.append({
                "refund_id": refund_id,
                "pay_id": pay_id,
                "amount": amount,
                "date": refund_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            # No bank credit because 100% refunded
            ground_truth[order_id] = {
                "label": "FULL_REFUND",
                "reason": f"Full refund of ₹{amount} processed; zero settlement deposited.",
                "discrepancy_amount": amount,
                "tax_audit": {
                    "status": "CLEAN",
                    "tax_leakage": 0.0
                }
            }

        elif 61 <= i <= 62:
            # 6. Chargeback / Dispute Hold
            payments.append({
                "pay_id": pay_id,
                "order_id": order_id,
                "amount_captured": amount,
                "mdr_fee": expected_mdr,
                "gst_on_fee": expected_gst,
                "status": "disputed",
                "date": tx_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            dispute_id = f"disp_{os.urandom(4).hex()}"
            dispute_date = tx_date + timedelta(days=1)
            disputes.append({
                "dispute_id": dispute_id,
                "pay_id": pay_id,
                "status": "under_review",
                "reason": "fraudulent_claim",
                "date": dispute_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            # Bank payout frozen
            ground_truth[order_id] = {
                "label": "CHARGEBACK_HOLD",
                "reason": f"Funds of ₹{amount} held by card network due to active chargeback dispute {dispute_id}.",
                "discrepancy_amount": amount,
                "tax_audit": {
                    "status": "CLEAN",
                    "tax_leakage": 0.0
                }
            }

        elif 63 <= i <= 64:
            # 7. Fee Miscalculation / Overcharge (MDR charged at 3.5% instead of contracted 2.0%)
            inflated_mdr = round(amount * 0.035, 2)
            inflated_gst = round(inflated_mdr * GST_RATE, 2)
            inflated_total_fee = round(inflated_mdr + inflated_gst, 2)
            overcharged_net = round(amount - inflated_total_fee, 2)
            fee_leakage = round(inflated_total_fee - total_fee, 2)

            payments.append({
                "pay_id": pay_id,
                "order_id": order_id,
                "amount_captured": amount,
                "mdr_fee": inflated_mdr,
                "gst_on_fee": inflated_gst,
                "status": "captured",
                "date": tx_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            settlement_id = f"setl_{os.urandom(4).hex()}"
            settle_date = tx_date + timedelta(days=2)
            batch_id = f"batch_{settle_date.strftime('%Y%m%d')}_{i}"
            utr = f"UTR{random.randint(100000000000, 999999999999)}"

            settlements.append({
                "settlement_id": settlement_id,
                "pay_id": pay_id,
                "net_amount": overcharged_net,
                "batch_id": batch_id,
                "date": settle_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            bank_entries.append({
                "utr": utr,
                "batch_id": batch_id,
                "amount_credited": overcharged_net,
                "date": settle_date.strftime("%Y-%m-%d %H:%M:%S")
            })
            ground_truth[order_id] = {
                "label": "FEE_MISCALCULATION",
                "reason": f"MDR rate charged at 3.5% instead of contracted 2.0%. Fee leakage: ₹{fee_leakage}.",
                "discrepancy_amount": fee_leakage,
                "tax_audit": {
                    "status": "CLEAN",
                    "tax_leakage": 0.0
                }
            }

        elif i == 65:
            # 8. Deliberately Ambiguous (Missing Gateway Record / Ghost Entry for Failure Recovery Demo)
            # Invoice exists in ERP, but payment record is missing from Gateway export
            ground_truth[order_id] = {
                "label": "UNRESOLVED_REQUIRES_INVESTIGATION",
                "reason": "Ghost transaction: Invoice logged in ERP but absent from Razorpay Gateway settlement file.",
                "discrepancy_amount": amount,
                "tax_audit": {
                    "status": "CLEAN",
                    "tax_leakage": 0.0
                }
            }

    # Add the 2 bundled bank entries for the many-to-one batch groups
    if batch_1_settlements:
        sum_1 = round(sum(item[0] for item in batch_1_settlements), 2)
        bank_entries.append({
            "utr": f"UTR{random.randint(100000000000, 999999999999)}",
            "batch_id": "batch_20260828_GRP1",
            "amount_credited": sum_1,
            "date": batch_1_settlements[0][1].strftime("%Y-%m-%d %H:%M:%S")
        })

    if batch_2_settlements:
        sum_2 = round(sum(item[0] for item in batch_2_settlements), 2)
        bank_entries.append({
            "utr": f"UTR{random.randint(100000000000, 999999999999)}",
            "batch_id": "batch_20260829_GRP2",
            "amount_credited": sum_2,
            "date": batch_2_settlements[0][1].strftime("%Y-%m-%d %H:%M:%S")
        })

    # Save all files to output_dir
    files_to_save = {
        "invoices.json": invoices,
        "payments.json": payments,
        "settlements.json": settlements,
        "bank_entries.json": bank_entries,
        "refunds.json": refunds,
        "disputes.json": disputes,
        "ground_truth.json": ground_truth
    }

    for filename, data in files_to_save.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Generated {filepath} ({len(data) if isinstance(data, list) else len(data)} records)")

    print("\nDataset Generation Complete! 65 records generated with known ground truth.")

if __name__ == "__main__":
    generate_synthetic_dataset()
