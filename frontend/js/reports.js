const API_BASE_R = "/api";

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("generateBtn");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    const resultEl = document.getElementById("reportResult");
    resultEl.innerHTML = "Generating report...";
    try {
      const payload = {
        case_name: document.getElementById("case_name").value,
        disaster_type: document.getElementById("disaster_type").value,
      };
      const res = await fetch(`${API_BASE_R}/report`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      resultEl.innerHTML = `
        Report generated: <strong>${data.filename}</strong><br>
        <a class="btn" style="display:inline-block;margin-top:10px;text-decoration:none;" href="${API_BASE_R}/report/${data.filename}" target="_blank">Download PDF</a>
      `;
    } catch (err) {
      resultEl.innerHTML = `<span style="color:#e5484d">Failed: ${err.message}. Assess at least one site first.</span>`;
    }
  });
});
