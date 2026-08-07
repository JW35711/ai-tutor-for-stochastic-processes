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
const learningNote = document.querySelector("#learningNote");
const learnerProfile = document.querySelector("#learnerProfile");
const misconceptions = document.querySelector("#misconceptions");
const quizButton = document.querySelector("#quizButton");
const quizPanel = document.querySelector("#quizPanel");

let sessionId = window.localStorage.getItem("stochasticTutorSession");
let activeModuleId = "module01";

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

function renderChart(series, chartSpec = {}) {
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
  const allX = series.flatMap((item) =>
    item.x?.length === item.values.length
      ? item.x
      : item.values.map((_, index) => index),
  );
  const minX = Math.min(...allX);
  const maxX = Math.max(...allX);
  const xSpread = maxX - minX || 1;
  const colors = ["#c8ff5a", "#7fe8df", "#ff8a5b", "#b6a3ff", "#f9d66f"];
  const polylines = series.slice(0, 5).map((item, seriesIndex) => {
    const xValues = item.x?.length === item.values.length
      ? item.x
      : item.values.map((_, index) => index);
    const coordinates = [];
    item.values.forEach((value, index) => {
      if (chartSpec.step === "post" && index > 0) {
        coordinates.push([xValues[index], item.values[index - 1]]);
      }
      coordinates.push([xValues[index], value]);
    });
    const points = coordinates
      .map(([xValue, value]) => {
        const x = padding + ((xValue - minX) / xSpread) * (width - padding * 2);
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
      <text x="${width - 120}" y="${height - 3}" fill="#a7aa9e" font-size="10">${escapeHtml(chartSpec.x_label || "index")} ${maxX.toFixed(2)}</text>
    </svg>
  `;
}

function renderProfile(memory, note = "") {
  learningNote.textContent = note || "测验和仿真实验会共同形成学习证据。";
  learnerProfile.innerHTML = memory?.modules?.length
    ? memory.modules
        .map((item) => {
          const percent = Math.round(Number(item.mastery) * 100);
          return `
            <div class="profile-item">
              <div><strong>${escapeHtml(item.module_id.toUpperCase())}</strong><span>${escapeHtml(item.attempts)} 次仿真 · ${escapeHtml(item.quiz_correct)}/${escapeHtml(item.quiz_attempts)} 测验</span></div>
              <div class="mastery-track" aria-label="掌握度 ${percent}%"><i style="width:${percent}%"></i></div>
              <small>练习证据 ${percent}%</small>
            </div>
          `;
        })
        .join("")
    : "<p>尚无学习记录。</p>";

  misconceptions.innerHTML = memory?.misconceptions?.length
    ? `
      <p class="diagnosis-title">已识别的概念误区</p>
      ${memory.misconceptions
        .map((item) => `<p><strong>${escapeHtml(item.code)}</strong><br>${escapeHtml(item.correction)}</p>`)
        .join("")}
    `
    : "";
}

function renderEvidence(payload) {
  emptyEvidence.classList.add("hidden");
  evidenceContent.classList.remove("hidden");
  renderChart(payload.result?.series, payload.result?.chart);

  parameters.innerHTML = Object.entries(payload.parameters)
    .map(([key, value]) => `
      <div class="metric">
        <span>${escapeHtml(key)}</span>
        <strong>${escapeHtml(Array.isArray(value) ? JSON.stringify(value) : value)}</strong>
      </div>
    `)
    .join("");

  renderProfile(payload.memory, payload.learning_note);

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
    activeModuleId = payload.module_id;
    window.localStorage.setItem("stochasticTutorSession", sessionId);
    addMessage("agent", payload.answer);
    renderEvidence(payload);
  } catch (error) {
    addMessage("agent", `运行失败：${error.message}`);
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = "运行 Agent <span>→</span>";
  }
}

async function openQuiz() {
  quizButton.disabled = true;
  try {
    const response = await fetch(`/api/quiz?module_id=${encodeURIComponent(activeModuleId)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "无法加载测验");
    const quiz = payload.quiz;
    quizPanel.classList.remove("hidden");
    quizPanel.innerHTML = `
      <p class="quiz-module">${escapeHtml(quiz.module_id.toUpperCase())} · CONCEPT CHECK</p>
      <strong>${escapeHtml(quiz.question)}</strong>
      <div class="quiz-choices">
        ${quiz.choices.map((choice, index) => `<button type="button" data-answer="${index}">${String.fromCharCode(65 + index)}. ${escapeHtml(choice)}</button>`).join("")}
      </div>
      <p class="quiz-feedback"></p>
    `;
    quizPanel.querySelectorAll("[data-answer]").forEach((button) => {
      button.addEventListener("click", () => submitQuiz(quiz.id, Number(button.dataset.answer)));
    });
  } catch (error) {
    quizPanel.classList.remove("hidden");
    quizPanel.textContent = `测验加载失败：${error.message}`;
  } finally {
    quizButton.disabled = false;
  }
}

async function submitQuiz(questionId, answerIndex) {
  const buttons = quizPanel.querySelectorAll("[data-answer]");
  buttons.forEach((button) => { button.disabled = true; });
  const response = await fetch("/api/quiz/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId, answer_index: answerIndex, session_id: sessionId }),
  });
  const payload = await response.json();
  const feedback = quizPanel.querySelector(".quiz-feedback");
  if (!response.ok) {
    feedback.textContent = payload.error || "提交失败";
    return;
  }
  sessionId = payload.session_id;
  window.localStorage.setItem("stochasticTutorSession", sessionId);
  const result = payload.result;
  feedback.className = `quiz-feedback ${result.correct ? "correct" : "incorrect"}`;
  feedback.textContent = `${result.correct ? "回答正确。" : "还差一步。"}${result.explanation}`;
  emptyEvidence.classList.add("hidden");
  evidenceContent.classList.remove("hidden");
  renderProfile(payload.memory, "测验结果已经写入持久化学习档案。下一步可以运行对应仿真验证答案。");
}

quizButton.addEventListener("click", openQuiz);

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

resetButton.addEventListener("click", async () => {
  if (sessionId) {
    try {
      await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    } catch (_) {
      // A local reset should still work when the server has just restarted.
    }
  }
  sessionId = null;
  window.localStorage.removeItem("stochasticTutorSession");
  conversation.innerHTML = `
    <article class="message agent-message">
      <span class="message-label">AGENT</span>
      <p>新会话已开始。描述你想观察的随机过程。</p>
    </article>
  `;
  evidenceContent.classList.add("hidden");
  emptyEvidence.classList.remove("hidden");
  quizPanel.classList.add("hidden");
  input.focus();
});
