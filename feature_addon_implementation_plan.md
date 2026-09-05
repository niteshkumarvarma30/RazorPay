# Add-On Implementation Plan: Live API Integration + Confidence Calibration

Two independent features. Build and test each in isolation before wiring into the dashboard —
neither depends on the other, so they can be built in either order or in parallel.

---

## Feature 1: Real Razorpay Test-Mode API Integration

### Goal
Prove the matcher works on data it didn't generate itself, by pulling real records from
Razorpay's sandboxed Test Mode API and running them through the existing pipeline unchanged.

### Tech Stack
| Component | Choice | Why |
|---|---|---|
| API client | `razorpay` official Python SDK, or plain `requests` with Basic Auth | SDK handles auth/pagination for you; `requests` is fine if you want zero new dependencies |
| Auth | `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` (already in `.env`) | Already provisioned, just unused so far |
| Caching layer | Simple in-memory dict or SQLite table (`live_fetch_cache`) keyed by fetch timestamp | Avoid hammering the API on every dashboard refresh; also gives you a "last fetched at" timestamp to show live-ness |
| Schema adapter | New module `ingestion/razorpay_live_adapter.py` | Converts Razorpay's real API JSON shape into your existing `Payment` / `Settlement` dataclass shape — this is the only new "translation" logic needed |
| Source tagging | Add a `source: "live" | "synthetic"` field to every record | Powers the UI badge distinguishing live vs. synthetic rows |

### Architecture
```
Razorpay Test API (Payments, Settlements endpoints)
        │
        ▼
ingestion/razorpay_live_adapter.py   ← maps real API fields to your internal schema, tags source="live"
        │
        ▼
(merged with) synthetic edge-case records, tagged source="synthetic"
        │
        ▼
engine/matcher.py   ← UNCHANGED — this is the whole point, it shouldn't need to know the data's origin
        │
        ▼
API endpoint: GET /api/reconcile-live   ← new endpoint, or add ?mode=live to existing /api/reconcile
        │
        ▼
Frontend: new "Live Data" section/tab
```

### Build Steps

**Step 1 — API client + auth smoke test**
- Add `razorpay` SDK to `requirements.txt`, load keys from `.env`.
- Write a standalone script `scripts/test_live_connection.py` that calls `client.payment.all()` and `client.settlement.all()` and prints raw JSON.
- **Acceptance test:** script runs, prints at least one real payment/settlement object from Test Mode without error.

**Step 2 — Schema adapter**
- Write `ingestion/razorpay_live_adapter.py` with a function `fetch_live_records() -> (list[Payment], list[Settlement])`.
- Map Razorpay's real field names (`id`, `order_id`, `amount`, `fee`, `tax`, `status`, `created_at`, etc.) onto your existing internal dataclasses — don't invent a new schema, reuse Phase-1's.
- Tag every record `source="live"`.
- **Acceptance test:** unit test asserts the adapter's output objects satisfy the same interface/type your synthetic generator's objects do (e.g. `isinstance` checks, required fields present).

**Step 3 — Merge with synthetic edge cases**
- Since chargebacks/refunds/fee-overcharges are hard to trigger live in Test Mode, keep generating those synthetically and tag them `source="synthetic"`.
- Merge both lists before handing off to `matcher.py`.
- **Acceptance test:** merged dataset contains records with both `source` tags; matcher runs without modification on the combined set.

**Step 4 — Caching + "last fetched" timestamp**
- Wrap `fetch_live_records()` with a simple TTL cache (e.g. 60 seconds) so repeated dashboard loads don't spam the API.
- Store `last_fetched_at` and expose it via the API response.
- **Acceptance test:** two calls within the TTL window return identical data without a second network call; a call after TTL expiry triggers a fresh fetch.

**Step 5 — New API endpoint**
- `GET /api/reconcile?mode=live` (or a dedicated `/api/reconcile-live`) — returns match results plus a `source` field per record and a `data_freshness` timestamp.
- **Acceptance test:** endpoint returns valid JSON with both live and synthetic records correctly tagged.

**Step 6 — Frontend "Live Data" section**
- New dashboard tab: summary line "`X of Y records pulled live from Razorpay Test API — last refreshed at HH:MM:SS`".
- Table with a colored badge per row (🟢 Live / 🔵 Synthetic).
- "Refresh now" button that re-triggers the fetch and visibly updates the timestamp — this is the moment that proves it's real during a live demo.
- **Acceptance test:** clicking refresh updates the timestamp and at least one row's data live, without a page reload.

### Fallback / Failure Handling
- If the Razorpay API is unreachable during the actual demo (network issues, rate limits), the adapter should catch the error and fall back to a cached last-known-good response with a visible "⚠️ showing cached live data from HH:MM" notice — never crash the dashboard mid-demo.

---

## Feature 2: Confidence Calibration Chart

### Goal
Prove your classifier's stated confidence scores are actually meaningful — i.e., a 90%-confidence
prediction really is right about 90% of the time — using your existing ground truth file.

### Tech Stack
| Component | Choice | Why |
|---|---|---|
| Computation | Python, `pandas` | You already have classifier outputs (`confidence`) and `ground_truth.json` — this is a groupby/aggregation, not new ML |
| Chart | Recharts (`LineChart` or `ScatterChart`) on the frontend, or matplotlib if you want a static image | Matches your existing frontend stack; Recharts keeps it interactive/consistent with the rest of the dashboard |
| New module | `metrics/calibration.py` | Single-purpose script: buckets predictions, computes actual accuracy per bucket |
| New endpoint | `GET /api/calibration` | Returns bucketed data for the frontend to chart |

### Architecture
```
engine/classifier.py output (per-record: predicted_label, confidence)
                │
                ▼
ground_truth.json (per-record: true_label)   ← join on record_id
                │
                ▼
metrics/calibration.py
   1. bucket predictions by confidence (e.g. 90-100, 70-90, 50-70, <50)
   2. within each bucket: accuracy = (predicted_label == true_label).mean()
   3. output: [{bucket: "90-100%", predicted_confidence: 95, actual_accuracy: 96.2, n: 40}, ...]
                │
                ▼
API endpoint: GET /api/calibration
                │
                ▼
Frontend: new "Model Trust" or "Calibration" section
   - line/scatter chart: x = stated confidence, y = actual accuracy
   - reference diagonal line (perfect calibration)
   - caption: "Our 90%+ confidence predictions were correct 96% of the time (n=40)"
```

### Build Steps

**Step 1 — Bucketing logic**
- Write `metrics/calibration.py` with a function `compute_calibration(predictions, ground_truth, buckets=[(90,100),(70,90),(50,70),(0,50)])`.
- For each record: join predicted confidence + predicted label against ground truth's true label by `record_id`.
- **Acceptance test:** unit test with a small hand-crafted set of predictions/ground truth returns the expected per-bucket accuracy and count.

**Step 2 — Sample-size guardrail**
- If a bucket has fewer than ~5 records, mark it `low_sample: true` in the output instead of reporting a potentially misleading 100%/0% accuracy — small buckets are noisy and reporting them plainly can undercut your own credibility.
- **Acceptance test:** a bucket with 2 records is flagged `low_sample`, a bucket with 20 is not.

**Step 3 — API endpoint**
- `GET /api/calibration` returns the bucketed JSON described above, plus a top-line sentence pre-computed server-side (e.g. `"90%+ confidence predictions were correct 96.2% of the time (n=40)"`) so the frontend doesn't need to reconstruct that phrasing.
- **Acceptance test:** endpoint output matches what `compute_calibration()` returns directly, confirming no drift between the API and the underlying computation.

**Step 4 — Frontend chart**
- New dashboard section: Recharts line/scatter plot, x-axis = stated confidence bucket midpoint, y-axis = actual accuracy, plus a static reference line at y=x.
- Show the pre-computed headline sentence above the chart.
- If any bucket is `low_sample`, annotate it on the chart (e.g. lighter color, "(n=3, low sample)" label) rather than hiding it.
- **Acceptance test:** chart renders correctly with the live `/api/calibration` data; low-sample buckets are visually distinguished.

### Failure Handling
- If `ground_truth.json` is ever missing (e.g. running against live API data with no known ground truth), the calibration endpoint should return a clear `"calibration_unavailable": true` response rather than crashing or fabricating numbers — calibration is inherently a synthetic-data-only feature since it needs known-correct labels.

---

## Notes for Antigravity

- Build Feature 1 Steps 1–3 and Feature 2 Steps 1–2 first — both are backend-only and independently testable with `pytest` before any UI work starts.
- Explicitly instruct: "`engine/matcher.py` and `engine/classifier.py` must not be modified for either feature" — both add-ons should be pure wrappers/consumers of existing logic, not changes to the core matching/classification code. This keeps your existing 96.92% ground-truth accuracy number stable and unaffected by these additions.
- For Feature 1, give it your actual `.env` variable names up front so it doesn't invent placeholder credential handling.
- For Feature 2, tell it explicitly not to hardcode bucket boundaries as magic numbers scattered across files — keep them in one config constant so the chart and backend never disagree on bucket definitions.
