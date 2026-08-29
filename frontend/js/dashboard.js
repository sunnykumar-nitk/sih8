// Shared config + dashboard page logic
const API_BASE = "/api";

async function fetchPriorityQueue() {
  const res = await fetch(`${API_BASE}/priority`);
  if (!res.ok) throw new Error("Failed to fetch priority queue");
  return res.json();
}

function levelBadge(level) {
  return `<span class="badge ${level}">${level}</span>`;
}

async function renderDashboard() {
  const cardsEl = document.getElementById("summaryCards");
  const tbody = document.querySelector("#priorityTable tbody");
  if (!cardsEl || !tbody) return; // not on dashboard page

  try {
    const sites = await fetchPriorityQueue();
    const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    sites.forEach(s => { counts[s.priority_level] = (counts[s.priority_level] || 0) + 1; });

    const totalPeople = sites.reduce((sum, s) => sum + (s.population_data?.estimated_affected_population || 0), 0);
    const totalPersonnel = sites.reduce((sum, s) => sum + (s.team_size?.total_personnel || 0), 0);

    cardsEl.innerHTML = `
      <div class="card"><div class="label">Critical</div><div class="value" style="color:#e5484d">${counts.CRITICAL}</div></div>
      <div class="card"><div class="label">High</div><div class="value" style="color:#ff9500">${counts.HIGH}</div></div>
      <div class="card"><div class="label">Medium</div><div class="value" style="color:#f0c93a">${counts.MEDIUM}</div></div>
      <div class="card"><div class="label">Low</div><div class="value" style="color:#33c07c">${counts.LOW}</div></div>
      <div class="card"><div class="label">Total Assessed</div><div class="value">${sites.length}</div></div>
      <div class="card"><div class="label">People Potentially Affected</div><div class="value" style="font-size:22px;">${totalPeople.toLocaleString()}</div></div>
      <div class="card"><div class="label">Personnel Needed</div><div class="value" style="font-size:22px;">${totalPersonnel}</div></div>
    `;

    tbody.innerHTML = sites.map(s => `
      <tr class="site-row" data-site="${s.site_id.replace(/"/g, '&quot;')}" style="cursor:pointer;" title="Click to ask the AI Assistant about this site">
        <td>${s.site_id}</td>
        <td>${s.asset_type || "-"}</td>
        <td>${s.priority_score}</td>
        <td>${levelBadge(s.priority_level)}</td>
        <td>${(s.explanation || s.reason || "").slice(0, 60)}</td>
      </tr>
    `).join("") || `<tr><td colspan="5">No sites assessed yet. Go to Assessments to add one.</td></tr>`;

    tbody.querySelectorAll(".site-row").forEach(row => {
      row.addEventListener("click", () => {
        const site = row.dataset.site;
        window.location.href = `assistant.html?ask=${encodeURIComponent(`Why is ${site} ranked the way it is?`)}`;
      });
    });
  } catch (e) {
    cardsEl.innerHTML = `<div class="card"><div class="label">Error</div><div class="value" style="font-size:14px;color:#e5484d">Could not reach API at ${API_BASE}. Is the backend running?</div></div>`;
  }
}

document.addEventListener("DOMContentLoaded", renderDashboard);

// ---- Teams page logic (shared file to avoid a build step) ----
async function loadTeams() {
  const tbody = document.querySelector("#teamsTable tbody");
  if (!tbody) return;
  const res = await fetch(`${API_BASE}/teams`);
  const teams = await res.json();
  tbody.innerHTML = teams.map(t => `
    <tr><td>${t.team_id}</td><td>${t.specialization}</td><td>${t.location ? t.location.lat + ", " + t.location.lon : "-"}</td></tr>
  `).join("") || `<tr><td colspan="3">No teams registered yet.</td></tr>`;
}

document.addEventListener("DOMContentLoaded", () => {
  const teamForm = document.getElementById("teamForm");
  if (teamForm) {
    loadTeams();
    teamForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        team_id: document.getElementById("team_id").value,
        specialization: document.getElementById("specialization").value,
        location: {
          lat: parseFloat(document.getElementById("team_lat").value),
          lon: parseFloat(document.getElementById("team_lon").value),
        },
      };
      await fetch(`${API_BASE}/teams`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      loadTeams();
    });
  }

  const allocateBtn = document.getElementById("allocateBtn");
  if (allocateBtn) {
    allocateBtn.addEventListener("click", async () => {
      const res = await fetch(`${API_BASE}/allocate`, { method: "POST" });
      const assignments = await res.json();
      const tbody = document.querySelector("#allocationTable tbody");
      tbody.innerHTML = assignments.map(a => `
        <tr><td>${a.site_id}</td><td>${a.team_id || "UNASSIGNED"}</td><td>${a.match_score}</td></tr>
      `).join("") || `<tr><td colspan="3">No sites or teams yet.</td></tr>`;
    });
  }
});
