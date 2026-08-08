const form = document.querySelector("#chatForm");
const input = document.querySelector("#questionInput");
const submitButton = document.querySelector("#submitButton");
const conversation = document.querySelector("#conversation");
const resetButton = document.querySelector("#resetButton");
const emptyEvidence = document.querySelector("#emptyEvidence");
const evidenceContent = document.querySelector("#evidenceContent");
const runMeta = document.querySelector("#runMeta");
const parameters = document.querySelector("#parameters");
const sources = document.querySelector("#sources");
const trace = document.querySelector("#trace");
const chart = document.querySelector("#chart");
const learningNote = document.querySelector("#learningNote");
const learnerProfile = document.querySelector("#learnerProfile");
const misconceptions = document.querySelector("#misconceptions");
const nextRecommendation = document.querySelector("#nextRecommendation");
const quizButton = document.querySelector("#quizButton");
const quizPanel = document.querySelector("#quizPanel");
const healthStatus = document.querySelector("#healthStatus");
const healthMeta = document.querySelector("#healthMeta");
const moduleCount = document.querySelector("#moduleCount");
const toolCount = document.querySelector("#toolCount");
const sourceCount = document.querySelector("#sourceCount");
const verificationBadge = document.querySelector("#verificationBadge");
const exportRunButton = document.querySelector("#exportRunButton");
const exportProfileButton = document.querySelector("#exportProfileButton");
const evaluationCount = document.querySelector("#evaluationCount");
const evaluationMeta = document.querySelector("#evaluationMeta");
const appVersion = document.querySelector("#appVersion");

let sessionId = window.localStorage.getItem("stochasticTutorSession");
let activeModuleId = "module01";
let latestRunPayload = null;
let mutationInFlight = false;

function setMutationState(isBusy, label = "运行中…") {
  mutationInFlight = isBusy;
  form.setAttribute("aria-busy", String(isBusy));
  submitButton.disabled = isBusy;
  quizButton.disabled = isBusy;
  resetButton.disabled = isBusy;
  if (isBusy) {
    submitButton.textContent = label;
  } else {
    submitButton.innerHTML = "运行 Agent <span>→</span>";
  }
}

function beginMutation(label) {
  if (mutationInFlight) return false;
  setMutationState(true, label);
  return true;
}

async function fetchJson(url, options = {}, timeoutMs = 45_000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    let payload;
    try {
      payload = await response.json();
    } catch (_) {
      throw new Error(`服务返回了无法解析的响应（HTTP ${response.status}）`);
    }
    if (!response.ok) {
      const requestId = payload.request_id || response.headers.get("X-Request-ID");
      const suffix = requestId ? `（请求 ${requestId.slice(0, 8)}）` : "";
      throw new Error(`${payload.error || `HTTP ${response.status}`}${suffix}`);
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(`请求超过 ${Math.round(timeoutMs / 1000)} 秒，已停止等待`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

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
  const colors = ["#635bdb", "#199aa4", "#d58a28", "#8f84ef", "#248a62"];
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
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#dcd8e5" />
      <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#dcd8e5" />
      ${polylines.join("")}
      <text x="${padding}" y="13" fill="#8a8795" font-size="10">max ${max.toFixed(3)}</text>
      <text x="${padding}" y="${height - 3}" fill="#8a8795" font-size="10">min ${min.toFixed(3)}</text>
      <text x="${width - 120}" y="${height - 3}" fill="#8a8795" font-size="10">${escapeHtml(chartSpec.x_label || "index")} ${maxX.toFixed(2)}</text>
    </svg>
  `;
}

function renderProfile(memory, note = "", recommendation = null) {
  learningNote.textContent = note || "测验和仿真实验会共同形成学习证据。";
  learnerProfile.innerHTML = memory?.modules?.length
    ? memory.modules
        .map((item) => {
          const percent = Math.round(Number(item.mastery) * 100);
          return `
            <div class="profile-item">
              <div><strong>${escapeHtml(item.module_id.toUpperCase())}</strong><span>${escapeHtml(item.attempts)} 次仿真 · ${escapeHtml(item.quiz_correct)}/${escapeHtml(item.quiz_attempts)} 测验</span></div>
              <progress class="mastery-track" max="100" value="${percent}" aria-label="练习证据 ${percent}%"></progress>
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

  if (recommendation) {
    nextRecommendation.innerHTML = `
      <span>NEXT PRACTICE</span>
      <strong>${escapeHtml(recommendation.module_id.toUpperCase())} · ${escapeHtml(recommendation.module_label)}</strong>
      <p>${escapeHtml(recommendation.reason)}</p>
      <button type="button">使用建议问题</button>
    `;
    nextRecommendation.querySelector("button").addEventListener("click", () => {
      input.value = recommendation.suggested_question;
      input.focus();
    });
  } else {
    nextRecommendation.innerHTML = "";
  }
}

function renderEvidence(payload) {
  emptyEvidence.classList.add("hidden");
  evidenceContent.classList.remove("hidden");
  verificationBadge.classList.toggle("invalid", !payload.verified);
  verificationBadge.textContent = payload.verified ? "VERIFIED" : "VALIDATION FAILED";
  latestRunPayload = payload;
  exportRunButton.disabled = false;
  exportProfileButton.disabled = false;
  const requestLabel = payload.request_id ? payload.request_id.slice(0, 8) : "local";
  const evidenceLabel = payload.run_sha256?.slice(0, 8) || "unknown";
  const corpusLabel = payload.sources?.[0]?.corpus_sha256?.slice(0, 8) || "unknown";
  runMeta.innerHTML = `
    <span>${escapeHtml(payload.module_id.toUpperCase())}</span>
    <span>${escapeHtml(payload.tool)}</span>
    <span>RUN ${escapeHtml(requestLabel)}</span>
    <span>EVID ${escapeHtml(evidenceLabel)}</span>
    <span>KB ${escapeHtml(corpusLabel)}</span>
    <span>${payload.llm_applied ? "LLM VERIFIED" : "OFFLINE GROUNDED"}</span>
  `;
  renderChart(payload.result?.series, payload.result?.chart);

  parameters.innerHTML = Object.entries(payload.parameters)
    .map(([key, value]) => `
      <div class="metric">
        <span>${escapeHtml(key)}</span>
        <strong>${escapeHtml(Array.isArray(value) ? JSON.stringify(value) : value)}</strong>
      </div>
    `)
    .join("");

  renderProfile(payload.memory, payload.learning_note, payload.recommendation);

  sources.innerHTML = payload.sources.length
    ? payload.sources
        .map((source) => `
          <div class="source-item">
            <strong>${escapeHtml(source.title)}</strong>
            <small>${escapeHtml(source.source)} · ${escapeHtml(source.kind || "course_note")}</small>
            <small>${escapeHtml(source.retrieval_mode || "retrieval")} · score ${escapeHtml(source.score ?? "—")} · sparse ${escapeHtml(source.score_breakdown?.sparse ?? "—")} · vector ${escapeHtml(source.score_breakdown?.vector ?? "—")}</small>
            <details>
              <summary>查看证据摘录</summary>
              <p>${escapeHtml(source.content || "暂无摘录")}</p>
            </details>
          </div>
        `)
        .join("")
    : "<p>没有检索到课程来源。</p>";

  trace.innerHTML = payload.trace
    .map((item) => `
      <li class="${item.status === "error" ? "trace-error" : ""}">
        <strong>${escapeHtml(item.node)}</strong> · ${escapeHtml(item.detail)}
        <small>${escapeHtml(item.duration_ms ?? "—")} ms</small>
      </li>
    `)
    .join("");
}

async function askAgent(question) {
  if (!beginMutation("运行中…")) return;
  addMessage("user", question);
  try {
    const payload = await fetchJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: sessionId }),
    });
    sessionId = payload.session_id;
    activeModuleId = payload.module_id;
    window.localStorage.setItem("stochasticTutorSession", sessionId);
    exportProfileButton.disabled = false;
    addMessage("agent", payload.answer);
    renderEvidence(payload);
  } catch (error) {
    addMessage("agent", `运行失败：${error.message}`);
  } finally {
    setMutationState(false);
    hydrateHealth();
  }
}

async function openQuiz() {
  if (mutationInFlight) return;
  quizButton.disabled = true;
  try {
    const payload = await fetchJson(
      `/api/quiz?module_id=${encodeURIComponent(activeModuleId)}`,
      {},
      15_000,
    );
    const quiz = payload.quiz;
    quizPanel.classList.remove("hidden");
    quizPanel.innerHTML = `
      <p class="quiz-module">${escapeHtml(quiz.module_id.toUpperCase())} · CONCEPT CHECK</p>
      <h3 id="quizQuestion" tabindex="-1">${escapeHtml(quiz.question)}</h3>
      <div class="quiz-choices" role="group" aria-labelledby="quizQuestion">
        ${quiz.choices.map((choice, index) => `<button type="button" data-answer="${index}" aria-pressed="false">${String.fromCharCode(65 + index)}. ${escapeHtml(choice)}</button>`).join("")}
      </div>
      <p class="quiz-feedback" role="status"></p>
    `;
    quizPanel.querySelectorAll("[data-answer]").forEach((button) => {
      button.addEventListener("click", () => submitQuiz(quiz.id, Number(button.dataset.answer)));
    });
    quizPanel.querySelector("h3").focus();
  } catch (error) {
    quizPanel.classList.remove("hidden");
    quizPanel.textContent = `测验加载失败：${error.message}`;
  } finally {
    quizButton.disabled = mutationInFlight;
  }
}

async function submitQuiz(questionId, answerIndex) {
  if (!beginMutation("保存测验…")) return;
  const buttons = quizPanel.querySelectorAll("[data-answer]");
  buttons.forEach((button) => {
    button.disabled = true;
    button.setAttribute("aria-pressed", String(Number(button.dataset.answer) === answerIndex));
  });
  const feedback = quizPanel.querySelector(".quiz-feedback");
  try {
    const payload = await fetchJson("/api/quiz/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: questionId, answer_index: answerIndex, session_id: sessionId }),
    });
    sessionId = payload.session_id;
    window.localStorage.setItem("stochasticTutorSession", sessionId);
    exportProfileButton.disabled = false;
    const result = payload.result;
    buttons.forEach((button) => {
      const index = Number(button.dataset.answer);
      button.classList.toggle("correct-answer", index === result.correct_index);
      button.classList.toggle(
        "incorrect-answer",
        index === answerIndex && index !== result.correct_index,
      );
    });
    feedback.className = `quiz-feedback ${result.correct ? "correct" : "incorrect"}`;
    feedback.textContent = `${result.correct ? "回答正确。" : "还差一步。"}${result.explanation}`;
    emptyEvidence.classList.add("hidden");
    evidenceContent.classList.remove("hidden");
    renderProfile(
      payload.memory,
      "测验结果已经写入持久化学习档案。下一步可以运行对应仿真验证答案。",
      payload.recommendation,
    );
    verificationBadge.classList.remove("invalid");
    verificationBadge.textContent = "ASSESSMENT SAVED";
  } catch (error) {
    feedback.className = "quiz-feedback incorrect";
    feedback.textContent = `提交失败：${error.message}`;
    buttons.forEach((button) => {
      button.disabled = false;
      button.setAttribute("aria-pressed", "false");
    });
  } finally {
    setMutationState(false);
  }
}

quizButton.addEventListener("click", openQuiz);

async function hydrateHealth() {
  try {
    const health = await fetchJson("/health", {}, 5_000);
    const ragCircuit = health.knowledge?.embedding_circuit?.state;
    const llmCircuit = health.llm?.provider_circuit?.state;
    const degraded = ragCircuit === "open" || llmCircuit === "open";
    healthStatus.classList.add("online");
    healthStatus.classList.toggle("degraded", degraded);
    healthStatus.innerHTML = degraded
      ? "<i></i> Agent online · fallback"
      : "<i></i> Agent online";
    const ragBackend = health.knowledge?.embedding_backend || "retrieval ready";
    healthMeta.textContent = `${health.modules} modules · ${health.tools} tools · ${ragBackend}`;
    appVersion.textContent = `v${health.version || "0.4.0"} · Interview build`;
    moduleCount.textContent = `${health.modules}/${health.modules}`;
    toolCount.textContent = health.tools;
    sourceCount.textContent = health.knowledge?.entries ?? "—";
    if (health.evaluation) {
      evaluationCount.textContent = health.evaluation.corpus_match
        ? `${health.evaluation.passed}/${health.evaluation.total}`
        : "STALE";
      const retrieval = health.evaluation.suites?.find((suite) => suite.id === "retrieval");
      const safety = health.evaluation.suites?.find((suite) => suite.id === "safety");
      evaluationMeta.textContent = health.evaluation.corpus_match && retrieval
        ? `RAG Hit@3 ${Math.round(retrieval.hit_at_3 * 100)}% · SAFETY ${safety?.passed ?? "—"}/${safety?.cases ?? "—"}`
        : "课程内容已变化，需要重跑评测";
    }
  } catch (_) {
    healthStatus.classList.remove("online", "degraded");
    healthStatus.innerHTML = "<i></i> Agent offline";
  }
}

hydrateHealth();

document.querySelectorAll("[data-scroll]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.scroll)?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

async function restoreSession() {
  if (!sessionId) return;
  try {
    const payload = await fetchJson(
      `/api/profile?session_id=${encodeURIComponent(sessionId)}`,
      {},
      15_000,
    );
    const profile = payload.profile;
    if (!profile.turns && !profile.quiz_attempts) {
      window.localStorage.removeItem("stochasticTutorSession");
      sessionId = null;
      return;
    }
    const latest = payload.history.at(-1);
    activeModuleId = latest?.module_id || profile.modules.at(-1)?.module_id || "module01";
    addMessage(
      "agent",
      `已恢复上次学习记录：${profile.turns} 次仿真实验，${profile.quiz_correct}/${profile.quiz_attempts} 道概念题正确。你可以直接继续修改上一轮参数。`,
    );
    emptyEvidence.classList.add("hidden");
    evidenceContent.classList.remove("hidden");
    chart.innerHTML = "<p>会话已恢复。继续提问后将显示新的仿真路径。</p>";
    verificationBadge.classList.remove("invalid");
    verificationBadge.textContent = "SESSION RESTORED";
    exportRunButton.disabled = true;
    exportProfileButton.disabled = false;
    runMeta.innerHTML = `<span>SESSION RESTORED</span><span>${escapeHtml(activeModuleId.toUpperCase())}</span>`;
    parameters.innerHTML = latest?.parameters
      ? Object.entries(latest.parameters)
          .map(([key, value]) => `<div class="metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></div>`)
          .join("")
      : "";
    sources.innerHTML = "<p>继续提问后重新检索 Notebook 证据。</p>";
    trace.innerHTML = "<li><strong>memory</strong> · restored persistent session</li>";
    renderProfile(
      profile,
      "已从 SQLite 恢复学习档案和上一轮工具参数。",
      payload.recommendation,
    );
  } catch (_) {
    // The service may still be starting; normal chat remains available.
  }
}

restoreSession();

function downloadJson(payload, filename) {
  const body = JSON.stringify(payload, null, 2);
  const blob = new Blob([body], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

exportRunButton.addEventListener("click", () => {
  if (!latestRunPayload) return;
  const runLabel = latestRunPayload.request_id?.slice(0, 8) || "local";
  downloadJson(
    latestRunPayload,
    `stochlab-${latestRunPayload.module_id}-${runLabel}.json`,
  );
});

exportProfileButton.addEventListener("click", async () => {
  if (!sessionId) return;
  exportProfileButton.disabled = true;
  try {
    const payload = await fetchJson(
      `/api/sessions/${encodeURIComponent(sessionId)}/export`,
      {},
      15_000,
    );
    const safeSessionLabel = sessionId
      .replace(/[^A-Za-z0-9_-]/g, "")
      .slice(0, 8) || "session";
    downloadJson(payload, `stochlab-learning-profile-${safeSessionLabel}.json`);
  } catch (error) {
    addMessage("agent", `学习档案导出失败：${error.message}`);
  } finally {
    exportProfileButton.disabled = false;
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (mutationInFlight) return;
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
  if (!beginMutation("重置中…")) return;
  if (sessionId) {
    try {
      await fetchJson(
        `/api/sessions/${encodeURIComponent(sessionId)}`,
        { method: "DELETE" },
        15_000,
      );
    } catch (error) {
      addMessage(
        "agent",
        `学习记录尚未删除：${error.message}。会话标识仍保留，请稍后重试。`,
      );
      setMutationState(false);
      return;
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
  verificationBadge.classList.remove("invalid");
  verificationBadge.textContent = "WAITING";
  latestRunPayload = null;
  exportRunButton.disabled = true;
  exportProfileButton.disabled = true;
  quizPanel.classList.add("hidden");
  setMutationState(false);
  input.focus();
});
