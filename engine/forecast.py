import json
from datetime import datetime, timedelta

class CashflowForecaster:
    """
    Phase 5: Deterministic Cashflow & Liquidity Forecaster
    Projects upcoming daily bank payouts based on in-flight captures, T+2 settlement schedule, and fee/refund rates.
    """
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir

    def generate_forecast(self, days_ahead=7):
        with open(f"{self.data_dir}/payments.json", "r") as f:
            payments = json.load(f)
        with open(f"{self.data_dir}/settlements.json", "r") as f:
            settlements = json.load(f)
        with open(f"{self.data_dir}/refunds.json", "r") as f:
            refunds = json.load(f)

        settled_pay_ids = set(s["pay_id"] for s in settlements)
        
        # Calculate historical refund rate
        total_captured = sum(p["amount_captured"] for p in payments)
        total_refunded = sum(r["amount"] for r in refunds)
        refund_rate = (total_refunded / total_captured) if total_captured > 0 else 0.02

        # Find in-flight payments (captured but not settled)
        in_flight = [p for p in payments if p["pay_id"] not in settled_pay_ids and p["status"] == "captured"]

        # Project by target settlement date (T+2 business days)
        daily_projection = {}
        contributing_orders = {}

        for p in in_flight:
            p_date = datetime.strptime(p["date"], "%Y-%m-%d %H:%M:%S")
            settle_date = (p_date + timedelta(days=2)).strftime("%Y-%m-%d")
            
            gross = p["amount_captured"]
            fee = round(p["mdr_fee"] + p["gst_on_fee"], 2)
            expected_net = round(gross - fee, 2)

            daily_projection[settle_date] = daily_projection.get(settle_date, 0.0) + expected_net
            contributing_orders.setdefault(settle_date, []).append({
                "order_id": p["order_id"],
                "pay_id": p["pay_id"],
                "gross_inr": gross,
                "fee_inr": fee,
                "projected_net_inr": expected_net
            })

        forecast_timeline = []
        total_projected_inr = 0.0

        for s_date, amount in sorted(daily_projection.items()):
            net_after_refund_reserve = round(amount * (1.0 - (refund_rate * 0.5)), 2)
            total_projected_inr += net_after_refund_reserve
            forecast_timeline.append({
                "settlement_date": s_date,
                "gross_projected_inr": round(amount, 2),
                "risk_adjusted_net_inr": net_after_refund_reserve,
                "order_count": len(contributing_orders[s_date]),
                "orders": contributing_orders[s_date]
            })

        return {
            "total_in_flight_orders": len(in_flight),
            "total_projected_bank_deposit_inr": round(total_projected_inr, 2),
            "historical_refund_rate_pct": round(refund_rate * 100, 2),
            "forecast_timeline": forecast_timeline
        }
