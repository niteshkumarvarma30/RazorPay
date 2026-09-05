# 🎬 5-Minute Video Recording Script
## **Project:** Autonomous AI Finance Controller & 3-Way Reconciliation System
**Event / Track:** Razorpay /buildathon — Track 04: AI Finance Controller  
**Target Duration:** 5 Minutes (~650–750 spoken words at 130–140 words per minute)  
**Live Demo URLs:** [http://localhost:8000](http://localhost:8000) or [http://localhost:3000](http://localhost:3000)

---

## ⏱️ Video Structure at a Glance

| Time | Phase | Focus | What to Show on Screen |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:45** | **The Hook & Problem** | The 3-Way Reconciliation nightmare | Homepage & 3-way badges |
| **0:45 – 1:45** | **Architecture & Tech Stack** | Code Decides, ML Flags, LLM Narrates | System Architecture & Pipeline |
| **1:45 – 2:45** | **Live Feature Demo** | 3-Way table, Evidence Graph, Fee Audit | Table, Graph Modal, Fee Leakage |
| **2:45 – 3:45** | **Roadblocks & Fixes** | What was broken & how we fixed it | Cleaned UI, typography, dual-server |
| **3:45 – 4:30** | **AI Copilot in Action** | Autonomous Q&A without order ID barriers | Floating Copilot chat asking anomaly query |
| **4:30 – 5:00** | **Conclusion & Impact** | Business ROI & Zero Hallucination | KPI overview & summary cards |

---

## 🎙️ Complete Word-for-Word Script with Screen Cues

### **[0:00 – 0:45] Phase 1: The Hook & The Core Problem**

* **🖥️ Screen Action:**  
  Start on the **Home / Overview Page** (`http://localhost:8000`). Hover over the top badges: *"ERP Invoices ⟷ Razorpay Gateway ⟷ Bank Statement"*. Scroll gently down to show the KPI summary cards.

* **🗣️ Spoken Script:**  
  > *"In high-volume digital payments, thousands of transactions happen every minute. But behind the scenes, finance teams face a massive bottleneck: **The Three-Way Reconciliation Nightmare**.*  
  >  
  > *Every business relies on three separate sources of truth: their internal ERP billing invoices, payment gateway records from Razorpay, and bank settlement statements.*  
  >  
  > *When sales spike, manual cross-checking on Excel breaks down completely. Timing drifts, missing webhooks, customer refunds, and gateway fee overcharges silently drain corporate cash flow.*  
  >  
  > *To solve this once and for all, I built the **Autonomous AI Finance Controller**: a production-ready reconciliation and audit platform that brings real-time visibility, automated dispute triage, and AI-powered auditing to corporate finance."*

---

### **[0:45 – 1:45] Phase 2: System Architecture & Core Principles**

* **🖥️ Screen Action:**  
  Navigate to the **System Architecture / Pipeline** section on the homepage, or switch to the main **Executive Dashboard Workspace**.

* **🗣️ Spoken Script:**  
  > *"Our entire system is architected around one core engineering principle:*  
  > ***'Code decides, ML flags, and the LLM narrates.'***  
  > *In finance, you cannot allow an AI to guess numbers or hallucinate financial audits. Mathematical truth must be deterministic.*  
  >  
  > *Our pipeline operates across three foundational tiers:*  
  > 1. *First, an **Ingestion & Normalization Layer** that ingests ERP billing records, Razorpay API transaction reports, and Bank UTR statements.*  
  > 2. *Second, a **Multi-Pass Reconciliation Engine** featuring exact hash joins, fuzzy tolerance matching using Levenshtein distance on order IDs, and a combinatorial subset-sum solver to untangle many-to-one batch bank deposits.*  
  > 3. *Third, an **Auditing & Forecasting Engine** running deterministic MDR fee audits, IsolationForest machine learning for anomaly detection, and a T+2 settlement forecaster.*  
  >  
  > *All of this is served via high-performance **FastAPI** backend microservices and accelerated with **Groq-powered Llama 3.3 70B** for zero-hallucination GraphRAG narration."*

---

### **[1:45 – 2:45] Phase 3: Live Dashboard & Feature Walkthrough**

* **🖥️ Screen Action:**  
  1. Click on the **3-Way Reconciliation** tab. Scroll through matched and unmatched rows.  
  2. Click the blue **"View Evidence"** button on an exception record to open the **Evidence Graph DAG Modal**.  
  3. Close the modal, then click on the **Fee Leakage Auditor** tab. Show the highlighted overcharge rows.  
  4. Click on the **Cashflow Forecaster** tab to show the 7-day rolling projection chart.

* **🗣️ Spoken Script:**  
  > *"Let's see the engine in action.*  
  >  
  > *On our **3-Way Reconciliation** table, every payment is matched across all three channels. Notice this flagged record: when I click **'View Evidence'**, the platform instantly renders an interactive **DAG (Directed Acyclic Graph)** modal.*  
  >  
  > *Instead of an auditor digging through raw SQL databases or endless spreadsheets, they see the exact lifecycle trace: Invoice billed, Razorpay authorized, payout batched, and bank UTR deposited. If a link breaks—like a missing bank credit or an uncaptured webhook—the exact point of failure is isolated in red.*  
  >  
  > *Next, looking at the **Fee Leakage Auditor**: The engine calculates statutory 2.0% MDR plus 18% GST down to the exact paisa. When Razorpay mistakenly deducts 3.5% on standard cards, it is flagged immediately with automated dispute recovery documentation.*  
  >  
  > *And under **Cash Flow Forecaster**, finance leaders get rolling T+2 liquidity predictions with 95% statistical confidence bounds to ensure working capital is always safeguarded."*

---

### **[2:45 – 3:45] Phase 4: Engineering Challenges: What Was Broken & How We Fixed It**

* **🖥️ Screen Action:**  
  Highlight the clean typography, show the responsive corporate theme, and demonstrate smooth interaction without layout jumps.

* **🗣️ Spoken Script:**  
  > *"Building a production-grade financial platform comes with hard real-world engineering challenges. Here are four critical roadblocks we encountered and resolved:*  
  >  
  > * **Issue 1: Broken LaTeX & Mathematical Formatting in UI**  
  >   *Early in development, workflow flowcharts rendered raw uncompiled math notation like `=P Invoices $\longleftrightarrow$ Razorpay`, confusing business users. We refactored the template rendering into clean Unicode indicators and responsive CSS status pills for crisp readability.*  
  >  
  > * **Issue 2: The Chatbot Order ID Bottleneck**  
  >   *Initially, our LLM copilot was too rigid. When asked high-level questions like 'Which payments need human review?', it stubbornly demanded a specific `order_id`. We redesigned our query dispatcher and context-injection layer so the model analyzes the entire reconciliation state simultaneously, summarizing all pending anomalies on demand.*  
  >  
  > * **Issue 3: Dual-Server Port Decoupling & CORS**  
  >   *When decoupling the frontend to run on port 3000 alongside the FastAPI engine on port 8000, API calls were blocked by browser CORS policies and hardcoded paths. We engineered an automatic fetch interceptor in `app.js` and enabled FastAPI `CORSMiddleware` to allow seamless dual-server operation across both ports.*  
  >  
  > * **Issue 4: UI Overlap & Visual Hierarchy**  
  >   *The original chatbot drawer covered critical KPI cards on standard laptop screens. We redesigned the UI into a modern corporate White & Blue executive theme with an unobtrusive, floating collapsible widget.*"

---

### **[3:45 – 4:30] Phase 5: Autonomous AI Copilot Live Demo**

* **🖥️ Screen Action:**  
  Click the floating chatbot icon in the bottom right corner.  
  Click one of the suggested prompts or type:  
  `"Which payments need human review and why?"`  
  Watch the streamed response appear with specific order details, root causes, and recommended steps.

* **🗣️ Spoken Script:**  
  > *"Now, let's test our Autonomous Finance Copilot.*  
  >  
  > *I open our floating assistant and ask: **'Which payments need human review and why?'***  
  >  
  > *Notice that I didn't need to look up a technical transaction hash. The LLM taps directly into our verified evidence subgraphs, filters for records with confidence below 85%, and explains each issue in plain English:*  
  > *It highlights which records suffered bank UTR mismatch, which orders had chargeback holds, and provides clear action items for the settlement team.*  
  >  
  > *This turns complex financial data into immediate operational decisions with zero hallucination."*

---

### **[4:30 – 5:00] Phase 6: Conclusion & Strategic Business Value**

* **🖥️ Screen Action:**  
  Close the chat widget, scroll up to show the top KPI metrics (Total Processed, 81.5% Automated Match Rate, 96.9% Ground Truth Accuracy, Net Recovered Leakage).

* **🗣️ Spoken Script:**  
  > *"To conclude, this system transforms financial reconciliation from a multi-day manual headache into an autonomous, real-time, audit-proof pipeline.*  
  >  
  > *By combining deterministic algorithms with machine learning and explainable AI, we achieve over 96% accuracy, plug revenue leakage, and give CFOs complete control over their money.*  
  >  
  > *Thank you for watching!"*

---

## 💡 Quick Speaker Tips for Recording
1. **Pacing:** Aim for a steady, relaxed pace. Do not rush.
2. **Tab Pre-loading:** Ensure both `http://localhost:8000` and `http://localhost:3000` are already loaded in your browser before starting screen recording.
3. **Cursor Movement:** Use your mouse cursor to intentionally point at numbers, table rows, and the evidence graph when you mention them.
4. **Resolution:** Record at 1080p (1920x1080) with browser zoom at 100% or 90% for maximum clarity.
