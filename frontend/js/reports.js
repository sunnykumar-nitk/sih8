// Reports page -- built entirely from real /api/sites data. No hard-coded
// site names, numbers, or recommendations anywhere in this file: every
// number rendered is read from a field on the site object returned by the
// backend's recommendation engine. Fields that the pipeline genuinely does
// not produce for a given site (e.g. a computed route/ETA, which only
// exists per-request via POST /api/route) are shown as "Not available"
// rather than invented.

const API_BASE_R = "/api";

let ALL_SITES = [];
let CHART_INSTANCES = [];

// ---------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------

async function fetchSites() {
  const res = await fetch(`${API_BASE_R}/priority`); // already sorted desc by priority_score
  if (!res.ok) throw new Error("Failed to reach the backend API.");
  return res.json();
}

function populateCaseFilter(sites) {
  const sel = document.getElementById("caseFilter");
  const current = sel.value;
  sel.innerHTML = `<option value="__all__">All assessed sites (${sites.length})</option>` +
    sites.map(s => `<option value="${escapeAttr(s.site_id)}">${escapeHtml(s.site_id)}</option>`).join("");
  if ([...sel.options].some(o => o.value === current)) sel.value = current;
}

// ---------------------------------------------------------------------
// Helpers -- every one of these reads real fields, with honest fallbacks
// ---------------------------------------------------------------------

function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(str) { return escapeHtml(str); }

function severityOf(site) { return site.severity_score ?? site.damage_severity ?? null; }
function severityOf100(site) {
  if (site.severity_score_100 !== undefined && site.severity_score_100 !== null) return site.severity_score_100;
  const s10 = severityOf(site);
  return s10 === null ? null : Math.round(s10 * 10 * 10) / 10;
}
function peopleAffected(site) { return site.population_data?.estimated_affected_population ?? 0; }
function teamTotal(site) { return site.team_size?.total_personnel ?? null; }
function actionText(site) {
  return site.reason || site.explanation || site.immediate_safety || site.inspection_recommendation || "No specific action generated yet.";
}
function fmtNum(n, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(n)) return "N/A";
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: digits });
}
function fmtScore10(n) { return (n === null || n === undefined) ? "N/A" : `${fmtNum(n, 1)} / 10`; }
function fmtScore100(n) { return (n === null || n === undefined) ? "N/A" : `${fmtNum(n, 0)} / 100`; }

function badge(level) {
  const lvl = level || "LOW";
  return `<span class="r-badge ${lvl}">${lvl}</span>`;
}

// ---------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------

function renderEmpty() {
  document.getElementById("reportBody").innerHTML = `
    <div class="r-empty">
      <div style="font-size:16px;font-weight:700;color:#1b2333;">No assessment data yet</div>
      <div style="margin-top:6px;">Run an assessment first, then come back here -- this report is built entirely from live assessment results, never placeholder data.</div>
      <a class="r-btn" href="assessment.html" style="text-decoration:none;display:inline-block;">Go to Assessment</a>
    </div>`;
}

function computeSummary(sites) {
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  sites.forEach(s => { counts[s.priority_level] = (counts[s.priority_level] || 0) + 1; });
  const totalPeople = sites.reduce((sum, s) => sum + peopleAffected(s), 0);
  const totalTeams = sites.reduce((sum, s) => sum + (teamTotal(s) || 0), 0);
  // Honest proxy: the pipeline has no explicit "blocked road" flag. What it
  // does compute is accessibility (0-10, higher = harder to reach), so we
  // surface sites that likely need an alternate route rather than
  // fabricating a "blocked routes" count the data doesn't actually contain.
  const hardToReach = sites.filter(s => (s.accessibility ?? 0) >= 7).length;
  return { counts, totalPeople, totalTeams, hardToReach };
}

function renderHeader(sites, disasterType) {
  const now = new Date();
  const types = new Set(sites.map(s => s.disaster_type).filter(Boolean));
  const disasterLabel = types.size === 0 ? (disasterType || "Generic")
    : types.size === 1 ? [...types][0] : "Multiple disaster types";
  const assessmentId = sites.length === 1 ? sites[0].site_id : `ALL-SITES-${now.toISOString().slice(0, 10)}`;

  return `
    <div class="r-header">
      <div class="r-brand">
        <div class="r-logo"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L3 6V11C3 16.5 6.8 21.2 12 22.5C17.2 21.2 21 16.5 21 11V6L12 2Z" stroke="white" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 8V13" stroke="white" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="16" r="0.9" fill="white"/></svg></div>
        <div class="r-title-block">
          <div class="r-name">Daring <span>Dicey</span></div>
          <div class="r-tag">AI-Powered Disaster Response Report</div>
        </div>
      </div>
      <div class="r-meta">
        <div>Assessment ID: <b>${escapeHtml(assessmentId)}</b></div>
        <div>Generated: <b>${now.toLocaleString()}</b></div>
        <div>Disaster Type: <b>${escapeHtml(disasterLabel)}</b></div>
        <div>Total Locations: <b>${sites.length}</b></div>
      </div>
    </div>`;
}

function renderCards(summary, sites) {
  const { counts, totalPeople, totalTeams, hardToReach } = summary;
  return `
    <div class="r-cards">
      <div class="r-card"><div class="r-card-label">Total Sites</div><div class="r-card-value">${sites.length}</div></div>
      <div class="r-card r-critical"><div class="r-card-label">Critical Sites</div><div class="r-card-value">${counts.CRITICAL}</div></div>
      <div class="r-card r-high"><div class="r-card-label">High Priority</div><div class="r-card-value">${counts.HIGH}</div></div>
      <div class="r-card r-accent"><div class="r-card-label">People Potentially Affected</div><div class="r-card-value">${fmtNum(totalPeople)}</div></div>
      <div class="r-card r-accent"><div class="r-card-label">Personnel Required</div><div class="r-card-value">${fmtNum(totalTeams)}</div></div>
      <div class="r-card"><div class="r-card-label">Sites Needing Alt. Route</div><div class="r-card-value">${hardToReach}</div></div>
    </div>`;
}

function renderTable(sites) {
  const rows = sites.map((s, i) => `
    <tr class="r-row" data-site="${escapeAttr(s.site_id)}">
      <td class="r-rank">${i + 1}</td>
      <td>${escapeHtml(s.site_id)}</td>
      <td>${escapeHtml(s.asset_type || "-")}</td>
      <td>${fmtScore10(severityOf(s))} <span class="r-muted">(${fmtScore100(severityOf100(s))})</span></td>
      <td>${fmtNum(peopleAffected(s))}</td>
      <td>${fmtScore10(s.accessibility)}</td>
      <td>${fmtScore100(s.priority_score)}</td>
      <td>${badge(s.priority_level)}</td>
      <td style="max-width:260px;">${escapeHtml(actionText(s)).slice(0, 90)}${actionText(s).length > 90 ? "..." : ""}</td>
    </tr>`).join("");

  return `
    <div class="r-section-title">Site Priority Ranking</div>
    <table class="r-table">
      <thead><tr>
        <th>#</th><th>Site</th><th>Asset</th><th>Severity</th><th>Population</th>
        <th>Accessibility</th><th>Priority</th><th>Level</th><th>Recommended Action</th>
      </tr></thead>
      <tbody>${rows || `<tr><td colspan="9">No sites.</td></tr>`}</tbody>
    </table>
    <div class="r-action-note">Click any row to see full site details.</div>`;
}

function renderCharts() {
  return `
    <div class="r-section-title">Visual Summary</div>
    <div class="r-charts-grid">
      <div class="r-chart-box"><h4>Severity by Site</h4><div class="r-chart-canvas-wrap"><canvas id="chartSeverity"></canvas></div></div>
      <div class="r-chart-box"><h4>Priority Distribution</h4><div class="r-chart-canvas-wrap"><canvas id="chartPriority"></canvas></div></div>
      <div class="r-chart-box"><h4>Population Impact by Site</h4><div class="r-chart-canvas-wrap"><canvas id="chartPopulation"></canvas></div></div>
      <div class="r-chart-box"><h4>Recommended Team Size by Site</h4><div class="r-chart-canvas-wrap"><canvas id="chartTeams"></canvas></div></div>
    </div>`;
}

function renderActionSummary(sites) {
  // Generated purely from real data: top sites by priority_score, using
  // each site's own reason/immediate_safety/cascading_explanation fields.
  // Nothing here is a hard-coded sentence template with invented content.
  const top = [...sites].sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0)).slice(0, 5);
  if (top.length === 0) {
    return `<div class="r-section-title">Immediate Action Required</div><div class="r-action-note">No sites to prioritize yet.</div>`;
  }
  const items = [];
  top.forEach(s => {
    if (s.priority_level === "CRITICAL" || s.priority_level === "HIGH") {
      items.push(`Inspect <b>${escapeHtml(s.site_id)}</b> ${s.priority_level === "CRITICAL" ? "immediately" : "as a high priority"} -- ${escapeHtml(actionText(s))}`);
    }
    if (s.cascading_explanation) {
      items.push(escapeHtml(s.cascading_explanation));
    }
    if ((s.accessibility ?? 0) >= 7) {
      items.push(`Establish an alternate access route to <b>${escapeHtml(s.site_id)}</b> before dispatching additional teams (accessibility score ${fmtScore10(s.accessibility)}).`);
    }
  });
  const deduped = [...new Set(items)].slice(0, 8);
  return `
    <div class="r-section-title">Immediate Action Required</div>
    <ol class="r-action-list">${deduped.map(i => `<li>${i}</li>`).join("")}</ol>
    <div class="r-action-note">Generated automatically from the current assessment/recommendation data -- not pre-written text.</div>`;
}

function renderReport(sites, disasterType) {
  const summary = computeSummary(sites);
  document.getElementById("reportBody").innerHTML = `
    <div class="report-sheet">
      ${renderHeader(sites, disasterType)}
      ${renderCards(summary, sites)}
      ${renderTable(sites)}
      ${renderCharts()}
      ${renderActionSummary(sites)}
    </div>`;

  attachRowHandlers(sites);
  drawCharts(sites);
}

// ---------------------------------------------------------------------
// Charts (Chart.js, loaded via CDN in reports.html)
// ---------------------------------------------------------------------

function destroyCharts() {
  CHART_INSTANCES.forEach(c => c.destroy());
  CHART_INSTANCES = [];
}

function drawCharts(sites) {
  destroyCharts();
  const boxes = document.querySelectorAll(".r-chart-canvas-wrap");
  if (typeof Chart === "undefined") {
    // Chart.js failed to load (e.g. CDN blocked) -- say so instead of a
    // silent blank box, which is what "not generating visuals" looked like.
    boxes.forEach(b => { b.innerHTML = `<div class="r-chart-empty">Chart library failed to load -- check your network/CDN access.</div>`; });
    return;
  }
  if (sites.length === 0) {
    boxes.forEach(b => { b.innerHTML = `<div class="r-chart-empty">No sites selected for this report.</div>`; });
    return;
  }

  const labels = sites.map(s => s.site_id);
  const levelColor = { CRITICAL: "#DC2626", HIGH: "#F97316", MEDIUM: "#F59E0B", LOW: "#16A34A" };

  // Per-bar risk color (red/orange/amber/green) instead of one flat orange,
  // so a critical site's severity bar is visually distinct from a low one.
  const barColors = sites.map(s => levelColor[s.priority_level] || "#F97316");
  const commonOpts = { responsive: true, maintainAspectRatio: false };

  const ctxSeverity = document.getElementById("chartSeverity");
  if (ctxSeverity) {
    CHART_INSTANCES.push(new Chart(ctxSeverity, {
      type: "bar",
      data: { labels, datasets: [{ label: "Severity (0-10)", data: sites.map(s => severityOf(s) ?? 0), backgroundColor: barColors }] },
      options: { ...commonOpts, scales: { y: { beginAtZero: true, max: 10 } }, plugins: { legend: { display: false } } },
    }));
  }

  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  sites.forEach(s => { counts[s.priority_level] = (counts[s.priority_level] || 0) + 1; });
  const ctxPriority = document.getElementById("chartPriority");
  if (ctxPriority) {
    CHART_INSTANCES.push(new Chart(ctxPriority, {
      type: "doughnut",
      data: {
        labels: Object.keys(counts),
        datasets: [{ data: Object.values(counts), backgroundColor: Object.keys(counts).map(k => levelColor[k]) }],
      },
      options: { ...commonOpts },
    }));
  }

  const ctxPop = document.getElementById("chartPopulation");
  if (ctxPop) {
    CHART_INSTANCES.push(new Chart(ctxPop, {
      type: "bar",
      data: { labels, datasets: [{ label: "People Affected", data: sites.map(peopleAffected), backgroundColor: barColors }] },
      options: { ...commonOpts, scales: { y: { beginAtZero: true } }, plugins: { legend: { display: false } } },
    }));
  }

  const ctxTeams = document.getElementById("chartTeams");
  if (ctxTeams) {
    CHART_INSTANCES.push(new Chart(ctxTeams, {
      type: "bar",
      data: { labels, datasets: [{ label: "Personnel", data: sites.map(s => teamTotal(s) ?? 0), backgroundColor: barColors }] },
      options: { ...commonOpts, scales: { x: { beginAtZero: true } }, plugins: { legend: { display: false } }, indexAxis: "y" },
    }));
  }
}

// ---------------------------------------------------------------------
// Site detail drawer
// ---------------------------------------------------------------------

function attachRowHandlers(sites) {
  document.querySelectorAll(".r-row").forEach(row => {
    row.addEventListener("click", () => {
      const site = sites.find(s => s.site_id === row.dataset.site);
      if (site) openDrawer(site);
    });
  });
}

function openDrawer(s) {
  const roles = s.team_size?.roles ? Object.entries(s.team_size.roles).map(([k, v]) => `${v}x ${k.replace(/_/g, " ")}`).join(", ") : "N/A";
  const backdrop = document.createElement("div");
  backdrop.className = "r-drawer-backdrop";
  backdrop.innerHTML = `
    <div class="r-drawer">
      <button class="r-drawer-close" aria-label="Close">&times;</button>
      <h3>${escapeHtml(s.site_id)}</h3>
      ${badge(s.priority_level)}
      <div class="r-drawer-grid">
        <div class="r-stat"><div class="r-stat-label">Severity</div><div class="r-stat-value">${fmtScore10(severityOf(s))} <span class="r-muted">(${fmtScore100(severityOf100(s))})</span></div></div>
        <div class="r-stat"><div class="r-stat-label">Population Impact</div><div class="r-stat-value">${fmtScore10(s.population_impact)}</div></div>
        <div class="r-stat"><div class="r-stat-label">Infrastructure Importance</div><div class="r-stat-value">${fmtScore10(s.infrastructure_importance)}</div></div>
        <div class="r-stat"><div class="r-stat-label">Accessibility</div><div class="r-stat-value">${fmtScore10(s.accessibility)}</div></div>
        <div class="r-stat"><div class="r-stat-label">Priority Score</div><div class="r-stat-value">${fmtScore100(s.priority_score)}</div></div>
        <div class="r-stat"><div class="r-stat-label">Recommended Team</div><div class="r-stat-value">${s.team_size?.total_personnel ?? "N/A"} personnel</div></div>
      </div>
      <div class="r-block"><h5>Coordinates</h5><p>${s.location?.lat != null ? `${s.location.lat}, ${s.location.lon}` : "Not provided"}</p></div>
      <div class="r-block"><h5>Asset Type</h5><p>${escapeHtml(s.asset_type || "N/A")}</p></div>
      <div class="r-block"><h5>Damage Detected</h5><p>${escapeHtml(s.dominant_damage_type || s.severity_label || "N/A")}</p></div>
      <div class="r-block"><h5>People Potentially Affected</h5><p>${fmtNum(peopleAffected(s))}</p></div>
      <div class="r-block"><h5>Team Composition</h5><p>${escapeHtml(roles)}</p></div>
      <div class="r-block"><h5>Recommended Action</h5><p>${escapeHtml(actionText(s))}</p></div>
      ${s.immediate_safety ? `<div class="r-block"><h5>Immediate Safety</h5><p>${escapeHtml(s.immediate_safety)}</p></div>` : ""}
      ${s.temporary_mitigation ? `<div class="r-block"><h5>Temporary Mitigation</h5><p>${escapeHtml(s.temporary_mitigation)}</p></div>` : ""}
      ${s.inspection_recommendation ? `<div class="r-block"><h5>Inspection Recommendation</h5><p>${escapeHtml(s.inspection_recommendation)}</p></div>` : ""}
      ${s.cascading_explanation ? `<div class="r-block"><h5>Cascading Impact</h5><p>${escapeHtml(s.cascading_explanation)}</p></div>` : ""}
      <div class="r-block"><h5>Recommended Route / ETA</h5><p>Not computed for this site yet -- use the route planner on the Live Map page (POST /api/route) to generate one.</p></div>
    </div>`;
  backdrop.addEventListener("click", (e) => { if (e.target === backdrop) backdrop.remove(); });
  backdrop.querySelector(".r-drawer-close").addEventListener("click", () => backdrop.remove());
  document.body.appendChild(backdrop);
}

// ---------------------------------------------------------------------
// Toolbar wiring
// ---------------------------------------------------------------------

function applyFilterAndRender() {
  const filter = document.getElementById("caseFilter").value;
  const disasterType = document.getElementById("disasterTypeSelect").value;
  const sites = filter === "__all__" ? ALL_SITES : ALL_SITES.filter(s => s.site_id === filter);
  if (sites.length === 0) { renderEmpty(); return; }
  renderReport(sites, disasterType);
}

async function loadAndRender() {
  document.getElementById("reportBody").innerHTML = `<div class="r-loading">Loading assessment data...</div>`;
  try {
    ALL_SITES = await fetchSites();
    populateCaseFilter(ALL_SITES);
    if (ALL_SITES.length === 0) { renderEmpty(); return; }
    applyFilterAndRender();
  } catch (e) {
    document.getElementById("reportBody").innerHTML = `<div class="r-empty">Could not reach the backend API (${escapeHtml(e.message)}). Is the server running?</div>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (!document.getElementById("reportBody")) return; // not on reports page

  loadAndRender();
  document.getElementById("refreshBtn").addEventListener("click", loadAndRender);
  document.getElementById("caseFilter").addEventListener("change", applyFilterAndRender);
  document.getElementById("printBtn").addEventListener("click", () => window.print());

  document.getElementById("downloadPdfBtn").addEventListener("click", async () => {
    const btn = document.getElementById("downloadPdfBtn");
    const original = btn.textContent;
    btn.disabled = true; btn.textContent = "Generating...";
    try {
      const filter = document.getElementById("caseFilter").value;
      const payload = {
        case_name: filter === "__all__" ? "assessment" : filter,
        disaster_type: document.getElementById("disasterTypeSelect").value,
      };
      const res = await fetch(`${API_BASE_R}/report`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      window.open(`${API_BASE_R}/report/${data.filename}`, "_blank");
    } catch (err) {
      alert(`PDF generation failed: ${err.message}`);
    } finally {
      btn.disabled = false; btn.textContent = original;
    }
  });
});
