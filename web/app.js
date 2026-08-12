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
const tutorLab = document.querySelector("#tutorLab");
const simulationView = document.querySelector("#simulationView");
const simulationTitle = document.querySelector("#simulationTitle");
const simulationSubtitle = document.querySelector("#simulationSubtitle");
const experimentPurpose = document.querySelector("#experimentPurpose");
const simulationChart = document.querySelector("#simulationChart");
const simulationLegend = document.querySelector("#simulationLegend");
const simulationMetrics = document.querySelector("#simulationMetrics");
const experimentTeachingNote = document.querySelector("#experimentTeachingNote");
const simulationSources = document.querySelector("#simulationSources");
const closeSimulationView = document.querySelector("#closeSimulationView");
const dashboard = document.querySelector(".dashboard");
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
const courseTitle = document.querySelector("#courseTitle");
const locationBreadcrumb = document.querySelector("#locationBreadcrumb");
const composerStatus = document.querySelector("#composerStatus");
const debugPanel = document.querySelector("#debugPanel");
const debugContent = document.querySelector("#debugContent");

let sessionId = window.localStorage.getItem("stochasticTutorSession");
let activeModuleId = window.localStorage.getItem("stochasticTutorCurrentModule") || "module00";
let currentConceptId = window.localStorage.getItem("stochasticTutorCurrentConcept");
let curriculum = null;
let mutationInFlight = false;
let latestPayload = null;
let masteryByConcept = {};
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
  // Extract LaTeX before HTML escaping.  In matrix environments `&` is a
  // column separator; escaping it first turns it into `&amp;`, which KaTeX
  // renders literally as "amp;".
  let raw = String(text || "");
  const stashMath = (match, value, display) => {
    const token = `@@MATH_${mathTokens.length}@@`;
    mathTokens.push({ token, value, display });
    return token;
  };
  raw = raw.replace(/\$\$([\s\S]*?)\$\$/g, (m, value) => stashMath(m, value, true));
  raw = raw.replace(/\$([^$\n]+)\$/g, (m, value) => stashMath(m, value, false));
  let safe = escapeHtml(raw);
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
    // Escape HTML delimiters in formulas, but deliberately preserve `&` for
    // LaTeX alignment commands such as `\begin{pmatrix} a & b \\ c & d \end{pmatrix}`.
    const safeMath = String(value)
      .replaceAll("&amp;", "&")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
    safe = safe.replace(token, `<span class="${klass}">${safeMath}</span>`);
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

function moduleNumber(module) {
  return String(module?.number ?? module?.module_id?.slice(-2) ?? "00").padStart(2, "0");
}

function moduleDisplayLabel(moduleId) {
  const module = curriculum?.modules.find((item) => item.module_id === moduleId);
  return module ? `Module ${moduleNumber(module)} · ${module.label}` : "Course module";
}

function autoGrowInput() {
  input.style.height = "auto";
  const maxHeight = 180;
  input.style.height = `${Math.min(input.scrollHeight, maxHeight)}px`;
  input.style.overflowY = input.scrollHeight > maxHeight ? "auto" : "hidden";
}

function setComposerLoading(loading) {
  mutationInFlight = loading;
  submitButton.disabled = loading;
  input.setAttribute("aria-busy", String(loading));
  conversation.setAttribute("aria-busy", String(loading));
  submitButton.innerHTML = loading
    ? 'Tutor is responding <span aria-hidden="true">…</span>'
    : 'Ask Tutor <span aria-hidden="true">→</span>';
  composerStatus.textContent = loading
    ? "Tutor is responding…"
    : "Press Enter to ask · Shift+Enter for a new line";
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
  if (!module.knowledge_points.some((point) => point.id === currentConceptId)) {
    currentConceptId = module.knowledge_points[0]?.id || null;
    if (currentConceptId) window.localStorage.setItem("stochasticTutorCurrentConcept", currentConceptId);
  }
  const concept = selectedConcept();
  if (!concept) return;
  const number = moduleNumber(module);
  locationBreadcrumb.textContent = `${module.label} / ${concept.title}`;
  moduleTabs.innerHTML = curriculum.modules.map((item) => {
    return `<button type="button" role="tab" aria-selected="${item.module_id === module.module_id}" aria-controls="curriculumContent" aria-label="Module ${moduleNumber(item)}" data-module-id="${escapeHtml(item.module_id)}"><span class="module-tab-number">Module ${moduleNumber(item)}</span></button>`;
  }).join("");
  curriculumContent.innerHTML = `
    <div class="curriculum-breadcrumb"><span>Course modules</span><span aria-hidden="true">/</span><strong>Module ${number}</strong><span aria-hidden="true">/</span><span>${escapeHtml(concept.title)}</span></div>
    <div class="selected-module-heading"><div><p class="section-label">MODULE ${number}</p><h3>${escapeHtml(module.label || "Stochastic Processes")}</h3><p class="module-purpose">${escapeHtml(module.purpose || module.summary || "Explore this stochastic-process model through practice and examples.")}</p></div><div class="module-meta"><span>${module.knowledge_points.length} knowledge points</span><span>Recommended order</span></div></div>
    <section class="learning-objectives" aria-labelledby="objectivesHeading"><h4 id="objectivesHeading">Learning objectives</h4><ul>${(module.learning_objectives || []).map((objective) => `<li>After this module, you should be able to ${escapeHtml(objective.replace(/^After this module, you should be able to /i, "").replace(/[.]$/, ""))}.</li>`).join("")}</ul></section>
    <div class="kp-heading"><p class="section-label">KNOWLEDGE POINTS</p><span>Start with 01</span></div>
    <ol class="concept-list" role="list">${module.knowledge_points.map((point, index) => { const status = masteryByConcept[point.id]?.status || "NOT_STARTED"; return `<li><button type="button" role="listitem" aria-current="${point.id === concept.id ? "true" : "false"}" aria-label="${escapeHtml(`${index + 1}. ${point.title}`)}" data-concept-id="${escapeHtml(point.id)}"><span class="concept-index">${String(index + 1).padStart(2, "0")}</span><span class="concept-copy"><strong>${escapeHtml(point.title)}</strong><small>${escapeHtml(point.description || point.summary)}</small></span><span class="concept-status concept-status-${status.toLowerCase().replaceAll("_", "-")}">${escapeHtml(status.replaceAll("_", " "))}</span><span class="concept-arrow" aria-hidden="true">→</span></button></li>`; }).join("")}</ol>
    <section class="concept-detail" aria-labelledby="conceptHeading"><p class="section-label">SELECTED KNOWLEDGE POINT</p><h4 id="conceptHeading">${escapeHtml(concept.title)}</h4><p>${escapeHtml(concept.description || concept.summary)}</p><p class="you-learn-label">You will learn</p><ul><li>${escapeHtml(concept.description || concept.summary)}</li><li>Use it to answer: ${escapeHtml(concept.practice_prompt)}</li></ul>${concept.experiments?.length ? `<div class="experiment-list"><p class="you-learn-label">Explore with simulations</p><ul>${concept.experiments.map((experiment) => `<li>${escapeHtml(experiment.title)}</li>`).join("")}</ul></div>` : ""}<div class="concept-actions"><button type="button" data-concept-action="learn">Learn</button><button type="button" data-concept-action="practice">Practice</button><button type="button" data-concept-action="hint">Hint</button>${concept.experiments?.length ? '<button type="button" class="primary-action" data-concept-action="simulation">Simulation</button>' : ""}<button type="button" data-concept-action="quiz">Quiz</button></div><p id="conceptActivity" class="concept-activity" role="status" aria-live="polite"></p></section>`;
  moduleTabs.querySelectorAll("[data-module-id]").forEach((button) => button.addEventListener("click", () => {
    const chosen = curriculum.modules.find((item) => item.module_id === button.dataset.moduleId);
    selectConcept(chosen.module_id, chosen.knowledge_points[0].id);
  }));
  curriculumContent.querySelectorAll("[data-concept-id]").forEach((button) => button.addEventListener("click", () => selectConcept(module.module_id, button.dataset.conceptId)));
  curriculumContent.querySelectorAll("[data-concept-action]").forEach((button) => button.addEventListener("click", () => {
    const chosen = selectedConcept();
    const activity = curriculumContent.querySelector(".concept-activity");
    if (button.dataset.conceptAction === "learn") { input.value = `Explain ${chosen.title} using the course material.`; autoGrowInput(); input.focus(); activity.textContent = "A focused learning question is ready in the tutor."; }
    if (button.dataset.conceptAction === "practice") { input.value = chosen.practice_prompt; autoGrowInput(); input.focus(); activity.textContent = "A practice question is ready in the tutor."; }
    if (button.dataset.conceptAction === "hint") { fetchJson("/api/hint", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ concept_id: chosen.id, session_id: sessionId, hint_level: 1 }) }).then((payload) => { sessionId = payload.session_id; window.localStorage.setItem("stochasticTutorSession", sessionId); activity.textContent = `Hint: ${payload.hint}`; }).catch((error) => { activity.textContent = `A hint is not available: ${error.message}`; }); }
    if (button.dataset.conceptAction === "simulation") askAgent(chosen.simulation_prompt);
    if (button.dataset.conceptAction === "quiz") openQuiz();
  }));
}

async function hydrateCurriculum() {
  try {
    curriculum = await fetchJson("/api/curriculum", {}, 10_000);
    if (curriculum.course_title) {
      courseTitle.textContent = curriculum.course_title;
      document.title = curriculum.course_title;
    }
    renderCurriculum();
  }
  catch (error) { curriculumContent.textContent = `Course modules could not be loaded: ${error.message}`; }
}

function seriesLabel(item, index) {
  return item?.name || item?.label || item?.title || `Series ${index + 1}`;
}

function renderChart(series, chartSpec = {}, target = chart) {
  if (!target) return;
  if (!series?.length || !series[0].values?.length) { target.textContent = "No chart is available for this result."; return; }
  const width = 980, height = 480, padding = 48;
  const allValues = series.flatMap((item) => item.values), min = Math.min(...allValues), max = Math.max(...allValues), spread = max - min || 1;
  const allX = series.flatMap((item) => item.x?.length === item.values.length ? item.x : item.values.map((_, index) => index));
  const minX = Math.min(...allX), maxX = Math.max(...allX), xSpread = maxX - minX || 1;
  const colors = ["#635bdb", "#199aa4", "#d58a28", "#8f84ef", "#248a62"];
  const tickCount = 4;
  const yTicks = Array.from({ length: tickCount + 1 }, (_, index) => min + (spread * index) / tickCount);
  const xTicks = Array.from({ length: tickCount + 1 }, (_, index) => minX + (xSpread * index) / tickCount);
  const yPosition = (value) => height - padding - ((value - min) / spread) * (height - padding * 2);
  const xPosition = (value) => padding + ((value - minX) / xSpread) * (width - padding * 2);
  const gridLines = [
    ...yTicks.map((value) => `<line x1="${padding}" y1="${yPosition(value).toFixed(1)}" x2="${width - padding}" y2="${yPosition(value).toFixed(1)}" class="chart-grid-line" />`),
    ...xTicks.map((value) => `<line x1="${xPosition(value).toFixed(1)}" y1="${padding}" x2="${xPosition(value).toFixed(1)}" y2="${height - padding}" class="chart-grid-line" />`),
  ].join("");
  const tickLabels = [
    ...yTicks.map((value) => `<text x="${padding - 10}" y="${(yPosition(value) + 5).toFixed(1)}" text-anchor="end" class="chart-tick-label">${value.toFixed(2)}</text>`),
    ...xTicks.map((value) => `<text x="${xPosition(value).toFixed(1)}" y="${height - padding + 24}" text-anchor="middle" class="chart-tick-label">${value.toFixed(2)}</text>`),
  ].join("");
  const polylines = series.slice(0, 5).map((item, seriesIndex) => {
    const xValues = item.x?.length === item.values.length ? item.x : item.values.map((_, index) => index);
    const points = item.values.map((value, index) => `${xPosition(xValues[index]).toFixed(1)},${yPosition(value).toFixed(1)}`).join(" ");
    const strokeWidth = series.length === 1 ? 3 : 2.5;
    return `<polyline points="${points}" fill="none" stroke="${colors[seriesIndex % colors.length]}" stroke-width="${strokeWidth}" opacity=".9" />`;
  }).join("");
  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Simulation chart"><rect x="${padding}" y="${padding}" width="${width - padding * 2}" height="${height - padding * 2}" class="chart-plot-background" />${gridLines}<line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" class="chart-axis-line" /><line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" class="chart-axis-line" />${polylines}${tickLabels}<text x="${width / 2}" y="${height - 6}" text-anchor="middle" class="chart-axis-label">${escapeHtml(chartSpec.x_label || "time")}</text><text x="16" y="${height / 2}" text-anchor="middle" class="chart-axis-label" transform="rotate(-90 16 ${height / 2})">${escapeHtml(chartSpec.y_label || "value")}</text></svg>`;
}

function renderLegend(series, target = simulationLegend) {
  if (!target) return;
  const colors = ["#635bdb", "#199aa4", "#d58a28", "#8f84ef", "#248a62"];
  target.innerHTML = series?.length ? `<strong class="legend-title">Legend</strong>${series.slice(0, 5).map((item, index) => `<span class="legend-item"><i style="--legend-color:${colors[index % colors.length]}" aria-hidden="true"></i><span>${escapeHtml(seriesLabel(item, index))}</span></span>`).join("")}` : "";
}

function renderStructuredVisualizations(result, target) {
  const visualizations = result?.visualizations || [];
  if (!target || !visualizations.length) return false;
  const colors = ["#635bdb", "#199aa4", "#d58a28", "#8f84ef", "#248a62"];
  const esc = (value) => escapeHtml(String(value ?? ""));
  const lineSvg = (items, labels = {}) => {
    const width = 520, height = 260, pad = 38;
    const values = items.flatMap((item) => item.values || item.y || []);
    if (!values.length) return "<p>No data available.</p>";
    const min = Math.min(...values), max = Math.max(...values), spread = max - min || 1;
    const xValues = items.flatMap((item) => item.x || (item.values || item.y || []).map((_, i) => i));
    const minX = Math.min(...xValues), maxX = Math.max(...xValues), xSpread = maxX - minX || 1;
    const xp = (x) => pad + ((x - minX) / xSpread) * (width - 2 * pad);
    const yp = (y) => height - pad - ((y - min) / spread) * (height - 2 * pad);
    const paths = items.map((item, index) => {
      const ys = item.values || item.y || [], xs = item.x?.length === ys.length ? item.x : ys.map((_, i) => i);
      const points = ys.map((y, i) => `${xp(xs[i]).toFixed(1)},${yp(y).toFixed(1)}`).join(" ");
      return `<polyline points="${points}" fill="none" stroke="${colors[index % colors.length]}" stroke-width="2" />`;
    }).join("");
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(labels.title || "Visualization")}"><line x1="${pad}" y1="${height-pad}" x2="${width-pad}" y2="${height-pad}" class="chart-axis-line" /><line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height-pad}" class="chart-axis-line" />${paths}<text x="${width/2}" y="${height-6}" text-anchor="middle" class="chart-axis-label">${esc(labels.x_label || "x")}</text><text x="14" y="${height/2}" text-anchor="middle" class="chart-axis-label" transform="rotate(-90 14 ${height/2})">${esc(labels.y_label || "value")}</text></svg>`;
  };
  const panelSvg = (panel, index) => {
    const items = [];
    if (panel.empirical && panel.theoretical) {
      items.push({ x: panel.x, values: panel.empirical }, { x: panel.x, values: panel.theoretical });
    } else if (panel.binomial && panel.poisson) {
      items.push({ x: panel.x, values: panel.binomial }, { x: panel.x, values: panel.poisson });
    }
    return `<article class="visualization-panel"><h4>${esc(panel.parameter ? Object.entries(panel.parameter).map(([k,v]) => `${k}=${v}`).join(", ") : `Panel ${index+1}`)}</h4>${lineSvg(items, { x_label: "value", y_label: "probability" })}</article>`;
  };
  const circleSvg = (states, circleSize, title) => {
    const width = 520, height = 300, cx = 260, cy = 145, radius = 105;
    const positions = (states || []).map((site) => { const a = (2 * Math.PI * site / circleSize) - Math.PI / 2; return [cx + radius * Math.cos(a), cy + radius * Math.sin(a)]; });
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}"><circle cx="${cx}" cy="${cy}" r="${radius}" fill="none" stroke="#b8b2d0" stroke-width="2" />${positions.map(([x,y]) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="8" fill="#635bdb" />`).join("")}<text x="${cx}" y="${height-12}" text-anchor="middle" class="chart-axis-label">${esc(title)}</text></svg>`;
  };
  const cards = visualizations.map((viz, index) => {
    if (viz.renderer === "multi_panel") return `<section class="visualization-card"><h3>${esc(viz.id)}</h3><div class="visualization-panels">${(viz.panels || []).map(panelSvg).join("")}</div></section>`;
    if (viz.renderer === "state_graph") {
      const nodes = viz.graph?.nodes || result.graph?.nodes || [], edges = viz.graph?.edges || result.graph?.edges || [];
      const width = 520, height = 280, cx = width / 2, cy = height / 2, radius = 92;
      const point = (i) => { const a = 2 * Math.PI * i / Math.max(nodes.length, 1) - Math.PI / 2; return [cx + radius * Math.cos(a), cy + radius * Math.sin(a)]; };
      const lines = edges.map((edge) => { const [x1,y1] = point(edge.source), [x2,y2] = point(edge.target); return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="#9b95b4" marker-end="url(#arrow)" /><text x="${((x1+x2)/2).toFixed(1)}" y="${((y1+y2)/2).toFixed(1)}" class="graph-edge-label">${Number(edge.weight).toFixed(2)}</text>`; }).join("");
      const circles = nodes.map((node, i) => { const [x,y] = point(i); return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="22" fill="#635bdb" /><text x="${x.toFixed(1)}" y="${(y+5).toFixed(1)}" text-anchor="middle" fill="white">${esc(node.label || node.id)}</text>`; }).join("");
      return `<section class="visualization-card"><h3>${esc(viz.id)}</h3><svg viewBox="0 0 ${width} ${height}" class="state-graph" role="img" aria-label="State transition graph"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#9b95b4" /></marker></defs>${lines}${circles}</svg></section>`;
    }
    if (viz.renderer === "absorption") {
      const data = viz.data || result.absorption || {};
      const items = (data.distribution || []).map((item) => ({ x: [item.state], values: [item.probability] }));
      return `<section class="visualization-card"><h3>${esc(viz.id)}</h3>${lineSvg(items, { x_label: "absorbing state", y_label: "probability" })}<p class="visualization-note">Empirical success probability: ${esc(data.success_probability)}; theoretical value: ${esc(data.theoretical_success_probability)}.</p></section>`;
    }
    if (viz.renderer === "scatter" || viz.renderer === "scatter_path") {
      const rawPoints = viz.data?.points || viz.path || [];
      const points = viz.x && viz.y ? [{ x: viz.x, values: viz.y }] : [{ x: rawPoints.map((p) => p[0]), values: rawPoints.map((p) => p[1]) }];
      return `<section class="visualization-card"><h3>${esc(viz.id)}</h3>${lineSvg(points, { x_label: "x", y_label: "y" })}</section>`;
    }
    if (viz.renderer === "thinning") {
      const accepted = viz.accepted_events || [], rejected = viz.rejected_events || [], candidates = viz.candidate_events || [];
      return `<section class="visualization-card"><h3>${esc(viz.id)}</h3><div class="event-raster thinning-raster"><div class="event-row"><span class="event-row-label">Candidates</span>${candidates.map((time) => `<i class="candidate-event" style="left:${(100 * time / (result.parameters?.horizon || 1)).toFixed(2)}%"></i>`).join("")}</div><div class="event-row"><span class="event-row-label">Accepted</span>${accepted.map((time) => `<i class="accepted-event" style="left:${(100 * time / (result.parameters?.horizon || 1)).toFixed(2)}%"></i>`).join("")}</div><div class="event-row"><span class="event-row-label">Rejected</span>${rejected.map((time) => `<i class="rejected-event" style="left:${(100 * time / (result.parameters?.horizon || 1)).toFixed(2)}%"></i>`).join("")}</div></div></section>`;
    }
    if (viz.renderer === "configuration" || viz.renderer === "interactive") {
      const states = viz.snapshots || viz.states || [];
      return `<section class="visualization-card"><h3>${esc(viz.id)}</h3><div class="configuration-grid">${states.slice(0, 4).map((state) => circleSvg(Array.isArray(state) ? state : state.positions, result.parameters?.circle_size || viz.circle_size || 12, "Particle configuration")).join("")}</div></section>`;
    }
    if (viz.renderer === "event_raster") return `<section class="visualization-card"><h3>${esc(viz.id)}</h3><div class="event-raster">${(result.raster_event_times || []).map((events, row) => `<div class="event-row" style="--row:${row}">${events.map((time) => `<i style="left:${(100 * time / (result.parameters?.horizon || 1)).toFixed(2)}%"></i>`).join("")}</div>`).join("")}</div></section>`;
    return `<section class="visualization-card"><h3>${esc(viz.id)}</h3><p>Visualization data are ready.</p></section>`;
  }).join("");
  target.innerHTML = `<div class="structured-visualizations">${cards}</div>`;
  return true;
}

function renderSourceList(sourceRows, target = sources) {
  if (!target) return;
  target.innerHTML = sourceRows?.length ? `<ul>${sourceRows.map((source) => `<li><span>${escapeHtml(source.title || source.source)}</span><small>${escapeHtml(source.source)}</small></li>`).join("")}</ul>` : "<p>No course sources were returned.</p>";
}

function renderSources(sourceRows) {
  renderSourceList(sourceRows, sources);
}

function showSimulationView(payload) {
  if (!simulationView) return;
  const series = payload.result?.series || [];
  const experiment = payload.experiment;
  simulationTitle.textContent = experiment?.title || payload.module_label || payload.module_id || "Simulation result";
  simulationSubtitle.textContent = payload.verified ? "Verified output from the Python simulation tool." : "Simulation output is ready for review.";
  if (experimentPurpose) experimentPurpose.textContent = experiment?.teaching_purpose || "";
  if (!renderStructuredVisualizations(payload.result, simulationChart)) renderChart(series, payload.result?.chart, simulationChart);
  renderLegend(series, simulationLegend);
  simulationMetrics.innerHTML = Object.entries(payload.parameters || {}).map(([key, value]) => `<div class="metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(Array.isArray(value) ? JSON.stringify(value) : value)}</strong></div>`).join("");
  if (experimentTeachingNote) {
    experimentTeachingNote.innerHTML = experiment
      ? `<p><strong>What to notice</strong> ${escapeHtml(experiment.expected_observation || "Compare the simulated output with the course theory.")}</p><p><strong>Theory connection</strong> ${escapeHtml(experiment.theory_connection || "Use the result to connect the model definition with its simulated behaviour.")}</p>`
      : "";
  }
  renderSourceList(payload.sources || [], simulationSources);
  tutorLab?.classList.add("simulation-active");
  dashboard?.classList.add("simulation-mode");
  simulationView.classList.remove("hidden");
  simulationView.scrollIntoView({ behavior: "smooth", block: "start" });
}

function hideSimulationView() {
  tutorLab?.classList.remove("simulation-active");
  dashboard?.classList.remove("simulation-mode");
  simulationView?.classList.add("hidden");
}

function renderProgress(memory, note, recommendation) {
  masteryByConcept = Object.fromEntries((memory?.knowledge_points || []).map((item) => [item.concept_id, item]));
  if (curriculum) renderCurriculum();
  learningNote.textContent = note || "Your practice and quiz activity will appear here.";
  learnerProfile.innerHTML = memory?.modules?.length ? memory.modules.map((item) => `<div class="profile-item"><div><strong>${escapeHtml(moduleDisplayLabel(item.module_id))}</strong><span>${escapeHtml(item.attempts)} practice runs · ${escapeHtml(item.quiz_correct)}/${escapeHtml(item.quiz_attempts)} quiz answers</span></div><progress max="100" value="${Math.round(Number(item.mastery) * 100)}" aria-label="${escapeHtml(moduleDisplayLabel(item.module_id))} progress"></progress></div>`).join("") : "<p>No learning record yet.</p>";
  misconceptions.innerHTML = memory?.misconceptions?.length ? `<p class="diagnosis-title">Things to review</p>${memory.misconceptions.map((item) => `<p><strong>${escapeHtml(item.code)}</strong><br />${escapeHtml(item.correction)}</p>`).join("")}` : "";
  nextRecommendation.innerHTML = recommendation ? `<span>NEXT PRACTICE</span><strong>${escapeHtml(moduleDisplayLabel(recommendation.module_id))}</strong><p>${escapeHtml(recommendation.reason)}</p>` : "";
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
    if (!renderStructuredVisualizations(payload.result, chart)) renderChart(payload.result?.series, payload.result?.chart);
    parameters.innerHTML = Object.entries(payload.parameters || {}).map(([key, value]) => `<div class="metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(Array.isArray(value) ? JSON.stringify(value) : value)}</strong></div>`).join("");
    showSimulationView(payload);
  } else { runMeta.textContent = "Concept explanation"; hideSimulationView(); }
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
  const cleanQuestion = String(question || "").trim();
  if (mutationInFlight || !cleanQuestion) return;
  setComposerLoading(true);
  addMessage("user", cleanQuestion);
  try {
    const payload = await fetchJson("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: cleanQuestion, session_id: sessionId }) });
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
  finally { setComposerLoading(false); input.focus(); autoGrowInput(); }
}

async function openQuiz() {
  if (mutationInFlight) return;
  try {
    const payload = await fetchJson(`/api/quiz?module_id=${encodeURIComponent(activeModuleId)}`);
    const quiz = payload.quiz;
    quizPanel.classList.remove("hidden");
    quizPanel.innerHTML = `<p class="quiz-module">${escapeHtml(moduleDisplayLabel(quiz.module_id))} · CHECK YOUR UNDERSTANDING</p><h3 id="quizQuestion">${escapeHtml(quiz.question)}</h3><div class="quiz-choices" role="group" aria-labelledby="quizQuestion">${quiz.choices.map((choice, index) => `<button type="button" data-answer="${index}">${String.fromCharCode(65 + index)}. ${escapeHtml(choice)}</button>`).join("")}</div><p class="quiz-feedback" role="status"></p>`;
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

let composing = false;
input.addEventListener("compositionstart", () => { composing = true; });
input.addEventListener("compositionend", () => { composing = false; autoGrowInput(); });
input.addEventListener("input", autoGrowInput);
input.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing || composing) return;
  event.preventDefault();
  if (!mutationInFlight && input.value.trim()) form.requestSubmit();
});
form.addEventListener("submit", (event) => { event.preventDefault(); if (mutationInFlight) return; const question = input.value.trim(); if (question) { input.value = ""; autoGrowInput(); askAgent(question); } });
quizButton.addEventListener("click", openQuiz);
resetButton.addEventListener("click", () => { sessionId = null; window.localStorage.removeItem("stochasticTutorSession"); hideSimulationView(); conversation.innerHTML = '<article class="message agent-message"><span class="message-label">TUTOR</span><div class="message-body"><p>Ask me about a concept, a module, or a simulation.</p></div></article>'; quizPanel.classList.add("hidden"); input.value = ""; autoGrowInput(); input.focus(); composerStatus.textContent = "Press Enter to ask · Shift+Enter for a new line"; });
closeSimulationView?.addEventListener("click", hideSimulationView);
document.querySelectorAll("[data-scroll]").forEach((button) => button.addEventListener("click", () => document.getElementById(button.dataset.scroll)?.scrollIntoView({ behavior: "smooth" })));

autoGrowInput();
hydrateHealth();
hydrateCurriculum();
