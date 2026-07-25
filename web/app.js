const form = document.querySelector("#chatForm");
const input = document.querySelector("#questionInput");
const submitButton = document.querySelector("#submitButton");
const conversation = document.querySelector("#conversation");
const resetButton = document.querySelector("#resetButton");
const emptyEvidence = document.querySelector("#emptyEvidence");
const evidenceContent = document.querySelector("#evidenceContent");
const parameters = document.querySelector("#parameters");
const sources = document.querySelector("#sources");
const trace = document.querySelector("#trace");
const chart = document.querySelector("#chart");

let sessionId = null;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatAnswer(text) {
  return escapeHtml(text)
    .replace(/^### (.+)$/gm, "<strong>$1</strong>")
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br>");
}

function addMessage(type, text) {
  const article = document.createElement("article");
  article.className = `message ${type === "user" ? "user-message" : "agent-message"}`;
  article.innerHTML = `
    <span class="message-label">${type === "user" ? "YOU" : "AGENT"}</span>
    <p>${type === "user" ? escapeHtml(text) : formatAnswer(text)}</p>
  `;
  conversation.append(article);
  conversation.scrollTop = conversation.scrollHeight;
}

function renderChart(series) {
  if (!series?.length || !series[0].values?.length) {
    chart.innerHTML = "<p>本次结果没有可绘制的路径。</p>";
    return;
  }
  const width = 640;
  const height = 210;
  const padding = 18;
  const allValues = series.flatMap((item) => item.values);
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const spread = max - min || 1;
  const maxLength = Math.max(...series.map((item) => item.values.length));
  const colors = ["#c8ff5a", "#7fe8df", "#ff8a5b", "#b6a3ff", "#f9d66f"];
  const polylines = series.slice(0, 5).map((item, seriesIndex) => {
    const points = item.values
      .map((value, index) => {
        const x = padding + (index / Math.max(item.values.length - 1, 1)) * (width - padding * 2);
        const y = height - padding - ((value - min) / spread) * (height - padding * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
    return `<polyline points="${points}" fill="none" stroke="${colors[seriesIndex % colors.length]}" stroke-width="2" opacity="0.9" />`;
  });
  chart.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Simulation chart">
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="rgba(255,255,255,.18)" />
      <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="rgba(255,255,255,.18)" />
      ${polylines.join("")}
      <text x="${padding}" y="13" fill="#a7aa9e" font-size="10">max ${max.toFixed(3)}</text>
      <text x="${padding}" y="${height - 3}" fill="#a7aa9e" font-size="10">min ${min.toFixed(3)}</text>
      <text x="${width - 95}" y="${height - 3}" fill="#a7aa9e" font-size="10">${maxLength} points</text>
    </svg>
  `;
}

function renderEvidence(payload) {
  emptyEvidence.classList.add("hidden");
  evidenceContent.classList.remove("hidden");
  renderChart(payload.result?.series);

  parameters.innerHTML = Object.entries(payload.parameters)
    .map(([key, value]) => `
      <div class="metric">
        <span>${escapeHtml(key)}</span>
        <strong>${escapeHtml(Array.isArray(value) ? JSON.stringify(value) : value)}</strong>
      </div>
    `)
    .join("");

  sources.innerHTML = payload.sources.length
    ? payload.sources
        .map((source) => `
          <div class="source-item">
            <strong>${escapeHtml(source.title)}</strong>
            <small>${escapeHtml(source.source)}</small>
          </div>
        `)
        .join("")
    : "<p>没有检索到课程来源。</p>";

  trace.innerHTML = payload.trace
    .map((item) => `
      <li><strong>${escapeHtml(item.node)}</strong> · ${escapeHtml(item.detail)}</li>
    `)
    .join("");
}

async function askAgent(question) {
  addMessage("user", question);
  submitButton.disabled = true;
  submitButton.textContent = "运行中…";
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: sessionId }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "请求失败");
    sessionId = payload.session_id;
    addMessage("agent", payload.answer);
    renderEvidence(payload);
  } catch (error) {
    addMessage("agent", `运行失败：${error.message}`);
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = "运行 Agent <span>→</span>";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  askAgent(question);
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.question;
    input.focus();
  });
});

resetButton.addEventListener("click", () => {
  sessionId = null;
  conversation.innerHTML = `
    <article class="message agent-message">
      <span class="message-label">AGENT</span>
      <p>新会话已开始。描述你想观察的随机过程。</p>
    </article>
  `;
  evidenceContent.classList.add("hidden");
  emptyEvidence.classList.remove("hidden");
  input.focus();
});
