# Add-On Implementation Plan: Tax-Line (GST) Matcher

Closes the 4th of Razorpay's 4 example directions. Reuses the existing `fee_audit.py`
pattern (recompute expected value from a known formula, compare to actual, flag deviation)
applied to tax line items instead of the MDR fee.

---

## Goal

Instead of treating tax as one flat number baked into the MDR+GST fee calculation you
already audit, break invoices down into their actual GST components (CGST/SGST/IGST) and
verify each component against what the payment/settlement records show — plus check for
TDS deductions where applicable. Flag any mismatch as a "tax-line exception," same way
you already flag fee leakage.

---

## Tech Stack

| Component | Choice | Why |
|---|---|---|
| Language/logic | Python, same as rest of `engine/` | No new dependencies needed — this is arithmetic + rule comparison, same pattern as `fee_audit.py` |
| New module | `engine/tax_audit.py` | Mirrors `engine/fee_audit.py` structure exactly, so it's fast to build and easy for Antigravity to pattern-match against existing code |
| Data model extension | Add `tax_lines` field to your `Invoice` schema | List of `{type: "CGST"|"SGST"|"IGST", rate: float, amount: float}` instead of one flat tax number |
| Synthetic data | Extend `data_gen/generator.py` | Add tax-line breakdown to generated invoices, plus 2-3 planted tax-mismatch cases (same pattern as your planted fee-overcharge cases) |
| API endpoint | `GET /api/tax-audit` | Same shape as your existing `/api/fee-audit` endpoint |
| Frontend | New "Tax Audit" tab, same visual pattern as your "Fee Leakage Audit" tab | Keeps UI consistent, minimal new design work |

---

## Domain Background (for whoever's building this)

- **Intra-state sales**: split as CGST (Central GST) + SGST (State GST), each typically half the total GST rate (e.g. 9% + 9% = 18%).
- **Inter-state sales**: charged as IGST (Integrated GST) at the full rate (e.g. 18%) instead of split.
- **TDS under Section 194-O**: for e-commerce operators, 1% TDS may be deducted at source on the gross transaction value by the payment aggregator/marketplace, separate from GST — some merchants miss this deduction in their books, which is a real-world discrepancy worth catching.
- Keep the actual rate table simple and configurable (e.g. a constants dict) rather than hardcoding numbers inline — GST rates can vary by product category in reality, but for hackathon scope a single flat rate (18%) with intra/inter-state split logic is enough to demonstrate the capability.

---

## Architecture

```
Invoice (extended with tax_lines: [{type, rate, amount}])
        │
        ▼
engine/tax_audit.py
   1. Determine if transaction is intra-state or inter-state (based on merchant/customer state field)
   2. Compute expected tax split:
        - intra-state: CGST = amount * rate/2, SGST = amount * rate/2
        - inter-state: IGST = amount * rate
   3. Compute expected TDS (if applicable): tds = gross_amount * 0.01
   4. Compare expected vs actual tax_lines on the invoice/payment record
   5. Flag mismatches > ₹0.50 threshold (same tolerance as fee_audit.py)
        │
        ▼
Output: list of TaxException { record_id, expected_breakdown, actual_breakdown, delta, type: "gst_mismatch"|"tds_missing" }
        │
        ▼
API: GET /api/tax-audit  →  { total_tax_leakage, exceptions: [...] }
        │
        ▼
Frontend: "Tax Audit" tab — mirrors your existing Fee Leakage Audit tab layout
```

---

## Build Steps

**Step 1 — Extend the data schema**
- Add `tax_lines: list[TaxLine]` to the `Invoice` dataclass, where `TaxLine = {type: str, rate: float, amount: float}`.
- Add a `merchant_state` and `customer_state` field to invoices (needed to determine intra vs inter-state).
- **Acceptance test:** existing tests for `Invoice` still pass with the new optional fields defaulted sensibly; no breakage in `matcher.py` or `classifier.py`.

**Step 2 — Extend synthetic data generator**
- For each generated invoice, compute a correct GST split (intra or inter-state, randomly assigned) and attach it as `tax_lines`.
- Plant 2-3 deliberate mismatches: e.g. one invoice charged CGST+SGST when it should have been IGST (wrong split type), one with a GST rate applied incorrectly (e.g. 12% instead of 18%), one missing the 1% TDS deduction entirely.
- Add these planted cases to `ground_truth.json` with a `true_label: "gst_mismatch"` or `"tds_missing"`.
- **Acceptance test:** generated dataset contains at least 2 tax-line exceptions, all present in ground truth with correct labels.

**Step 3 — Build `engine/tax_audit.py`**
- Function `audit_tax_lines(invoices) -> list[TaxException]`.
- For each invoice: determine intra/inter-state, compute expected CGST/SGST or IGST split, compute expected TDS if applicable, compare to actual `tax_lines`, flag if delta exceeds ₹0.50 tolerance.
- Mirror the exact structure of `fee_audit.py` (same tolerance-check pattern, same output shape convention) so the two modules are easy to maintain side by side.
- **Acceptance test:** running against the synthetic dataset from Step 2 correctly flags all planted mismatches and produces zero false positives on the clean records.

**Step 4 — API endpoint**
- `GET /api/tax-audit` returns `{ total_tax_leakage: float, exceptions: [...] }`, same response shape convention as `/api/fee-audit`.
- **Acceptance test:** endpoint output matches direct output of `audit_tax_lines()`, confirming no drift.

**Step 5 — Wire into metrics/scoring**
- Add tax-line exceptions to your existing `metrics/evaluator.py` precision/recall scorecard as a new row (same table format as your other exception types: Refund, Chargeback, etc.).
- **Acceptance test:** the metrics scorecard output includes a "GST/TDS Mismatch" row with precision/recall/F1 computed against ground truth, same as your other rows.

**Step 6 — Frontend "Tax Audit" tab**
- Copy the visual pattern of your existing Fee Leakage Audit tab: a headline "total tax leakage found" number, a table of flagged invoices with expected vs actual breakdown, and per-row evidence linking to the invoice ID.
- **Acceptance test:** tab renders live data from `/api/tax-audit`, matches what the backend returns.

---

## Notes for Antigravity

- Tell it explicitly: "Model `tax_audit.py` directly on the existing structure of `fee_audit.py` — same tolerance-check pattern, same function signature style, same output shape" — this keeps the codebase consistent and makes the feature fast to build since it's not inventing a new pattern.
- Do not touch `engine/matcher.py` or `engine/classifier.py` for this feature either — same rule as the previous two add-ons. Tax audit is a parallel, independent check, not a change to core matching logic.
- Keep the GST rate table as a single named constant (e.g. `GST_RATE = 0.18`, `TDS_RATE = 0.01`) in one place, not scattered across files — makes it trivial to explain and adjust during Q&A if a judge asks about rate assumptions.
- In the pitch/README, explicitly reference this as closing Razorpay's own 4th example direction ("Tax-line matcher") from the track page — make the connection to their stated menu obvious rather than assuming judges will notice on their own.
