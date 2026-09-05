import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class GraphNarrator:
    """
    Phase 6: GraphRAG Subgraph Narrator (Powered by Groq Llama-3.3-70B)
    Strictly translates computed graph nodes & edges into transparent, natural language audit sentences.
    Zero hallucination principle: Only states facts provided in the JSON subgraph.
    """
    def __init__(self):
        self.client = self._get_client()

    def _get_client(self):
        # 1. Check Groq API Key
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            return OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
                timeout=10.0
            )
        return None

    def narrate_subgraph(self, subgraph_data):
        """
        Narrates a specific transaction's evidence subgraph using Groq Llama 3.3.
        """
        if not subgraph_data or "nodes" not in subgraph_data:
            return "No evidence path available for this record."

        # Structured deterministic fallback data
        nodes = {n["type"]: n for n in subgraph_data.get("nodes", [])}
        edges = subgraph_data.get("edges", [])

        inv = nodes.get("Invoice", {})
        pay = nodes.get("Payment", {})
        setl = nodes.get("Settlement", {})
        bank = nodes.get("BankEntry", {})
        ref = nodes.get("Refund", {})
        disp = nodes.get("Dispute", {})

        # Use Groq LPU LLM Narration
        if self.client:
            try:
                system_prompt = (
                    "You are an AI Finance Auditor. Narrate the provided reconciliation subgraph into 2 precise sentences. "
                    "Rule 1: ONLY state facts and numbers present in the JSON. "
                    "Rule 2: Cite exact IDs (Invoice ID, Payment ID, Settlement ID, UTR). "
                    "Rule 3: Do NOT calculate or guess numbers."
                )
                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Reconciliation Subgraph:\n{json.dumps(subgraph_data, indent=2)}"}
                    ],
                    temperature=0.0,
                    max_tokens=250
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[GraphNarrator] Groq LLM call error: {e}")

        # Deterministic Ground-Truth Narration
        parts = []
        if inv:
            parts.append(f"Invoice {inv.get('invoice_id', 'N/A')} was billed for ₹{inv.get('amount', 0)}.")
        if pay:
            parts.append(f"Razorpay captured payment {pay.get('id', 'N/A')} on {pay.get('date', 'N/A')} with fee deduction of ₹{round(pay.get('mdr_fee', 0) + pay.get('gst_on_fee', 0), 2)}.")
        if ref:
            parts.append(f"A refund of ₹{ref.get('amount')} was issued under {ref.get('id')}.")
        if disp:
            parts.append(f"Funds are currently frozen due to active chargeback dispute {disp.get('id')} ({disp.get('reason')}).")
        if setl:
            parts.append(f"Net settlement amount of ₹{setl.get('net_amount')} was processed in batch {setl.get('batch_id')}.")
        if bank:
            parts.append(f"Funds were credited to the merchant bank account under UTR #{bank.get('id')}.")

        return " ".join(parts) if parts else "Reconciliation details logged."
