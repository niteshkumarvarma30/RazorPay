# Architectural Challenges & Engineering Solutions Log
## Razorpay /buildathon Track 04: AI Finance Controller & Multi-Source Reconciliation

This document provides a technical deep-dive into the architectural bottlenecks, failure modes, design dilemmas, and exact engineering solutions implemented throughout the development of the **RazorpayX AI Finance Controller**.

---

## 🏛️ Core Philosophy: Separation of Concerns
```
┌────────────────────────────────────────────────────────────────────────┐
│                        FINANCIAL ENGINE HIERARCHY                      │
│                                                                        │
│   1. CODE DECIDES       Deterministic Python / NetworkX Graph Matcher  │
│                         (Zero tolerance arithmetic, exact join, sums)  │
│                                                                        │
│   2. ML FLAGS           Scikit-Learn IsolationForest & Classifier      │
│                         (Statistical outlier detection & confidence)   │
│                                                                        │
│   3. LLM NARRATES       Groq Llama 3.3 70B GraphRAG Assistant          │
│                         (Explains bounded subgraphs without hallucination)
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Detailed Breakdown of Architectural Challenges & Solutions

### 1. The Many-to-One Settlement Dilemma
* **The Architectural Breakdown**:
  * In real-world payment operations, a Bank UTR deposit does not correspond 1:1 to an ERP Invoice. 
  * Razorpay batches dozens of customer payments together into a single settlement, deducts MDR fees and 18% GST, and transfers the net remainder.
  * Standard SQL `JOIN` or naive linear search fails completely when trying to reconcile aggregated payments against bulk bank entries.
* **The Engineering Solution**:
  * Built a **3-Pass Deterministic Graph Reconciliation Engine** in [`engine/matcher.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/engine/matcher.py):
    * **Pass 1 (Direct Exact 1:1)**: Resolves exact `(order_id, pay_id)` joins.
    * **Pass 2 (Windowed Heuristics)**: Resolves date-drifted and partial matches within configurable tolerance windows ($\pm ₹0.05$).
    * **Pass 3 (Subset-Sum Combinatorial Solver)**: Applies dynamic programming / subset-sum solving to identify exact combinations of payments that sum to the net bank batch credit amount.
  * Stored all entities (Invoices, Payments, Settlements, Bank Entries, Refunds, Disputes) as nodes in a **NetworkX Knowledge Graph**.

---

### 2. Eliminating LLM Hallucinations in Financial Operations
* **The Architectural Breakdown**:
  * LLMs natively struggle with deterministic math. When prompt-engineered agents attempt arithmetic or multi-source joins in raw prompts, they hallucinate phantom payments, fabricate bank UTRs, and guess fee calculations.
* **The Engineering Solution**:
  * Implemented strict **GraphRAG (Graph Retrieval-Augmented Generation)** in [`llm/narrator.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/llm/narrator.py) and [`llm/query_router.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/llm/query_router.py):
    1. The Python reconciliation engine computes the mathematical ground truth and extracts a localized NetworkX subgraph.
    2. The Groq Llama 3.3 70B prompt is strictly bounded with the verified JSON subgraph.
    3. The model is forbidden from calculating numbers; it acts purely as a financial storyteller and narrator for the CFO.

---

### 3. Transition from Passive Exception Reporting to "Autonomous Fault Attribution & Self-Healing"
* **The Architectural Breakdown**:
  * Traditional reconciliation tools only output a list of discrepancies. Finance Ops teams then spend weeks emailing support desks: *"Who caused this missing ₹300 — did Razorpay overcharge us, or did our ERP invoice make a typo?"*
* **The Engineering Solution**:
  * Built [`engine/fault_attribution.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/engine/fault_attribution.py) to trace a **4-Stage Money Flow Pipeline**:
    $$\text{1. ERP Invoicing} \longrightarrow \text{2. Gateway Capture} \longrightarrow \text{3. MDR Fee Deduction} \longrightarrow \text{4. Bank Settlement}$$
  * **Automatic Root-Cause Attribution**:
    * **`🔴 RAZORPAY_GATEWAY_FAULT`** (e.g. MDR rate charged at 3.5% vs contracted 2.0% $\rightarrow$ `ord_1063`):
      * Automatically generates a **Dispute Packet** (`CLAIM-RZP-xxxx`) with cryptographic SHA256 evidence hash.
      * 1-Click **"Dispatch Dispute Claim"** simulates direct submission to Razorpay's Merchant Resolution Desk with 48h SLA credit.
    * **`🔵 MERCHANT_USER_FAULT`** (e.g. Ghost ERP invoice without gateway payment $\rightarrow$ `ord_1065`):
      * Renders inline **"Correct Invoice & Self-Heal ⚡"** drawer.
      * Submits `POST /api/reverify-invoice`, re-runs the 3-pass matcher in real time, and turns the transaction from ⚠️ Exception $\rightarrow$ ✅ Reconciled.

---

### 4. Live Razorpay API Integration vs Schema Discrepancy & Rate Limiting
* **The Architectural Breakdown**:
  * Live Razorpay REST APIs return amounts in paise (integers), timestamps in UNIX epoch, and lack merchant ERP metadata.
  * Constant live fetching on every page reload causes severe API rate limiting and slow UI response times.
* **The Engineering Solution**:
  * Built [`ingestion/razorpay_live_adapter.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/ingestion/razorpay_live_adapter.py):
    * **60-Second TTL Caching Layer**: Eliminates redundant API calls while preserving real-time synchronization.
    * **Data Normalization Pipeline**: Converts paise to rupees, parses ISO timestamps, and synthesizes matching ERP state pairs for seamless 3-way reconciliation.
    * **Dual Ingestion Mode Switcher**: Allows toggling between `🔵 Synthetic 65-Record Benchmark` and `🟢 Live Razorpay API` with active "🔄 Sync Data" triggers.

---

### 5. Model Trust & Confidence Calibration Safeguards
* **The Architectural Breakdown**:
  * Machine learning models often suffer from overconfidence (e.g., claiming 95% confidence while only achieving 60% empirical accuracy on edge cases), which causes human finance operators to misplace trust.
* **The Engineering Solution**:
  * Built [`metrics/calibration.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/metrics/calibration.py):
    * Groups model predictions into 4 confidence bins: `[0.0-0.6, 0.6-0.75, 0.75-0.9, 0.9-1.0]`.
    * Computes empirical accuracy per bin against ground truth.
    * **Low-Sample Safety Guardrail**: Flags bins with $n < 5$ as `low_sample: true` to prevent false statistical confidence.

---

### 6. Statutory Tax & GST / Section 194-O TDS Compliance Auditing
* **The Architectural Breakdown**:
  * Indian e-commerce transactions require strict validation between Intra-State (CGST 9% + SGST 9%) and Inter-State (IGST 18%), plus mandatory 1% TDS deduction under Section 194-O.
  * Standard gateway logs do not verify whether merchant ERPs correctly allocated tax splits.
* **The Engineering Solution**:
  * Built [`engine/tax_audit.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/engine/tax_audit.py):
    * Verifies state routes (`merchant_state` vs `customer_state`) against applied tax types.
    * Flags rate discrepancies and missing TDS deductions.
    * Integrated into evaluation scorecard (`100% Precision`, `100% Recall`, `1.0 F1`).

---

### 7. Frontend UI/UX Evolution: From Dense Sidebar to White/Blue Corporate Layout with Floating AI Copilot
* **The Architectural Breakdown**:
  * Initial UI rendered a fixed 380px right chat sidebar, which cramped the main data table and truncated UTR numbers, amounts, and source badges.
  * Dark aesthetic did not match Razorpay's corporate identity.
* **The Engineering Solution**:
  * **White & Royal Blue Corporate Palette**: Redesigned UI using RazorpayX enterprise design tokens (`#ffffff`, `#f8fafc`, `#0c2340`, `#0284c7`, `#059669`).
  * **Dedicated Project Landing Page (`#landing-page`)**: Created an interactive overview home page explaining Track 04 architecture with a 1-click Finance Ops Portal Login.
  * **Floating CFO Copilot Widget (`#chat-floating-trigger`)**: Converted the chat drawer into a non-intrusive floating bubble in the bottom-right corner, freeing up 100% width for dashboard tables.

---

## 🧪 Comprehensive Verification Summary

| Component | Test File | Test Count | Status |
| :--- | :--- | :---: | :---: |
| Core 3-Way Matcher & Pipeline | [`tests/test_all_phases.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/tests/test_all_phases.py) | 8 Suites | ✅ **PASS** |
| Fault Attribution & Money Flow | [`tests/test_fault_attribution.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/tests/test_fault_attribution.py) | 3 Suites | ✅ **PASS** |
| Live API Adapter & Calibration | [`tests/test_feature_addons.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/tests/test_feature_addons.py) | 2 Suites | ✅ **PASS** |
| GST & 194-O TDS Tax Matcher | [`tests/test_tax_audit.py`](file:///c:/Users/varni/OneDrive/Desktop/RazorPay/tests/test_tax_audit.py) | 2 Suites | ✅ **PASS** |
| **Total Test Suite** | **All 4 Test Modules** | **15 Suites** | **100% PASS** |
