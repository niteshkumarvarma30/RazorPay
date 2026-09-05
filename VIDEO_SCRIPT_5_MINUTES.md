# 🎬 5-Minute Video Recording Script & Master Project Guide
## **Project:** Autonomous AI Finance Controller & 3-Way Reconciliation System
**Track:** Razorpay /buildathon — Track 04: AI Finance Controller ("Run the books and the cash position")  
**Target Duration:** 5 Minutes (~700 spoken words at 140 wpm)  
**Live Demo URLs:** [http://localhost:8000](http://localhost:8000) or [http://localhost:3000](http://localhost:3000)

---

## 🧭 Executive Summary of the Dashboard Architecture

Before recording, here is the complete layout of the **RazorpayX AI Finance Controller** interface:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  🏠 1. LANDING & ACCESS GATEWAY (#landing-page)                                                  │
│  • Brand Badge & Track 04 Banner | Hero Headline & Core Mission Statement                        │
│  • 1-Click Finance Ops Admin Login (cfo.finance@razorpay-merchant.com)                           │
│  • 6 Core Architectural Pillars: 3-Way Recon, Zero-Hallucination Agent, Fee Leakage,             │
│    Tax/GST Matcher, 7-Day Forecaster, Autonomous Self-Healing                                    │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
                                               │ (Click "Launch Dashboard 🚀")
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  🖥️ 2. MAIN EXECUTIVE WORKSPACE (#dashboard-app)                                                │
│                                                                                                  │
│  [LEFT SIDEBAR]                   [TOP CONTROL BAR]                                             │
│  • Brand: RazorpayX Recon         • Breadcrumbs: RazorpayX / Finance Ops / Ledger                │
│  • Navigation Tabs:               • Dual Ingestion Switcher: 🔵 Synthetic Batch | 🟢 Live API    │
│    - 📊 3-Way Reconciliation       • 🔄 "Sync Data" Trigger Button                               │
│    - ⚠️ Exceptions & Triage        • Contract Badge: 🛡️ 2.0% MDR + 18% GST                      │
│    - 🔍 Fee Leakage Audit                                                                        │
│    - 📑 Tax-Line (GST) Matcher    [KPI EXECUTIVE SUMMARY CARDS]                                 │
│    - 📈 Cashflow Forecaster       1. 3-Way Match Rate (81.54% Clean Instant Reconciliation)     │
│    - 🎯 Ground Truth & Trust      2. MDR Fee Leakage (₹ Overcharges Caught & Flagged)           │
│    - 🤖 Failure Recovery Agent    3. Active Exceptions (Refunds, Disputes, In-Transit)          │
│  • Sidebar Footer:                4. 7-Day Liquidity Forecast (Projected T+2 Bank Payout)        │
│    T+2 Settlement Cycle Active                                                                   │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  [CORE DASHBOARD WORKSPACE TABS]                                                                 │
│                                                                                                  │
│  Tab 1: 📊 3-Way Reconciliation Ledger                                                           │
│  • 9-Column Ledger: Source | Order ID | Pay ID | ERP Billed | Fee (MDR+GST) | Bank Credited |   │
│    Bank UTR | Recon Status Badge (Matched/Partial/Delayed) | 1-Click "View Evidence" Button      │
│                                                                                                  │
│  Tab 2: ⚠️ Exceptions & Triage Queue                                                             │
│  • Filter Pills: All | Refunds | Disputes & Chargebacks | In-Transit | Unresolved                │
│  • Action Trails with confidence metrics and root-cause fault classification                     │
│                                                                                                  │
│  Tab 3: 🔍 Gateway Fee Leakage Audit                                                             │
│  • Audits actual deducted fees vs statutory contract (2.0% MDR + 18% GST)                       │
│  • Highlights hidden overcharges (e.g. 3.5% rate anomalies) and calculates net leakage           │
│                                                                                                  │
│  Tab 4: 📑 Tax-Line (GST & Section 194-O TDS) Compliance Matcher                                 │
│  • State Routing Audit: Intra-State (CGST 9% + SGST 9%) vs Inter-State (IGST 18%)                │
│  • Validates 1% TDS deduction under Section 194-O and flags tax split variances                  │
│                                                                                                  │
│  Tab 5: 📈 Rolling Cashflow Forecaster                                                           │
│  • 7-Day Settlement projection tracking in-flight transactions, gross volume & net bank payout   │
│                                                                                                  │
│  Tab 6: 🎯 Ground Truth Verification & Confidence Calibration                                   │
│  • Statistical Confusion Matrix (Precision, Recall, F1-score across all transaction classes)    │
│  • 4-Bin Empirical Confidence Calibration with low-sample statistical guardrails                │
│                                                                                                  │
│  Tab 7: 🤖 Autonomous Failure Recovery Agent Sandbox                                             │
│  • Interactive investigation console testing ambiguous cases (e.g. ghost invoice ord_1065)      │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  [INTERACTIVE MODALS & FLOATING AGENTS]                                                          │
│                                                                                                  │
│  🔎 Evidence Audit Trail & Money Flow Modal (#evidence-modal)                                    │
│  • 4-Stage Money Flow Inspector: ERP Invoicing ⟶ Gateway Capture ⟶ MDR Fee ⟶ Bank Settlement    │
│  • Fault Attribution Card: 🔴 RAZORPAY_GATEWAY_FAULT vs 🔵 MERCHANT_USER_FAULT                  │
│  • Self-Healing Drawer: Live ERP invoice correction (POST /api/reverify-invoice)                 │
│  • NetworkX Knowledge Graph Subtree visualization + Groq Llama 3.3 GraphRAG Narration           │
│                                                                                                  │
│  💬 Floating CFO Copilot (#chat-drawer & #chat-floating-trigger)                                 │
│  • Collapsible floating bubble in bottom-right corner                                            │
│  • Quick Preset Chips: Needs Review | Match Rate | Fee Leakage | Tax & GST | Forecast | Disputes│
│  • Natural language question answering with zero-hallucination subgraph grounding               │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⏱️ Video Structure at a Glance (5 Minutes)

| Time | Segment | Focus | Screen Action |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:45** | **The Hook & Problem** | The 3-Way Reconciliation nightmare | Landing Page, login gateway, & core pillars |
| **0:45 – 1:45** | **Total Dashboard Tour** | Live walk-through of all metrics & tabs | KPI cards, 3-way table, Fee audit, Tax matcher |
| **1:45 – 2:45** | **Evidence DAG & Self-Healing** | Money Flow, Fault Attribution & Healing | Click "View Evidence", show DAG, fix invoice |
| **2:45 – 3:45** | **Architectural Challenges** | Hard problems from the Challenges Log | Explain Many-to-One, Hallucination, & Live API |
| **3:45 – 4:30** | **Autonomous AI Copilot** | Groq Llama 3.3 without order ID barriers | Open floating chat, ask "Which need review?" |
| **4:30 – 5:00** | **Conclusion & Impact** | Ground Truth accuracy & enterprise ROI | Show Ground Truth tab (96.9% accuracy) & close |

---

## 🎙️ Word-for-Word Video Script with Screen Actions

### **[0:00 – 0:45] Minute 1: The Hook & Core Problem**

* **🖥️ Screen Action:**  
  Start on the **Landing Page** (`http://localhost:8000`). Point cursor to the track banner and the title: *"Autonomous Multi-Source Reconciliation & AI Finance Controller"*. Scroll down to the 6 Core Architectural Pillars grid. Then click **"Access Live Reconciliation Engine ⚡"** to smoothly enter the main dashboard.

* **🗣️ Spoken Script:**  
  > *"In digital payments, thousands of transactions happen every second. But behind the scenes, finance teams face a massive bottleneck: **The Three-Way Reconciliation Nightmare**.*  
  >  
  > *Every business operates across three separate sources of truth: internal ERP sales invoices, payment gateway records from Razorpay, and bank settlement statements.*  
  >  
  > *When transaction volumes spike, manual cross-checking on Excel completely breaks down. Timing drifts, missing webhooks, customer refunds, and gateway fee overcharges silently drain corporate cash flow.*  
  >  
  > *To solve this once and for all, I built the **Autonomous AI Finance Controller**: a production-grade reconciliation and audit platform that brings real-time visibility, automated dispute triage, and AI-powered auditing to corporate finance."*

---

### **[0:45 – 1:45] Minute 2: Total Dashboard Tour & Core Engines**

* **🖥️ Screen Action:**  
  1. Hover over the **Top Navbar**: Show the **Dual Ingestion Switcher** (`🔵 Synthetic Batch` vs `🟢 Live Razorpay API`) and the **🔄 Sync Data** button.
  2. Point to the **4 Executive KPI Cards**:
     - `3-Way Match Rate (81.5%)`
     - `MDR Fee Leakage` (overcharges caught)
     - `Active Exceptions` (refunds, disputes, in-transit)
     - `7-Day Liquidity Forecast` (projected bank payout)
  3. Click through the tabs:
     - **3-Way Reconciliation Ledger**: Show the 9-column matched table.
     - **Fee Leakage Audit**: Show the red-highlighted overcharge rows where actual fee exceeded contract.
     - **Tax-Line Matcher**: Show Intra-State vs Inter-State GST breakdown and Section 194-O TDS compliance.
     - **Cashflow Forecaster**: Show 7-day rolling settlement liquidity.

* **🗣️ Spoken Script:**  
  > *"Welcome to the Executive Finance Workspace.*  
  >  
  > *At the top, our **Dual Ingestion Engine** lets us toggle seamlessly between our 65-record benchmark and live Razorpay REST APIs with a 60-second caching layer.*  
  >  
  > *Our **Executive KPI Cards** immediately tell the CFO their cash position: our automated match rate, cumulative fee leakage caught, active exceptions, and 7-day projected liquidity.*  
  >  
  > *In the **3-Way Reconciliation Ledger**, every transaction is unified across ERP Billed amount, Razorpay fees, and Bank UTR deposits.*  
  >  
  > *Under **Fee Leakage Audit**, the engine calculates statutory 2.0% MDR plus 18% GST down to the exact paisa, instantly flagging overcharges when a gateway mistakenly charges 3.5%.*  
  >  
  > *And in our **Tax Matcher**, we audit Intra-State CGST/SGST versus Inter-State IGST splits and enforce Section 194-O 1% TDS deductions—achieving 100% precision and recall on compliance."*

---

### **[1:45 – 2:45] Minute 3: Evidence DAG, Fault Attribution & Self-Healing**

* **🖥️ Screen Action:**  
  1. Switch back to **3-Way Reconciliation** or **Exceptions & Triage**.
  2. Click the blue **"View Evidence"** button on an exception record (e.g., `ord_1065` or `ord_1063`).
  3. The **Evidence Audit Trail Modal** pops up:
     - Point to the **4-Stage Money Flow Inspector** (`ERP ⟶ Gateway ⟶ Fee ⟶ Bank`).
     - Point to the **Fault Attribution Card** (highlighting `🔴 RAZORPAY_GATEWAY_FAULT` or `🔵 MERCHANT_USER_FAULT`).
     - Show the **Self-Healing Drawer**: Edit the amount/state, click **"Save & Instant Re-Reconcile ⚡"**, and show the status turn green!
     - Scroll down to show the **NetworkX Knowledge Graph Subtree**.

* **🗣️ Spoken Script:**  
  > *"Let's inspect how the system handles exceptions.*  
  >  
  > *When I click **'View Evidence'** on a flagged transaction, the platform renders our **Evidence Audit Trail Modal**.*  
  >  
  > *Instead of raw SQL logs, an auditor sees the full **4-Stage Money Flow**: ERP Invoicing, Gateway Capture, MDR Deduction, and Bank Settlement.*  
  >  
  > *Notice our **Automated Fault Attribution**: It doesn't just say 'unmatched'. It isolates whether the fault is `RAZORPAY_GATEWAY_FAULT`—like an overcharged fee that automatically generates an audit-proof dispute packet—or `MERCHANT_USER_FAULT` from an ERP typo.*  
  >  
  > *Even better, our **Self-Healing Drawer** allows the merchant to correct invoice details directly inline. With one click, it fires a reverification request, re-runs our matching engine, and instantly turns the exception into a verified reconciled record."*

---

### **[2:45 – 3:45] Minute 4: Deep-Dive Architectural Challenges & Solutions**
*(Directly citing the Architectural Challenges & Engineering Solutions Log)*

* **🖥️ Screen Action:**  
  Navigate to the **Ground Truth & Trust** tab (`#tab-metrics`). Show the **Confusion Matrix** (Precision, Recall, F1) and the **Model Trust & Confidence Calibration** grid.

* **🗣️ Spoken Script:**  
  > *"Solving financial reconciliation required overcoming deep architectural roadblocks documented in our engineering log:*  
  >  
  > * **Challenge 1: The Many-to-One Settlement Dilemma**:  
  >   *In the real world, banks do not receive 1:1 transaction deposits. Razorpay batches dozens of payments together into single lump-sum settlements. Standard SQL joins fail completely. We engineered a **3-Pass Deterministic Matcher**: Pass 1 does exact joins, Pass 2 applies sliding-window tolerance heuristics, and Pass 3 runs a **Subset-Sum Combinatorial Solver** that uses dynamic programming to mathematically prove which combination of payments sums to the net bank batch credit.*  
  >  
  > * **Challenge 2: Eliminating LLM Hallucinations**:  
  >   *LLMs notoriously hallucinate when asked to compute arithmetic. We adopted the strict rule: **'Code decides, ML flags, LLM narrates.'** The Python NetworkX graph computes ground truth and extracts bounded subgraphs. The LLM is forbidden from doing math; it strictly translates proven subgraphs into executive English.*  
  >  
  > * **Challenge 3: Model Trust & Confidence Calibration**:  
  >   *Machine learning models are frequently overconfident on edge cases. In this tab, we group model predictions into 4 confidence bins, computing empirical real-world accuracy per bin with low-sample safety guardrails so finance operators never place blind trust in the model.*  
  >  
  > * **Challenge 4: UI/UX & Decoupling**:  
  >   *We completely redesigned the UI from a cramped dark layout into Razorpay's corporate White & Blue theme, decoupled the architecture with dynamic CORS interceptors, and converted the chatbot into a floating widget to preserve 100% screen width for financial tables.*"

---

### **[3:45 – 4:30] Minute 5: Autonomous AI Copilot Live Demo**

* **🖥️ Screen Action:**  
  Click the floating **💬 CFO Copilot** bubble in the bottom-right corner.  
  Click the preset chip or type:  
  `"Which payments need human review and why?"`  
  Watch the streamed response generate with specific order IDs, failure root causes, and recovery instructions.

* **🗣️ Spoken Script:**  
  > *"Now let's see our Autonomous Copilot in action.*  
  >  
  > *Previously, AI finance bots were rigid—asking for an order ID whenever you asked a question. We re-engineered our query dispatcher with global state context.*  
  >  
  > *I simply click **'Which payments need human review?'***  
  >  
  > *Powered by Groq-accelerated **Llama 3.3 70B**, the agent immediately analyzes the active reconciliation state, filters for records below our 85% confidence threshold, and breaks down the exact issues: separating gateway fee overcharges from in-transit settlements and chargeback holds.*  
  >  
  > *It gives the operations team immediate, actionable recovery steps without requiring manual SQL queries or spreadsheet lookup."*

---

### **[4:30 – 5:00] Conclusion & Business Impact**

* **🖥️ Screen Action:**  
  Close the chat widget, scroll up to the top summary, and show the clean reconciled ledger.

* **🗣️ Spoken Script:**  
  > *"In summary, the RazorpayX AI Finance Controller turns financial reconciliation from an error-prone, multi-day manual chore into an autonomous, real-time, audit-proof system.*  
  >  
  > *With 96.9% ground truth accuracy, automated fee leakage recovery, statutory GST compliance, and self-healing dispute resolution, we provide CFOs with complete confidence over their cash position.*  
  >  
  > *Thank you for watching!"*

---

## 📚 Technical Terms Cheat Sheet for Recording

| Term | How to Explain in Simple English |
| :--- | :--- |
| **3-Way Reconciliation** | Cross-checking internal ERP Invoices against Razorpay Gateway logs and Bank Statements to prove every rupee billed was deposited. |
| **UTR (Unique Transaction Reference)** | The official 16–22 character tracking code generated by banks for every NEFT, RTGS, or UPI money deposit. |
| **MDR (Merchant Discount Rate)** | The processing fee charged by Razorpay (contracted at 2.0% + 18% GST). |
| **Fee Leakage** | Hidden overcharges where a gateway silently charges higher fees (e.g. 3.5% instead of 2.0%). |
| **Subset-Sum Solver** | A computer science algorithm that solves the puzzle of finding which combination of small customer payments adds up to one bulk bank deposit. |
| **GraphRAG** | Grounding the LLM in a verified knowledge graph of financial nodes and edges so the AI cannot hallucinate numbers. |
| **Fault Attribution** | Automatically classifying whether an anomaly was caused by the payment gateway (`GATEWAY_FAULT`) or internal accounting typos (`USER_FAULT`). |
| **Self-Healing** | Allowing finance operators to correct data inline and trigger instant real-time re-matching without restarting data pipelines. |
| **T+2 Settlement Cycle** | "Transaction Day + 2 Business Days"—the standard schedule under which gateway funds settle into bank accounts. |
