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
const overviewNextTitle = document.querySelector("#overviewNextTitle");
const overviewNextText = document.querySelector("#overviewNextText");
const overviewActivity = document.querySelector("#overviewActivity");
const overviewRecent = document.querySelector("#overviewRecent");
const overviewContinue = document.querySelector("#overviewContinue");
const quizButton = document.querySelector("#quizButton");
const quizPanel = document.querySelector("#quizPanel");
const practicePanel = document.querySelector("#practicePanel");
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
const simulationSearch = document.querySelector("#simulationSearch");
const simulationFilter = document.querySelector("#simulationFilter");
const simulationCatalogue = document.querySelector("#simulationCatalogue");
const simulationCatalogueGrid = document.querySelector("#simulationCatalogueGrid");
const simulationCount = document.querySelector("#simulationCount");
const simulationDetail = document.querySelector("#simulationDetail");
const authControls = document.querySelector("#authControls");
const authPopover = document.querySelector("#authPopover");

const translations = {
  en: {
    "nav.overview": "Overview", "nav.course": "Course", "nav.tutor": "AI Tutor", "nav.simulation": "Simulation Lab", "nav.progress": "My Progress",
    "sidebar.ready": "Ready to learn", "sidebar.note": "Verified simulations are available when useful.", "topbar.workspace": "Course workspace", "language.label": "Language", "health.connecting": "Connecting", "health.ready": "Ready to learn", "health.offline": "Offline",
    "common.engineering": "ENGINEERING MATHEMATICS", "common.newChat": "New chat", "common.sources": "Sources", "common.tutor": "TUTOR", "common.you": "YOU", "common.legend": "Legend", "common.noData": "No data available.", "common.whatToNotice": "What to notice", "common.theoryConnection": "Theory connection", "common.checkUnderstanding": "CHECK YOUR UNDERSTANDING", "common.hint": "Hint", "common.hintUnavailable": "A hint is not available",
    "overview.title": "Continue your stochastic-process journey", "overview.intro": "Learn concepts, practice problems, and explore stochastic models through verified simulations.", "overview.next": "NEXT UP", "overview.nextTitle": "Start with Module 00", "overview.nextText": "Build a reliable Monte Carlo foundation before exploring stochastic models.", "overview.openCourse": "Open course", "overview.recommended": "recommended", "overview.snapshot": "YOUR SNAPSHOT", "overview.modules": "modules", "overview.points": "knowledge points", "overview.tools": "verified tools", "overview.activity": "Your learning activity will appear here after your first practice or quiz.", "overview.quick": "QUICK ACCESS", "overview.choose": "Choose how to learn", "overview.askTutor": "Ask the Tutor", "overview.askTutorDesc": "Get a grounded explanation from the course material.", "overview.explore": "Explore a simulation", "overview.exploreDesc": "Run an approved experiment and inspect its chart.", "overview.review": "Review progress", "overview.reviewDesc": "See mastery, review items, and the next recommendation.", "overview.recent": "RECENT ACTIVITY", "overview.momentum": "Keep your momentum", "overview.openTutor": "Open tutor", "overview.noRecent": "No recent activity yet. Ask a concept question or try the first module.",
    "course.intro": "Browse the eleven modules and move from a knowledge point to a verified experiment.", "course.modules": "COURSE MODULES", "course.choose": "Choose a module", "course.loading": "Loading course modules…",
    "tutor.title": "Ask, understand, and follow up", "tutor.intro": "Chat with the course tutor. Explanations are grounded in the notebooks and lecture notes.", "tutor.chat": "TUTOR CHAT", "tutor.ask": "Ask a question", "tutor.quiz": "Check your understanding", "tutor.empty": "Ask me about a concept, a module, or a simulation.", "tutor.askLabel": "Ask the tutor", "tutor.placeholder": "For example: What is Brownian motion?", "tutor.askButton": "Ask Tutor", "tutor.composer": "Press Enter to ask · Shift+Enter for a new line", "tutor.support": "LEARNING SUPPORT", "tutor.results": "Results", "tutor.ready": "Ready when you are", "tutor.resultHint": "Sources and simulation details will appear here after a Tutor response.",
    "simulation.label": "SIMULATION", "simulation.title": "Explore verified experiments", "simulation.intro": "Choose a knowledge point in Course or ask the Tutor for an explicit simulation.", "simulation.catalogue": "EXPERIMENT CATALOGUE", "simulation.emptyTitle": "Simulation results appear here", "simulation.emptyText": "Start from a course knowledge point with a Simulation action, or ask the Tutor: “Simulate Brownian motion with 100 steps.”", "simulation.browse": "Browse course experiments", "simulation.verified": "VERIFIED EXPERIMENT", "simulation.result": "Simulation result", "simulation.verifiedOutput": "Verified output from the selected stochastic-process model.", "simulation.backTutor": "Back to tutor", "simulation.sources": "Sources and parameters", "simulation.search": "Search title, module, or knowledge point", "simulation.allModules": "All modules", "simulation.goal": "Learning goal", "simulation.type": "Experiment type", "simulation.parameters": "Parameters", "simulation.visualization": "Visualization", "simulation.open": "Open experiment", "simulation.run": "Run experiment", "simulation.ask": "Ask Tutor about this", "simulation.backCatalogue": "Back to catalogue", "simulation.noMatches": "No experiments match this search.", "simulation.verifiedCard": "Verified notebook experiment",
    "progress.title": "Your learning record", "progress.intro": "Practice and quiz activity are saved to your local learner profile.", "progress.record": "LEARNING RECORD", "progress.mastery": "Mastery by module", "progress.local": "Local memory", "progress.emptyNote": "Your practice and quiz activity will appear here.", "progress.noRecord": "No learning record yet.",
    "auth.signIn": "Sign in", "auth.register": "Create account", "auth.continueGuest": "Continue as Guest", "auth.username": "Username", "auth.password": "Password", "auth.submit": "Continue", "auth.logout": "Log out", "auth.signedIn": "Signed in as", "auth.switch": "Use another account", "auth.invalid": "Please check your username and password.",
  },
  zh: {
    "nav.overview": "概览", "nav.course": "课程", "nav.tutor": "AI 导师", "nav.simulation": "模拟实验室", "nav.progress": "我的进度",
    "sidebar.ready": "可以开始学习", "sidebar.note": "需要时可以使用经过验证的模拟实验。", "topbar.workspace": "课程工作区", "language.label": "语言", "health.connecting": "连接中", "health.ready": "可以学习", "health.offline": "离线",
    "common.engineering": "工程数学", "common.newChat": "新建对话", "common.sources": "来源", "common.tutor": "导师", "common.you": "你", "common.legend": "图例", "common.noData": "没有可用数据。", "common.whatToNotice": "观察重点", "common.theoryConnection": "理论联系", "common.checkUnderstanding": "检查理解", "common.hint": "提示", "common.hintUnavailable": "暂无提示",
    "overview.title": "继续你的随机过程学习", "overview.intro": "学习概念、练习问题，并通过经过验证的模拟探索随机模型。", "overview.next": "下一步", "overview.nextTitle": "从 Module 00 开始", "overview.nextText": "先建立可靠的蒙特卡洛基础，再学习随机模型。", "overview.openCourse": "打开课程", "overview.recommended": "推荐", "overview.snapshot": "学习概览", "overview.modules": "个模块", "overview.points": "个知识点", "overview.tools": "个验证工具", "overview.activity": "完成第一次练习或测验后，你的学习记录会显示在这里。", "overview.quick": "快捷入口", "overview.choose": "选择学习方式", "overview.askTutor": "询问导师", "overview.askTutorDesc": "从课程材料中获得有依据的解释。", "overview.explore": "探索模拟", "overview.exploreDesc": "运行一个经过批准的实验并查看图表。", "overview.review": "查看进度", "overview.reviewDesc": "查看掌握度、待复习内容和下一步推荐。", "overview.recent": "最近活动", "overview.momentum": "保持学习节奏", "overview.openTutor": "打开导师", "overview.noRecent": "还没有最近活动。可以提问一个概念，或从第一个模块开始。",
    "course.intro": "浏览 11 个模块，从知识点进入经过验证的实验。", "course.modules": "课程模块", "course.choose": "选择一个模块", "course.loading": "正在加载课程模块…",
    "tutor.title": "提问、理解并继续追问", "tutor.intro": "与课程导师对话。回答基于 notebook 和课程讲义。", "tutor.chat": "导师对话", "tutor.ask": "提出问题", "tutor.quiz": "检查理解", "tutor.empty": "你可以问我概念、模块或模拟实验。", "tutor.askLabel": "询问导师", "tutor.placeholder": "例如：什么是布朗运动？", "tutor.askButton": "询问导师", "tutor.composer": "按 Enter 提问 · Shift+Enter 换行", "tutor.support": "学习支持", "tutor.results": "结果", "tutor.ready": "准备好了", "tutor.resultHint": "导师回答后，来源和模拟详情会显示在这里。",
    "simulation.label": "模拟", "simulation.title": "探索经过验证的实验", "simulation.intro": "在课程中选择知识点，或向导师明确提出模拟请求。", "simulation.catalogue": "实验目录", "simulation.emptyTitle": "模拟结果会显示在这里", "simulation.emptyText": "从课程知识点点击知识点中的 Simulation，或向导师提问：“模拟 100 步布朗运动。”", "simulation.browse": "浏览课程实验", "simulation.verified": "经过验证的实验", "simulation.result": "模拟结果", "simulation.verifiedOutput": "所选随机过程模型的验证输出。", "simulation.backTutor": "返回导师", "simulation.sources": "来源和参数", "simulation.search": "搜索实验标题、模块或知识点", "simulation.allModules": "全部模块", "simulation.goal": "学习目标", "simulation.type": "实验类型", "simulation.parameters": "参数", "simulation.visualization": "可视化", "simulation.open": "打开实验", "simulation.run": "运行实验", "simulation.ask": "询问导师", "simulation.backCatalogue": "返回实验目录", "simulation.noMatches": "没有匹配的实验。", "simulation.verifiedCard": "已验证的 notebook 实验",
    "progress.title": "你的学习记录", "progress.intro": "练习和测验活动会保存到本地学习者档案。", "progress.record": "学习记录", "progress.mastery": "按模块查看掌握度", "progress.local": "本地记忆", "progress.emptyNote": "你的练习和测验活动会显示在这里。", "progress.noRecord": "还没有学习记录。",
    "auth.signIn": "登录", "auth.register": "创建账户", "auth.continueGuest": "以访客继续", "auth.username": "用户名", "auth.password": "密码", "auth.submit": "继续", "auth.logout": "退出登录", "auth.signedIn": "已登录：", "auth.switch": "切换账户", "auth.invalid": "请检查用户名和密码。",
  },
  sv: {
    "nav.overview": "Översikt", "nav.course": "Kurs", "nav.tutor": "AI-handledare", "nav.simulation": "Simuleringslabb", "nav.progress": "Mina framsteg",
    "sidebar.ready": "Redo att lära", "sidebar.note": "Verifierade simuleringar finns tillgängliga när de behövs.", "topbar.workspace": "Kursyta", "language.label": "Språk", "health.connecting": "Ansluter", "health.ready": "Redo att lära", "health.offline": "Offline",
    "common.engineering": "TEKNISK MATEMATIK", "common.newChat": "Ny chatt", "common.sources": "Källor", "common.tutor": "HANDLEDARE", "common.you": "DU", "common.legend": "Teckenförklaring", "common.noData": "Inga data tillgängliga.", "common.whatToNotice": "Observera", "common.theoryConnection": "Teoretisk koppling", "common.checkUnderstanding": "KONTROLLERA DIN FÖRSTÅELSE", "common.hint": "Ledtråd", "common.hintUnavailable": "Ingen ledtråd är tillgänglig",
    "overview.title": "Fortsätt din resa i stokastiska processer", "overview.intro": "Lär dig begrepp, öva på problem och utforska stokastiska modeller genom verifierade simuleringar.", "overview.next": "NÄSTA STEG", "overview.nextTitle": "Börja med Module 00", "overview.nextText": "Bygg en stabil grund i Monte Carlo innan du utforskar stokastiska modeller.", "overview.openCourse": "Öppna kursen", "overview.recommended": "rekommenderas", "overview.snapshot": "DIN ÖVERSIKT", "overview.modules": "moduler", "overview.points": "kunskapspunkter", "overview.tools": "verifierade verktyg", "overview.activity": "Din studieaktivitet visas här efter din första övning eller ditt första quiz.", "overview.quick": "SNABBÅTKOMST", "overview.choose": "Välj hur du vill lära dig", "overview.askTutor": "Fråga handledaren", "overview.askTutorDesc": "Få en förankrad förklaring från kursmaterialet.", "overview.explore": "Utforska en simulering", "overview.exploreDesc": "Kör ett godkänt experiment och granska diagrammet.", "overview.review": "Granska framsteg", "overview.reviewDesc": "Se behärskning, repetitionspunkter och nästa rekommendation.", "overview.recent": "SENASTE AKTIVITET", "overview.momentum": "Fortsätt hålla takten", "overview.openTutor": "Öppna handledaren", "overview.noRecent": "Ingen aktivitet ännu. Ställ en begreppsfråga eller prova den första modulen.",
    "course.intro": "Bläddra bland de elva modulerna och gå från en kunskapspunkt till ett verifierat experiment.", "course.modules": "KURSMODULER", "course.choose": "Välj en modul", "course.loading": "Laddar kursmoduler…",
    "tutor.title": "Fråga, förstå och följ upp", "tutor.intro": "Chatta med kursens handledare. Förklaringarna bygger på notebook-filerna och föreläsningsanteckningarna.", "tutor.chat": "HANDLEDARCHATT", "tutor.ask": "Ställ en fråga", "tutor.quiz": "Kontrollera din förståelse", "tutor.empty": "Fråga mig om ett begrepp, en modul eller en simulering.", "tutor.askLabel": "Fråga handledaren", "tutor.placeholder": "Till exempel: Vad är Browns rörelse?", "tutor.askButton": "Fråga handledaren", "tutor.composer": "Tryck Enter för att fråga · Shift+Enter för ny rad", "tutor.support": "LÄRANDESTÖD", "tutor.results": "Resultat", "tutor.ready": "Redo när du är", "tutor.resultHint": "Källor och simuleringsdetaljer visas här efter ett svar från handledaren.",
    "simulation.label": "SIMULERING", "simulation.title": "Utforska verifierade experiment", "simulation.intro": "Välj en kunskapspunkt i Kurs eller be handledaren om en uttrycklig simulering.", "simulation.catalogue": "EXPERIMENTKATALOG", "simulation.emptyTitle": "Simuleringsresultat visas här", "simulation.emptyText": "Börja från en kunskapspunkt med åtgärden Simulation, eller fråga handledaren: ”Simulate Brownian motion with 100 steps.”", "simulation.browse": "Bläddra bland kursexperiment", "simulation.verified": "VERIFIERAT EXPERIMENT", "simulation.result": "Simuleringsresultat", "simulation.verifiedOutput": "Verifierat resultat från den valda stokastiska modellen.", "simulation.backTutor": "Tillbaka till handledaren", "simulation.sources": "Källor och parametrar", "simulation.search": "Sök efter titel, modul eller kunskapspunkt", "simulation.allModules": "Alla moduler", "simulation.goal": "Lärandemål", "simulation.type": "Experimenttyp", "simulation.parameters": "Parametrar", "simulation.visualization": "Visualisering", "simulation.open": "Öppna experiment", "simulation.run": "Kör experiment", "simulation.ask": "Fråga handledaren", "simulation.backCatalogue": "Tillbaka till katalogen", "simulation.noMatches": "Inga experiment matchar sökningen.", "simulation.verifiedCard": "Verifierat notebook-experiment",
    "progress.title": "Din studiehistorik", "progress.intro": "Övnings- och quizaktivitet sparas i din lokala lärarprofil.", "progress.record": "STUDIEHISTORIK", "progress.mastery": "Behärskning per modul", "progress.local": "Lokalt minne", "progress.emptyNote": "Din övnings- och quizaktivitet visas här.", "progress.noRecord": "Ingen studiehistorik ännu.",
    "auth.signIn": "Logga in", "auth.register": "Skapa konto", "auth.continueGuest": "Fortsätt som gäst", "auth.username": "Användarnamn", "auth.password": "Lösenord", "auth.submit": "Fortsätt", "auth.logout": "Logga ut", "auth.signedIn": "Inloggad som", "auth.switch": "Byt konto", "auth.invalid": "Kontrollera användarnamn och lösenord.",
  },
};

let sessionId = window.localStorage.getItem("stochasticTutorSession");
let activeModuleId = window.localStorage.getItem("stochasticTutorCurrentModule") || "module00";
let currentConceptId = window.localStorage.getItem("stochasticTutorCurrentConcept");
let curriculum = null;
let mutationInFlight = false;
let latestPayload = null;
let latestSimulationPayload = null;
let masteryByConcept = {};
let activeViewId = window.localStorage.getItem("stochasticTutorActiveView") || "overviewView";
let language = window.localStorage.getItem("stochlabLanguage") || "en";
let pendingTutorAction = {};
let experimentRegistry = [];
let toolCatalogue = {};
let activeExperimentId = null;
let currentUser = null;
const debugMode = new URLSearchParams(window.location.search).get("debug") === "1";
if (debugMode) debugPanel.classList.remove("hidden");

function t(key, fallback = key) {
  return translations[language]?.[key] || translations.en[key] || fallback;
}

function closeAuthPopover() {
  authPopover?.classList.add("hidden");
  if (authPopover) authPopover.innerHTML = "";
}

function renderAuthControls() {
  if (!authControls) return;
  if (currentUser) {
    authControls.innerHTML = `<span class="auth-user">${escapeHtml(t("auth.signedIn"))} ${escapeHtml(currentUser.username)}</span><button type="button" class="ghost-button" data-auth-logout>${escapeHtml(t("auth.logout"))}</button>`;
    authControls.querySelector("[data-auth-logout]")?.addEventListener("click", logoutUser);
    closeAuthPopover();
    return;
  }
  authControls.innerHTML = `<button type="button" class="ghost-button" data-auth-mode="login">${escapeHtml(t("auth.signIn"))}</button><button type="button" class="ghost-button" data-auth-mode="register">${escapeHtml(t("auth.register"))}</button><button type="button" class="ghost-button" data-auth-guest>${escapeHtml(t("auth.continueGuest"))}</button>`;
  authControls.querySelectorAll("[data-auth-mode]").forEach((button) => button.addEventListener("click", () => openAuthPopover(button.dataset.authMode)));
  authControls.querySelector("[data-auth-guest]")?.addEventListener("click", continueAsGuest);
}

function openAuthPopover(mode = "login", message = "") {
  if (!authPopover) return;
  const isRegister = mode === "register";
  authPopover.classList.remove("hidden");
  authPopover.innerHTML = `<form id="authForm"><h3>${escapeHtml(isRegister ? t("auth.register") : t("auth.signIn"))}</h3><label>${escapeHtml(t("auth.username"))}<input name="username" autocomplete="username" minlength="3" maxlength="32" required /></label><label>${escapeHtml(t("auth.password"))}<input name="password" type="password" autocomplete="${isRegister ? "new-password" : "current-password"}" minlength="8" maxlength="128" required /></label><p class="auth-error" role="alert">${escapeHtml(message)}</p><div class="auth-actions"><button type="submit" class="primary-action">${escapeHtml(t("auth.submit"))}</button><button type="button" class="ghost-button" data-auth-close>${escapeHtml(t("auth.continueGuest"))}</button></div></form>`;
  authPopover.querySelector("[data-auth-close]")?.addEventListener("click", closeAuthPopover);
  authPopover.querySelector("form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const endpoint = isRegister ? "/api/auth/register" : "/api/auth/login";
    try {
      const payload = await fetchJson(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: formData.get("username"), password: formData.get("password") }) });
      currentUser = payload.user;
      sessionId = payload.user.session_id;
      window.localStorage.setItem("stochasticTutorSession", sessionId);
      renderAuthControls();
      await hydrateProfile();
    } catch (error) {
      openAuthPopover(mode, error.message || t("auth.invalid"));
    }
  });
  authPopover.querySelector("input")?.focus();
}

async function hydrateProfile() {
  if (!sessionId) return;
  try {
    const payload = await fetchJson(`/api/profile?session_id=${encodeURIComponent(sessionId)}&ui_language=${encodeURIComponent(language)}`);
    renderProgress(payload.profile, "", payload.recommendation);
    renderOverview(payload.profile, payload.recommendation);
  } catch (_) { /* a guest can start with an empty profile */ }
}

function continueAsGuest() {
  currentUser = null;
  sessionId = null;
  window.localStorage.removeItem("stochasticTutorSession");
  renderAuthControls();
  hydrateProfile();
}

async function logoutUser() {
  try { await fetchJson("/api/auth/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); } catch (_) { /* clear local state even if the server is unavailable */ }
  continueAsGuest();
}

async function hydrateAuth() {
  try {
    const payload = await fetchJson("/api/auth/me", {}, 5_000);
    currentUser = payload.authenticated ? payload.user : null;
    if (currentUser) {
      sessionId = currentUser.session_id;
      window.localStorage.setItem("stochasticTutorSession", sessionId);
    }
  } catch (_) { currentUser = null; }
  renderAuthControls();
  await hydrateProfile();
}

const assessmentStrings = {
  en: {
    check: "CHECK YOUR UNDERSTANDING", practiceLabel: "KNOWLEDGE POINT PRACTICE",
    submit: "Submit answer", retry: "Retry", showReference: "Show reference answer",
    reference: "Reference answer", empty: "Write an answer before submitting.",
    correct: "Correct", incorrect: "Not quite", incomplete: "Incomplete",
    needsMore: "Your answer needs more information.", allHints: "All hints used",
    continue: "Continue", review: "Review this concept", quizRetry: "Try the quiz again",
  },
  zh: {
    check: "检查理解", practiceLabel: "知识点练习",
    submit: "提交答案", retry: "重试", showReference: "显示参考答案",
    reference: "参考答案", empty: "请先写下答案再提交。",
    correct: "回答正确", incorrect: "还不够准确", incomplete: "信息不完整",
    needsMore: "你的答案还需要更多信息。", allHints: "提示已全部使用",
    continue: "继续", review: "复习这个知识点", quizRetry: "再做一次测验",
  },
  sv: {
    check: "KONTROLLERA DIN FÖRSTÅELSE", practiceLabel: "ÖVNING FÖR KUNSKAPSPUNKT",
    submit: "Skicka svar", retry: "Försök igen", showReference: "Visa referenssvar",
    reference: "Referenssvar", empty: "Skriv ett svar innan du skickar in det.",
    correct: "Rätt", incorrect: "Inte riktigt", incomplete: "Ofullständigt",
    needsMore: "Ditt svar behöver mer information.", allHints: "Alla ledtrådar använda",
    continue: "Fortsätt", review: "Repetera detta begrepp", quizRetry: "Försök med quizet igen",
  },
};

function assessmentText(key) {
  return assessmentStrings[language]?.[key] || assessmentStrings.en[key] || key;
}

function conceptTitleForId(conceptId) {
  return curriculum?.modules.flatMap((module) => module.knowledge_points).find((point) => point.id === conceptId)?.title || conceptId;
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
  if (verificationBadge && !latestPayload) verificationBadge.textContent = t("tutor.ready");
  if (activeViewId) showView(activeViewId, { syncHash: false });
  if (curriculum) renderCurriculum();
  if (experimentRegistry.length) renderExperimentCatalogue();
  renderAuthControls();
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
  if (options.syncHash !== false) {
    const route = viewId === "courseView" ? "#/course" : viewId === "tutorView" ? "#/tutor" : viewId === "simulationLabView" ? "#/simulations" : viewId === "progressView" ? "#/progress" : "#/overview";
    if (window.location.hash !== route) window.history.pushState({ route }, "", route);
  }
  if (options.focus) target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function parseRoute() {
  const raw = window.location.hash.replace(/^#\/?/, "").replace(/\/$/, "");
  const parts = raw ? raw.split("/") : ["overview"];
  if (parts[0] === "course") return { view: "courseView", kind: parts[1] ? (parts[2] ? "concept" : "module") : "overview", moduleId: parts[1] || null, conceptId: parts[2] || null };
  if (parts[0] === "tutor") return { view: "tutorView", kind: "tutor" };
  if (parts[0] === "simulations") return { view: "simulationLabView", kind: parts[1] ? "experiment" : "catalogue", experimentId: parts[1] || null };
  if (parts[0] === "progress") return { view: "progressView", kind: "progress" };
  return { view: "overviewView", kind: "overview" };
}

function setRoute(route, { replace = false, focus = true } = {}) {
  const hash = route.startsWith("#") ? route : `#/${route.replace(/^\//, "")}`;
  if (window.location.hash !== hash) {
    const method = replace ? "replaceState" : "pushState";
    window.history[method]({ route: hash }, "", hash);
  }
  applyRoute({ focus });
}

function courseRoute() {
  const route = parseRoute();
  return route.view === "courseView" ? route : { view: "courseView", kind: "overview", moduleId: null, conceptId: null };
}

function applyRoute({ focus = false } = {}) {
  const route = parseRoute();
  activeViewId = route.view;
  if (route.moduleId && curriculum?.modules.some((item) => item.module_id === route.moduleId)) activeModuleId = route.moduleId;
  if (route.conceptId) currentConceptId = route.conceptId;
  if (route.view === "courseView" && curriculum) renderCurriculum();
  if (route.view === "simulationLabView") {
    if (route.kind === "experiment" && experimentRegistry.length) showExperimentDetail(route.experimentId, { navigate: false });
    else showExperimentCatalogue();
  }
  showView(route.view, { syncHash: false, focus });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// Experiment metadata is authored in notebooks and may contain Markdown
// headings.  The catalogue is a compact card, so strip presentation markers
// rather than exposing raw notebook syntax to students.
function cleanExperimentText(value) {
  return String(value || "")
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/\s+/g, " ")
    .trim();
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

function localizedActionPrompt(action, concept, experiment = null) {
  const title = concept?.title || "this concept";
  const experimentTitle = experiment?.title || title;
  if (language === "zh") {
    if (action === "learn") return `什么是${title}？请结合课程材料解释。`;
    if (action === "practice") return `请给我一道关于${title}的练习题。`;
    if (action === "simulation") return `请展示一个帮助我理解${experimentTitle}的模拟实验。`;
    if (action === "quiz") return `测试我对${title}的理解。`;
  }
  if (language === "sv") {
    if (action === "learn") return `Vad är ${title}? Förklara med kursmaterialet.`;
    if (action === "practice") return `Ge mig en övning om ${title}.`;
    if (action === "simulation") return `Visa mig en simulering som hjälper mig att förstå ${experimentTitle}.`;
    if (action === "quiz") return `Testa min förståelse av ${title}.`;
  }
  if (action === "learn") return `What is ${title}? Explain it using the course material.`;
  if (action === "practice") return concept?.practice_prompt || `Give me a practice question about ${title}.`;
  if (action === "simulation") return experiment?.simulation_prompt || `Show me a simulation that helps me understand ${experimentTitle}.`;
  return `Test my understanding of ${title}.`;
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
  setRoute(`course/${moduleId}/${conceptId}`);
}

function renderCurriculum() {
  if (!curriculum?.modules?.length || !moduleTabs || !curriculumContent) return;
  const route = courseRoute();
  const module = route.moduleId ? curriculum.modules.find((item) => item.module_id === route.moduleId) : null;
  const number = moduleNumber(module);
  const ui = language === "zh"
    ? { modules: "课程模块", selected: "已选择知识点", objectives: "学习目标", points: "知识点", start: "从 01 开始", learn: "学习", practice: "练习", hint: "提示", simulation: "模拟", quiz: "测验", learnLabel: "你将学习", explore: "探索模拟", after: "完成本模块后，你应能够", order: "推荐顺序" }
    : language === "sv"
      ? { modules: "Kursmoduler", selected: "VALD KUNSKAPSPUNKT", objectives: "Lärandemål", points: "KUNSKAPSPUNKTER", start: "Börja med 01", learn: "Lär dig", practice: "Öva", hint: "Ledtråd", simulation: "Simulering", quiz: "Quiz", learnLabel: "Du lär dig", explore: "Utforska med simuleringar", after: "Efter denna modul ska du kunna", order: "Rekommenderad ordning" }
      : { modules: "Course modules", selected: "SELECTED KNOWLEDGE POINT", objectives: "Learning objectives", points: "KNOWLEDGE POINTS", start: "Start with 01", learn: "Learn", practice: "Practice", hint: "Hint", simulation: "Simulation", quiz: "Quiz", learnLabel: "You will learn", explore: "Explore with simulations", after: "After this module, you should be able to", order: "Recommended order" };
  moduleTabs.innerHTML = curriculum.modules.map((item) => `<button type="button" role="tab" aria-selected="${item.module_id === module?.module_id}" aria-controls="curriculumContent" aria-label="Module ${moduleNumber(item)}" data-module-id="${escapeHtml(item.module_id)}"><span class="module-tab-number">Module ${moduleNumber(item)}</span></button>`).join("");
  moduleTabs.querySelectorAll("[data-module-id]").forEach((button) => button.addEventListener("click", () => setRoute(`course/${button.dataset.moduleId}`)));
  if (!module) {
    courseTitle && (courseTitle.textContent = curriculum.course_title || "Introduction to Stochastic Processes with Applications");
    locationBreadcrumb.textContent = ui.modules;
    curriculumContent.innerHTML = `<div class="module-card-grid">${curriculum.modules.map((item) => `<article class="module-card"><div class="module-card-number">Module ${moduleNumber(item)}</div><h3>${escapeHtml(item.label)}</h3><p>${escapeHtml(item.purpose || item.summary || "")}</p><div class="module-card-meta"><span>${item.knowledge_points.length} ${language === "zh" ? "个知识点" : language === "sv" ? "kunskapspunkter" : "knowledge points"}</span><span>${item.knowledge_points.reduce((sum, point) => sum + (point.experiments || []).length, 0)} ${language === "zh" ? "个实验" : language === "sv" ? "experiment" : "experiments"}</span></div><button type="button" class="primary-action" data-open-module="${escapeHtml(item.module_id)}">${language === "zh" ? "打开模块" : language === "sv" ? "Öppna modul" : "Open module"} →</button></article>`).join("")}</div>`;
    curriculumContent.querySelectorAll("[data-open-module]").forEach((button) => button.addEventListener("click", () => setRoute(`course/${button.dataset.openModule}`)));
    return;
  }
  if (!module.knowledge_points.some((point) => point.id === (route.conceptId || currentConceptId))) currentConceptId = module.knowledge_points[0]?.id || null;
  const concept = module.knowledge_points.find((point) => point.id === (route.conceptId || currentConceptId)) || module.knowledge_points[0];
  currentConceptId = concept?.id || null;
  activeModuleId = module.module_id;
  window.localStorage.setItem("stochasticTutorCurrentModule", activeModuleId);
  if (currentConceptId) window.localStorage.setItem("stochasticTutorCurrentConcept", currentConceptId);
  locationBreadcrumb.textContent = route.conceptId ? `${module.label} / ${concept.title}` : `${ui.modules} / ${module.label}`;
  curriculumContent.innerHTML = `
    <div class="curriculum-breadcrumb"><button type="button" class="breadcrumb-button" data-course-root>${ui.modules}</button><span aria-hidden="true">/</span><strong>${language === "zh" ? "模块" : language === "sv" ? "Modul" : "Module"} ${moduleNumber(module)}</strong>${route.conceptId ? `<span aria-hidden="true">/</span><span>${escapeHtml(concept.title)}</span>` : ""}</div>
    <div class="selected-module-heading"><div><p class="section-label">${language === "zh" ? "模块" : "MODULE"} ${moduleNumber(module)}</p><h3>${escapeHtml(module.label || "Stochastic Processes")}</h3><p class="module-purpose">${escapeHtml(module.purpose || module.summary || "")}</p></div><div class="module-meta"><span>${module.knowledge_points.length} ${language === "zh" ? "个知识点" : "knowledge points"}</span><span>${module.knowledge_points.reduce((sum, point) => sum + (point.experiments || []).length, 0)} ${language === "zh" ? "个实验" : "experiments"}</span></div></div>
    <section class="learning-objectives" aria-labelledby="objectivesHeading"><h4 id="objectivesHeading">${ui.objectives}</h4><ul>${(module.learning_objectives || []).map((objective) => `<li>${escapeHtml(objective)}</li>`).join("")}</ul></section>
    <div class="kp-heading"><p class="section-label">${ui.points}</p><span>${ui.start}</span></div>
    <ol class="concept-list" role="list">${module.knowledge_points.map((point, index) => { const status = masteryByConcept[point.id]?.status || "NOT_STARTED"; return `<li><button type="button" role="listitem" aria-current="${point.id === concept.id ? "true" : "false"}" aria-label="${escapeHtml(`${index + 1}. ${point.title}`)}" data-concept-id="${escapeHtml(point.id)}"><span class="concept-index">${String(index + 1).padStart(2, "0")}</span><span class="concept-copy"><strong>${escapeHtml(point.title)}</strong><small>${escapeHtml(point.description || point.summary)}</small></span><span class="concept-status concept-status-${status.toLowerCase().replaceAll("_", "-")}">${escapeHtml(status.replaceAll("_", " "))}</span><span class="concept-arrow" aria-hidden="true">→</span></button></li>`; }).join("")}</ol>
    <section class="concept-detail" aria-labelledby="conceptHeading"><p class="section-label">${ui.selected}</p><h4 id="conceptHeading">${escapeHtml(concept.title)}</h4><p>${escapeHtml(concept.description || concept.summary)}</p><p class="you-learn-label">${ui.learnLabel}</p><ul><li>${escapeHtml(concept.description || concept.summary)}</li><li>${language === "zh" ? "用于回答：" : "Use it to answer: "}${escapeHtml(concept.practice_prompt)}</li></ul>${concept.prerequisites?.length ? `<p class="prerequisite-note"><strong>${language === "zh" ? "先修：" : language === "sv" ? "Förkunskaper: " : "Prerequisites: "}</strong>${escapeHtml(concept.prerequisites.join(", "))}</p>` : ""}${concept.experiments?.length ? `<div class="experiment-list"><p class="you-learn-label">${ui.explore}</p><ul>${concept.experiments.map((experiment) => `<li><button type="button" class="link-button" data-open-experiment="${escapeHtml(experiment.experiment_id)}">${escapeHtml(experiment.title)}</button></li>`).join("")}</ul></div>` : ""}<div class="concept-actions"><button type="button" data-concept-action="learn">${ui.learn}</button><button type="button" data-concept-action="practice">${ui.practice}</button><button type="button" data-concept-action="hint">${ui.hint}</button>${concept.experiments?.length ? `<button type="button" class="primary-action" data-concept-action="simulation">${ui.simulation}</button>` : ""}<button type="button" data-concept-action="quiz">${ui.quiz}</button></div><p id="conceptActivity" class="concept-activity" role="status" aria-live="polite"></p></section>`;
  curriculumContent.querySelector("[data-course-root]")?.addEventListener("click", () => setRoute("course"));
  curriculumContent.querySelectorAll("[data-concept-id]").forEach((button) => button.addEventListener("click", () => selectConcept(module.module_id, button.dataset.conceptId)));
  curriculumContent.querySelectorAll("[data-open-experiment]").forEach((button) => button.addEventListener("click", () => setRoute(`simulations/${button.dataset.openExperiment}`)));
  curriculumContent.querySelectorAll("[data-concept-action]").forEach((button) => button.addEventListener("click", () => {
    const chosen = selectedConcept();
    const activity = curriculumContent.querySelector(".concept-activity");
    if (button.dataset.conceptAction === "learn") { pendingTutorAction = { action_type: "learn", concept_id: chosen.id }; input.value = localizedActionPrompt("learn", chosen); autoGrowInput(); input.focus(); activity.textContent = language === "zh" ? "已在导师输入框中准备好学习问题。" : language === "sv" ? "En fokuserad inlärningsfråga är klar i handledaren." : "A focused learning question is ready in the tutor."; setRoute("tutor"); }
    if (button.dataset.conceptAction === "practice") { openPractice(chosen.id); }
    if (button.dataset.conceptAction === "hint") { fetchJson("/api/hint", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ concept_id: chosen.id, session_id: sessionId, hint_level: 1, ui_language: language }) }).then((payload) => { sessionId = payload.session_id; window.localStorage.setItem("stochasticTutorSession", sessionId); activity.textContent = `${t("common.hint")}: ${payload.hint}`; }).catch((error) => { activity.textContent = `${t("common.hintUnavailable")}: ${error.message}`; }); }
    if (button.dataset.conceptAction === "simulation") { const experiment = (chosen.experiments || [])[0]; askAgent(localizedActionPrompt("simulation", chosen, experiment), { action_type: "simulation", concept_id: chosen.id, experiment_id: experiment?.experiment_id }); }
    if (button.dataset.conceptAction === "quiz") { pendingTutorAction = { action_type: "quiz", concept_id: chosen.id }; activity.textContent = localizedActionPrompt("quiz", chosen); openQuiz(chosen.id); }
  }));
}

function experimentById(experimentId) {
  return experimentRegistry.find((item) => item.experiment_id === experimentId) || null;
}

function experimentContext(experiment) {
  const module = curriculum?.modules.find((item) => item.module_id === experiment?.module_id);
  const concept = module?.knowledge_points.find((item) => item.id === experiment?.concept_id);
  return { module, concept };
}

function experimentParameterRows(experiment) {
  const params = experiment?.supported_parameters || [];
  return params.filter((item) => item?.name && item.name !== "seed").slice(0, 12);
}

function renderExperimentCatalogue() {
  if (!simulationCatalogueGrid) return;
  const query = (simulationSearch?.value || "").trim().toLowerCase();
  const moduleFilter = simulationFilter?.value || "all";
  const matches = experimentRegistry.filter((experiment) => {
    if (moduleFilter !== "all" && experiment.module_id !== moduleFilter) return false;
    const { module, concept } = experimentContext(experiment);
    const haystack = [experiment.title, experiment.teaching_purpose, experiment.simulation_engine, module?.label, concept?.title, experiment.source_notebook].join(" ").toLowerCase();
    return !query || haystack.includes(query);
  });
  if (simulationCount) simulationCount.textContent = `${matches.length} / ${experimentRegistry.length}`;
  simulationCatalogueGrid.innerHTML = matches.length ? matches.map((experiment) => {
    const { module, concept } = experimentContext(experiment);
    const params = experimentParameterRows(experiment);
    return `<article class="experiment-card"><div class="experiment-card-top"><span class="experiment-module">${escapeHtml(moduleDisplayLabel(experiment.module_id))}</span><span class="experiment-type">${escapeHtml(experiment.simulation_engine || "verified")}</span></div><h3>${escapeHtml(experiment.title)}</h3><p>${escapeHtml(cleanExperimentText(experiment.teaching_purpose || concept?.summary || ""))}</p><div class="experiment-card-meta"><span>${escapeHtml(concept?.title || "Course experiment")}</span>${params.length ? `<span>${params.length} ${language === "zh" ? "个参数" : language === "sv" ? "parametrar" : "parameters"}</span>` : ""}<span>${escapeHtml(experiment.visualization_id || "visualization")}</span></div><button type="button" class="ghost-button" data-open-experiment="${escapeHtml(experiment.experiment_id)}">${t("simulation.open")} <span aria-hidden="true">→</span></button></article>`;
  }).join("") : `<div class="catalogue-empty"><strong>${escapeHtml(t("simulation.noMatches"))}</strong></div>`;
  simulationCatalogueGrid.querySelectorAll("[data-open-experiment]").forEach((button) => button.addEventListener("click", () => setRoute(`simulations/${button.dataset.openExperiment}`)));
}

function showExperimentCatalogue() {
  simulationCatalogue?.classList.remove("hidden");
  simulationDetail?.classList.add("hidden");
  simulationView?.classList.add("hidden");
  dashboard?.classList.remove("simulation-mode");
  renderExperimentCatalogue();
}

function showExperimentDetail(experimentId, { navigate = true } = {}) {
  const experiment = experimentById(experimentId);
  if (!experiment || !simulationDetail) return showExperimentCatalogue();
  activeExperimentId = experimentId;
  const { module, concept } = experimentContext(experiment);
  const params = experimentParameterRows(experiment);
  if (navigate) setRoute(`simulations/${experimentId}`);
  simulationCatalogue?.classList.add("hidden");
  simulationView?.classList.add("hidden");
  simulationDetail.classList.remove("hidden");
  locationBreadcrumb.textContent = `${t("nav.simulation")} / ${module?.label || experiment.module_id} / ${experiment.title}`;
  const teachingPurpose = cleanExperimentText(experiment.teaching_purpose || "");
  const theoryConnection = cleanExperimentText(experiment.theory_connection || "");
  simulationDetail.innerHTML = `<div class="simulation-detail-header"><div><button type="button" class="breadcrumb-button" data-back-catalogue>${t("simulation.backCatalogue")}</button><p class="kicker">${escapeHtml(t("simulation.verified"))}</p><h2>${escapeHtml(experiment.title)}</h2><p class="simulation-subtitle">${escapeHtml(teachingPurpose)}</p></div><span class="experiment-type">${escapeHtml(experiment.simulation_engine || "verified")}</span></div><div class="detail-summary-grid"><div><span class="detail-label">${escapeHtml(t("simulation.goal"))}</span><strong>${escapeHtml(teachingPurpose || cleanExperimentText(concept?.summary || ""))}</strong></div><div><span class="detail-label">${escapeHtml(t("common.theoryConnection"))}</span><strong>${escapeHtml(theoryConnection)}</strong></div><div><span class="detail-label">${escapeHtml(language === "zh" ? "知识点" : language === "sv" ? "Kunskapspunkt" : "Knowledge point")}</span><strong>${escapeHtml(concept?.title || "")}</strong></div></div><section class="parameter-editor"><div class="panel-heading compact"><div><p class="kicker">${escapeHtml(t("simulation.parameters"))}</p><h3>${escapeHtml(experiment.simulation_engine || "Python tool")}</h3></div></div>${params.length ? `<div class="parameter-grid">${params.map((parameter) => `<label><span>${escapeHtml(parameter.name)}</span><input type="number" step="any" data-experiment-param="${escapeHtml(parameter.name)}" value="${escapeHtml(parameter.default ?? "")}" ${parameter.required ? "required" : ""} /></label>`).join("")}</div>` : `<p class="muted-copy">${escapeHtml(language === "zh" ? "此 notebook 目标没有可编辑的工具参数；运行将使用工具默认值。" : language === "sv" ? "Detta notebookmål har inga redigerbara verktygsparametrar; standardvärden används." : "This notebook target has no editable tool parameters; the tool defaults will be used.")}</p>`}<div class="detail-actions"><button type="button" class="primary-action" data-run-experiment>${t("simulation.run")} <span aria-hidden="true">→</span></button><button type="button" class="ghost-button" data-ask-experiment>${t("simulation.ask")}</button></div><p id="experimentDetailStatus" class="concept-activity" role="status" aria-live="polite"></p></section><div class="detail-provenance"><span>${escapeHtml(module?.label || experiment.module_id)}</span><span>${escapeHtml(experiment.source_notebook || "notebook")}</span><span>${escapeHtml(experiment.visualization_id || "visualization")}</span></div>`;
  simulationDetail.querySelector("[data-back-catalogue]")?.addEventListener("click", () => setRoute("simulations"));
  simulationDetail.querySelector("[data-run-experiment]")?.addEventListener("click", () => {
    const values = [...simulationDetail.querySelectorAll("[data-experiment-param]")].filter((field) => field.value !== "").map((field) => `${field.dataset.experimentParam} ${field.value}`).join(", ");
    const prompt = `Simulate ${experiment.title}${values ? ` with ${values}` : ""}.`;
    pendingTutorAction = { action_type: "simulation", concept_id: experiment.concept_id || undefined, experiment_id: experiment.experiment_id };
    askAgent(prompt, pendingTutorAction);
  });
  simulationDetail.querySelector("[data-ask-experiment]")?.addEventListener("click", () => {
    const prompt = language === "zh" ? `请解释实验“${experiment.title}”与课程理论的联系。` : language === "sv" ? `Förklara hur experimentet ${experiment.title} hänger ihop med kursens teori.` : `Explain how the experiment ${experiment.title} connects to the course theory.`;
    pendingTutorAction = { action_type: "learn", concept_id: experiment.concept_id || undefined, experiment_id: experiment.experiment_id };
    input.value = prompt; autoGrowInput(); setRoute("tutor"); input.focus();
  });
}

async function hydrateExperiments() {
  try {
    const payload = await fetchJson("/api/experiments", {}, 10_000);
    experimentRegistry = payload.experiments || [];
    if (simulationFilter) simulationFilter.innerHTML = `<option value="all">${escapeHtml(t("simulation.allModules"))}</option>${(curriculum?.modules || []).map((module) => `<option value="${escapeHtml(module.module_id)}">${escapeHtml(moduleDisplayLabel(module.module_id))}</option>`).join("")}`;
    renderExperimentCatalogue();
  } catch (_) {
    experimentRegistry = [];
    if (simulationCatalogueGrid) simulationCatalogueGrid.innerHTML = `<div class="catalogue-empty"><strong>${escapeHtml(t("simulation.noMatches"))}</strong></div>`;
  }
}

async function hydrateCurriculum() {
  try {
    curriculum = await fetchJson("/api/curriculum", {}, 10_000);
    if (curriculum.course_title) {
      if (courseTitle) courseTitle.textContent = curriculum.course_title;
      document.title = curriculum.course_title;
    }
    renderCurriculum();
    await hydrateExperiments();
    applyRoute({ focus: false });
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

function addSimulationCard(payload) {
  if (!conversation || !payload?.tool_called) return;
  const experiment = payload.experiment || {};
  const card = document.createElement("article");
  card.className = "message simulation-message-card";
  const cardId = `inline-simulation-${Date.now()}`;
  card.innerHTML = `<span class="message-label">${escapeHtml(t("simulation.verified"))}</span><div class="simulation-card-heading"><div><h3>${escapeHtml(experiment.title || payload.module_label || t("simulation.result"))}</h3><p>${renderTutorMarkdown(cleanExperimentText(experiment.teaching_purpose || t("simulation.verifiedOutput")))}</p></div><span class="experiment-type">${escapeHtml(experiment.simulation_engine || payload.tool || "verified")}</span></div><div id="${cardId}" class="inline-simulation-visual"></div><div class="inline-simulation-meta">${Object.entries(payload.parameters || {}).slice(0, 5).map(([key, value]) => `<span><strong>${escapeHtml(key)}</strong> ${escapeHtml(Array.isArray(value) ? JSON.stringify(value) : value)}</span>`).join("")}</div><p class="inline-simulation-summary">${renderTutorMarkdown(cleanExperimentText(payload.result_summary || experiment.expected_observation || "Verified output from the Python simulation tool."))}</p><div class="inline-simulation-actions"><button type="button" class="ghost-button" data-open-lab>${escapeHtml(t("simulation.open"))} →</button></div>`;
  conversation.append(card);
  const visual = card.querySelector(`#${cardId}`);
  if (!renderStructuredVisualizations(payload.result, visual)) renderChart(payload.result?.series, payload.result?.chart, visual);
  card.querySelector("[data-open-lab]")?.addEventListener("click", () => {
    const id = experiment.experiment_id || payload.experiment_id;
    if (id) setRoute(`simulations/${id}`);
    else showSimulationView(payload);
  });
  renderMath(card);
  conversation.scrollTop = conversation.scrollHeight;
}

function hideSimulationView() {
  tutorLab?.classList.remove("simulation-active");
  dashboard?.classList.remove("simulation-mode");
  document.querySelector("#simulationCatalogue")?.classList.remove("hidden");
  simulationDetail?.classList.add("hidden");
  simulationView?.classList.add("hidden");
}

function renderProgress(memory, note, recommendation) {
  masteryByConcept = Object.fromEntries((memory?.knowledge_points || []).map((item) => [item.concept_id, item]));
  if (curriculum) renderCurriculum();
  learningNote.textContent = note || t("progress.emptyNote");
  const moduleRows = memory?.modules?.length ? memory.modules.map((item) => `<div class="profile-item module-summary"><div><strong>${escapeHtml(moduleDisplayLabel(item.module_id))}</strong><span>${escapeHtml(item.quiz_correct || 0)}/${escapeHtml(item.quiz_attempts || 0)} ${language === "zh" ? "道测验正确" : language === "sv" ? "quizsvar" : "quiz answers"}</span></div><progress max="100" value="${Math.round(Number(item.mastery || 0) * 100)}" aria-label="${escapeHtml(moduleDisplayLabel(item.module_id))} aggregate mastery heuristic"></progress></div>`).join("") : "";
  const kpRows = memory?.knowledge_points?.length ? memory.knowledge_points.map((item) => { const point = curriculum?.modules.flatMap((module) => module.knowledge_points).find((candidate) => candidate.id === item.concept_id); const status = item.status || "NOT_STARTED"; const last = item.last_practiced_at ? new Date(item.last_practiced_at).toLocaleDateString() : "—"; const marker = item.recent_misconceptions?.length ? (language === "zh" ? " · 需要复习" : language === "sv" ? " · behöver repetition" : " · needs review") : ""; return `<div class="profile-item kp-profile-item"><div><strong>${escapeHtml(point?.title || item.concept_id)}</strong><span>${escapeHtml(status.replaceAll("_", " "))}${marker} · ${escapeHtml(item.correct_count || 0)}/${escapeHtml(item.attempt_count || 0)} ${language === "zh" ? "正确" : language === "sv" ? "rätt" : "correct"} · ${escapeHtml(item.hint_count || 0)} ${language === "zh" ? "次提示" : language === "sv" ? "ledtrådar" : "hints"} · ${escapeHtml(last)}</span></div><progress max="100" value="${Math.round(Number(item.mastery_score || 0) * 100)}" aria-label="${escapeHtml(point?.title || item.concept_id)} mastery heuristic"></progress></div>`; }).join("") : `<p>${escapeHtml(t("progress.noRecord"))}</p>`;
  learnerProfile.innerHTML = moduleRows + kpRows;
  misconceptions.innerHTML = memory?.misconceptions?.length ? `<p class="diagnosis-title">${language === "zh" ? "需要复习" : "Things to review"}</p>${memory.misconceptions.map((item) => `<p><strong>${escapeHtml(item.code)}</strong><br />${escapeHtml(item.correction)}</p>`).join("")}` : "";
  nextRecommendation.innerHTML = recommendation ? `<span>${language === "zh" ? "下一步" : language === "sv" ? "NÄSTA STEG" : "NEXT STEP"}</span><strong>${escapeHtml(recommendation.action_label || recommendation.decision_type || "LEARN")} · ${escapeHtml(recommendation.concept_title || recommendation.target_concept || moduleDisplayLabel(recommendation.module_id))}</strong><p>${escapeHtml(recommendation.decision_reason || recommendation.reason || "")}</p><small>${escapeHtml(recommendation.suggested_question || "")}</small>` : "";
  renderOverview(memory, recommendation);
}

function renderOverview(memory, recommendation) {
  if (!recommendation) return;
  const title = recommendation.concept_title || recommendation.target_concept || moduleDisplayLabel(recommendation.module_id);
  if (overviewNextTitle) overviewNextTitle.textContent = `${recommendation.action_label || recommendation.decision_type || "LEARN"} · ${title}`;
  if (overviewNextText) overviewNextText.textContent = recommendation.decision_reason || recommendation.reason || recommendation.suggested_question || "";
  if (overviewActivity && memory) overviewActivity.textContent = memory.knowledge_points?.length ? (language === "zh" ? "掌握度只根据已提交的练习和测验证据更新。" : language === "sv" ? "Behärskning uppdateras endast från inskickade övnings- och quizsvar." : "Mastery is updated only from submitted practice and quiz evidence.") : t("overview.activity");
  if (overviewRecent && memory?.knowledge_points?.length) overviewRecent.textContent = recommendation.suggested_question || recommendation.reason || "";
  if (overviewContinue) overviewContinue.onclick = () => {
    if (recommendation.module_id && recommendation.concept_id) setRoute(`course/${recommendation.module_id}/${recommendation.concept_id}`);
    else setRoute(`course/${recommendation.module_id || "module00"}`);
  };
}

function renderResponse(payload) {
  latestPayload = payload;
  const isSimulation = payload.intent === "simulation" || payload.tool_called;
  if (isSimulation) latestSimulationPayload = payload;
  // A short follow-up such as “What changed?” is still attached to the last
  // experiment. Keep its verified chart visible while the new explanation is
  // shown in chat, but do not carry stale simulation evidence into an
  // unrelated concept question.
  const displaySimulation = isSimulation || Boolean(payload.active_experiment_id && latestSimulationPayload);
  const simulationPayload = isSimulation ? payload : latestSimulationPayload;
  evidenceContent.classList.remove("hidden");
  emptyEvidence.classList.add("hidden");
  verificationBadge.textContent = displaySimulation ? (simulationPayload?.verified ? "VERIFIED" : "CHECK RESULT") : "CONCEPT";
  simulationSection.classList.toggle("hidden", !displaySimulation);
  if (displaySimulation && simulationPayload) {
    runMeta.textContent = simulationPayload.module_label || simulationPayload.module_id || "Simulation";
    if (!renderStructuredVisualizations(simulationPayload.result, chart)) renderChart(simulationPayload.result?.series, simulationPayload.result?.chart);
    parameters.innerHTML = Object.entries(simulationPayload.parameters || {}).map(([key, value]) => `<div class="metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(Array.isArray(value) ? JSON.stringify(value) : value)}</strong></div>`).join("");
    // The result is also rendered as an inline Tutor artifact below. Keep the
    // dedicated Lab route available through that card instead of taking the
    // learner away from the conversation automatically.
    hideSimulationView();
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

async function askAgent(question, action = {}) {
  const cleanQuestion = String(question || "").trim();
  if (mutationInFlight || !cleanQuestion) return;
  const fromSimulationLab = activeViewId === "simulationLabView" && action.action_type === "simulation";
  setComposerLoading(true);
  addMessage("user", cleanQuestion);
  try {
    const payload = await fetchJson("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: cleanQuestion, session_id: sessionId, ui_language: language, ...pendingTutorAction, ...action }) });
    pendingTutorAction = {};
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
    addMessage("agent", payload.answer); renderResponse(payload); if (payload.tool_called) addSimulationCard(payload); renderOverview(payload.memory, payload.recommendation);
    if (fromSimulationLab && payload.tool_called) showSimulationView(payload);
    else showView("tutorView");
  } catch (error) { addMessage("agent", language === "zh" ? `这次请求未能完成：${error.message}` : `I could not complete that request: ${error.message}`); }
  finally { setComposerLoading(false); input.focus(); autoGrowInput(); }
}

async function openQuiz(conceptId = null) {
  if (mutationInFlight) return;
  try {
    // The course has one compact quiz per module; a knowledge-point action
    // keeps its concept context for navigation but uses the module bank.
    const payload = await fetchJson(`/api/quiz?module_id=${encodeURIComponent(activeModuleId)}`);
    const quiz = payload.quiz;
    quizPanel.classList.remove("hidden");
    quizPanel.setAttribute("aria-label", assessmentText("check"));
    quizPanel.dataset.actionType = "quiz";
    quizPanel.dataset.questionId = quiz.id;
    if (conceptId) quizPanel.dataset.conceptId = conceptId;
    quizPanel.innerHTML = `<p class="quiz-module">${escapeHtml(moduleDisplayLabel(quiz.module_id))} · ${escapeHtml(assessmentText("check"))}</p><h3 id="quizQuestion">${escapeHtml(quiz.question)}</h3><div class="quiz-choices" role="group" aria-labelledby="quizQuestion">${quiz.choices.map((choice, index) => `<button type="button" data-answer="${index}">${String.fromCharCode(65 + index)}. ${escapeHtml(choice)}</button>`).join("")}</div><p class="quiz-feedback" role="status" aria-live="polite"></p><div class="assessment-next-actions"></div>`;
    quizPanel.querySelectorAll("[data-answer]").forEach((button) => button.addEventListener("click", () => submitQuiz(quiz.id, Number(button.dataset.answer))));
    setRoute("tutor");
  } catch (error) { quizPanel.classList.remove("hidden"); quizPanel.textContent = language === "zh" ? `测验加载失败：${error.message}` : `The quiz could not be loaded: ${error.message}`; }
}

async function openPractice(conceptId) {
  if (mutationInFlight || !practicePanel) return;
  try {
    const payload = await fetchJson(`/api/practice?concept_id=${encodeURIComponent(conceptId)}`);
    const practice = payload.practice;
    practicePanel.classList.remove("hidden");
    practicePanel.setAttribute("aria-label", assessmentText("practiceLabel"));
    practicePanel.dataset.conceptId = conceptId;
    practicePanel.dataset.questionId = practice.id;
    practicePanel.dataset.attemptNumber = "1";
    practicePanel.dataset.hintLevel = "0";
    practicePanel.dataset.referenceShown = "false";
    practicePanel.classList.remove("practice-correct", "practice-incorrect", "practice-incomplete");
    practicePanel.innerHTML = `<p class="quiz-module">${escapeHtml(conceptTitleForId(conceptId))} · ${escapeHtml(assessmentText("practiceLabel"))}</p><h3>${escapeHtml(practice.question)}</h3><textarea class="practice-answer" rows="4" maxlength="2000" placeholder="${language === "zh" ? "写下你的答案…" : language === "sv" ? "Skriv ditt svar…" : "Write your answer…"}"></textarea><div class="practice-actions"><button type="button" class="ghost-button" data-practice-hint>① ${escapeHtml(t("common.hint"))}</button><button type="button" class="primary-action" data-practice-submit>${escapeHtml(assessmentText("submit"))}</button></div><p class="practice-hint" role="status" aria-live="polite"></p><p class="practice-feedback quiz-feedback" role="status" aria-live="polite"></p><div class="assessment-next-actions"></div>`;
    practicePanel.querySelector("[data-practice-hint]")?.addEventListener("click", () => requestPracticeHint(practicePanel));
    practicePanel.querySelector("[data-practice-submit]")?.addEventListener("click", () => submitPractice(practicePanel));
    setRoute("tutor");
  } catch (error) { practicePanel.classList.remove("hidden"); practicePanel.textContent = `${language === "zh" ? "练习加载失败" : language === "sv" ? "Övningen kunde inte laddas" : "Practice could not be loaded"}: ${error.message}`; }
}

async function requestPracticeHint(panel) {
  const hintButton = panel.querySelector("[data-practice-hint]");
  if (!hintButton || hintButton.disabled) return;
  const nextLevel = Math.min(3, Number(panel.dataset.hintLevel || 0) + 1);
  try {
    const payload = await fetchJson("/api/hint", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ concept_id: panel.dataset.conceptId, question_id: panel.dataset.questionId, hint_level: nextLevel, session_id: sessionId, ui_language: language }) });
    panel.dataset.hintLevel = String(payload.hint_level);
    panel.querySelector(".practice-hint").textContent = `${t("common.hint")} ${payload.hint_level}: ${payload.hint}`;
    if (payload.hint_level >= 3) {
      hintButton.disabled = true;
      hintButton.textContent = assessmentText("allHints");
    } else {
      hintButton.textContent = `${payload.hint_level + 1} ${t("common.hint")}`;
    }
  } catch (error) { panel.querySelector(".practice-hint").textContent = `${t("common.hintUnavailable")}: ${error.message}`; }
}

function renderPracticeState(panel, state, result = {}, payload = {}) {
  const feedback = panel.querySelector(".practice-feedback");
  const textarea = panel.querySelector(".practice-answer");
  const submit = panel.querySelector("[data-practice-submit]");
  const actions = panel.querySelector(".assessment-next-actions");
  const icon = state === "correct" ? "✓" : state === "incorrect" ? "✕" : "!";
  const label = state === "correct" ? assessmentText("correct") : state === "incorrect" ? assessmentText("incorrect") : assessmentText("incomplete");
  const explanation = state === "incomplete" ? (result.explanation || assessmentText("needsMore")) : (result.explanation || "");
  panel.classList.remove("practice-correct", "practice-incorrect", "practice-incomplete");
  panel.classList.add(`practice-${state}`);
  feedback.className = `practice-feedback quiz-feedback ${state}`;
  feedback.innerHTML = `<span class="assessment-state-icon" aria-hidden="true">${icon}</span> <strong>${escapeHtml(label)}</strong> ${escapeHtml(explanation)}`;
  if (state === "correct") {
    textarea.disabled = true;
    submit.disabled = true;
    actions.innerHTML = `<button type="button" class="primary-action" data-practice-continue>${escapeHtml(assessmentText("continue"))}</button>`;
    actions.querySelector("[data-practice-continue]")?.addEventListener("click", () => {
      const recommendation = payload.recommendation;
      if (recommendation?.module_id && recommendation?.concept_id) setRoute(`course/${recommendation.module_id}/${recommendation.concept_id}`);
      else setRoute("course");
    });
    return;
  }
  textarea.disabled = false;
  submit.disabled = false;
  actions.innerHTML = `<button type="button" class="ghost-button" data-practice-retry>${escapeHtml(assessmentText("retry"))}</button><button type="button" class="ghost-button" data-practice-reference>${escapeHtml(assessmentText("showReference"))}</button>`;
  actions.querySelector("[data-practice-retry]")?.addEventListener("click", () => { textarea.value = ""; textarea.focus(); feedback.textContent = ""; });
  actions.querySelector("[data-practice-reference]")?.addEventListener("click", () => {
    panel.dataset.referenceShown = "true";
    const reference = payload.reference_answer || result.reference_answer || result.expected_answer;
    // Keep the action container in the DOM so a later retry can render a new
    // state without losing its controls.
    actions.innerHTML = `<div class="practice-reference"><strong>${escapeHtml(assessmentText("reference"))}</strong><p>${escapeHtml(reference || assessmentText("needsMore"))}</p></div>`;
  });
}

async function submitPractice(panel) {
  const answer = panel.querySelector(".practice-answer")?.value.trim();
  if (!answer) {
    renderPracticeState(panel, "incomplete", { explanation: assessmentText("empty") });
    panel.querySelector(".practice-answer")?.focus();
    return;
  }
  const button = panel.querySelector("[data-practice-submit]"); button.disabled = true;
  try {
    const payload = await fetchJson("/api/practice", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ concept_id: panel.dataset.conceptId, question_id: panel.dataset.questionId, student_answer: answer, hint_level: Number(panel.dataset.hintLevel || 0), attempt_number: Number(panel.dataset.attemptNumber || 1), session_id: sessionId, ui_language: language, reference_shown: panel.dataset.referenceShown === "true" }) });
    sessionId = payload.session_id; window.localStorage.setItem("stochasticTutorSession", sessionId);
    const result = payload.result || {};
    panel.dataset.attemptNumber = String(Number(panel.dataset.attemptNumber || 1) + 1);
    const state = result.correct === true ? "correct" : result.correct === false ? "incorrect" : "incomplete";
    renderPracticeState(panel, state, result, payload);
    renderProgress(payload.memory, payload.learning_note, payload.recommendation); renderOverview(payload.memory, payload.recommendation);
  } catch (error) { panel.querySelector(".quiz-feedback").textContent = `${language === "zh" ? "答案保存失败" : language === "sv" ? "Svaret kunde inte sparas" : "The answer could not be saved"}: ${error.message}`; button.disabled = false; }
}

async function submitQuiz(questionId, answerIndex) {
  const buttons = quizPanel.querySelectorAll("[data-answer]"); buttons.forEach((button) => { button.disabled = true; });
  try {
    const payload = await fetchJson("/api/quiz/submit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question_id: questionId, answer_index: answerIndex, session_id: sessionId, ui_language: language }) });
    sessionId = payload.session_id; window.localStorage.setItem("stochasticTutorSession", sessionId);
    const result = payload.result;
    const selected = buttons[answerIndex];
    buttons.forEach((button) => button.classList.remove("correct-answer", "incorrect-answer"));
    if (result.correct) selected.classList.add("correct-answer");
    else {
      selected.classList.add("incorrect-answer");
      if (buttons[result.correct_index]) buttons[result.correct_index].classList.add("correct-answer");
    }
    const feedback = quizPanel.querySelector(".quiz-feedback");
    feedback.className = `quiz-feedback ${result.correct ? "correct" : "incorrect"}`;
    feedback.innerHTML = `<span class="assessment-state-icon" aria-hidden="true">${result.correct ? "✓" : "✕"}</span> <strong>${escapeHtml(result.correct ? assessmentText("correct") : assessmentText("incorrect"))}</strong> ${escapeHtml(result.explanation || "")}`;
    const next = quizPanel.querySelector(".assessment-next-actions");
    next.innerHTML = `<button type="button" class="${result.correct ? "primary-action" : "ghost-button"}" data-quiz-next>${escapeHtml(result.correct ? assessmentText("continue") : assessmentText("quizRetry"))}</button>`;
    next.querySelector("[data-quiz-next]")?.addEventListener("click", () => result.correct ? setRoute(`course/${payload.recommendation?.module_id || activeModuleId}`) : openQuiz(quizPanel.dataset.conceptId || null));
    renderProgress(payload.memory, language === "zh" ? "测验结果已保存。" : language === "sv" ? "Quizresultatet har sparats." : "Your quiz result has been saved.", payload.recommendation);
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
quizButton.addEventListener("click", () => openQuiz());
resetButton.addEventListener("click", () => { sessionId = null; latestSimulationPayload = null; window.localStorage.removeItem("stochasticTutorSession"); hideSimulationView(); conversation.innerHTML = `<article class="message agent-message"><span class="message-label">${t("common.tutor")}</span><div class="message-body"><p>${escapeHtml(t("tutor.empty"))}</p></div></article>`; quizPanel.classList.add("hidden"); input.value = ""; autoGrowInput(); input.focus(); composerStatus.textContent = t("tutor.composer"); });
closeSimulationView?.addEventListener("click", () => { hideSimulationView(); showView("tutorView", { focus: true }); });
function routeForView(view) {
  return view === "courseView" ? "course" : view === "tutorView" ? "tutor" : view === "simulationLabView" ? "simulations" : view === "progressView" ? "progress" : "overview";
}
navItems.forEach((button) => button.addEventListener("click", () => setRoute(routeForView(button.dataset.view))));
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => setRoute(routeForView(button.dataset.view))));
simulationSearch?.addEventListener("input", renderExperimentCatalogue);
simulationFilter?.addEventListener("change", renderExperimentCatalogue);
window.addEventListener("hashchange", () => applyRoute({ focus: false }));
window.addEventListener("popstate", () => applyRoute({ focus: false }));
languageSelect?.addEventListener("change", () => {
  language = ["en", "zh", "sv"].includes(languageSelect.value) ? languageSelect.value : "en";
  window.localStorage.setItem("stochlabLanguage", language);
  applyTranslations();
  hydrateHealth();
  if (curriculum) renderCurriculum();
  if (experimentRegistry.length) renderExperimentCatalogue();
});

autoGrowInput();
hydrateHealth();
hydrateCurriculum();
hydrateAuth();
applyRoute({ focus: false });
applyTranslations();
