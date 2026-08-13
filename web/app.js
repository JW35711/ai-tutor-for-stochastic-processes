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
const courseTitle = document.querySelector("#courseViewTitle");
const locationBreadcrumb = document.querySelector("#locationBreadcrumb");
const composerStatus = document.querySelector("#composerStatus");
const debugPanel = document.querySelector("#debugPanel");
const debugContent = document.querySelector("#debugContent");
const navItems = document.querySelectorAll(".nav-item[data-view]");
const appViews = document.querySelectorAll(".app-view");
const languageSelect = document.querySelector("#languageSelect");

const translations = {
  en: {
    "nav.overview": "Overview", "nav.course": "Course", "nav.tutor": "AI Tutor", "nav.simulation": "Simulation Lab", "nav.progress": "My Progress",
    "sidebar.ready": "Ready to learn", "sidebar.note": "Verified simulations are available when useful.", "topbar.workspace": "Course workspace", "language.label": "Language", "health.connecting": "Connecting", "health.ready": "Ready to learn", "health.offline": "Offline",
    "common.engineering": "ENGINEERING MATHEMATICS", "common.newChat": "New chat", "common.sources": "Sources", "common.tutor": "TUTOR", "common.you": "YOU", "common.legend": "Legend", "common.noData": "No data available.", "common.whatToNotice": "What to notice", "common.theoryConnection": "Theory connection", "common.checkUnderstanding": "CHECK YOUR UNDERSTANDING", "common.hint": "Hint", "common.hintUnavailable": "A hint is not available",
    "overview.title": "Continue your stochastic-process journey", "overview.intro": "Learn concepts, practice problems, and explore stochastic models through verified simulations.", "overview.next": "NEXT UP", "overview.nextTitle": "Start with Module 00", "overview.nextText": "Build a reliable Monte Carlo foundation before exploring stochastic models.", "overview.openCourse": "Open course", "overview.recommended": "recommended", "overview.snapshot": "YOUR SNAPSHOT", "overview.modules": "modules", "overview.points": "knowledge points", "overview.tools": "verified tools", "overview.activity": "Your learning activity will appear here after your first practice or quiz.", "overview.quick": "QUICK ACCESS", "overview.choose": "Choose how to learn", "overview.askTutor": "Ask the Tutor", "overview.askTutorDesc": "Get a grounded explanation from the course material.", "overview.explore": "Explore a simulation", "overview.exploreDesc": "Run an approved experiment and inspect its chart.", "overview.review": "Review progress", "overview.reviewDesc": "See mastery, review items, and the next recommendation.", "overview.recent": "RECENT ACTIVITY", "overview.momentum": "Keep your momentum", "overview.openTutor": "Open tutor", "overview.noRecent": "No recent activity yet. Ask a concept question or try the first module.",
    "course.intro": "Browse the eleven modules and move from a knowledge point to a verified experiment.", "course.modules": "COURSE MODULES", "course.choose": "Choose a module", "course.loading": "Loading course modules…",
    "tutor.title": "Ask, understand, and follow up", "tutor.intro": "Chat with the course tutor. Explanations are grounded in the notebooks and lecture notes.", "tutor.chat": "TUTOR CHAT", "tutor.ask": "Ask a question", "tutor.quiz": "Check your understanding", "tutor.empty": "Ask me about a concept, a module, or a simulation.", "tutor.askLabel": "Ask the tutor", "tutor.placeholder": "For example: What is Brownian motion?", "tutor.askButton": "Ask Tutor", "tutor.composer": "Press Enter to ask · Shift+Enter for a new line", "tutor.support": "LEARNING SUPPORT", "tutor.results": "Results", "tutor.ready": "Ready when you are", "tutor.resultHint": "Sources and simulation details will appear here after a Tutor response.",
    "simulation.label": "SIMULATION", "simulation.title": "Explore verified experiments", "simulation.intro": "Choose a knowledge point in Course or ask the Tutor for an explicit simulation.", "simulation.catalogue": "EXPERIMENT CATALOGUE", "simulation.emptyTitle": "Simulation results appear here", "simulation.emptyText": "Start from a course knowledge point with a Simulation action, or ask the Tutor: “Simulate Brownian motion with 100 steps.”", "simulation.browse": "Browse course experiments", "simulation.verified": "VERIFIED EXPERIMENT", "simulation.result": "Simulation result", "simulation.verifiedOutput": "Verified output from the selected stochastic-process model.", "simulation.backTutor": "Back to tutor", "simulation.sources": "Sources and parameters",
    "progress.title": "Your learning record", "progress.intro": "Practice and quiz activity are saved to your local learner profile.", "progress.record": "LEARNING RECORD", "progress.mastery": "Mastery by module", "progress.local": "Local memory", "progress.emptyNote": "Your practice and quiz activity will appear here.", "progress.noRecord": "No learning record yet.",
  },
  zh: {
    "nav.overview": "概览", "nav.course": "课程", "nav.tutor": "AI 导师", "nav.simulation": "模拟实验室", "nav.progress": "我的进度",
    "sidebar.ready": "可以开始学习", "sidebar.note": "需要时可以使用经过验证的模拟实验。", "topbar.workspace": "课程工作区", "language.label": "语言", "health.connecting": "连接中", "health.ready": "可以学习", "health.offline": "离线",
    "common.engineering": "工程数学", "common.newChat": "新建对话", "common.sources": "来源", "common.tutor": "导师", "common.you": "你", "common.legend": "图例", "common.noData": "没有可用数据。", "common.whatToNotice": "观察重点", "common.theoryConnection": "理论联系", "common.checkUnderstanding": "检查理解", "common.hint": "提示", "common.hintUnavailable": "暂无提示",
    "overview.title": "继续你的随机过程学习", "overview.intro": "学习概念、练习问题，并通过经过验证的模拟探索随机模型。", "overview.next": "下一步", "overview.nextTitle": "从 Module 00 开始", "overview.nextText": "先建立可靠的蒙特卡洛基础，再学习随机模型。", "overview.openCourse": "打开课程", "overview.recommended": "推荐", "overview.snapshot": "学习概览", "overview.modules": "个模块", "overview.points": "个知识点", "overview.tools": "个验证工具", "overview.activity": "完成第一次练习或测验后，你的学习记录会显示在这里。", "overview.quick": "快捷入口", "overview.choose": "选择学习方式", "overview.askTutor": "询问导师", "overview.askTutorDesc": "从课程材料中获得有依据的解释。", "overview.explore": "探索模拟", "overview.exploreDesc": "运行一个经过批准的实验并查看图表。", "overview.review": "查看进度", "overview.reviewDesc": "查看掌握度、待复习内容和下一步推荐。", "overview.recent": "最近活动", "overview.momentum": "保持学习节奏", "overview.openTutor": "打开导师", "overview.noRecent": "还没有最近活动。可以提问一个概念，或从第一个模块开始。",
    "course.intro": "浏览 11 个模块，从知识点进入经过验证的实验。", "course.modules": "课程模块", "course.choose": "选择一个模块", "course.loading": "正在加载课程模块…",
    "tutor.title": "提问、理解并继续追问", "tutor.intro": "与课程导师对话。回答基于 notebook 和课程讲义。", "tutor.chat": "导师对话", "tutor.ask": "提出问题", "tutor.quiz": "检查理解", "tutor.empty": "你可以问我概念、模块或模拟实验。", "tutor.askLabel": "询问导师", "tutor.placeholder": "例如：什么是布朗运动？", "tutor.askButton": "询问导师", "tutor.composer": "按 Enter 提问 · Shift+Enter 换行", "tutor.support": "学习支持", "tutor.results": "结果", "tutor.ready": "准备好了", "tutor.resultHint": "导师回答后，来源和模拟详情会显示在这里。",
    "simulation.label": "模拟", "simulation.title": "探索经过验证的实验", "simulation.intro": "在课程中选择知识点，或向导师明确提出模拟请求。", "simulation.catalogue": "实验目录", "simulation.emptyTitle": "模拟结果会显示在这里", "simulation.emptyText": "从课程知识点点击 Simulation，或向导师提问：“模拟 100 步布朗运动。”", "simulation.browse": "浏览课程实验", "simulation.verified": "经过验证的实验", "simulation.result": "模拟结果", "simulation.verifiedOutput": "所选随机过程模型的验证输出。", "simulation.backTutor": "返回导师", "simulation.sources": "来源和参数",
    "progress.title": "你的学习记录", "progress.intro": "练习和测验活动会保存到本地学习者档案。", "progress.record": "学习记录", "progress.mastery": "按模块查看掌握度", "progress.local": "本地记忆", "progress.emptyNote": "你的练习和测验活动会显示在这里。", "progress.noRecord": "还没有学习记录。",
  },
  sv: {
    "nav.overview": "Översikt", "nav.course": "Kurs", "nav.tutor": "AI-handledare", "nav.simulation": "Simuleringslabb", "nav.progress": "Mina framsteg",
    "sidebar.ready": "Redo att lära", "sidebar.note": "Verifierade simuleringar finns tillgängliga när de behövs.", "topbar.workspace": "Kursyta", "language.label": "Språk", "health.connecting": "Ansluter", "health.ready": "Redo att lära", "health.offline": "Offline",
    "common.engineering": "TEKNISK MATEMATIK", "common.newChat": "Ny chatt", "common.sources": "Källor", "common.tutor": "HANDLEDARE", "common.you": "DU", "common.legend": "Teckenförklaring", "common.noData": "Inga data tillgängliga.", "common.whatToNotice": "Observera", "common.theoryConnection": "Teoretisk koppling", "common.checkUnderstanding": "KONTROLLERA DIN FÖRSTÅELSE", "common.hint": "Ledtråd", "common.hintUnavailable": "Ingen ledtråd är tillgänglig",
    "overview.title": "Fortsätt din resa i stokastiska processer", "overview.intro": "Lär dig begrepp, öva på problem och utforska stokastiska modeller genom verifierade simuleringar.", "overview.next": "NÄSTA STEG", "overview.nextTitle": "Börja med Module 00", "overview.nextText": "Bygg en stabil grund i Monte Carlo innan du utforskar stokastiska modeller.", "overview.openCourse": "Öppna kursen", "overview.recommended": "rekommenderas", "overview.snapshot": "DIN ÖVERSIKT", "overview.modules": "moduler", "overview.points": "kunskapspunkter", "overview.tools": "verifierade verktyg", "overview.activity": "Din studieaktivitet visas här efter din första övning eller ditt första quiz.", "overview.quick": "SNABBÅTKOMST", "overview.choose": "Välj hur du vill lära dig", "overview.askTutor": "Fråga handledaren", "overview.askTutorDesc": "Få en förankrad förklaring från kursmaterialet.", "overview.explore": "Utforska en simulering", "overview.exploreDesc": "Kör ett godkänt experiment och granska diagrammet.", "overview.review": "Granska framsteg", "overview.reviewDesc": "Se behärskning, repetitionspunkter och nästa rekommendation.", "overview.recent": "SENASTE AKTIVITET", "overview.momentum": "Fortsätt hålla takten", "overview.openTutor": "Öppna handledaren", "overview.noRecent": "Ingen aktivitet ännu. Ställ en begreppsfråga eller prova den första modulen.",
    "course.intro": "Bläddra bland de elva modulerna och gå från en kunskapspunkt till ett verifierat experiment.", "course.modules": "KURSMODULER", "course.choose": "Välj en modul", "course.loading": "Laddar kursmoduler…",
    "tutor.title": "Fråga, förstå och följ upp", "tutor.intro": "Chatta med kursens handledare. Förklaringarna bygger på notebook-filerna och föreläsningsanteckningarna.", "tutor.chat": "HANDLEDARCHATT", "tutor.ask": "Ställ en fråga", "tutor.quiz": "Kontrollera din förståelse", "tutor.empty": "Fråga mig om ett begrepp, en modul eller en simulering.", "tutor.askLabel": "Fråga handledaren", "tutor.placeholder": "Till exempel: Vad är Browns rörelse?", "tutor.askButton": "Fråga handledaren", "tutor.composer": "Tryck Enter för att fråga · Shift+Enter för ny rad", "tutor.support": "LÄRANDESTÖD", "tutor.results": "Resultat", "tutor.ready": "Redo när du är", "tutor.resultHint": "Källor och simuleringsdetaljer visas här efter ett svar från handledaren.",
    "simulation.label": "SIMULERING", "simulation.title": "Utforska verifierade experiment", "simulation.intro": "Välj en kunskapspunkt i Kurs eller be handledaren om en uttrycklig simulering.", "simulation.catalogue": "EXPERIMENTKATALOG", "simulation.emptyTitle": "Simuleringsresultat visas här", "simulation.emptyText": "Börja från en kunskapspunkt med åtgärden Simulation, eller fråga handledaren: ”Simulate Brownian motion with 100 steps.”", "simulation.browse": "Bläddra bland kursexperiment", "simulation.verified": "VERIFIERAT EXPERIMENT", "simulation.result": "Simuleringsresultat", "simulation.verifiedOutput": "Verifierat resultat från den valda stokastiska modellen.", "simulation.backTutor": "Tillbaka till handledaren", "simulation.sources": "Källor och parametrar",
    "progress.title": "Din studiehistorik", "progress.intro": "Övnings- och quizaktivitet sparas i din lokala lärarprofil.", "progress.record": "STUDIEHISTORIK", "progress.mastery": "Behärskning per modul", "progress.local": "Lokalt minne", "progress.emptyNote": "Din övnings- och quizaktivitet visas här.", "progress.noRecord": "Ingen studiehistorik ännu.",
  },
};

let sessionId = window.localStorage.getItem("stochasticTutorSession");
let activeModuleId = window.localStorage.getItem("stochasticTutorCurrentModule") || "module00";
let currentConceptId = window.localStorage.getItem("stochasticTutorCurrentConcept");
let curriculum = null;
let mutationInFlight = false;
let latestPayload = null;
let masteryByConcept = {};
let activeViewId = window.localStorage.getItem("stochasticTutorActiveView") || "overviewView";
let language = window.localStorage.getItem("stochlabLanguage") || "en";
const debugMode = new URLSearchParams(window.location.search).get("debug") === "1";
if (debugMode) debugPanel.classList.remove("hidden");

function t(key, fallback = key) {
  return translations[language]?.[key] || translations.en[key] || fallback;
}

function applyTranslations() {
  document.documentElement.lang = language === "zh" ? "zh-CN" : language === "sv" ? "sv-SE" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n, node.textContent);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.setAttribute("placeholder", t(node.dataset.i18nPlaceholder, node.getAttribute("placeholder") || ""));
  });
  if (languageSelect) {
    languageSelect.value = language;
    languageSelect.setAttribute("aria-label", language === "zh" ? "语言" : language === "sv" ? "Språk" : "Language");
  }
  if (activeViewId) showView(activeViewId);
}

function showView(viewId, options = {}) {
  const target = document.getElementById(viewId) || document.getElementById("overviewView");
  if (!target) return;
  activeViewId = target.id;
  window.localStorage.setItem("stochasticTutorActiveView", activeViewId);
  appViews.forEach((view) => view.classList.toggle("active-view", view === target));
  navItems.forEach((item) => {
    const selected = item.dataset.view === activeViewId;
    item.classList.toggle("active", selected);
    item.setAttribute("aria-current", selected ? "page" : "false");
  });
  locationBreadcrumb.textContent = target.querySelector("h1")?.textContent || "Course workspace";
  if (options.focus) target.scrollIntoView({ behavior: "smooth", block: "start" });
}

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
  // Extract every supported delimiter before escaping prose.  Display forms
  // are matched first so their inner dollars are never mistaken for inline
  // math.  The placeholder is plain text and therefore cannot be altered by
  // the Markdown/HTML pass below.
  raw = raw.replace(/\$\$([\s\S]*?)\$\$|\\\[([\s\S]*?)\\\]|\\\(([\s\S]*?)\\\)|\$([^$\n]+)\$/g, (match, dollars, brackets, parens, inline) => {
    const value = dollars ?? brackets ?? parens ?? inline ?? "";
    const display = dollars !== undefined || brackets !== undefined;
    return stashMath(match, value, display);
  });
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
      // Older provider responses occasionally contain the HTML entity name
      // inside a matrix cell ("amp;").  Repair only inside extracted math;
      // normal prose remains safely escaped below.
      .replaceAll("&amp;", "&")
      .replaceAll("amp;", "&")
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
  article.innerHTML = `<span class="message-label">${type === "user" ? t("common.you") : t("common.tutor")}</span><div class="message-body">${type === "user" ? `<p>${escapeHtml(text)}</p>` : `<p>${renderTutorMarkdown(text)}</p>`}</div>`;
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
  const moduleWord = language === "zh" ? "模块" : language === "sv" ? "Modul" : "Module";
  return module ? `${moduleWord} ${moduleNumber(module)} · ${module.label}` : (language === "zh" ? "课程模块" : language === "sv" ? "Kursmodul" : "Course module");
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
    ? `${language === "zh" ? "导师正在回答" : "Tutor is responding"} <span aria-hidden="true">…</span>`
    : `${t("tutor.askButton")} <span aria-hidden="true">→</span>`;
  composerStatus.textContent = loading
    ? (language === "zh" ? "导师正在回答…" : "Tutor is responding…")
    : t("tutor.composer");
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
  const ui = language === "zh"
    ? { modules: "课程模块", selected: "已选择知识点", objectives: "学习目标", points: "知识点", start: "从 01 开始", learn: "学习", practice: "练习", hint: "提示", simulation: "模拟", quiz: "测验", learnLabel: "你将学习", explore: "探索模拟", after: "完成本模块后，你应能够", order: "推荐顺序" }
    : language === "sv"
      ? { modules: "Kursmoduler", selected: "VALD KUNSKAPSPUNKT", objectives: "Lärandemål", points: "KUNSKAPSPUNKTER", start: "Börja med 01", learn: "Lär dig", practice: "Öva", hint: "Ledtråd", simulation: "Simulering", quiz: "Quiz", learnLabel: "Du lär dig", explore: "Utforska med simuleringar", after: "Efter denna modul ska du kunna", order: "Rekommenderad ordning" }
    : { modules: "Course modules", selected: "SELECTED KNOWLEDGE POINT", objectives: "Learning objectives", points: "KNOWLEDGE POINTS", start: "Start with 01", learn: "Learn", practice: "Practice", hint: "Hint", simulation: "Simulation", quiz: "Quiz", learnLabel: "You will learn", explore: "Explore with simulations", after: "After this module, you should be able to", order: "Recommended order" };
  if (activeViewId === "courseView") locationBreadcrumb.textContent = `${module.label} / ${concept.title}`;
  moduleTabs.innerHTML = curriculum.modules.map((item) => {
    return `<button type="button" role="tab" aria-selected="${item.module_id === module.module_id}" aria-controls="curriculumContent" aria-label="Module ${moduleNumber(item)}" data-module-id="${escapeHtml(item.module_id)}"><span class="module-tab-number">Module ${moduleNumber(item)}</span></button>`;
  }).join("");
  curriculumContent.innerHTML = `
    <div class="curriculum-breadcrumb"><span>${ui.modules}</span><span aria-hidden="true">/</span><strong>${language === "zh" ? "模块" : language === "sv" ? "Modul" : "Module"} ${number}</strong><span aria-hidden="true">/</span><span>${escapeHtml(concept.title)}</span></div>
    <div class="selected-module-heading"><div><p class="section-label">${language === "zh" ? "模块" : "MODULE"} ${number}</p><h3>${escapeHtml(module.label || "Stochastic Processes")}</h3><p class="module-purpose">${escapeHtml(module.purpose || module.summary || "Explore this stochastic-process model through practice and examples.")}</p></div><div class="module-meta"><span>${module.knowledge_points.length} ${language === "zh" ? "个知识点" : "knowledge points"}</span><span>${ui.order}</span></div></div>
    <section class="learning-objectives" aria-labelledby="objectivesHeading"><h4 id="objectivesHeading">${ui.objectives}</h4><ul>${(module.learning_objectives || []).map((objective) => `<li>${ui.after} ${escapeHtml(objective.replace(/^After this module, you should be able to /i, "").replace(/[.]$/, ""))}.</li>`).join("")}</ul></section>
    <div class="kp-heading"><p class="section-label">${ui.points}</p><span>${ui.start}</span></div>
    <ol class="concept-list" role="list">${module.knowledge_points.map((point, index) => { const status = masteryByConcept[point.id]?.status || "NOT_STARTED"; return `<li><button type="button" role="listitem" aria-current="${point.id === concept.id ? "true" : "false"}" aria-label="${escapeHtml(`${index + 1}. ${point.title}`)}" data-concept-id="${escapeHtml(point.id)}"><span class="concept-index">${String(index + 1).padStart(2, "0")}</span><span class="concept-copy"><strong>${escapeHtml(point.title)}</strong><small>${escapeHtml(point.description || point.summary)}</small></span><span class="concept-status concept-status-${status.toLowerCase().replaceAll("_", "-")}">${escapeHtml(status.replaceAll("_", " "))}</span><span class="concept-arrow" aria-hidden="true">→</span></button></li>`; }).join("")}</ol>
    <section class="concept-detail" aria-labelledby="conceptHeading"><p class="section-label">${ui.selected}</p><h4 id="conceptHeading">${escapeHtml(concept.title)}</h4><p>${escapeHtml(concept.description || concept.summary)}</p><p class="you-learn-label">${ui.learnLabel}</p><ul><li>${escapeHtml(concept.description || concept.summary)}</li><li>${language === "zh" ? "用于回答：" : "Use it to answer: "}${escapeHtml(concept.practice_prompt)}</li></ul>${concept.experiments?.length ? `<div class="experiment-list"><p class="you-learn-label">${ui.explore}</p><ul>${concept.experiments.map((experiment) => `<li>${escapeHtml(experiment.title)}</li>`).join("")}</ul></div>` : ""}<div class="concept-actions"><button type="button" data-concept-action="learn">${ui.learn}</button><button type="button" data-concept-action="practice">${ui.practice}</button><button type="button" data-concept-action="hint">${ui.hint}</button>${concept.experiments?.length ? `<button type="button" class="primary-action" data-concept-action="simulation">${ui.simulation}</button>` : ""}<button type="button" data-concept-action="quiz">${ui.quiz}</button></div><p id="conceptActivity" class="concept-activity" role="status" aria-live="polite"></p></section>`;
  moduleTabs.querySelectorAll("[data-module-id]").forEach((button) => button.addEventListener("click", () => {
    const chosen = curriculum.modules.find((item) => item.module_id === button.dataset.moduleId);
    selectConcept(chosen.module_id, chosen.knowledge_points[0].id);
  }));
  curriculumContent.querySelectorAll("[data-concept-id]").forEach((button) => button.addEventListener("click", () => selectConcept(module.module_id, button.dataset.conceptId)));
  curriculumContent.querySelectorAll("[data-concept-action]").forEach((button) => button.addEventListener("click", () => {
    const chosen = selectedConcept();
    const activity = curriculumContent.querySelector(".concept-activity");
    if (button.dataset.conceptAction === "learn") { input.value = `Explain ${chosen.title} using the course material.`; autoGrowInput(); input.focus(); activity.textContent = language === "zh" ? "已在导师输入框中准备好学习问题。" : "A focused learning question is ready in the tutor."; showView("tutorView"); }
    if (button.dataset.conceptAction === "practice") { input.value = chosen.practice_prompt; autoGrowInput(); input.focus(); activity.textContent = language === "zh" ? "已在导师输入框中准备好练习问题。" : "A practice question is ready in the tutor."; showView("tutorView"); }
    if (button.dataset.conceptAction === "hint") { fetchJson("/api/hint", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ concept_id: chosen.id, session_id: sessionId, hint_level: 1 }) }).then((payload) => { sessionId = payload.session_id; window.localStorage.setItem("stochasticTutorSession", sessionId); activity.textContent = `${t("common.hint")}: ${payload.hint}`; }).catch((error) => { activity.textContent = `${t("common.hintUnavailable")}: ${error.message}`; }); }
    if (button.dataset.conceptAction === "simulation") askAgent(chosen.simulation_prompt);
    if (button.dataset.conceptAction === "quiz") openQuiz();
  }));
}

async function hydrateCurriculum() {
  try {
    curriculum = await fetchJson("/api/curriculum", {}, 10_000);
    if (curriculum.course_title) {
      if (courseTitle) courseTitle.textContent = curriculum.course_title;
      document.title = curriculum.course_title;
    }
    renderCurriculum();
  }
  catch (error) { curriculumContent.textContent = language === "zh" ? `课程模块加载失败：${error.message}` : `Course modules could not be loaded: ${error.message}`; }
}

function seriesLabel(item, index) {
  return item?.name || item?.label || item?.title || `Series ${index + 1}`;
}

function renderChart(series, chartSpec = {}, target = chart) {
  if (!target) return;
  if (!series?.length || !series[0].values?.length) { target.textContent = language === "zh" ? "此结果没有可用图表。" : "No chart is available for this result."; return; }
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
  target.innerHTML = series?.length ? `<strong class="legend-title">${t("common.legend")}</strong>${series.slice(0, 5).map((item, index) => `<span class="legend-item"><i style="--legend-color:${colors[index % colors.length]}" aria-hidden="true"></i><span>${escapeHtml(seriesLabel(item, index))}</span></span>`).join("")}` : "";
}

function renderStructuredVisualizations(result, target) {
  const visualizations = result?.visualizations || [];
  if (!target || !visualizations.length) return false;
  const colors = ["#635bdb", "#199aa4", "#d58a28", "#8f84ef", "#248a62"];
  const esc = (value) => escapeHtml(String(value ?? ""));
  const lineSvg = (items, labels = {}) => {
    const width = 520, height = 260, pad = 38;
    const values = items.flatMap((item) => item.values || item.y || []);
    if (!values.length) return `<p>${t("common.noData")}</p>`;
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
    if (viz.renderer === "line" || viz.renderer === "step_process") {
      const items = [{ x: viz.x, values: viz.values, name: viz.labels?.[0] || viz.id }];
      return `<section class="visualization-card"><h3>${esc(viz.id)}</h3>${lineSvg(items, { x_label: viz.x_label || "x", y_label: viz.y_label || "value" })}</section>`;
    }
    if (viz.renderer === "empirical_vs_theoretical") {
      const items = [{ x: viz.x, values: viz.empirical, name: "empirical" }, { x: viz.x, values: viz.theoretical, name: "theoretical" }];
      return `<section class="visualization-card"><h3>${esc(viz.id)}</h3>${lineSvg(items, { x_label: viz.labels?.x || "x", y_label: viz.labels?.y || "value" })}<p class="visualization-note">Empirical and theoretical curves are shown together.</p></section>`;
    }
    if (viz.renderer === "multi_panel") {
      if (viz.paths) {
        const pathItems = Object.entries(viz.paths).map(([name, path]) => ({ name, x: (path || []).map((point, i) => point?.[0] ?? i), values: (path || []).map((point) => point?.[1] ?? 0) }));
        return `<section class="visualization-card"><h3>${esc(viz.id)}</h3>${lineSvg(pathItems, { x_label: "step", y_label: "position" })}</section>`;
      }
      return `<section class="visualization-card"><h3>${esc(viz.id)}</h3><div class="visualization-panels">${(viz.panels || []).map(panelSvg).join("")}</div></section>`;
    }
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
    if (viz.renderer === "event_raster") return `<section class="visualization-card"><h3>${esc(viz.id)}</h3><div class="event-raster">${(viz.event_times || result.raster_event_times || []).map((events, row) => `<div class="event-row" style="--row:${row}">${events.map((time) => `<i style="left:${(100 * time / (result.parameters?.horizon || 1)).toFixed(2)}%"></i>`).join("")}</div>`).join("")}</div></section>`;
    return `<section class="visualization-card"><h3>${esc(viz.id)}</h3><p>Visualization data are ready.</p></section>`;
  }).join("");
  target.innerHTML = `<div class="structured-visualizations">${cards}</div>`;
  return true;
}

function renderSourceList(sourceRows, target = sources) {
  if (!target) return;
  target.innerHTML = sourceRows?.length ? `<ul>${sourceRows.map((source) => `<li><span>${escapeHtml(source.title || source.source)}</span><small>${escapeHtml(source.source)}</small></li>`).join("")}</ul>` : `<p>${language === "zh" ? "没有返回课程来源。" : "No course sources were returned."}</p>`;
}

function renderSources(sourceRows) {
  renderSourceList(sourceRows, sources);
}

function showSimulationView(payload) {
  if (!simulationView) return;
  const series = payload.result?.series || [];
  const experiment = payload.experiment;
  simulationTitle.textContent = experiment?.title || payload.module_label || payload.module_id || "Simulation result";
  simulationSubtitle.textContent = payload.verified ? (language === "zh" ? "来自 Python 模拟工具的验证输出。" : "Verified output from the Python simulation tool.") : (language === "zh" ? "模拟输出已准备好查看。" : "Simulation output is ready for review.");
  if (experimentPurpose) experimentPurpose.textContent = experiment?.teaching_purpose || "";
  if (!renderStructuredVisualizations(payload.result, simulationChart)) renderChart(series, payload.result?.chart, simulationChart);
  renderLegend(series, simulationLegend);
  simulationMetrics.innerHTML = Object.entries(payload.parameters || {}).map(([key, value]) => `<div class="metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(Array.isArray(value) ? JSON.stringify(value) : value)}</strong></div>`).join("");
  if (experimentTeachingNote) {
    experimentTeachingNote.innerHTML = experiment
      ? `<p><strong>${t("common.whatToNotice")}</strong> ${escapeHtml(experiment.expected_observation || "Compare the simulated output with the course theory.")}</p><p><strong>${t("common.theoryConnection")}</strong> ${escapeHtml(experiment.theory_connection || "Use the result to connect the model definition with its simulated behaviour.")}</p>`
      : "";
  }
  renderSourceList(payload.sources || [], simulationSources);
  tutorLab?.classList.add("simulation-active");
  dashboard?.classList.add("simulation-mode");
  const catalogue = document.querySelector("#simulationCatalogue");
  catalogue?.classList.add("hidden");
  simulationView.classList.remove("hidden");
  showView("simulationLabView", { focus: true });
}

function hideSimulationView() {
  tutorLab?.classList.remove("simulation-active");
  dashboard?.classList.remove("simulation-mode");
  document.querySelector("#simulationCatalogue")?.classList.remove("hidden");
  simulationView?.classList.add("hidden");
}

function renderProgress(memory, note, recommendation) {
  masteryByConcept = Object.fromEntries((memory?.knowledge_points || []).map((item) => [item.concept_id, item]));
  if (curriculum) renderCurriculum();
  learningNote.textContent = note || t("progress.emptyNote");
  learnerProfile.innerHTML = memory?.modules?.length ? memory.modules.map((item) => `<div class="profile-item"><div><strong>${escapeHtml(moduleDisplayLabel(item.module_id))}</strong><span>${escapeHtml(item.attempts)} ${language === "zh" ? "次练习" : "practice runs"} · ${escapeHtml(item.quiz_correct)}/${escapeHtml(item.quiz_attempts)} ${language === "zh" ? "道测验正确" : "quiz answers"}</span></div><progress max="100" value="${Math.round(Number(item.mastery) * 100)}" aria-label="${escapeHtml(moduleDisplayLabel(item.module_id))} progress"></progress></div>`).join("") : `<p>${escapeHtml(t("progress.noRecord"))}</p>`;
  misconceptions.innerHTML = memory?.misconceptions?.length ? `<p class="diagnosis-title">${language === "zh" ? "需要复习" : "Things to review"}</p>${memory.misconceptions.map((item) => `<p><strong>${escapeHtml(item.code)}</strong><br />${escapeHtml(item.correction)}</p>`).join("")}` : "";
  nextRecommendation.innerHTML = recommendation ? `<span>${language === "zh" ? "下一次练习" : "NEXT PRACTICE"}</span><strong>${escapeHtml(moduleDisplayLabel(recommendation.module_id))}</strong><p>${escapeHtml(recommendation.reason)}</p>` : "";
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
  } else { runMeta.textContent = language === "zh" ? "概念解释" : "Concept explanation"; hideSimulationView(); }
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
    const payload = await fetchJson("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: cleanQuestion, session_id: sessionId, ui_language: language }) });
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
    if (!payload.tool_called) showView("tutorView");
  } catch (error) { addMessage("agent", language === "zh" ? `这次请求未能完成：${error.message}` : `I could not complete that request: ${error.message}`); }
  finally { setComposerLoading(false); input.focus(); autoGrowInput(); }
}

async function openQuiz() {
  if (mutationInFlight) return;
  try {
    const payload = await fetchJson(`/api/quiz?module_id=${encodeURIComponent(activeModuleId)}`);
    const quiz = payload.quiz;
    quizPanel.classList.remove("hidden");
    quizPanel.innerHTML = `<p class="quiz-module">${escapeHtml(moduleDisplayLabel(quiz.module_id))} · ${t("common.checkUnderstanding")}</p><h3 id="quizQuestion">${escapeHtml(quiz.question)}</h3><div class="quiz-choices" role="group" aria-labelledby="quizQuestion">${quiz.choices.map((choice, index) => `<button type="button" data-answer="${index}">${String.fromCharCode(65 + index)}. ${escapeHtml(choice)}</button>`).join("")}</div><p class="quiz-feedback" role="status"></p>`;
    quizPanel.querySelectorAll("[data-answer]").forEach((button) => button.addEventListener("click", () => submitQuiz(quiz.id, Number(button.dataset.answer))));
  } catch (error) { quizPanel.classList.remove("hidden"); quizPanel.textContent = language === "zh" ? `测验加载失败：${error.message}` : `The quiz could not be loaded: ${error.message}`; }
}

async function submitQuiz(questionId, answerIndex) {
  const buttons = quizPanel.querySelectorAll("[data-answer]"); buttons.forEach((button) => { button.disabled = true; });
  try {
    const payload = await fetchJson("/api/quiz/submit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question_id: questionId, answer_index: answerIndex, session_id: sessionId }) });
    sessionId = payload.session_id; window.localStorage.setItem("stochasticTutorSession", sessionId);
    const result = payload.result; quizPanel.querySelector(".quiz-feedback").textContent = `${result.correct ? (language === "zh" ? "回答正确。" : "Correct. ") : (language === "zh" ? "再想想。" : "Not quite. ")}${result.explanation}`; renderProgress(payload.memory, language === "zh" ? "测验结果已保存。" : "Your quiz result has been saved.", payload.recommendation);
  } catch (error) { quizPanel.querySelector(".quiz-feedback").textContent = language === "zh" ? `答案保存失败：${error.message}` : `The answer could not be saved: ${error.message}`; buttons.forEach((button) => { button.disabled = false; }); }
}

async function hydrateHealth() { try { await fetchJson("/health", {}, 5_000); healthStatus.classList.add("online"); healthStatus.innerHTML = `<i></i>${escapeHtml(t("health.ready"))}`; } catch (_) { healthStatus.innerHTML = `<i></i>${escapeHtml(t("health.offline"))}`; } }

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
resetButton.addEventListener("click", () => { sessionId = null; window.localStorage.removeItem("stochasticTutorSession"); hideSimulationView(); conversation.innerHTML = `<article class="message agent-message"><span class="message-label">${t("common.tutor")}</span><div class="message-body"><p>${escapeHtml(t("tutor.empty"))}</p></div></article>`; quizPanel.classList.add("hidden"); input.value = ""; autoGrowInput(); input.focus(); composerStatus.textContent = t("tutor.composer"); });
closeSimulationView?.addEventListener("click", () => { hideSimulationView(); showView("tutorView", { focus: true }); });
navItems.forEach((button) => button.addEventListener("click", () => showView(button.dataset.view, { focus: true })));
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view, { focus: true })));
languageSelect?.addEventListener("change", () => {
  language = ["en", "zh", "sv"].includes(languageSelect.value) ? languageSelect.value : "en";
  window.localStorage.setItem("stochlabLanguage", language);
  applyTranslations();
  hydrateHealth();
  if (curriculum) renderCurriculum();
});

autoGrowInput();
hydrateHealth();
hydrateCurriculum();
showView(activeViewId);
applyTranslations();
