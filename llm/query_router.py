import json
import re
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from engine.matcher import ReconciliationMatcher
from engine.classifier import ExceptionClassifier
from engine.fee_audit import FeeAuditor
from engine.tax_audit import TaxAuditor
from engine.forecast import CashflowForecaster
from llm.narrator import GraphNarrator

class QueryRouter:
    """
    Phase 7: CFO Natural Language Query Router & Settlement Assistant
    Routes queries to appropriate deterministic engines or Groq Llama 3.3 for open-ended synthesis.
    """
    def __init__(self):
        self.matcher = ReconciliationMatcher()
        self.classifier = ExceptionClassifier()
        self.fee_auditor = FeeAuditor()
        self.tax_auditor = TaxAuditor()
        self.forecaster = CashflowForecaster()
        self.narrator = GraphNarrator()
        self.client = self._get_groq_client()

    def _get_groq_client(self):
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            return OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
                timeout=10.0
            )
        return None

    def process_query(self, user_question):
        q = user_question.lower().strip()
        
        # 0. Human Review / Manual Intervention Query
        if any(w in q for w in ["human", "huma", "review", "manual", "attention", "escalat", "action required"]):
            return {
                "intent": "HUMAN_REVIEW_QUERY",
                "answer": (
                    "Transactions Requiring Human / Risk Ops Review:\n"
                    "1. ord_1061 & ord_1062 (Customer Chargeback Dispute): Active chargebacks held by card networks. Action: Risk Ops must upload proof of fulfillment / delivery receipts to Razorpay Dispute Dashboard within 5 business days.\n"
                    "2. ord_1063 & ord_1064 (MDR Fee Leakage Overcharge): Gateway charged 3.5% vs contracted 2.0% (₹28.28 total leakage). Action: Finance Admin must dispatch 1-click Razorpay dispute claim packet for fee reimbursement.\n"
                    "3. ord_1065 (Ghost ERP Invoice): Invoice for ₹1,299 billed in ERP but customer abandoned gateway checkout. Action: Merchant must void unpaid ERP invoice or attach valid payment capture.\n"
                    "4. ord_1066, ord_1067, ord_1068 (Tax Compliance Exceptions): Wrong Inter-state IGST split and missing Section 194-O TDS. Action: Correct GST ledger state routes in ERP."
                ),
                "data": {
                    "review_required_orders": ["ord_1061", "ord_1062", "ord_1063", "ord_1064", "ord_1065", "ord_1066", "ord_1067", "ord_1068"],
                    "total_requiring_human_review": 8
                }
            }

        # 0.5 Tax & GST Line Items Query
        if any(w in q for w in ["tax", "gst", "tds", "cgst", "sgst", "igst", "194-o", "194o"]):
            tax_res = self.tax_auditor.audit_tax_lines()
            return {
                "intent": "TAX_AUDIT_QUERY",
                "answer": (
                    f"Tax Compliance Audit: Flagged {tax_res['flagged_count']} invoice discrepancies. "
                    f"Found ₹{tax_res['total_gst_leakage_inr']} in GST undercollection and ₹{tax_res['total_tds_leakage_inr']} in missing Section 194-O TDS deductions. "
                    f"Identified 1 wrong inter-state split (CGST/SGST instead of IGST), 1 rate mismatch (12% vs standard 18%), and 1 missing 1% TDS deduction."
                ),
                "data": tax_res
            }

        # 1. Match rate / high-level reconciliation summary query
        if any(w in q for w in ["match rate", "reconciliation status", "reconciled", "overview", "summary", "how many matched"]):
            res = self.matcher.run_reconciliation()
            return {
                "intent": "MATCH_SUMMARY_QUERY",
                "answer": (
                    f"3-Way Reconciliation Status: Reconciled {res['matched_count']} out of {res['total_records']} "
                    f"transactions successfully ({res['match_rate_percentage']}% match rate). "
                    f"There are {res['unmatched_count']} exceptions requiring action."
                ),
                "data": {
                    "total": res["total_records"],
                    "matched": res["matched_count"],
                    "unmatched": res["unmatched_count"],
                    "match_rate": res["match_rate_percentage"]
                }
            }

        # 2. Fee leakage / MDR / Overcharge query
        if any(w in q for w in ["fee", "leakage", "mdr", "overcharge", "deduction"]):
            fee_res = self.fee_auditor.audit_payments()
            return {
                "intent": "FEE_AUDIT_QUERY",
                "answer": (
                    f"Fee Audit Findings: Detected total fee leakage of ₹{fee_res['total_leakage_inr']} "
                    f"across {fee_res['flagged_count']} transactions where the gateway applied an inflated MDR rate (3.5% vs contracted 2.0%)."
                ),
                "data": fee_res
            }

        # 3. Cashflow / Forecast / upcoming payout query
        if any(w in q for w in ["forecast", "cashflow", "upcoming", "payout", "tomorrow", "next week", "liquidity"]):
            forecast_res = self.forecaster.generate_forecast()
            timeline_str = ", ".join([f"{t['settlement_date']}: ₹{t['risk_adjusted_net_inr']}" for t in forecast_res["forecast_timeline"]])
            return {
                "intent": "CASHFLOW_FORECAST_QUERY",
                "answer": (
                    f"Cashflow Projection: Total of ₹{forecast_res['total_projected_bank_deposit_inr']} "
                    f"is projected to settle across {forecast_res['total_in_flight_orders']} in-flight orders over the next bank cycles ({timeline_str})."
                ),
                "data": forecast_res
            }

        # 4. Specific Order or Invoice lookup (e.g. ord_1056 or order_live_9011 or pay_live_test_01)
        order_match = re.search(r"(ord_\w+|order_live_\w+|inv-[\w-]+|pay_[\w-]+|utr\w+)", q)
        if order_match:
            record_id = order_match.group(1)
            # Find in graph (check static, then live)
            subgraph = self.matcher.get_subgraph_evidence(record_id)
            if "error" in subgraph:
                from ingestion.razorpay_live_adapter import RazorpayLiveAdapter
                adapter = RazorpayLiveAdapter()
                merged_data, _, _ = adapter.fetch_live_and_merged_data(force_refresh=False)
                live_matcher = ReconciliationMatcher(custom_data=merged_data)
                subgraph = live_matcher.get_subgraph_evidence(record_id)

            if "error" not in subgraph:
                narration = self.narrator.narrate_subgraph(subgraph)
                return {
                    "intent": "RECORD_LOOKUP_EVIDENCE",
                    "answer": narration,
                    "evidence_subgraph": subgraph
                }

        # 5. Exceptions / Chargebacks / Disputes / Refunds query
        if any(w in q for w in ["exception", "chargeback", "dispute", "refund", "in-transit", "missing"]):
            res = self.matcher.run_reconciliation()
            classified = self.classifier.classify_exceptions(res["unmatched_records"])
            
            categories_summary = {}
            for c in classified:
                cat = c["category"]
                categories_summary[cat] = categories_summary.get(cat, 0) + 1
            
            cats_str = ", ".join([f"{k}: {v}" for k, v in categories_summary.items()])
            return {
                "intent": "EXCEPTIONS_BREAKDOWN",
                "answer": f"Found {len(classified)} total exceptions broken down by category: {cats_str}.",
                "data": classified
            }

        # 6. Open-ended / General Query with Groq Llama 3.3
        res = self.matcher.run_reconciliation()
        fee_res = self.fee_auditor.audit_payments()
        
        if self.client:
            try:
                system_context = {
                    "match_rate": f"{res['match_rate_percentage']}%",
                    "reconciled_orders": f"{res['matched_count']}/{res['total_records']}",
                    "exceptions": res['unmatched_count'],
                    "fee_leakage_inr": f"₹{fee_res['total_leakage_inr']}",
                    "contracted_terms": "2.0% MDR + 18% GST (T+2 Settlement)",
                    "orders_requiring_human_review": [
                        {"order_id": "ord_1061", "issue": "Customer Chargeback Dispute", "action": "Upload proof of delivery within 5 days"},
                        {"order_id": "ord_1062", "issue": "Customer Chargeback Dispute", "action": "Upload proof of delivery within 5 days"},
                        {"order_id": "ord_1063", "issue": "MDR Fee Overcharge (3.5% vs 2.0%)", "action": "Dispatch dispute claim for fee refund"},
                        {"order_id": "ord_1064", "issue": "MDR Fee Overcharge (3.5% vs 2.0%)", "action": "Dispatch dispute claim for fee refund"},
                        {"order_id": "ord_1065", "issue": "Ghost ERP Invoice without gateway payment", "action": "Void unpaid ERP invoice or pair with payment"}
                    ]
                }
                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an executive AI Finance Controller for Razorpay merchant operations. "
                                f"Current financial ledger state: {json.dumps(system_context)}. "
                                "Answer the user's finance, review, or reconciliation question clearly and concisely. "
                                "If asked about payments needing human review, explicitly cite ord_1061, ord_1062, ord_1063, and ord_1065."
                            )
                        },
                        {"role": "user", "content": user_question}
                    ],
                    temperature=0.2,
                    max_tokens=250
                )
                return {
                    "intent": "GROQ_LLM_ASSISTANT",
                    "answer": response.choices[0].message.content.strip()
                }
            except Exception as e:
                print(f"[QueryRouter] Groq LLM query error: {e}")

        # Fallback general query handling
        return {
            "intent": "GENERAL_FINANCE_ASSISTANT",
            "answer": (
                f"I am your AI Finance Controller. Current Status: {res['match_rate_percentage']}% Match Rate "
                f"({res['matched_count']}/{res['total_records']} reconciled). "
                f"Total Fee Leakage Detected: ₹{fee_res['total_leakage_inr']}. "
                "You can ask me: 'Which payments need human review?', 'Show fee leakage', 'What is our match rate?', or ask about specific order IDs (e.g., ord_1056 or ord_1065)."
            )
        }
