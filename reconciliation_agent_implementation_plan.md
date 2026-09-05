# AI Finance Reconciliation Agent — Implementation Plan

Architecture principle driving every decision below: **code decides, ML flags, LLM narrates.**
Never let the LLM compute a number or decide a match — it only explains and translates language.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Fast to write, great data/graph/ML libraries |
| API server | FastAPI | Async, auto-generates OpenAPI docs, minimal boilerplate |
| Data storage | SQLite (via SQLAlchemy) or DuckDB | Zero-setup, embeddable, good enough for 50–5,000 synthetic records |
| Data wrangling | pandas | Joins, grouping, date-window filtering |
| Evidence graph | NetworkX | In-memory graph = your audit trail data structure (not a retrieval index) |
| Fuzzy string matching | rapidfuzz | For "similar" name/ID matching (Pass 2) |
| Subset-sum solver | Custom DP / `itertools` w/ pruning | Many-to-one settlement splitting (bounded set size, so brute-force-with-pruning is fine) |
| Anomaly detection | scikit-learn (`IsolationForest`, or simple z-score) | Flags unusual fee/amount deviations — genuine ML, not LLM guesswork |
| LLM (narration + NL→query) | Claude API (Anthropic) or Gemini API | Used ONLY for phrasing sentences and translating NL questions into structured queries — never for matching or arithmetic |
| Frontend | React + Vite + Tailwind | Fast to scaffold, good for dashboards |
| Charts | Recharts | Match-rate trend, forecast chart, leakage total |
| Synthetic data generator | Python script (`faker` + manual anomaly injection) | You need ground-truth labels to report precision/recall |
| Deployment (optional) | Vercel (frontend) + Render/Railway (backend) | Only if you need a live demo URL; local is fine for judging |

---

## Data Model

```
Invoice        { invoice_id, order_id, amount, date, customer_id }
Payment        { pay_id, order_id, amount_captured, mdr_fee, gst_on_fee, status, date }
Settlement     { settlement_id, pay_id, net_amount, batch_id, date }
BankEntry      { utr, batch_id, amount_credited, date }
Refund         { refund_id, pay_id, amount, date }
Dispute        { dispute_id, pay_id, status, date }
Exception      { record_id, type, confidence, explanation_ids[], resolved_by }
```

Ground-truth label field (`true_label`) lives ONLY in your synthetic data generator's output —
used for scoring, never fed to the matching engine itself.

---

## Phase-by-Phase Build Plan

### Phase 0 — Synthetic Data Generator
**Goal:** Produce 50–100 realistic records with planted anomalies and known ground truth.
- Generate clean matched records (majority case).
- Inject: partial refund, full refund, T+2 in-transit delay, chargeback/dispute hold,
  fee miscalculation, many-to-one settlement batch (1 bank UTR = N settlements),
  one deliberately unresolvable ambiguous case (for the Failure Recovery demo).
- Output: `invoices.json`, `payments.json`, `settlements.json`, `bank_entries.json`, plus a hidden `ground_truth.json`.
- **Acceptance test:** row counts match, every planted anomaly type appears at least twice, ground truth file never imported by matching code.

### Phase 1 — Deterministic Matching Engine
**Goal:** 3-pass matcher, zero LLM involvement.
- Pass 1: exact join on `order_id` / `pay_id` / `utr`.
- Pass 2: fuzzy/tolerance join — amount within MDR+GST formula, date within T+2 window.
- Pass 3: subset-sum solver — explain one `BankEntry.amount` as sum of N `Settlement.net_amount`.
- Build the NetworkX graph: nodes = records, edges = `BILLED_AS`, `DEDUCTED`, `BUNDLED_INTO`, `DEPOSITED_VIA_UTR`, `REFUNDED_TO_CUSTOMER`, `HELD_BY_DISPUTE`.
- **Acceptance test:** match rate computed and printed; every matched edge traceable back to source record IDs.

### Phase 2 — Exception Classification
**Goal:** For unmatched nodes, classify why (rule-based decision tree, not ML/LLM).
- Rules: has `Refund` edge → "refund"; missing bank edge but within T+2 window → "in-transit delay"; has `Dispute` edge → "chargeback hold"; else → "unresolved — needs review".
- Attach a confidence score (1.0 for exact, lower for fuzzy/ambiguous).
- **Acceptance test:** every unmatched record gets exactly one classification + confidence + supporting IDs.

### Phase 3 — Fee Audit Layer (your differentiator)
**Goal:** Recompute expected MDR% + GST fee per transaction, flag deviations.
- Formula: `expected_fee = amount * mdr_rate * (1 + gst_rate)`.
- Compare to `Payment.mdr_fee + gst_on_fee`; flag if delta > ₹0.50.
- Sum total flagged delta → "total leakage found" headline number.
- **Acceptance test:** at least one planted fee-miscalculation record is caught with the exact ₹ delta shown.

### Phase 4 — Anomaly Detection (stretch)
**Goal:** ML flags statistically unusual records the rules didn't catch.
- Feature vector per transaction: fee delta, settlement delay in days, amount.
- `IsolationForest` (or z-score if time is short) flags outliers.
- **Acceptance test:** flagged outliers cross-checked against ground truth — report false positive rate.

### Phase 5 — Cashflow Forecast
**Goal:** Deterministic projection, not LLM guessing.
- Sum orders still "in processing" in the last 48h.
- Apply T+2 rule and known fee % to project net deposit by date.
- Optional: adjust by historical refund rate (simple moving average).
- **Acceptance test:** forecast number is fully traceable to a list of contributing order IDs.

### Phase 6 — LLM Narration Layer
**Goal:** Turn a computed subgraph into a clean sentence — nothing more.
- Prompt template takes JSON subgraph (IDs, amounts, dates, edges) as strict context.
- System prompt: "Only state facts present in the provided JSON. Cite every ID exactly as given. Do not compute new numbers."
- Temperature 0, no external knowledge.
- **Acceptance test:** manually verify 5 narrations against source JSON — every number and ID must be traceable.

### Phase 7 — Q&A Chatbot
**Goal:** NL question → structured query → computed answer → narrated.
- LLM's only job: map "why was payout short yesterday" → a query spec like `{date: "yesterday", type: "exceptions"}`.
- Run that query against your DB/graph in code.
- Pass the result back to the LLM for narration (Phase 6 logic reused).
- **Acceptance test:** ask 10 varied questions, confirm every numeric answer matches what code computed independently.

### Phase 8 — Investigation Agent (stretch, satisfies "AI Judgment")
**Goal:** Justify agentic AI narrowly — only for genuinely ambiguous unresolved cases.
- Tools: `query_refunds(pay_id)`, `query_disputes(pay_id)`, `query_support_tickets(order_id)`.
- Agent loop only triggers for records still "unresolved" after Phases 1–4.
- Log its full reasoning trace for the audit UI.
- **Acceptance test:** agent's conclusion matches ground truth for the planted ambiguous case, or correctly escalates to human review.

### Phase 9 — Metrics & Scoring
**Goal:** Report like a classifier, not just a percentage.
- Precision/recall per exception type against `ground_truth.json`.
- False-match rate.
- Total leakage found (₹).
- **Acceptance test:** a single `metrics.json` output file judges could independently re-derive from your data.

### Phase 10 — Frontend Dashboard
**Goal:** Visual proof surface.
- Match-rate summary card, exception list (with evidence IDs shown), leakage total, forecast chart, chat panel.
- Graph visualization for the "prove it" click-through (optional but impressive).
- **Acceptance test:** every number on screen has a "show evidence" affordance linking to source IDs.

### Phase 11 — Failure Recovery Demo
**Goal:** Show the one case that couldn't be resolved confidently.
- Confirm the deliberately unresolvable case from Phase 0 is correctly flagged "needs human review" with a confidence score below threshold, not silently guessed.
- Script this moment explicitly into your demo narration.

### Phase 12 — Packaging
- README with architecture diagram (matcher → classifier → fee audit → forecast → LLM layer).
- One-paragraph explicit answer to "why not RAG for matching" ready to say out loud.
- Demo script hitting: match rate, leakage number, one exception explained with IDs, one forecast, one chatbot Q&A, the failure-recovery case.

---

## Suggested Repo Structure

```
/data_gen/          synthetic data + ground truth generator
/engine/
  matcher.py         Phase 1
  classifier.py       Phase 2
  fee_audit.py        Phase 3
  anomaly.py           Phase 4 (stretch)
  forecast.py          Phase 5
/llm/
  narrator.py          Phase 6
  query_router.py       Phase 7
  investigator_agent.py Phase 8 (stretch)
/api/                FastAPI routes wiring engine + llm to frontend
/frontend/           React app
/metrics/            precision/recall scoring scripts
README.md
```

## Notes for building this with Antigravity (or any agentic coding tool)

- Feed it **one phase at a time** with its acceptance test as the definition of done — agentic coders perform far better against a concrete pass/fail check than an open-ended spec.
- Give it the data schema up front so every phase's code agrees on field names.
- Explicitly instruct it: "Phases 1–5 must contain zero LLM/API calls" — this is easy for an agent to violate by default (LLM-based coding agents like reaching for an LLM call even when a rule/formula would do), so state the constraint directly.
- Ask it to write a small pytest for each phase's acceptance test before moving on.
