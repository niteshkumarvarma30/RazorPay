import json
import numpy as np
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    """
    Phase 4: ML Anomaly Detector (Isolation Forest)
    Flags multi-dimensional statistical outliers in transactions (e.g. unusual fee-to-amount ratios or outlier transaction volumes).
    """
    def __init__(self, contamination=0.08):
        self.model = IsolationForest(contamination=contamination, random_state=42)

    def detect_anomalies(self, payments_file="data/payments.json"):
        with open(payments_file, "r") as f:
            payments = json.load(f)

        if len(payments) < 10:
            return {"anomalies": []}

        # Feature matrix: [amount, total_fee, fee_ratio]
        features = []
        for p in payments:
            amt = p["amount_captured"]
            fee = p["mdr_fee"] + p["gst_on_fee"]
            ratio = (fee / amt) if amt > 0 else 0
            features.append([amt, fee, ratio])

        X = np.array(features)
        preds = self.model.fit_predict(X)
        scores = self.model.decision_function(X)

        anomalies = []
        for i, (pred, score) in enumerate(zip(preds, scores)):
            if pred == -1: # Outlier flagged
                p = payments[i]
                anomalies.append({
                    "pay_id": p["pay_id"],
                    "order_id": p["order_id"],
                    "amount": p["amount_captured"],
                    "fee": round(p["mdr_fee"] + p["gst_on_fee"], 2),
                    "fee_ratio_pct": round(((p["mdr_fee"] + p["gst_on_fee"]) / p["amount_captured"]) * 100, 2),
                    "anomaly_score": round(float(score), 4),
                    "reason": "Statistically abnormal fee-to-volume ratio or transaction size."
                })

        return {
            "total_analyzed": len(payments),
            "anomalies_detected_count": len(anomalies),
            "anomalies": anomalies
        }
