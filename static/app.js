// Dynamic API Base for dual-server support (e.g. port 3000 frontend & port 8000 backend)
const API_BASE = (window.location.port === "8000" || window.location.port === "") ? "" : "http://localhost:8000";
const _origFetch = window.fetch;
window.fetch = function(url, options) {
  if (typeof url === "string" && url.startsWith("/api/")) {
    url = API_BASE + url;
  }
  return _origFetch(url, options);
};

// App State
let allReconciliationData = null;
let allExceptions = [];
let currentMode = "synthetic"; // "synthetic" or "live"
let currentModalRecordId = null;
let currentModalFaultData = null;

// Page Gateway Controls
function enterDashboard() {
  const landing = document.getElementById("landing-page");
  const dashboard = document.getElementById("dashboard-app");
  if (landing) landing.style.display = "none";
  if (dashboard) dashboard.style.display = "flex";

  // Load all dashboard components
  loadReconciliation();
  loadFeeAudit();
  loadTaxAudit();
  loadForecast();
  loadMetrics();
  loadCalibration();
}

function returnToHome() {
  const landing = document.getElementById("landing-page");
  const dashboard = document.getElementById("dashboard-app");
  if (dashboard) dashboard.style.display = "none";
  if (landing) landing.style.display = "flex";
}

// Mode Switching (Feature 1)
function setMode(mode) {
  currentMode = mode;
  document.querySelectorAll(".mode-toggle-btn").forEach(b => b.classList.remove("active", "live"));
  
  if (mode === "live") {
    const liveBtn = document.getElementById("btn-mode-live");
    if (liveBtn) liveBtn.classList.add("active", "live");
    const synthBtn = document.getElementById("btn-mode-synth");
    if (synthBtn) synthBtn.classList.remove("active");
  } else {
    const synthBtn = document.getElementById("btn-mode-synth");
    if (synthBtn) synthBtn.classList.add("active");
    const liveBtn = document.getElementById("btn-mode-live");
    if (liveBtn) liveBtn.classList.remove("active");
  }

  loadReconciliation(false);
}

function refreshData() {
  loadReconciliation(true);
}

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));

  const targetTab = document.getElementById(`tab-${tabId}`);
  if (targetTab) targetTab.classList.remove("hidden");

  // Highlight active button
  const activeBtn = Array.from(document.querySelectorAll(".nav-item")).find(b => b.getAttribute("onclick")?.includes(tabId));
  if (activeBtn) activeBtn.classList.add("active");

  const tabTitles = {
    "reconciliation": "3-Way Reconciliation Ledger",
    "exceptions": "Exceptions & Recovery Queue",
    "fee-audit": "Gateway MDR Fee Leakage Audit",
    "tax-audit": "Tax-Line (GST & 194-O TDS) Matcher",
    "forecast": "Rolling Cashflow Forecaster",
    "metrics": "Ground Truth & Model Calibration",
    "investigation": "Autonomous Failure Recovery Agent"
  };
  const titleEl = document.getElementById("active-tab-title");
  if (titleEl && tabTitles[tabId]) {
    titleEl.innerText = tabTitles[tabId];
  }
}

// 1. Fetch Reconciliation Data (Supporting Live Mode)
async function loadReconciliation(forceRefresh = false) {
  try {
    const url = `/api/reconcile?mode=${currentMode}&refresh=${forceRefresh}`;
    const res = await fetch(url);
    const data = await res.json();
    allReconciliationData = data;
    allExceptions = data.exceptions || [];

    // Freshness Banner
    const freshnessEl = document.getElementById("freshness-text");
    if (freshnessEl) freshnessEl.innerText = data.data_freshness;
    
    const badge = document.getElementById("freshness-badge");
    if (badge) {
      if (data.is_live) {
        badge.className = "badge badge-matched";
        badge.innerText = `Live API (${data.summary.live_records_count || 1} Live Records) 🟢`;
      } else {
        badge.className = "badge badge-intransit";
        badge.innerText = "Synthetic Batch 🔵";
      }
    }

    // Update KPI Cards
    const summary = data.summary;
    const matchRateEl = document.getElementById("kpi-match-rate");
    if (matchRateEl) matchRateEl.innerText = `${summary.match_rate_percentage}%`;

    const matchSubEl = document.getElementById("kpi-match-sub");
    if (matchSubEl) matchSubEl.innerText = `${summary.matched_count} of ${summary.total_records} reconciled`;

    const leakageEl = document.getElementById("kpi-leakage");
    if (leakageEl) leakageEl.innerText = `₹${summary.total_fee_leakage_inr.toFixed(2)}`;

    const leakageSubEl = document.getElementById("kpi-leakage-sub");
    if (leakageSubEl) leakageSubEl.innerText = `${summary.overcharge_count} transactions flagged`;

    const exceptionsEl = document.getElementById("kpi-exceptions");
    if (exceptionsEl) exceptionsEl.innerText = `${summary.unmatched_count}`;

    // Render Matched Table
    const matchedBody = document.getElementById("matched-table-body");
    if (matchedBody) {
      matchedBody.innerHTML = "";
      const liveNote = data.is_live ? ` (${data.summary.live_records_count || 1} live)` : "";
      const countEl = document.getElementById("matched-table-count");
      if (countEl) countEl.innerText = `Showing ${data.matched_records.length} records${liveNote}`;

      data.matched_records.forEach(rec => {
        const isLive = rec.source === "live";
        const sourceBadge = isLive 
          ? `<span class="badge-source-live">🟢 Live API</span>` 
          : `<span class="badge-source-synth">🔵 Synth</span>`;

        const tr = document.createElement("tr");
        if (isLive) {
          tr.style.background = "#ecfdf5";
          tr.style.borderLeft = "4px solid #059669";
        }

        tr.innerHTML = `
          <td>${sourceBadge}</td>
          <td><strong>${rec.order_id}</strong><br><small style="color:var(--text-muted)">${rec.invoice_id}</small></td>
          <td><code>${rec.pay_id}</code></td>
          <td>₹${rec.amount_billed.toFixed(2)}</td>
          <td style="color:#dc2626; font-weight:600;">-₹${rec.fee_deducted.toFixed(2)}</td>
          <td style="color:#059669; font-weight:700;">₹${rec.bank_credited.toFixed(2)}</td>
          <td><code>${rec.utr}</code></td>
          <td><span class="badge badge-matched">3-Way Matched</span></td>
          <td><button class="btn-proof" onclick="showEvidenceModal('${rec.order_id}')">Proof 🔗</button></td>
        `;
        matchedBody.appendChild(tr);
      });
    }

    renderExceptionsTable(allExceptions);

  } catch (err) {
    console.error("Error loading reconciliation:", err);
  }
}

// Render Exceptions Table
function renderExceptionsTable(exceptionsList) {
  const excBody = document.getElementById("exceptions-table-body");
  if (!excBody) return;
  excBody.innerHTML = "";

  if (exceptionsList.length === 0) {
    excBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No exceptions found for this filter.</td></tr>`;
    return;
  }

  exceptionsList.forEach(exc => {
    let badgeClass = "badge-unresolved";
    let cat = exc.category;
    if (cat.includes("REFUND")) badgeClass = "badge-refund";
    else if (cat.includes("DISPUTE") || cat.includes("CHARGEBACK")) badgeClass = "badge-dispute";
    else if (cat.includes("IN_TRANSIT")) badgeClass = "badge-intransit";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${exc.order_id}</strong><br><small style="color:var(--text-muted)">${exc.invoice_id || 'N/A'}</small></td>
      <td><span class="badge ${badgeClass}">${exc.category}</span></td>
      <td style="font-weight:700;">${(exc.confidence * 100).toFixed(0)}%</td>
      <td style="color:#d97706; font-weight:700;">₹${exc.discrepancy_inr.toFixed(2)}</td>
      <td style="font-size:0.78rem; color:var(--text-muted)">${exc.action_required}</td>
      <td><button class="btn-proof" onclick="showEvidenceModal('${exc.order_id}')">Audit Graph 🔗</button></td>
    `;
    excBody.appendChild(tr);
  });
}

// Filter Exceptions
function filterExceptions() {
  const filterVal = document.getElementById("exception-filter").value;
  if (filterVal === "ALL") {
    renderExceptionsTable(allExceptions);
  } else {
    const filtered = allExceptions.filter(e => e.category.includes(filterVal));
    renderExceptionsTable(filtered);
  }
}

// 2. Fetch Fee Leakage Audit
async function loadFeeAudit() {
  try {
    const res = await fetch("/api/fee-audit");
    const data = await res.json();

    const tbody = document.getElementById("fee-audit-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!data.flagged_transactions || data.flagged_transactions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No fee overcharges detected.</td></tr>`;
      return;
    }

    data.flagged_transactions.forEach(f => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${f.order_id}</strong></td>
        <td><code>${f.pay_id}</code></td>
        <td>₹${f.amount_captured.toFixed(2)}</td>
        <td style="color:#dc2626; font-weight:600;">₹${f.actual_fee_charged.toFixed(2)}</td>
        <td>₹${f.contracted_expected_fee.toFixed(2)}</td>
        <td><span class="badge badge-refund">${f.effective_mdr_charged_pct}% (Contract: 2%)</span></td>
        <td style="color:#dc2626; font-weight:700;">+₹${f.overcharge_leakage_inr.toFixed(2)}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading fee audit:", err);
  }
}

// 2.5 Fetch Tax-Line (GST & Section 194-O TDS) Audit
async function loadTaxAudit() {
  try {
    const res = await fetch("/api/tax-audit");
    const data = await res.json();

    const headline = document.getElementById("tax-headline-summary");
    if (headline) {
      headline.innerHTML = `⚠️ <strong>Tax Variance:</strong> ₹${data.total_gst_leakage_inr.toFixed(2)} GST Undercollected | ₹${data.total_tds_leakage_inr.toFixed(2)} Missing TDS (${data.flagged_count} flagged invoices)`;
    }

    const tbody = document.getElementById("tax-audit-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!data.tax_exceptions || data.tax_exceptions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">All invoices compliant with Indian GST & TDS rules.</td></tr>`;
      return;
    }

    data.tax_exceptions.forEach(t => {
      const isWrongSplit = t.mismatch_categories.includes("WRONG_GST_SPLIT");
      const isRateMismatch = t.mismatch_categories.includes("GST_RATE_MISMATCH");
      const isTdsMissing = t.mismatch_categories.includes("TDS_194O_MISSING");

      let actualGstStr = t.actual_tax_lines.map(l => `${l.type} ${(l.rate * 100).toFixed(0)}%: ₹${l.amount}`).join(", ");
      let expectedGstStr = t.expected_tax_lines.map(l => `${l.type} ${(l.rate * 100).toFixed(0)}%: ₹${l.amount}`).join(", ");
      let deltaStr = [];
      if (t.gst_leakage_inr > 0) deltaStr.push(`GST: +₹${t.gst_leakage_inr.toFixed(2)}`);
      if (t.tds_leakage_inr > 0) deltaStr.push(`TDS: +₹${t.tds_leakage_inr.toFixed(2)}`);
      if (isWrongSplit && deltaStr.length === 0) deltaStr.push(`Split Mismatch`);

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${t.order_id}</strong><br><small style="color:var(--text-muted)">${t.invoice_id}</small></td>
        <td>₹${t.amount_billed.toFixed(2)}</td>
        <td><span class="badge ${t.transaction_type === 'Intra-State' ? 'badge-matched' : 'badge-intransit'}">${t.transaction_type}</span><br><small style="color:var(--text-muted)">${t.merchant_state} ➔ ${t.customer_state}</small></td>
        <td style="color:${isWrongSplit || isRateMismatch ? '#dc2626' : 'inherit'}; font-weight:600;">${actualGstStr}</td>
        <td style="color:#059669; font-weight:600;">${expectedGstStr}</td>
        <td style="color:${isTdsMissing ? '#dc2626' : 'inherit'}">₹${t.actual_tds.toFixed(2)} / <small style="color:var(--text-muted)">₹${t.expected_tds.toFixed(2)}</small></td>
        <td style="color:#dc2626; font-weight:700;">${deltaStr.join(" | ")}</td>
        <td style="font-size:0.75rem; color:var(--text-muted)">${t.action_required}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading tax audit:", err);
  }
}

// 3. Fetch Forward Cash Forecaster
async function loadForecast() {
  try {
    const res = await fetch("/api/forecast");
    const data = await res.json();

    const kpiEl = document.getElementById("kpi-forecast");
    const total = data.total_projected_7day_inr || data.total_7day_projected_inr || 0;
    if (kpiEl) kpiEl.innerText = `₹${total.toFixed(2)}`;

    const tbody = document.getElementById("forecast-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    data.forecast_timeline.forEach(t => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${t.settlement_date}</strong></td>
        <td><span class="badge badge-intransit">${t.pending_transactions_count} orders</span></td>
        <td>₹${t.gross_projected_inr.toFixed(2)}</td>
        <td style="color:#0284c7; font-weight:700;">₹${t.risk_adjusted_net_inr.toFixed(2)}</td>
        <td><span class="badge badge-intransit">In-Flight T+2</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading forecast:", err);
  }
}

// 4. Fetch Ground Truth Evaluation
async function loadMetrics() {
  try {
    const res = await fetch("/api/metrics");
    const data = await res.json();

    const tbody = document.getElementById("metrics-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    const classes = data.class_level_performance;
    for (const [className, m] of Object.entries(classes)) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${className}</strong></td>
        <td>${m.true_positives}</td>
        <td>${m.false_positives}</td>
        <td style="color:#059669; font-weight:700;">${(m.precision * 100).toFixed(1)}%</td>
        <td style="color:#059669; font-weight:700;">${(m.recall * 100).toFixed(1)}%</td>
        <td style="color:#0284c7; font-weight:700;">${(m.f1_score * 100).toFixed(1)}%</td>
      `;
      tbody.appendChild(tr);
    }
  } catch (err) {
    console.error("Error loading metrics:", err);
  }
}

// Feature 2: Load Confidence Calibration
async function loadCalibration() {
  try {
    const res = await fetch("/api/calibration");
    const data = await res.json();

    const headlineEl = document.getElementById("calibration-headline");
    if (!data.calibration_available) {
      if (headlineEl) headlineEl.innerText = data.message || "Calibration unavailable.";
      return;
    }

    if (headlineEl) {
      headlineEl.innerHTML = `🎯 <strong>Calibration Result:</strong> ${data.headline_summary}`;
    }

    const grid = document.getElementById("calibration-grid");
    if (!grid) return;
    grid.innerHTML = "";

    data.calibration_bins.forEach(bin => {
      const card = document.createElement("div");
      card.style.background = "#f8fafc";
      card.style.border = "1px solid var(--border-light)";
      card.style.borderRadius = "10px";
      card.style.padding = "1rem";

      const accPct = (bin.empirical_accuracy * 100).toFixed(1);
      const confPct = (bin.avg_stated_confidence * 100).toFixed(1);

      card.innerHTML = `
        <div style="font-size:0.78rem; font-weight:700; color:var(--text-muted); margin-bottom:0.25rem;">
          ${bin.bin_label}
        </div>
        <div style="font-size:1.25rem; font-weight:800; color:#0c2340; margin-bottom:0.35rem;">
          ${accPct}% Accuracy
        </div>
        <div style="background:#e2e8f0; height:8px; border-radius:4px; overflow:hidden; margin:0.5rem 0;">
          <div style="height:100%; width:${accPct}%; background:linear-gradient(90deg, #0284c7, #059669); border-radius:4px;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted);">
          <span>Stated: ${confPct}%</span>
          <span>Sample: ${bin.sample_size}</span>
        </div>
      `;
      grid.appendChild(card);
    });

  } catch (err) {
    console.error("Error loading calibration:", err);
  }
}

// 5. Evidence Graph Modal & GraphRAG Narration (Groq Powered)
async function showEvidenceModal(recordId) {
  currentModalRecordId = recordId;
  const modal = document.getElementById("evidence-modal");
  const modalTitle = document.getElementById("modal-title");
  const graphContent = document.getElementById("modal-graph-content");
  const narration = document.getElementById("modal-narration");
  const moneyFlowEl = document.getElementById("modal-money-flow");
  const faultCardEl = document.getElementById("modal-fault-card");
  const selfHealDrawer = document.getElementById("modal-self-heal-drawer");

  modalTitle.innerText = `Evidence Audit Trail & Money Flow for: ${recordId}`;
  graphContent.innerHTML = "Tracing NetworkX Knowledge Graph nodes & edges...";
  narration.innerText = "Narrating evidence trail via Groq Llama 3.3...";
  moneyFlowEl.innerHTML = `<div style="color:var(--text-muted); font-size:0.8rem;">Loading money flow stages...</div>`;
  faultCardEl.innerHTML = `<div style="color:var(--text-muted); font-size:0.8rem;">Analyzing root cause fault...</div>`;
  if (selfHealDrawer) selfHealDrawer.classList.add("hidden");

  modal.classList.remove("hidden");

  try {
    // 1. Fetch Fault Attribution & Money Flow
    const faultRes = await fetch(`/api/fault-attribution/${recordId}`);
    if (faultRes.ok) {
      const faultData = await faultRes.json();
      currentModalFaultData = faultData;

      // Render Money Flow
      moneyFlowEl.innerHTML = "";
      faultData.money_flow.forEach(step => {
        const stepCard = document.createElement("div");
        stepCard.className = `flow-step-box ${step.status}`;
        stepCard.innerHTML = `
          <div class="flow-title">${step.stage}</div>
          <div class="flow-val">₹${step.amount.toFixed(2)}</div>
          <div class="flow-detail">${step.detail}</div>
        `;
        moneyFlowEl.appendChild(stepCard);
      });

      // Render Fault Card
      faultCardEl.className = `fault-box ${faultData.fault_party}`;
      let actionBtnHtml = "";
      if (faultData.action_type === "DISPUTE_CLAIM") {
        actionBtnHtml = `
          <button class="btn-dispute-action" onclick="dispatchDisputeClaim('${faultData.record_id}', ${faultData.fee_overcharge_inr}, '${faultData.dispute_packet.evidence_hash}')">
            🚀 1-Click File Razorpay Dispute (Claim ₹${faultData.fee_overcharge_inr.toFixed(2)})
          </button>
        `;
      } else if (faultData.action_type === "INVOICE_CORRECTION") {
        actionBtnHtml = `
          <button class="btn-heal-action" onclick="toggleSelfHealDrawer()">
            🛠️ Correct Merchant ERP Invoice & Self-Heal ⚡
          </button>
        `;
      }

      faultCardEl.innerHTML = `
        <div class="fault-box-title">${faultData.fault_title}</div>
        <div class="fault-box-desc">${faultData.root_cause}</div>
        <div>${actionBtnHtml}</div>
      `;

      // Pre-fill Self Heal fields
      if (faultData.editable_invoice) {
        document.getElementById("heal-amount").value = faultData.editable_invoice.amount;
        document.getElementById("heal-state").value = faultData.editable_invoice.customer_state;
      }
    }

    // 2. Fetch NetworkX Graph Evidence
    const res = await fetch(`/api/evidence/${recordId}?mode=${currentMode}`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server returned status ${res.status}`);
    }
    const data = await res.json();

    if (!data.nodes || !data.edges) {
      throw new Error("Invalid graph structure received.");
    }

    // Render formatted ASCII / JSON Graph
    let graphText = `[KNOWLEDGE GRAPH SUBTREE]\n`;
    graphText += `Target Entity: ${data.record_id}\n\nNODES (${data.nodes.length}):\n`;
    data.nodes.forEach(n => {
      graphText += `  • [${n.type}] ${n.id} (${JSON.stringify(n)})\n`;
    });

    graphText += `\nEDGES & RELATIONS (${data.edges.length}):\n`;
    data.edges.forEach(e => {
      graphText += `  ➔ ${e.source} ==[${e.relation}]==> ${e.target}\n`;
    });

    graphContent.innerText = graphText;

    // 3. Fetch Narration from Chat
    const chatRes = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: `Explain evidence for ${recordId}` })
    });
    const chatData = await chatRes.json();
    narration.innerText = `🤖 Groq GraphRAG Audit Narration: ${chatData.answer}`;

  } catch (err) {
    graphContent.innerText = `Error retrieving evidence graph: ${err.message || err}`;
    narration.innerText = `Unable to generate narration for ${recordId}.`;
  }
}

function toggleSelfHealDrawer() {
  const drawer = document.getElementById("modal-self-heal-drawer");
  if (drawer) drawer.classList.toggle("hidden");
}

// Action: 1-Click File Razorpay Dispute Claim
async function dispatchDisputeClaim(orderId, amount, hash) {
  try {
    const res = await fetch("/api/dispute-claim", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_id: orderId,
        claim_type: "MDR_FEE_OVERCHARGE_REIMBURSEMENT",
        overcharge_amount_inr: amount,
        evidence_hash: hash
      })
    });
    const data = await res.json();
    const faultCard = document.getElementById("modal-fault-card");
    faultCard.className = "fault-box";
    faultCard.style.border = "1px solid #10b981";
    faultCard.style.background = "#ecfdf5";
    faultCard.innerHTML = `
      <div style="color:#065f46; font-weight:800; font-size:0.95rem; margin-bottom:0.25rem;">
        ✅ Dispute Ticket Dispatched Successfully!
      </div>
      <div style="font-size:0.82rem; color:#0f172a; line-height:1.4;">
        ${data.message}<br>
        <strong>Ticket Reference:</strong> <code>${data.claim_id}</code> | <strong>Claimed:</strong> ₹${data.amount_inr.toFixed(2)}
      </div>
    `;
  } catch (err) {
    alert(`Failed to file dispute: ${err}`);
  }
}

// Action: Self-Healing Invoice Re-Verification
async function submitInvoiceCorrection() {
  if (!currentModalRecordId) return;

  const amount = parseFloat(document.getElementById("heal-amount").value);
  const state = document.getElementById("heal-state").value;
  const btn = document.getElementById("btn-submit-heal");

  btn.innerText = "Re-Verifying with NetworkX Matcher...";
  btn.disabled = true;

  try {
    const res = await fetch("/api/reverify-invoice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_id: currentModalRecordId,
        invoice_id: currentModalFaultData?.invoice_id || `INV-${currentModalRecordId}`,
        amount: amount,
        customer_state: state,
        merchant_state: "Maharashtra",
        pay_id: currentModalFaultData?.payment_id || `pay_${currentModalRecordId}_healed`
      })
    });
    const data = await res.json();

    btn.innerText = "✅ Successfully Reconciled!";
    btn.style.background = "#059669";

    // Refresh Dashboard Data in background
    loadReconciliation(true);
    loadFeeAudit();
    loadTaxAudit();

    // Re-load modal view
    setTimeout(() => {
      showEvidenceModal(currentModalRecordId);
    }, 800);

  } catch (err) {
    alert(`Re-verification error: ${err}`);
    btn.innerText = "Retry";
    btn.disabled = false;
  }
}

function closeModal() {
  document.getElementById("evidence-modal").classList.add("hidden");
}

// Toggle Floating CFO Chatbot Window
function toggleFloatingChat() {
  const chatDrawer = document.getElementById("chat-drawer");
  if (chatDrawer) {
    chatDrawer.classList.toggle("hidden");
    if (!chatDrawer.classList.contains("hidden")) {
      const input = document.getElementById("chat-input");
      if (input) setTimeout(() => input.focus(), 150);
    }
  }
}

// 6. CFO Settlement Q&A Chat
async function sendMessage() {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text) return;

  const chatContainer = document.getElementById("chat-messages");
  
  // Append User message
  const userMsg = document.createElement("div");
  userMsg.className = "message-bubble user";
  userMsg.innerText = text;
  chatContainer.appendChild(userMsg);
  input.value = "";
  chatContainer.scrollTop = chatContainer.scrollHeight;

  // Append Loading
  const loadingMsg = document.createElement("div");
  loadingMsg.className = "message-bubble agent";
  loadingMsg.innerText = "Querying reconciliation engine & Groq LLM...";
  chatContainer.appendChild(loadingMsg);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text })
    });
    const data = await res.json();
    loadingMsg.innerHTML = data.answer;
  } catch (err) {
    loadingMsg.innerText = `Error processing query: ${err}`;
  }
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function askPreset(promptText) {
  const chatDrawer = document.getElementById("chat-drawer");
  if (chatDrawer && chatDrawer.classList.contains("hidden")) {
    chatDrawer.classList.remove("hidden");
  }
  document.getElementById("chat-input").value = promptText;
  sendMessage();
}

// 7. Failure Recovery Demo (Investigation Agent)
async function runInvestigation() {
  const recordId = document.getElementById("investigate-input").value.trim();
  const resDiv = document.getElementById("investigation-result");
  resDiv.style.display = "block";
  resDiv.innerText = "Running autonomous multi-tool investigation agent...";

  try {
    const res = await fetch("/api/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ record_id: recordId })
    });
    const data = await res.json();

    let output = `[AUTONOMOUS INVESTIGATION AGENT TRACE]\n`;
    output += `Target Record: ${data.record_id}\n`;
    output += `Classification: ${data.classification}\n`;
    output += `Confidence: ${(data.confidence * 100).toFixed(1)}%\n`;
    output += `Requires Human Review: ${data.needs_human_review ? '⚠️ YES (Safety Gate Triggered)' : 'NO'}\n\n`;
    output += `REASONING AUDIT LOG:\n`;
    data.reasoning_trace.forEach(t => {
      output += `  ${t}\n`;
    });
    output += `\nRECOMMENDED ACTION:\n  ${data.recommendation}\n`;

    resDiv.innerText = output;
  } catch (err) {
    resDiv.innerText = `Investigation error: ${err}`;
  }
}
