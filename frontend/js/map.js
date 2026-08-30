const API_BASE_M = "/api";

const LEVEL_COLORS = { CRITICAL: "#DC2626", HIGH: "#F97316", MEDIUM: "#F59E0B", LOW: "#16A34A" };

let mainMap;
let routePickMode = null; // "origin" | "destination" | null
let routeOriginMarker = null, routeDestMarker = null;

async function initMap() {
  mainMap = L.map("map").setView([20.5, 80.0], 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(mainMap);

  // Clicking the map, when in "pick origin/destination" mode, sets the
  // road-block simulation's coordinates instead of just panning.
  mainMap.on("click", (e) => {
    if (!routePickMode) return;
    const lat = Math.round(e.latlng.lat * 10000) / 10000;
    const lon = Math.round(e.latlng.lng * 10000) / 10000;
    if (routePickMode === "origin") {
      document.getElementById("routeOriginLat").value = lat;
      document.getElementById("routeOriginLon").value = lon;
      if (routeOriginMarker) mainMap.removeLayer(routeOriginMarker);
      routeOriginMarker = L.marker([lat, lon], { title: "Origin" }).addTo(mainMap).bindPopup("Origin").openPopup();
    } else if (routePickMode === "destination") {
      document.getElementById("routeDestLat").value = lat;
      document.getElementById("routeDestLon").value = lon;
      if (routeDestMarker) mainMap.removeLayer(routeDestMarker);
      routeDestMarker = L.marker([lat, lon], { title: "Destination" }).addTo(mainMap).bindPopup("Destination").openPopup();
    }
    routePickMode = null;
  });

  try {
    const res = await fetch(`${API_BASE_M}/priority`);
    const sites = await res.json();

    if (!sites.length) {
      L.popup().setLatLng([20.5, 80.0]).setContent("No sites assessed yet. Go to Assessments first.").openOn(mainMap);
      return;
    }

    const bounds = [];
    sites.forEach(s => {
      if (!s.location || s.location.lat === undefined) return;
      const color = LEVEL_COLORS[s.priority_level] || "#6B7280";
      const marker = L.circleMarker([s.location.lat, s.location.lon], {
        radius: 10, fillColor: color, color: "#fff", weight: 1, fillOpacity: 0.9,
      }).addTo(mainMap);
      marker.bindPopup(`
        <strong>${s.site_id}</strong><br>
        Priority: ${s.priority_score}/100 (${s.priority_level})<br>
        ${s.explanation || s.reason || ""}
      `);
      bounds.push([s.location.lat, s.location.lon]);
    });
    if (bounds.length) mainMap.fitBounds(bounds, { padding: [40, 40] });
  } catch (e) {
    console.error("Could not load sites for map:", e);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initMap();

  const setOriginBtn = document.getElementById("setOriginBtn");
  const setDestBtn = document.getElementById("setDestBtn");
  const compareBtn = document.getElementById("compareRouteBtn");
  if (!setOriginBtn) return; // not on the map page's road-block panel

  setOriginBtn.addEventListener("click", () => { routePickMode = "origin"; });
  setDestBtn.addEventListener("click", () => { routePickMode = "destination"; });

  compareBtn.addEventListener("click", async () => {
    const originLat = parseFloat(document.getElementById("routeOriginLat").value);
    const originLon = parseFloat(document.getElementById("routeOriginLon").value);
    const destLat = parseFloat(document.getElementById("routeDestLat").value);
    const destLon = parseFloat(document.getElementById("routeDestLon").value);
    const resultEl = document.getElementById("routeResult");

    if ([originLat, originLon, destLat, destLon].some(isNaN)) {
      resultEl.innerHTML = `<span style="color:#DC2626">Set both an origin and a destination first (use the buttons above, then click the map).</span>`;
      return;
    }

    resultEl.innerHTML = `<span style="color:var(--text-secondary)">Calculating routes...</span>`;

    const origin = { lat: originLat, lon: originLon };
    const destination = { lat: destLat, lon: destLon };

    try {
      const [clearRes, blockedRes] = await Promise.all([
        fetch(`${API_BASE_M}/route`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ origin, destination, blocked: false }) }),
        fetch(`${API_BASE_M}/route`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ origin, destination, blocked: true }) }),
      ]);
      const clear = await clearRes.json();
      const blocked = await blockedRes.json();
      const extraMinutes = Math.round((blocked.travel_time_minutes - clear.travel_time_minutes) * 10) / 10;

      resultEl.innerHTML = `
        <div class="cards" style="margin-bottom:0;">
          <div class="card">
            <div class="label">Clear Route</div>
            <div class="value" style="font-size:20px;">${clear.travel_time_minutes} min</div>
            <div style="font-size:11.5px;color:var(--text-secondary);margin-top:4px;">${clear.distance_km} km &middot; ${clear.route_status}</div>
          </div>
          <div class="card">
            <div class="label">If Blocked</div>
            <div class="value" style="font-size:20px;color:var(--critical);">${blocked.travel_time_minutes} min</div>
            <div style="font-size:11.5px;color:var(--text-secondary);margin-top:4px;">${blocked.distance_km} km &middot; ${blocked.route_status}</div>
          </div>
          <div class="card">
            <div class="label">Extra Delay If Blocked</div>
            <div class="value" style="font-size:20px;color:${extraMinutes > 0 ? 'var(--high)' : 'var(--low)'};">+${extraMinutes} min</div>
            <div style="font-size:11.5px;color:var(--text-secondary);margin-top:4px;">vs. clear route</div>
          </div>
        </div>
        <div style="margin-top:14px; font-size:14px;"><b style="color:var(--accent-orange)">Recommended action:</b> ${blocked.recommended_action}</div>
      `;
    } catch (e) {
      resultEl.innerHTML = `<span style="color:#DC2626">Could not calculate routes: ${e.message}</span>`;
    }
  });
});
