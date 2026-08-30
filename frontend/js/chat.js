const API_BASE_C = "/api";

const SUGGESTED_QUESTIONS = [
  "Which site has the highest priority?",
  "Why is the top site ranked highest?",
  "Which site has the highest population impact?",
  "Which site is hardest to reach?",
  "Does any site affect a hospital?",
  "How many sites need a structural engineer?",
  "Which site should emergency teams visit first?",
  "How should teams be allocated?",
  "Which site has the lowest priority?",
  "Give me a complete emergency response plan.",
];

let currentMode = "auto";
let onlineAvailable = false;

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

function scrollLogToBottom() {
  const log = document.getElementById("chatLog");
  log.scrollTop = log.scrollHeight;
}

function addSystemMessage(text) {
  const log = document.getElementById("chatLog");
  log.appendChild(el("div", "msg system", text));
  scrollLogToBottom();
}

function addUserMessage(text) {
  const log = document.getElementById("chatLog");
  const msg = el("div", "msg user");
  msg.textContent = text;
  log.appendChild(msg);
  scrollLogToBottom();
}

function addBotMessage(result) {
  const log = document.getElementById("chatLog");
  const msg = el("div", "msg bot");
  const answerLine = el("div");
  answerLine.textContent = result.answer || "I couldn't find an answer for that.";
  msg.appendChild(answerLine);

  const modeLabels = { offline_rules: "Offline rule match", online_llm: "Online AI (Gemini)", offline_fallback: "Offline summary" };
  const factors = result.supporting_factors || [];
  const sources = result.data_sources || [];

  if (result.confidence_note || factors.length || sources.length || result.mode_used) {
    const meta = el("div", "meta");
    let metaHtml = "";
    if (result.mode_used) metaHtml += `<span class="tag">${modeLabels[result.mode_used] || result.mode_used}</span>`;
    factors.forEach(f => metaHtml += `<span class="tag">factor: ${f}</span>`);
    if (result.confidence_note) metaHtml += `<div style="margin-top:6px;">${result.confidence_note}</div>`;
    if (sources.length) metaHtml += `<div style="margin-top:4px; opacity:0.8;">Source: ${sources.join("; ")}</div>`;
    meta.innerHTML = metaHtml;
    msg.appendChild(meta);
  }

  log.appendChild(msg);
  scrollLogToBottom();
}

function addTypingIndicator() {
  const log = document.getElementById("chatLog");
  const msg = el("div", "msg bot typing-indicator", `<span class="typing-dots"><span></span><span></span><span></span></span>`);
  log.appendChild(msg);
  scrollLogToBottom();
  return msg;
}

async function sendQuestion(question) {
  if (!question.trim()) return;
  addUserMessage(question);
  const typingEl = addTypingIndicator();

  try {
    const res = await fetch(`${API_BASE_C}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, mode: currentMode }),
    });
    typingEl.remove();
    if (!res.ok) throw new Error(await res.text());
    const result = await res.json();
    addBotMessage(result);
  } catch (err) {
    typingEl.remove();
    addSystemMessage("Could not reach the assistant. Is the backend running?");
  }
}

function renderSuggestions() {
  const box = document.getElementById("chatSuggestions");
  box.innerHTML = "";
  SUGGESTED_QUESTIONS.forEach(q => {
    const chip = el("div", "suggestion-chip", q);
    chip.addEventListener("click", () => sendQuestion(q));
    box.appendChild(chip);
  });
}

async function loadStatus() {
  const banner = document.getElementById("statusBanner");
  try {
    const res = await fetch(`${API_BASE_C}/chat/status`);
    const status = await res.json();
    onlineAvailable = !!status.online_available;
    const onlineBtn = document.querySelector('.mode-btn[data-mode="online"]');
    if (onlineBtn && !onlineAvailable) {
      onlineBtn.disabled = true;
      onlineBtn.title = "Set GEMINI_API_KEY on the server to enable online mode.";
      onlineBtn.style.opacity = "0.4";
      onlineBtn.style.cursor = "not-allowed";
    }
    if (status.sites_available === 0) {
      banner.style.display = "inline-flex";
      banner.textContent = "No sites assessed yet -- run an assessment first so the assistant has real data to answer from.";
    } else {
      banner.style.display = "none";
    }
  } catch (e) {
    // backend unreachable -- non-fatal for the page itself
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderSuggestions();
  loadStatus();
  addSystemMessage("Ask me anything about the sites assessed this session -- I only answer from real data, never guesses.");

  const params = new URLSearchParams(window.location.search);
  const prefilled = params.get("ask");
  if (prefilled) {
    sendQuestion(prefilled);
  }

  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentMode = btn.dataset.mode;
    });
  });

  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSendBtn");
  sendBtn.addEventListener("click", () => {
    const q = input.value;
    input.value = "";
    sendQuestion(q);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendBtn.click();
    }
  });
});
