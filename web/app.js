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
const chart = document.querySelector("#chart");
const simulationSection = document.querySelector("#simulationSection");
const learningNote = document.querySelector("#learningNote");
const learnerProfile = document.querySelector("#learnerProfile");
const misconceptions = document.querySelector("#misconceptions");
const nextRecommendation = document.querySelector("#nextRecommendation");
const quizButton = document.querySelector("#quizButton");
const quizPanel = document.querySelector("#quizPanel");
const healthStatus = document.querySelector("#healthStatus");
const verificationBadge = document.querySelector("#verificationBadge");
const moduleTabs = document.querySelector("#moduleTabs");
const curriculumContent = document.querySelector("#curriculumContent");
const debugPanel = document.querySelector("#debugPanel");
const debugContent = document.querySelector("#debugContent");

let sessionId = window.localStorage.getItem("stochasticTutorSession");
let activeModuleId = window.localStorage.getItem("stochasticTutorCurrentModule") || "module00";
let currentConceptId = window.localStorage.getItem("stochasticTutorCurrentConcept");
let curriculum = null;
let mutationInFlight = false;
let latestPayload = null;
const debugMode = new URLSearchParams(window.location.search).get("debug") === "1";
if (debugMode) debugPanel.classList.remove("hidden");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderTutorMarkdown(text) {
  const mathTokens = [];
  let safe = escapeHtml(text || "");
  const stashMath = (match, value, display) => {
    const token = `@@MATH_${mathTokens.length}@@`;
    mathTokens.push({ token, value, display });
    return token;
  };
  safe = safe.replace(/\$\$([\s\S]*?)\$\$/g, (m, value) => stashMath(m, value, true));
  safe = safe.replace(/\$([^$\n]+)\$/g, (m, value) => stashMath(m, value, false));
  safe = safe
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/^[-*] (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)(?:<br>)?/g, "<ul>$1</ul>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n\n+/g, "</p><p>")
    .replace(/\n/g, "<br>");
  mathTokens.forEach(({ token, value, display }) => {
    const klass = display ? "math-display" : "math-inline";
    safe = safe.replace(token, `<span class="${klass}">${escapeHtml(value)}</span>`);
  });
  return safe;
}

function renderMath(root) {
  if (!window.katex) return;
  root.querySelectorAll(".math-inline, .math-display").forEach((node) => {
    window.katex.render(node.textContent, node, {
      displayMode: node.classList.contains("math-display"),
      throwOnError: false,
      trust: false,
    });
  });
}

function addMessage(type, text) {
  const article = document.createElement("article");
  article.className = `message ${type === "user" ? "user-message" : "agent-message"}`;
  article.innerHTML = `<span class="message-label">${type === "user" ? "YOU" : "TUTOR"}</span><div class="message-body">${type === "user" ? `<p>${escapeHtml(text)}</p>` : `<p>${renderTutorMarkdown(text)}</p>`}</div>`;
  conversation.append(article);
  renderMath(article);
  conversation.scrollTop = conversation.scrollHeight;
}

async function fetchJson(url, options = {}, timeoutMs = 45_000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
    return payload;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("The request took too long. Please try again.");
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function selectedModule() {
  return curriculum?.modules.find((module) => module.module_id === activeModuleId) || curriculum?.modules[0];
}

function selectedConcept() {
  return selectedModule()?.knowledge_points.find((point) => point.id === currentConceptId) || selectedModule()?.knowledge_points[0];
}

function selectConcept(moduleId, conceptId) {
  activeModuleId = moduleId;
  currentConceptId = conceptId;
  window.localStorage.setItem("stochasticTutorCurrentModule", moduleId);
  window.localStorage.setItem("stochasticTutorCurrentConcept", conceptId);
  renderCurriculum();
}

function renderCurriculum() {
  if (!curriculum?.modules?.length) return;
  const module = selectedModule();
  if (!module) return;
  const concept = selectedConcept();
  moduleTabs.innerHTML = curriculum.modules.map((item) => {
    const number = item.module_id.slice(-2);
    return `<button type="button" role="tab" aria-selected="${item.module_id === module.module_id}" data-module-id="${escapeHtml(item.module_id)}">Module ${number}</button>`;
  }).join("");
  curriculumContent.innerHTML = `
    <div class="selected-module-heading"><p class="section-label">SELECTED MODULE</p><h3>${escapeHtml(`Module ${String(module.number ?? module.module_id.slice(-2)).padStart(2, "0")} — ${module.label || module.module_label || "Stochastic Processes"}`)}</h3><p>${escapeHtml(module.summary || "Explore definitions, examples, practice questions, and verified simulations.")}</p></div>
    <p class="section-label">KNOWLEDGE POINTS</p>
    <div class="concept-list" role="list">${module.knowledge_points.map((point) => `<button type="button" role="listitem" aria-pressed="${point.id === concept.id}" data-concept-id="${escapeHtml(point.id)}">${escapeHtml(point.title)}</button>`).join("")}</div>
    <p class="concept-summary"><strong>${escapeHtml(concept.title)}</strong><br />${escapeHtml(concept.summary)}</p>
    <div class="concept-actions"><button type="button" data-concept-action="learn">Learn</button><button type="button" data-concept-action="practice">Practice</button>${concept.simulation_tool ? '<button type="button" class="primary-action" data-concept-action="simulation">Simulation</button>' : ""}<button type="button" data-concept-action="quiz">Quiz</button></div>
    <p id="conceptActivity" class="concept-activity"></p>`;
  moduleTabs.querySelectorAll("[data-module-id]").forEach((button) => button.addEventListener("click", () => {
    const chosen = curriculum.modules.find((item) => item.module_id === button.dataset.moduleId);
    selectConcept(chosen.module_id, chosen.knowledge_points[0].id);
  }));
  curriculumContent.querySelectorAll("[data-concept-id]").forEach((button) => button.addEventListener("click", () => selectConcept(module.module_id, button.dataset.conceptId)));
  curriculumContent.querySelectorAll("[data-concept-action]").forEach((button) => button.addEventListener("click", () => {
    const chosen = selectedConcept();
    const activity = curriculumContent.querySelector(".concept-activity");
    if (button.dataset.conceptAction === "learn") activity.textContent = chosen.summary;
    if (button.dataset.conceptAction === "practice") { input.value = chosen.practice_prompt; input.focus(); }
    if (button.dataset.conceptAction === "simulation") askAgent(chosen.simulation_prompt);
    if (button.dataset.conceptAction === "quiz") openQuiz();
  }));
}

async function hydrateCurriculum() {
  try { curriculum = await fetchJson("/api/curriculum", {}, 10_000); renderCurriculum(); }
  catch (error) { curriculumContent.textContent = `Course modules could not be loaded: ${error.message}`; }
}

function renderChart(series, chartSpec = {}) {
  if (!series?.length || !series[0].values?.length) { chart.textContent = "No chart is available for this result."; return; }
  const width = 640, height = 210, padding = 18;
  const allValues = series.flatMap((item) => item.values), min = Math.min(...allValues), max = Math.max(...allValues), spread = max - min || 1;
  const allX = series.flatMap((item) => item.x?.length === item.values.length ? item.x : item.values.map((_, index) => index));
  const minX = Math.min(...allX), maxX = Math.max(...allX), xSpread = maxX - minX || 1;
  const colors = ["#635bdb", "#199aa4", "#d58a28", "#8f84ef", "#248a62"];
  const polylines = series.slice(0, 5).map((item, seriesIndex) => {
    const xValues = item.x?.length === item.values.length ? item.x : item.values.map((_, index) => index);
    const points = item.values.map((value, index) => `${(padding + ((xValues[index] - minX) / xSpread) * (width - padding * 2)).toFixed(1)},${(height - padding - ((value - min) / spread) * (height - padding * 2)).toFixed(1)}`).join(" ");
    return `<polyline points="${points}" fill="none" stroke="${colors[seriesIndex % colors.length]}" stroke-width="2" opacity=".9" />`;
  }).join("");
  chart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Simulation chart"><line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#dcd8e5" /><line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#dcd8e5" />${polylines}<text x="${padding}" y="13" fill="#8a8795" font-size="10">max ${max.toFixed(3)}</text><text x="${padding}" y="${height - 3}" fill="#8a8795" font-size="10">min ${min.toFixed(3)}</text><text x="${width - 130}" y="${height - 3}" fill="#8a8795" font-size="10">${escapeHtml(chartSpec.x_label || "time")} ${maxX.toFixed(2)}</text></svg>`;
}

function renderSources(sourceRows) {
  sources.innerHTML = sourceRows?.length ? `<ul>${sourceRows.map((source) => `<li><span>${escapeHtml(source.title || source.source)}</span><small>${escapeHtml(source.source)}</small></li>`).join("")}</ul>` : "<p>No course sources were returned.</p>";
}

function renderProgress(memory, note, recommendation) {
  learningNote.textContent = note || "Your practice and quiz activity will appear here.";
  learnerProfile.innerHTML = memory?.modules?.length ? memory.modules.map((item) => `<div class="profile-item"><div><strong>${escapeHtml(item.module_id.toUpperCase())}</strong><span>${escapeHtml(item.attempts)} practice runs · ${escapeHtml(item.quiz_correct)}/${escapeHtml(item.quiz_attempts)} quiz answers</span></div><progress max="100" value="${Math.round(Number(item.mastery) * 100)}"></progress></div>`).join("") : "<p>No learning record yet.</p>";
  misconceptions.innerHTML = memory?.misconceptions?.length ? `<p class="diagnosis-title">Things to review</p>${memory.misconceptions.map((item) => `<p><strong>${escapeHtml(item.code)}</strong><br />${escapeHtml(item.correction)}</p>`).join("")}` : "";
  nextRecommendation.innerHTML = recommendation ? `<span>NEXT PRACTICE</span><strong>${escapeHtml(recommendation.module_id.toUpperCase())} · ${escapeHtml(recommendation.module_label)}</strong><p>${escapeHtml(recommendation.reason)}</p>` : "";
}

function renderResponse(payload) {
  latestPayload = payload;
  evidenceContent.classList.remove("hidden");
  emptyEvidence.classList.add("hidden");
  verificationBadge.textContent = payload.tool_called ? (payload.verified ? "VERIFIED" : "CHECK RESULT") : "CONCEPT";
  const isSimulation = payload.intent === "simulation" || payload.tool_called;
  simulationSection.classList.toggle("hidden", !isSimulation);
  if (isSimulation) {
    runMeta.textContent = payload.module_label || payload.module_id || "Simulation";
    renderChart(payload.result?.series, payload.result?.chart);
    parameters.innerHTML = Object.entries(payload.parameters || {}).map(([key, value]) => `<div class="metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(Array.isArray(value) ? JSON.stringify(value) : value)}</strong></div>`).join("");
  } else runMeta.textContent = "Concept explanation";
  renderSources(payload.sources || []);
  renderProgress(payload.memory, payload.learning_note, payload.recommendation);
  if (debugMode) {
    debugContent.textContent = JSON.stringify({
      intent: payload.intent,
      module_id: payload.module_id,
      concept_id: payload.concept_id,
      related_module_ids: payload.related_module_ids || [],
      related_concept_ids: payload.related_concept_ids || [],
      tool_called: payload.tool_called,
      tool: payload.tool,
      llm_enabled: payload.llm_enabled,
      llm_applied: payload.llm_applied,
      observability: payload.observability,
      workflow: payload.workflow,
      trace: payload.trace,
      sources: (payload.sources || []).map((source) => source.source),
    }, null, 2);
  }
}

async function askAgent(question) {
  if (mutationInFlight) return;
  mutationInFlight = true; submitButton.disabled = true; addMessage("user", question);
  try {
    const payload = await fetchJson("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, session_id: sessionId }) });
    sessionId = payload.session_id; window.localStorage.setItem("stochasticTutorSession", sessionId);
    if (payload.module_id?.startsWith("module")) {
      activeModuleId = payload.module_id;
      const matchingModule = curriculum?.modules.find((item) => item.module_id === activeModuleId);
      if (matchingModule) {
        currentConceptId = payload.concept_id || matchingModule.knowledge_points[0]?.id || null;
        window.localStorage.setItem("stochasticTutorCurrentModule", activeModuleId);
        if (currentConceptId) window.localStorage.setItem("stochasticTutorCurrentConcept", currentConceptId);
        renderCurriculum();
      }
    }
    addMessage("agent", payload.answer); renderResponse(payload);
  } catch (error) { addMessage("agent", `I could not complete that request: ${error.message}`); }
  finally { mutationInFlight = false; submitButton.disabled = false; submitButton.innerHTML = "Ask Tutor <span>→</span>"; }
}

async function openQuiz() {
  if (mutationInFlight) return;
  try {
    const payload = await fetchJson(`/api/quiz?module_id=${encodeURIComponent(activeModuleId)}`);
    const quiz = payload.quiz;
    quizPanel.classList.remove("hidden");
    quizPanel.innerHTML = `<p class="quiz-module">${escapeHtml(quiz.module_id.toUpperCase())} · CHECK YOUR UNDERSTANDING</p><h3 id="quizQuestion">${escapeHtml(quiz.question)}</h3><div class="quiz-choices" role="group" aria-labelledby="quizQuestion">${quiz.choices.map((choice, index) => `<button type="button" data-answer="${index}">${String.fromCharCode(65 + index)}. ${escapeHtml(choice)}</button>`).join("")}</div><p class="quiz-feedback" role="status"></p>`;
    quizPanel.querySelectorAll("[data-answer]").forEach((button) => button.addEventListener("click", () => submitQuiz(quiz.id, Number(button.dataset.answer))));
  } catch (error) { quizPanel.classList.remove("hidden"); quizPanel.textContent = `The quiz could not be loaded: ${error.message}`; }
}

async function submitQuiz(questionId, answerIndex) {
  const buttons = quizPanel.querySelectorAll("[data-answer]"); buttons.forEach((button) => { button.disabled = true; });
  try {
    const payload = await fetchJson("/api/quiz/submit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question_id: questionId, answer_index: answerIndex, session_id: sessionId }) });
    sessionId = payload.session_id; window.localStorage.setItem("stochasticTutorSession", sessionId);
    const result = payload.result; quizPanel.querySelector(".quiz-feedback").textContent = `${result.correct ? "Correct. " : "Not quite. "}${result.explanation}`; renderProgress(payload.memory, "Your quiz result has been saved.", payload.recommendation);
  } catch (error) { quizPanel.querySelector(".quiz-feedback").textContent = `The answer could not be saved: ${error.message}`; buttons.forEach((button) => { button.disabled = false; }); }
}

async function hydrateHealth() { try { await fetchJson("/health", {}, 5_000); healthStatus.classList.add("online"); healthStatus.innerHTML = "<i></i> Ready to learn"; } catch (_) { healthStatus.innerHTML = "<i></i> Offline"; } }

form.addEventListener("submit", (event) => { event.preventDefault(); const question = input.value.trim(); if (question) { input.value = ""; askAgent(question); } });
quizButton.addEventListener("click", openQuiz);
resetButton.addEventListener("click", () => { sessionId = null; window.localStorage.removeItem("stochasticTutorSession"); conversation.innerHTML = '<article class="message agent-message"><span class="message-label">TUTOR</span><p>Ask me about a concept, a module, or a simulation.</p></article>'; quizPanel.classList.add("hidden"); });
document.querySelectorAll("[data-scroll]").forEach((button) => button.addEventListener("click", () => document.getElementById(button.dataset.scroll)?.scrollIntoView({ behavior: "smooth" })));

hydrateHealth();
hydrateCurriculum();
