const API_BASE_A = "/api";
const MAX_IMAGES = 10;
const MAX_VIDEOS = 10;
let selectedFiles = [];

function isVideoFile(name) {
  return /\.(mp4|mov|avi|mkv|webm)$/i.test(name);
}

// Never render NaN / undefined / null / Infinity to the user -- show a
// plain "Data unavailable" instead (see PROJECT feedback: "NaN" was showing
// up for population density / households affected with no location).
function _fmtStat(value, suffix) {
  const n = Number(value);
  if (value === undefined || value === null || !Number.isFinite(n)) {
    return "Data unavailable";
  }
  return n.toLocaleString() + (suffix ? " " + suffix : "");
}

// --- Location picker + live population preview ---------------------------
// Known demo disaster locations, so a click near them (or a preset button)
// lands on a spot the population service actually has reference data for.
const DEMO_LOCATIONS = {
  "Nepal Flood (Kathmandu)": [27.7050, 85.3100],
  "Assam Flood (Guwahati)": [26.1445, 91.7362],
  "Ahmedabad Crash": [23.0300, 72.5750],
};

let pickerMap, pickerMarker, popPreviewTimer;

function initLocationPicker() {
  const el = document.getElementById("locationPicker");
  if (!el || typeof L === "undefined") return;

  pickerMap = L.map("locationPicker").setView([20.5, 80.0], 4);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(pickerMap);

  pickerMap.on("click", (e) => setPickedLocation(e.latlng.lat, e.latlng.lng));

  // Quick-jump buttons for the three demo scenarios
  const DemoControl = L.Control.extend({
    onAdd: function () {
      const div = L.DomUtil.create("div", "leaflet-bar");
      div.style.background = "#FFFFFF";
      div.style.padding = "4px";
      div.style.display = "flex";
      div.style.flexDirection = "column";
      div.style.gap = "3px";
      Object.entries(DEMO_LOCATIONS).forEach(([name, [lat, lon]]) => {
        const btn = L.DomUtil.create("button", "", div);
        btn.textContent = name;
        btn.type = "button";
        btn.style.cssText = "font-size:10.5px;padding:4px 8px;background:#FFF7ED;color:#111827;border:1px solid #E5E7EB;border-radius:5px;cursor:pointer;white-space:nowrap;";
        L.DomEvent.on(btn, "click", (ev) => {
          L.DomEvent.stopPropagation(ev);
          pickerMap.setView([lat, lon], 12);
          setPickedLocation(lat, lon);
        });
      });
      return div;
    },
  });
  new DemoControl({ position: "topright" }).addTo(pickerMap);
}

function setPickedLocation(lat, lon) {
  lat = Math.round(lat * 10000) / 10000;
  lon = Math.round(lon * 10000) / 10000;
  document.getElementById("lat").value = lat;
  document.getElementById("lon").value = lon;

  if (pickerMarker) pickerMap.removeLayer(pickerMarker);
  pickerMarker = L.marker([lat, lon]).addTo(pickerMap);

  fetchPopulationPreview(lat, lon);
}

async function fetchPopulationPreview(lat, lon) {
  const box = document.getElementById("popPreview");
  box.className = "pop-preview show";
  box.innerHTML = `<div style="color:var(--text-secondary)">Looking up population context...</div>`;
  try {
    const res = await fetch(`${API_BASE_A}/population?lat=${lat}&lon=${lon}`);
    const pop = await res.json();
    const isReal = pop.data_label && pop.data_label.startsWith("REFERENCE");
    box.innerHTML = `
      <div class="row"><span class="k">Data source</span><span class="v" style="color:${isReal ? 'var(--low)' : '#ffce6b'}">${pop.data_label}</span></div>
      ${pop.region_matched ? `<div class="row"><span class="k">Region matched</span><span class="v">${pop.region_matched}</span></div>` : ""}
      <div class="row"><span class="k">Est. affected population</span><span class="v">${Number(pop.estimated_affected_population).toLocaleString()}</span></div>
      <div class="row"><span class="k">Population density</span><span class="v">${Number(pop.population_density).toLocaleString()} /km²</span></div>
      <div class="row"><span class="k">Households affected</span><span class="v">${Number(pop.households_affected).toLocaleString()}</span></div>
    `;
  } catch (e) {
    box.innerHTML = `<span style="color:#DC2626">Could not fetch population data.</span>`;
  }
}

// Manual lat/lon typing also updates the map pin + preview
function wireManualLatLon() {
  const latEl = document.getElementById("lat");
  const lonEl = document.getElementById("lon");
  function syncFromInputs() {
    const lat = parseFloat(latEl.value), lon = parseFloat(lonEl.value);
    if (!isNaN(lat) && !isNaN(lon) && pickerMap) {
      pickerMap.setView([lat, lon], 11);
      if (pickerMarker) pickerMap.removeLayer(pickerMarker);
      pickerMarker = L.marker([lat, lon]).addTo(pickerMap);
      clearTimeout(popPreviewTimer);
      popPreviewTimer = setTimeout(() => fetchPopulationPreview(lat, lon), 400);
    }
  }
  latEl.addEventListener("change", syncFromInputs);
  lonEl.addEventListener("change", syncFromInputs);
}

function wireDisasterTypeHint() {
  const select = document.getElementById("disaster_type");
  const conditionsInput = document.getElementById("disaster_conditions");
  const hint = document.getElementById("disasterConditionsHint");
  if (!select || !hint) return;
  function sync() {
    if (select.value === "generic") {
      hint.textContent = "-- used as-is (manual slider)";
      conditionsInput.disabled = false;
      conditionsInput.style.opacity = "1";
    } else {
      hint.textContent = "-- auto-computed from photo evidence for this disaster type; slider ignored";
      conditionsInput.disabled = true;
      conditionsInput.style.opacity = "0.5";
    }
  }
  select.addEventListener("change", sync);
  sync();
}

document.addEventListener("DOMContentLoaded", () => {
  initLocationPicker();
  wireManualLatLon();
  wireDisasterTypeHint();

  const dropZone = document.getElementById("uploadDrop");
  const fileInput = document.getElementById("fileInput");
  const fileListEl = document.getElementById("fileList");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const uploadStatus = document.getElementById("uploadStatus");

  if (!dropZone) return; // not on the assessment page

  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("dragover"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    addFiles(Array.from(e.dataTransfer.files));
  });
  fileInput.addEventListener("change", () => addFiles(Array.from(fileInput.files)));

  function addFiles(newFiles) {
    let imgCount = selectedFiles.filter(f => !isVideoFile(f.name)).length;
    let vidCount = selectedFiles.filter(f => isVideoFile(f.name)).length;
    let rejected = 0;
    for (const f of newFiles) {
      if (isVideoFile(f.name)) {
        if (vidCount >= MAX_VIDEOS) { rejected++; continue; }
        vidCount++;
      } else {
        if (imgCount >= MAX_IMAGES) { rejected++; continue; }
        imgCount++;
      }
      selectedFiles.push(f);
    }
    if (rejected > 0) {
      uploadStatus.textContent = `${rejected} file(s) skipped -- limit is ${MAX_IMAGES} photos + ${MAX_VIDEOS} videos.`;
    }
    renderFileList();
  }

  function renderFileList() {
    const imgCount = selectedFiles.filter(f => !isVideoFile(f.name)).length;
    const vidCount = selectedFiles.filter(f => isVideoFile(f.name)).length;
    fileListEl.innerHTML = selectedFiles.map((f, i) => {
      const isVideo = isVideoFile(f.name);
      return `<span class="file-chip">${isVideo ? "🎬" : "🖼️"} ${f.name} <a href="#" data-idx="${i}" style="color:#DC2626;text-decoration:none;">✕</a></span>`;
    }).join("") + (selectedFiles.length ? `<div style="font-size:11px;color:var(--text-secondary);margin-top:6px;">${imgCount} / ${MAX_IMAGES} photos, ${vidCount} / ${MAX_VIDEOS} videos selected</div>` : "");

    fileListEl.querySelectorAll("a[data-idx]").forEach(a => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        selectedFiles.splice(parseInt(a.dataset.idx), 1);
        renderFileList();
      });
    });

    analyzeBtn.disabled = selectedFiles.length === 0;
  }

  analyzeBtn.addEventListener("click", async () => {
    const caseName = document.getElementById("case_name").value.trim();
    if (!caseName) {
      uploadStatus.textContent = "Enter a case name first (e.g. \"Nepal Flood\").";
      return;
    }
    if (selectedFiles.length === 0) return;

    analyzeBtn.disabled = true;
    uploadStatus.textContent = `Analyzing ${selectedFiles.length} file(s) -- extracting video frames and running detection...`;
    document.getElementById("resultCard").innerHTML = "";

    const formData = new FormData();
    selectedFiles.forEach(f => formData.append("files", f));
    formData.append("case_name", caseName);
    formData.append("asset_type", document.getElementById("asset_type").value);
    const lat = document.getElementById("lat").value;
    const lon = document.getElementById("lon").value;
    if (lat) formData.append("lat", lat);
    if (lon) formData.append("lon", lon);
    formData.append("accessibility", document.getElementById("accessibility").value);
    formData.append("disaster_type", document.getElementById("disaster_type").value);
    formData.append("disaster_conditions", document.getElementById("disaster_conditions").value);

    try {
      const res = await fetch(`${API_BASE_A}/upload-batch`, { method: "POST", body: formData });
      if (!res.ok) throw new Error(await res.text());
      const result = await res.json();
      uploadStatus.textContent = `Done -- analyzed ${result.total_frames_analyzed} frame(s) across ${result.files_processed.length} file(s).`;
      renderResultCard(result);
    } catch (err) {
      uploadStatus.innerHTML = `<span style="color:#DC2626">Analysis failed: ${err.message}</span>`;
    } finally {
      analyzeBtn.disabled = false;
    }
  });
});

function renderResultCard(r) {
  const levelColors = { CRITICAL: "#DC2626", HIGH: "#F97316", MEDIUM: "#F59E0B", LOW: "#16A34A" };
  const levelIcons = { CRITICAL: "🔴", HIGH: "🟠", MEDIUM: "🟡", LOW: "🟢" };
  const color = levelColors[r.priority_level] || "#6B7280";

  const imgUrl = r.preview_image_path
    ? `${API_BASE_A}/preview-image?path=${encodeURIComponent(r.preview_image_path)}`
    : null;

  const breakdown = r.breakdown || {};
  const breakdownMax = r.breakdown_max || {};
  const factorLabels = {
    damage_severity: "Damage Severity",
    population_impact: "Population Impact",
    infrastructure_importance: "Infrastructure Importance",
    accessibility: "Accessibility",
    disaster_conditions: "Disaster Conditions",
    critical_facility_impact: "Critical Facility Impact",
    cascading_impact: "Cascading Impact",
    human_impact: "Human Impact",
    time_sensitivity: "Time Sensitivity",
    alternative_route_risk: "Alternative Route Risk",
    data_confidence: "Data Confidence",
  };

  // show only the factors with a meaningful weight, top 6, in the mockup's order
  const orderedKeys = ["damage_severity", "population_impact", "infrastructure_importance", "accessibility", "critical_facility_impact", "cascading_impact"];

  const breakdownHtml = orderedKeys.filter(k => breakdownMax[k] > 0).map(k => {
    const val = breakdown[k] || 0;
    const max = breakdownMax[k] || 1;
    const pct = Math.min(100, (val / max) * 100);
    return `
      <div class="bar-row">
        <div class="bar-label">${factorLabels[k] || k}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%; background:${color};"></div></div>
        <div class="bar-value">${val.toFixed(1)}/${max.toFixed(0)}</div>
      </div>`;
  }).join("");

  const mitigationHtml = (r.temporary_mitigation || []).map(m => `<li>${m}</li>`).join("");

  const cascadeHtml = r.cascading_explanation ? `
    <div class="card-section">
      <h3>Cascading Impact</h3>
      <div class="rec-line">${r.cascading_explanation}</div>
      ${(r.nearby_critical_facilities || []).length ? `<div style="margin-top:6px;">${r.nearby_critical_facilities.map(n => `<span class="file-chip">${n}</span>`).join("")}</div>` : ""}
    </div>` : "";

  const dfa = r.disaster_factor_analysis || null;
  const disasterFactorHtml = (dfa && r.disaster_type && r.disaster_type !== "generic") ? `
    <div class="card-section">
      <h3>Disaster-Specific Factors -- ${r.disaster_type.replace(/_/g, " ").toUpperCase()}</h3>
      <div class="stat-row"><span class="k">Evidence-based score</span><span class="v">${dfa.disaster_conditions} / 10</span></div>
      ${(dfa.matched_factors || []).length ? `<div class="rec-line" style="margin-top:6px;">Matched: ${dfa.matched_factors.join(", ")}</div>` : ""}
      ${dfa.explanation ? `<div class="rec-line" style="color:var(--text-secondary);">${dfa.explanation}</div>` : ""}
    </div>` : "";

  const roleLabels = {
    structural_engineers: "Structural Engineer(s)",
    road_flood_engineers: "Road/Flood Engineer(s)",
    fire_safety_officers: "Fire Safety Officer(s)",
    medical_personnel: "Medical Personnel",
    drone_operator: "Drone Operator",
    general_responders: "General Responders",
  };
  const teamSize = r.team_size || null;
  const teamSizeHtml = teamSize ? `
    <div class="card-section" style="border-bottom:none;">
      <h3>Recommended Team Size -- ${teamSize.total_personnel} personnel</h3>
      ${Object.entries(teamSize.roles).map(([role, count]) => `
        <div class="stat-row"><span class="k">${roleLabels[role] || role}</span><span class="v">${count}</span></div>
      `).join("")}
      <div class="rec-line" style="margin-top:8px; color:var(--text-secondary);">${teamSize.reason}</div>
    </div>` : "";

  const popData = r.population_data || {};
  const coverage = r.image_coverage || null;
  const popHtml = popData.estimated_affected_population !== undefined ? `
    <div class="card-section">
      <h3>Population Context <span style="text-transform:none;color:${(popData.data_label||"").startsWith("REFERENCE") ? "var(--low)" : "#ffce6b"};font-weight:600;">(${popData.data_label || "unknown"})</span></h3>
      <div class="stat-row"><span class="k">Estimated affected population</span><span class="v">${_fmtStat(popData.estimated_affected_population)}</span></div>
      <div class="stat-row"><span class="k">Population density</span><span class="v">${_fmtStat(popData.population_density, "/km²")}</span></div>
      <div class="stat-row"><span class="k">Households affected</span><span class="v">${_fmtStat(popData.households_affected)}</span></div>
      ${coverage ? `
      <div class="stat-row" style="margin-top:8px;"><span class="k">Estimated affected area (from imagery)</span><span class="v">${coverage.estimated_affected_area_km2} km²</span></div>
      <div class="stat-row"><span class="k">Visible damage coverage</span><span class="v">${(coverage.avg_affected_fraction * 100).toFixed(0)}% of surveyed area</span></div>
      <div class="rec-line" style="margin-top:6px; font-size:12px; color:var(--text-secondary);">Based on ${r.files_processed.length} file(s) at an assumed ${coverage.area_per_file_km2} km² coverage each -- population estimate scales with how much flood/fire/debris is actually visible, not just the pin location.</div>
      ` : ""}
    </div>` : "";

  const html = `
    <div class="card-shell">
      <div class="card-header">SITE ASSESSMENT -- ${r.site_id.toUpperCase()}</div>

      <div class="card-top">
        <div class="card-image">
          ${imgUrl ? `<img src="${imgUrl}" alt="Site preview">` : `<div style="height:150px;display:flex;align-items:center;justify-content:center;color:var(--text-secondary);font-size:12px;">No preview available</div>`}
          <div class="cap">AI DETECTION -- ${r.files_processed.length} file(s), ${r.total_frames_analyzed} frame(s) analyzed</div>
        </div>
        <div class="card-stats">
          <div class="stat-row"><span class="k">Infrastructure</span><span class="v">${(r.asset_type || "-").toUpperCase()}</span></div>
          <div class="stat-row"><span class="k">Damage</span><span class="v">${(r.dominant_damage_type || "-").replace(/_/g, " ")}</span></div>
          <div class="stat-row"><span class="k">Severity</span><span class="v">${r.severity_score} / 10 &middot; ${r.severity_score_100 ?? Math.round((r.severity_score || 0) * 10 * 10) / 10} / 100 (${r.severity_label})</span></div>
          <div class="stat-row"><span class="k">Priority</span><span class="v">${r.priority_score} / 100</span></div>
          <div class="stat-row"><span class="k">Status</span><span class="v"><span class="status-pill" style="background:${color};color:#FFFFFF;">${levelIcons[r.priority_level] || ""} ${r.priority_level}</span></span></div>
          <div class="stat-row" style="margin-top:10px;"><span class="k">AI Confidence</span><span class="v">${(r.ai_confidence * 100).toFixed(0)}%</span></div>
          <div class="stat-row"><span class="k">Data Confidence</span><span class="v">${r.data_confidence_pct}%</span></div>
        </div>
      </div>

      <div class="card-section">
        <h3>Why ${r.priority_level}?</h3>
        ${breakdownHtml}
      </div>

      ${popHtml}
      ${disasterFactorHtml}
      ${cascadeHtml}

      <div class="card-section">
        <h3>Recommendation</h3>
        <div class="rec-line"><b>${levelIcons[r.priority_level] || ""} ${r.inspection_recommendation || "Inspect"}</b></div>
        <div class="rec-line">Team: ${r.team_equipment.team}</div>
        <div class="rec-line">Equipment: ${r.team_equipment.equipment.join(" + ")}</div>
        <div class="rec-line" style="margin-top:10px;">Immediate safety: ${r.immediate_safety}</div>
        <div class="rec-line">Temporary Mitigation:</div>
        <ul class="mitigation">${mitigationHtml}</ul>
        <div class="rec-line" style="margin-top:10px; color:var(--text-secondary);">Reason: ${r.reason}</div>
      </div>

      ${teamSizeHtml}
    </div>
  `;

  document.getElementById("resultCard").innerHTML = html;
}
