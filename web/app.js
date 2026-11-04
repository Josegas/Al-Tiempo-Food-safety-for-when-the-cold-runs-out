"use strict";
// Al Tiempo web client: plain JS, no build step. Talks to /api/* on the same domain (CloudFront).
// Agent text is never inserted as HTML: everything goes through textContent / DOM nodes.
// The browser never calculates or extracts food-safety times: it only shows what the backend sent.

const SCENARIOS = [
  // [icon, tone, es title, es description, es prompt, en title, en description, en prompt]
  ["window", "primary",
    "Ventana segura", "Cocinaste y no tienes refri: te decimos hasta qué hora se puede comer.",
    "Cociné frijoles a las 12:00 y no tengo refri. ¿Hasta qué hora se pueden comer?",
    "Safe window", "You cooked and have no fridge: find out until what time it can be eaten.",
    "I cooked beans at 12:00 and I have no fridge. Until what time can we eat them?"],
  ["baby", "",
    "Bebé + arroz", "Reglas más estrictas para bebés y niños pequeños.",
    "¿Le doy a mi bebé el arroz que cociné hace 5 horas? Estuvo fuera del refri.",
    "Baby + rice", "Stricter rules for babies and young children.",
    "Can I give my baby the rice I cooked 5 hours ago? It was out of the fridge."],
  ["outage", "",
    "Apagón", "Se fue la luz: cuánto aguantan el refri y el congelador.",
    "Se fue la luz a las 06:00, no he abierto el refri y el congelador está lleno. ¿Qué hago?",
    "Power outage", "The power went out: how long the fridge and freezer keep food.",
    "The power went out at 06:00. I haven't opened the fridge and the freezer is full. What do I do?"],
  ["shelter", "",
    "Albergue (120 personas)", "Tandas de cocina para que nada se sirva fuera de tiempo.",
    "Coordino un albergue con 120 personas. La comida es de 13:00 a 15:00, arroz y frijoles, sin forma de mantenerla caliente.",
    "Shelter (120 people)", "Cooking batches so nothing is served past its time.",
    "I run a shelter with 120 people. Lunch is 13:00 to 15:00, rice and beans, no way to keep food hot."],
  ["plan", "",
    "Planear comidas", "A qué hora cocinar según tus horarios de comida.",
    "Somos 5 en casa, comemos a las 14:00 y cenamos a las 20:00. ¿A qué hora cocino?",
    "Plan meals", "When to cook, based on when you eat.",
    "We are 5 at home, lunch at 14:00 and dinner at 20:00. When should I cook?"],
  ["bell", "",
    "Recordatorio", "Un aviso antes de que se acabe el tiempo.",
    "Cociné pollo a las 12:00. Prográmame un recordatorio para comerlo a tiempo.",
    "Reminder", "A heads-up before the time runs out.",
    "I cooked chicken at 12:00. Schedule a reminder so we eat it in time."],
  ["danger", "danger",
    "Señales de alarma", "Diarrea o vómito: cuándo ir a la clínica. Sin diagnósticos ni dosis.",
    "Mi hija de 2 años tiene diarrea, está muy dormida y casi no quiere beber. Estamos en México.",
    "Danger signs", "Diarrhea or vomiting: when to go to a clinic. No diagnosis, no doses.",
    "My 2-year-old daughter has diarrhea, she is very sleepy and barely drinks. We are in Mexico."],
];

const I18N = {
  es: {
    skip: "Ir a escribir tu pregunta",
    brandSub: "Inocuidad cuando falta el frío",
    langGroup: "Idioma", modeGroup: "Modo",
    modeDemo: "Simulado", modeLive: "Real",
    demoLabel: "Modo simulado",
    demoPills: ["Día de 38 °C", "Reloj fijo 12:00", "Recordatorios en ~1 min"],
    demoNote: "Resultados iguales para todos. No son tus condiciones reales.",
    liveLabel: "Modo real",
    livePills: ["Tu hora real"],
    geo: {
      idle: "Ubicación: no solicitada",
      asking: "Pidiendo tu ubicación…",
      granted: "Ubicación compartida (~1 km)",
      denied: "Sin ubicación: se usa el límite más estricto (1 h)",
      unsupported: "Sin ubicación: se usa el límite más estricto (1 h)",
    },
    liveNote: "Con tu permiso usamos tu ubicación redondeada (~1 km) para el pronóstico de calor. Datos del clima: Open-Meteo.com.",
    heroTitle: "Comida segura, incluso cuando no hay refrigerador.",
    heroText: "Dinos qué cocinaste y a qué hora. Al Tiempo aplica reglas oficiales de inocuidad y el calor del día, y te da una hora clara: cómelo antes de… o deséchalo.",
    scenTitle: "Elige una situación",
    howTitle: "Cómo decide Al Tiempo",
    steps: [
      ["Tú describes la situación", "Con tus palabras: qué cocinaste, a qué hora y para quién."],
      ["El motor aplica reglas oficiales", "Código probado con reglas de la OMS, la FDA, los CDC y el NHS calcula la hora límite. La IA no calcula."],
      ["El verificador revisa la respuesta", "Si la respuesta trae una hora que el motor no dio, se bloquea y se usa una respuesta segura."],
      ["El agente te lo explica", "En español o inglés, y también en voz."],
    ],
    panelTitle: "Conversación",
    badgeDemo: "Simulado: 38 °C, 12:00", badgeLive: "Tu hora real",
    welcomeTitle: "Cuéntame qué cocinaste y a qué hora.",
    welcomeText: "Por ejemplo: «Cociné frijoles a las 12:00 y no tengo refri». También puedes elegir una situación.",
    placeholder: "¿Qué cocinaste y a qué hora?",
    send: "Enviar",
    thinking: "Revisando las reglas oficiales…",
    listen: "Escuchar", listening: "Reproduciendo…", voiceFail: "No se pudo reproducir el audio",
    tools: {
      compute_safe_window: "Ventana segura", track_outage: "Apagón", plan_meals: "Plan de comidas",
      plan_shelter_batches: "Tandas del albergue", schedule_reminder: "Recordatorio",
      check_danger_signs: "Señales de alarma", get_forecast: "Pronóstico",
    },
    tl: {
      title: "La ventana segura", cooked: "Cocinado", now: "Ahora", remind: "Aviso", limit: "Límite",
      left: (m) => `Quedan ${fmtLeft(m, "es")} para comerlo.`, expired: "Ya pasó el límite: deséchalo.",
      by: (src) => src ? `Decide: ${src}` : "Decide: nuestra regla más estricta para bebés y niños",
      why: (d, t) => ({
        FDA_HOT_1H: t == null
          ? "Por qué 1 hora: no tenemos el pronóstico del clima, así que suponemos calor (más de 32 °C), el caso más seguro."
          : `Por qué 1 hora: el pronóstico llega a ${t} °C. Con más de 32 °C, la FDA baja el límite de 2 horas a 1: con calor, las bacterias se multiplican más rápido.`,
        FDA_2H: t == null ? null : `Por qué 2 horas: el pronóstico no pasa de 32 °C (máximo ${t} °C). A temperatura ambiente, la OMS y la FDA dicen máximo 2 horas.`,
        WHO_COOKED_2H: t == null ? null : `Por qué 2 horas: el pronóstico no pasa de 32 °C (máximo ${t} °C). A temperatura ambiente, la OMS y la FDA dicen máximo 2 horas.`,
        NHS_RICE_1H: "Por qué 1 hora: el NHS pide refrigerar el arroz cocido dentro de 1 hora. Sin refri, usamos esa hora como límite para comerlo.",
        POLICY_CHILD_STRICT: "Por qué 1 hora: para bebés y niños pequeños usamos una regla más estricta que la oficial. Los menores de 5 años cargan el 29% del daño por comida contaminada (OMS).",
        CDC_FORMULA_2H: "Por qué 2 horas: los CDC piden usar la fórmula preparada dentro de 2 horas.",
        CDC_FORMULA_FEED_1H: "Por qué 1 hora: los CDC piden usar la fórmula dentro de 1 hora desde que el bebé empieza a tomar, y tirar lo que sobre.",
      })[d.rule_id] || null,
      aria: (d) => `Línea de tiempo. ${d.cooked_known ? `Cocinado a las ${d.cooked_at_hhmm}. Límite: ${d.eat_by_hhmm}. ` : ""}Ahora son las ${d.now_hhmm}.`,
    },
    sh: {
      title: "Plan de tandas", batch: (i, n) => `Tanda ${i} · ${n} porciones`,
      cook: "Cocinar", serve: "Servir", discard: "Desechar",
      hot: (c) => `Mantener arriba de ${c} °C todo el servicio.`,
      by: (src) => src ? `Decide: ${src}` : "Decide: nuestra regla más estricta para bebés y niños",
      print: "Imprimir plan", people: (n) => `${n} personas`,
      aria: (d) => `Plan de tandas para ${d.people} personas. ` + d.batches.map((b, i) => `Tanda ${i + 1}: cocinar a las ${b.start_cooking_hhmm}, servir desde las ${b.ready_hhmm}, desechar a las ${b.discard_hhmm}.`).join(" "),
    },
    offline: {
      banner: "Sin conexión. Las respuestas necesitan internet; mientras tanto, usa la regla básica.",
      title: "Sin conexión: regla básica",
      rules: [
        "Con calor (más de 32 °C), no dejes comida cocida fuera más de 1 hora. Sin calor, máximo 2 horas.",
        "Arroz cocido: máximo 1 hora fuera.",
        "Bebés y niños pequeños: prepárales al momento y no guardes sobras.",
        "Diarrea con mucho sueño, sin poder beber, ojos hundidos o sangre: ve a la clínica o llama a emergencias.",
      ],
      doubt: "Si tienes duda, tírala.",
      src: "Fuentes: U.S. FDA, OMS y NHS. La regla para niños es más estricta a propósito.",
    },
    rulesUsed: "Reglas aplicadas",
    verified: "Revisada por el verificador",
    replaced: "El verificador la cambió por la respuesta segura",
    reminder: "Recordatorio",
    reminderAt: "para las",
    errorTitle: "No llegó la respuesta",
    error: "No pude responder. Si tienes duda, tira la comida.",
    retry: "Intentar de nuevo",
    disclaimer: "Al Tiempo da orientación general de inocuidad basada en fuentes oficiales (OMS, FDA, CDC, NHS). No es consejo médico. En una emergencia, llama a tu número local de emergencias.",
    linkCode: "Código en GitHub",
    sources: "Fuentes y métricas",
  },
  en: {
    skip: "Skip to typing your question",
    brandSub: "Food safety when the cold runs out",
    langGroup: "Language", modeGroup: "Mode",
    modeDemo: "Simulated", modeLive: "Live",
    demoLabel: "Simulated mode",
    demoPills: ["38 °C day", "Clock fixed at 12:00", "Reminders in ~1 min"],
    demoNote: "Same results for everyone. These are not your real conditions.",
    liveLabel: "Live mode",
    livePills: ["Your real time"],
    geo: {
      idle: "Location: not requested",
      asking: "Asking for your location…",
      granted: "Location shared (~1 km)",
      denied: "No location: the strictest limit (1 h) is used",
      unsupported: "No location: the strictest limit (1 h) is used",
    },
    liveNote: "With your permission we use your rounded location (~1 km) for the heat forecast. Weather data by Open-Meteo.com.",
    heroTitle: "Food safety, even when the cold runs out.",
    heroText: "Tell it what you cooked and when. Al Tiempo applies official food-safety rules and today's heat, and gives you a clear time: eat it before… or throw it away.",
    scenTitle: "Pick a situation",
    howTitle: "How Al Tiempo decides",
    steps: [
      ["You describe the situation", "In your own words: what you cooked, when, and for whom."],
      ["The engine applies official rules", "Tested code with WHO, FDA, CDC and NHS rules works out the deadline. The AI does not calculate."],
      ["The verifier checks the answer", "If the answer has a time the engine didn't produce, it is blocked and a safe answer is used."],
      ["The agent explains it to you", "In English or Spanish, and out loud too."],
    ],
    panelTitle: "Conversation",
    badgeDemo: "Simulated: 38 °C, 12:00", badgeLive: "Your real time",
    welcomeTitle: "Tell me what you cooked and when.",
    welcomeText: "For example: “I cooked beans at 12:00 and I have no fridge.” Or pick a situation.",
    placeholder: "What did you cook, and when?",
    send: "Send",
    thinking: "Checking the official rules…",
    listen: "Listen", listening: "Playing…", voiceFail: "Audio could not be played",
    tools: {
      compute_safe_window: "Safe window", track_outage: "Power outage", plan_meals: "Meal plan",
      plan_shelter_batches: "Shelter batches", schedule_reminder: "Reminder",
      check_danger_signs: "Danger signs", get_forecast: "Forecast",
    },
    tl: {
      title: "The safe window", cooked: "Cooked", now: "Now", remind: "Reminder", limit: "Limit",
      left: (m) => `${fmtLeft(m, "en")} left to eat it.`, expired: "The limit has passed: throw it away.",
      by: (src) => src ? `Decided by: ${src}` : "Decided by: our stricter rule for babies and young children",
      why: (d, t) => ({
        FDA_HOT_1H: t == null
          ? "Why 1 hour: we have no weather forecast, so we assume heat (over 32 °C), the safest case."
          : `Why 1 hour: the forecast reaches ${t} °C. Above 32 °C, the FDA cuts the limit from 2 hours to 1: in the heat, bacteria multiply faster.`,
        FDA_2H: t == null ? null : `Why 2 hours: the forecast stays at or below 32 °C (max ${t} °C). At room temperature, WHO and the FDA say 2 hours at most.`,
        WHO_COOKED_2H: t == null ? null : `Why 2 hours: the forecast stays at or below 32 °C (max ${t} °C). At room temperature, WHO and the FDA say 2 hours at most.`,
        NHS_RICE_1H: "Why 1 hour: the NHS says to refrigerate cooked rice within 1 hour. Without a fridge, we use that hour as the limit to eat it.",
        POLICY_CHILD_STRICT: "Why 1 hour: for babies and young children we use a rule stricter than the official one. Children under 5 carry 29% of the harm from unsafe food (WHO).",
        CDC_FORMULA_2H: "Why 2 hours: the CDC says to use prepared formula within 2 hours.",
        CDC_FORMULA_FEED_1H: "Why 1 hour: the CDC says to use formula within 1 hour of when feeding begins, and throw out what is left.",
      })[d.rule_id] || null,
      aria: (d) => `Timeline. ${d.cooked_known ? `Cooked at ${d.cooked_at_hhmm}. Limit: ${d.eat_by_hhmm}. ` : ""}Now it is ${d.now_hhmm}.`,
    },
    sh: {
      title: "Batch plan", batch: (i, n) => `Batch ${i} · ${n} portions`,
      cook: "Cook", serve: "Serve", discard: "Discard",
      hot: (c) => `Keep above ${c} °C for the whole service.`,
      by: (src) => src ? `Decided by: ${src}` : "Decided by: our stricter rule for babies and young children",
      print: "Print plan", people: (n) => `${n} people`,
      aria: (d) => `Batch plan for ${d.people} people. ` + d.batches.map((b, i) => `Batch ${i + 1}: cook at ${b.start_cooking_hhmm}, serve from ${b.ready_hhmm}, discard at ${b.discard_hhmm}.`).join(" "),
    },
    offline: {
      banner: "You are offline. Answers need internet; meanwhile, use the basic rule.",
      title: "Offline: the basic rule",
      rules: [
        "On a hot day (over 32 °C / 90 °F), don't keep cooked food out more than 1 hour. Otherwise, 2 hours at most.",
        "Cooked rice: 1 hour out at most.",
        "Babies and young children: prepare food fresh and keep no leftovers.",
        "Diarrhea with heavy sleepiness, not drinking, sunken eyes or blood: go to a clinic or call emergency services.",
      ],
      doubt: "If in doubt, throw it out.",
      src: "Sources: U.S. FDA, WHO and NHS. The rule for children is stricter on purpose.",
    },
    rulesUsed: "Rules applied",
    verified: "Checked by the verifier",
    replaced: "The verifier replaced it with the safe answer",
    reminder: "Reminder",
    reminderAt: "for",
    errorTitle: "The answer didn't arrive",
    error: "I could not answer. If in doubt, throw the food away.",
    retry: "Try again",
    disclaimer: "Al Tiempo gives general food-safety guidance from official sources (WHO, FDA, CDC, NHS). It is not medical advice. In an emergency, call your local emergency number.",
    linkCode: "Code on GitHub",
    sources: "Sources and metrics",
  },
};

const RULE_TOOLS = new Set(["compute_safe_window", "track_outage", "plan_meals", "plan_shelter_batches",
  "schedule_reminder", "check_danger_signs"]);

const state = {
  lang: (navigator.language || "es").toLowerCase().startsWith("es") ? "es" : "en",
  mode: "demo",
  sessionId: newSessionId(),
  coords: null,
  geo: "idle",
  seenReminders: new Set(),
  busy: false,
  warm: null,
  lastPrompt: "",
};

function newSessionId() {
  const rnd = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now());
  return `web-${rnd}-${Date.now()}`; // >= 33 chars (AgentCore requirement)
}

const $ = (sel) => document.querySelector(sel);
const t = (key) => I18N[state.lang][key];
const SVGNS = "http://www.w3.org/2000/svg";

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function icon(name, cls = "ic") {
  const svg = document.createElementNS(SVGNS, "svg");
  svg.setAttribute("class", cls);
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const use = document.createElementNS(SVGNS, "use");
  use.setAttribute("href", `#i-${name}`);
  svg.appendChild(use);
  return svg;
}

// ---------------------------------------------------------------- rendering of static UI
function render() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
  document.querySelectorAll("[data-i18n-aria]").forEach((n) => { n.setAttribute("aria-label", t(n.dataset.i18nAria)); });
  $("#prompt").placeholder = t("placeholder");
  document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === state.lang)));
  document.querySelectorAll("[data-mode]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === state.mode)));
  document.body.dataset.view = state.mode;
  renderModebar();
  renderNetbar();
  renderScenarios();
  renderSteps();
  if (!$("#chat").querySelector(".msg")) renderWelcome();
  if ($(".topbar")) requestAnimationFrame(syncHeader);
}

function renderModebar() {
  const bar = $("#modebar");
  bar.replaceChildren();
  const inner = el("div", "modebar-inner");
  const demo = state.mode === "demo";
  const label = el("span", "mode-label");
  label.append(icon(demo ? "sun" : "pin"), el("span", "", demo ? t("demoLabel") : t("liveLabel")));
  const pills = el("ul", "pills");
  const items = demo ? t("demoPills") : [...t("livePills"), t("geo")[state.geo]];
  items.forEach((p) => pills.appendChild(el("li", "pill", p)));
  inner.append(label, pills, el("p", "mode-note", demo ? t("demoNote") : t("liveNote")));
  bar.appendChild(inner);
  const badge = $("#panel-mode");
  badge.replaceChildren(icon(demo ? "sun" : "pin"), el("span", "", demo ? t("badgeDemo") : t("badgeLive")));
}

function renderScenarios() {
  const box = $("#scenario-cards");
  box.replaceChildren();
  const es = state.lang === "es";
  SCENARIOS.forEach((s, i) => {
    const [ic, tone] = s;
    const title = es ? s[2] : s[5];
    const desc = es ? s[3] : s[6];
    const prompt = es ? s[4] : s[7];
    const b = el("button", `card${tone ? ` card-${tone}` : ""}`);
    b.type = "button";
    b.dataset.scenario = String(i);
    const tid = `scen-${i}-t`;
    const did = `scen-${i}-d`;
    b.setAttribute("aria-labelledby", tid);
    b.setAttribute("aria-describedby", did);
    const ib = el("span", "card-icon");
    ib.appendChild(icon(ic));
    const tx = el("span", "card-text");
    const ti = el("span", "card-title", title); ti.id = tid;
    const de = el("span", "card-desc", desc); de.id = did;
    tx.append(ti, de);
    b.append(ib, tx);
    b.addEventListener("click", () => { send(prompt); focusConversation(); });
    box.appendChild(b);
  });
}

function renderSteps() {
  const ol = $("#how-steps");
  ol.replaceChildren();
  t("steps").forEach(([title, text], i) => {
    const li = el("li", `step step-${i + 1}`);
    li.append(el("span", "step-title", title), el("span", "step-text", text));
    ol.appendChild(li);
  });
}

function renderWelcome() {
  const chat = $("#chat");
  chat.replaceChildren();
  const w = el("div", "welcome");
  const mark = $(".mark").cloneNode(true);
  mark.setAttribute("class", "mark welcome-mark");
  w.append(mark, el("p", "welcome-title", t("welcomeTitle")), el("p", "welcome-text", t("welcomeText")));
  chat.appendChild(w);
}

function focusConversation() {
  // On phones the conversation is below the cards: bring it into view after choosing a situation.
  if (window.matchMedia("(max-width: 1023px)").matches) {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    $("#panel").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }
}

// ---------------------------------------------------------------- safe rich text (no innerHTML)
// Shows **bold** as <strong>.
function appendInline(parent, text) {
  String(text).split(/\*\*(.+?)\*\*/g).forEach((part, i) => {
    if (i % 2) {
      parent.appendChild(el("strong", "", part));
    } else if (part) {
      parent.appendChild(document.createTextNode(part));
    }
  });
}

// Paragraphs, "- " / "1. " lists and "#" headings, built with DOM nodes only.
function renderAnswer(container, text) {
  const blocks = String(text).replace(/\r\n/g, "\n").trim().split(/\n{2,}/);
  for (const block of blocks) {
    let list = null;
    let para = null;
    for (const raw of block.split("\n")) {
      const line = raw.trimEnd();
      if (!line.trim()) continue;
      const h = line.match(/^\s*#{1,4}\s+(.*)$/);
      const ul = line.match(/^\s*[-*•]\s+(.*)$/);
      const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
      if (h) {
        list = null; para = null;
        const hh = el("p", "ans-h"); appendInline(hh, h[1]); container.appendChild(hh);
      } else if (ul || ol) {
        para = null;
        const kind = ul ? "ul" : "ol";
        if (!list || list.tagName.toLowerCase() !== kind) { list = el(kind, "ans-list"); container.appendChild(list); }
        const li = el("li"); appendInline(li, (ul || ol)[1]); list.appendChild(li);
      } else {
        list = null;
        if (!para) { para = el("p", "ans-p"); container.appendChild(para); } else { para.appendChild(document.createElement("br")); }
        appendInline(para, line.trim());
      }
    }
  }
}

// ---------------------------------------------------------------- chat messages
function addNode(node) {
  const chat = $("#chat");
  chat.querySelector(".welcome")?.remove();
  chat.appendChild(node);
  chat.scrollTop = chat.scrollHeight;
  if (window.matchMedia("(min-width: 1024px)").matches === false) {
    node.scrollIntoView({ behavior: "auto", block: "nearest" });
  }
  return node;
}

function userMessage(text) {
  const m = el("div", "msg msg-user");
  m.appendChild(el("p", "ans-p", text));
  return addNode(m);
}

function typingMessage() {
  const m = el("div", "msg msg-bot msg-typing");
  m.setAttribute("aria-label", t("thinking"));
  const dots = el("span", "dots");
  dots.append(el("i"), el("i"), el("i"));
  m.append(dots, el("span", "typing-text", t("thinking")));
  return addNode(m);
}

function botMessage(answer, metrics, decision) {
  const m = el("article", "msg msg-bot");
  const body = el("div", "ans");
  renderAnswer(body, answer);
  m.appendChild(body);
  const tl = safeWindowTimeline(decision) || shelterTimeline(decision);
  if (tl) m.appendChild(tl);
  m.appendChild(decisionTrail(metrics));
  const meta = el("div", "meta");
  const btn = el("button", "listen");
  btn.type = "button";
  btn.append(icon("speaker"), el("span", "", t("listen")));
  btn.addEventListener("click", () => speak(answer, btn));
  meta.appendChild(btn);
  if (decision && decision.kind === "shelter_plan" && tl) meta.appendChild(printButton(m));
  if (metrics && metrics.api_ms) meta.appendChild(el("span", "latency", `${(metrics.api_ms / 1000).toFixed(1)} s`));
  m.appendChild(meta);
  return addNode(m);
}

// ---------------------------------------------------------------- safe-window timeline
// Drawn only from `decision` (the rules engine's numbers, passed through by the API), never from
// the model's text. Old backends don't send it: then nothing is drawn.
const HHMM = /^([01]\d|2[0-3]):([0-5]\d)$/;
function toMin(hhmm) { const m = HHMM.exec(hhmm || ""); return m ? Number(m[1]) * 60 + Number(m[2]) : null; }
function fmtLeft(min, lang) {
  const h = Math.floor(min / 60), m = min % 60;
  if (!h) return `${m} min`;
  return m ? `${h} h ${m} min` : `${h} h`;
}

function safeWindowTimeline(d) {
  if (!d || d.kind !== "safe_window") return null;
  const T = t("tl");
  const eat = toMin(d.eat_by_hhmm), now = toMin(d.now_hhmm);
  if (eat == null || now == null) return null;
  const expired = d.status === "discard_now";
  const fig = el("figure", expired ? "tl tl-expired" : "tl");
  fig.setAttribute("aria-label", T.aria(d));
  fig.appendChild(el("figcaption", "tl-title", T.title));

  // Positions on a line from "cooked" (0) to "limit" (1). Times can cross midnight.
  let start = d.cooked_known ? toMin(d.cooked_at_hhmm) : null;
  const span = start == null ? null : ((eat - start + 1440) % 1440) || 1440;
  const pos = (hhmm) => {
    const x = toMin(hhmm);
    if (x == null || span == null) return null;
    const off = (x - start + 1440) % 1440;
    return off > span ? null : off / span;
  };
  const track = el("div", "tl-track");
  track.setAttribute("aria-hidden", "true");
  const fill = el("div", "tl-fill");
  const pNow = expired ? 1 : pos(d.now_hhmm);
  if (pNow != null) fill.style.width = `${(pNow * 100).toFixed(1)}%`;
  track.appendChild(fill);
  const pRem = expired ? null : pos(d.reminder_at_hhmm);
  if (pRem != null && pRem > (pNow ?? 0)) {
    const r = el("span", "tl-tick tl-tick-rem");
    r.style.left = `${(pRem * 100).toFixed(1)}%`;
    track.appendChild(r);
  }
  if (pNow != null && !expired) {
    const n = el("span", "tl-tick tl-tick-now");
    n.style.left = `${(pNow * 100).toFixed(1)}%`;
    track.appendChild(n);
  }
  if (span != null) fig.appendChild(track);

  // The same facts as text (what screen readers and small screens rely on).
  const list = el("dl", "tl-points");
  const point = (cls, label, value) => {
    if (!value) return;
    const w = el("div", `tl-pt ${cls}`);
    w.append(el("dt", "", label), el("dd", "", value));
    list.appendChild(w);
  };
  // Chronological order. Unknown cooking time: the engine assumed "long ago", so its limit is not
  // a real clock time for this dish and is not shown.
  if (d.cooked_known) point("pt-cooked", T.cooked, d.cooked_at_hhmm);
  if (expired) {
    if (d.cooked_known) point("pt-limit pt-past", T.limit, d.eat_by_hhmm);
    point(d.cooked_known ? "pt-now pt-end" : "pt-now", T.now, d.now_hhmm);
  } else {
    point("pt-now", T.now, d.now_hhmm);
    point("pt-rem", T.remind, d.reminder_at_hhmm);
    point("pt-limit pt-end", T.limit, d.eat_by_hhmm);
  }
  fig.appendChild(list);

  const status = el("p", "tl-status");
  status.append(icon(expired ? "alert" : "window"));
  const left = expired ? null : (Number.isInteger(d.minutes_left) ? d.minutes_left : (eat - now + 1440) % 1440);
  status.appendChild(el("span", "", expired ? T.expired : T.left(left)));
  fig.appendChild(status);
  const temp = Number.isFinite(d.max_temp_c) ? String(Math.round(d.max_temp_c * 10) / 10) : null;
  const why = T.why(d, temp);
  if (why) fig.appendChild(el("p", "tl-why", why));
  fig.appendChild(el("p", "tl-src", T.by(d.source && d.source.kind !== "policy" ? d.source.name : null)));
  return fig;
}

// ---------------------------------------------------------------- shelter batch timeline
// One row per batch: cook -> serve -> discard. Every time comes from `decision.batches` (the
// engine's plan_shelter_batches output, passed through by the API); nothing is computed here
// except where to draw each time on a shared axis.
function shelterTimeline(d) {
  if (!d || d.kind !== "shelter_plan" || !Array.isArray(d.batches) || !d.batches.length) return null;
  const T = t("sh");
  const ok = d.batches.every((b) => HHMM.test(b.start_cooking_hhmm || "") && HHMM.test(b.ready_hhmm || "") && HHMM.test(b.discard_hhmm || ""));
  if (!ok) return null;
  const fig = el("figure", "tl sh");
  fig.setAttribute("aria-label", T.aria(d));
  const cap = el("figcaption", "tl-title", T.title);
  if (d.people) cap.appendChild(el("span", "sh-people", ` · ${T.people(d.people)}`));
  fig.appendChild(cap);

  // Shared axis from the first "cook" to the last "discard" (same day; batches don't cross midnight).
  const t0 = Math.min(...d.batches.map((b) => toMin(b.start_cooking_hhmm)));
  const t1 = Math.max(...d.batches.map((b) => toMin(b.discard_hhmm)));
  const span = Math.max(t1 - t0, 1);
  const at = (hhmm) => `${(((toMin(hhmm) - t0) / span) * 100).toFixed(1)}%`;

  const list = el("ol", "sh-list");
  d.batches.forEach((b, i) => {
    const li = el("li", "sh-batch");
    li.appendChild(el("p", "sh-name", T.batch(i + 1, b.portions)));
    const track = el("div", "sh-track");
    track.setAttribute("aria-hidden", "true");
    const cook = el("span", "sh-seg sh-cook");
    cook.style.left = at(b.start_cooking_hhmm);
    cook.style.width = `calc(${at(b.ready_hhmm)} - ${at(b.start_cooking_hhmm)})`;
    const serve = el("span", "sh-seg sh-serve");
    serve.style.left = at(b.ready_hhmm);
    serve.style.width = `calc(${at(b.discard_hhmm)} - ${at(b.ready_hhmm)})`;
    const end = el("span", "sh-end");
    end.style.left = at(b.discard_hhmm);
    track.append(cook, serve, end);
    li.appendChild(track);
    const pts = el("dl", "tl-points sh-points");
    const point = (cls, label, value) => {
      const w = el("div", `tl-pt ${cls}`);
      w.append(el("dt", "", label), el("dd", "", value));
      pts.appendChild(w);
    };
    point("pt-cook", T.cook, b.start_cooking_hhmm);
    point("pt-now", T.serve, b.ready_hhmm);
    point("pt-limit pt-end", T.discard, b.discard_hhmm);
    li.appendChild(pts);
    list.appendChild(li);
  });
  fig.appendChild(list);
  const hot = d.batches.find((b) => Number.isFinite(b.keep_above_c));
  if (hot) fig.appendChild(el("p", "tl-why", T.hot(hot.keep_above_c)));
  fig.appendChild(el("p", "tl-src", T.by(d.source && d.source.kind !== "policy" ? d.source.name : null)));
  return fig;
}

// Prints only this answer (plan text + batch timeline + verifier seal), with the print stylesheet.
function printButton(msg) {
  const b = el("button", "listen print-btn");
  b.type = "button";
  b.append(icon("print"), el("span", "", t("sh").print));
  b.addEventListener("click", () => {
    document.querySelectorAll(".print-target").forEach((x) => x.classList.remove("print-target"));
    msg.classList.add("print-target");
    // The printout says which mode produced it (a simulated 38 °C plan must not pass for a real one).
    msg.dataset.printHead = `Al Tiempo · ${state.mode === "demo" ? t("badgeDemo") : t("badgeLive")}`;
    document.body.classList.add("printing");
    window.print();
  });
  return b;
}
window.addEventListener("afterprint", () => {
  document.body.classList.remove("printing");
  document.querySelectorAll(".print-target").forEach((x) => x.classList.remove("print-target"));
});

// Shows which rules tools ran and what the verifier did, using only the structured `metrics`
// the backend returned (tools_used, verifier_blocked). Nothing is inferred from the text.
function decisionTrail(metrics) {
  const wrap = el("div", "trail");
  if (!metrics) return wrap;
  const used = (metrics.tools_used || []).filter((x) => RULE_TOOLS.has(x));
  if (!used.length && !metrics.verifier_blocked) return wrap;
  if (used.length) {
    const names = [...new Set(used)].map((x) => t("tools")[x] || x).join(", ");
    const r = el("span", "trail-item");
    r.append(el("span", "trail-k", `${t("rulesUsed")}:`), el("span", "trail-v", ` ${names}`));
    wrap.appendChild(r);
  }
  const v = el("span", metrics.verifier_blocked ? "seal seal-swap" : "seal");
  v.append(icon(metrics.verifier_blocked ? "swap" : "shield"), el("span", "", metrics.verifier_blocked ? t("replaced") : t("verified")));
  wrap.appendChild(v);
  return wrap;
}

function errorMessage(text, retryPrompt) {
  const m = el("div", "msg msg-error");
  m.setAttribute("role", "alert");
  const head = el("p", "err-title");
  head.append(icon("alert"), el("span", "", t("errorTitle")));
  m.append(head, el("p", "ans-p", text || t("error")));
  if (retryPrompt) {
    const b = el("button", "retry");
    b.type = "button";
    b.append(icon("retry"), el("span", "", t("retry")));
    b.addEventListener("click", () => { m.remove(); send(retryPrompt, { echo: false }); });
    m.appendChild(b);
  }
  return addNode(m);
}

// No signal: the agent can't answer, so show the official basics (cached with the page by sw.js).
function offlineMessage() {
  const O = t("offline");
  const m = el("div", "msg msg-offline");
  m.setAttribute("role", "alert");
  const head = el("p", "err-title");
  head.append(icon("alert"), el("span", "", O.title));
  const list = el("ul", "ans-list");
  O.rules.forEach((r) => list.appendChild(el("li", "", r)));
  m.append(head, list, el("p", "offline-doubt", O.doubt), el("p", "tl-src", O.src));
  return addNode(m);
}

function isOffline(e) {
  return navigator.onLine === false || e instanceof TypeError; // fetch() rejects with TypeError without network
}

function renderNetbar() {
  const bar = $("#netbar");
  bar.hidden = navigator.onLine !== false;
  bar.textContent = bar.hidden ? "" : t("offline").banner;
}
window.addEventListener("online", renderNetbar);
window.addEventListener("offline", renderNetbar);

function reminderMessage(r) {
  const m = el("div", "msg msg-reminder");
  const head = el("p", "rem-head");
  head.append(icon("bell"), el("span", "", t("reminder")), el("span", "rem-time", `${t("reminderAt")} ${r.at_local}`));
  const body = el("p", "ans-p");
  appendInline(body, r.message);
  m.append(head, body);
  return addNode(m);
}

// ---------------------------------------------------------------- API
async function api(path, options) {
  const res = await fetch(path, { headers: { "content-type": "application/json" }, ...options });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

async function send(prompt, { echo = true } = {}) {
  prompt = (prompt || "").trim();
  if (!prompt || state.busy) return;
  state.busy = true;
  state.lastPrompt = prompt;
  setBusy(true);
  if (echo) userMessage(prompt);
  const typing = typingMessage();
  if (/recordatorio|reminder/i.test(prompt) && "Notification" in window && Notification.permission === "default") {
    Notification.requestPermission().catch(() => {});
  }
  const body = {
    prompt, language: state.lang, session_id: state.sessionId, demo: state.mode === "demo",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    ...(state.mode === "live" && state.coords ? { lat: state.coords.lat, lon: state.coords.lon } : {}),
  };
  try {
    await state.warm; // if the session is still starting, wait for it instead of starting a 2nd one
    const { data } = await api("/api/chat", { method: "POST", body: JSON.stringify(body) });
    typing.remove();
    if (data.error || !data.answer) {
      errorMessage(data.answer || t("error"), data.error === "daily_cap" ? null : prompt);
    } else {
      botMessage(data.answer, data.metrics, data.decision);
    }
  } catch (e) {
    typing.remove();
    if (isOffline(e)) offlineMessage();
    else errorMessage(t("error"), prompt);
  } finally {
    state.busy = false;
    setBusy(false);
  }
}

function setBusy(busy) {
  $("#send").disabled = busy;
  document.querySelectorAll(".card").forEach((c) => { c.disabled = busy; });
  $("#panel").setAttribute("aria-busy", String(busy));
}

async function speak(text, btn) {
  btn.disabled = true;
  const label = btn.querySelector("span");
  label.textContent = t("listening");
  try {
    const { ok, data } = await api("/api/voice", { method: "POST", body: JSON.stringify({ text: text.replace(/\*\*/g, ""), language: state.lang }) });
    if (ok && data.audio_base64) {
      await new Audio(`data:audio/mpeg;base64,${data.audio_base64}`).play();
    } else {
      btn.title = t("voiceFail");
    }
  } catch (e) {
    btn.title = t("voiceFail");
  } finally {
    btn.disabled = false;
    label.textContent = t("listen");
  }
}

async function pollReminders() {
  try {
    const { ok, data } = await api(`/api/reminders?session_id=${encodeURIComponent(state.sessionId)}`, { method: "GET" });
    if (!ok) return;
    for (const r of data.reminders || []) {
      if (state.seenReminders.has(r.reminder_id)) continue;
      state.seenReminders.add(r.reminder_id);
      reminderMessage(r);
      const text = `${t("reminder")} (${r.at_local}): ${r.message}`;
      if ("Notification" in window && Notification.permission === "granted") new Notification("Al Tiempo", { body: text });
    }
  } catch (e) { /* offline: try again later */ }
}

// Start this conversation's agent session while the user reads the page, so the first answer
// takes ~2 s instead of ~6 s. Best effort: if it fails, the chat still works (just slower).
function warmUp() {
  state.warm = api("/api/warm", {
    method: "POST",
    body: JSON.stringify({ session_id: state.sessionId, language: state.lang, demo: state.mode === "demo" }),
  }).catch(() => {});
}

function resetConversation() {
  state.sessionId = newSessionId();
  state.seenReminders = new Set();
  renderWelcome();
}

function setMode(mode) {
  if (mode === state.mode) return;
  state.mode = mode;
  resetConversation(); // new conversation when switching mode: never mix simulated and real results
  if (mode === "live" && !state.coords) {
    if (navigator.geolocation) {
      state.geo = "asking";
      navigator.geolocation.getCurrentPosition(
        (p) => { state.coords = { lat: +p.coords.latitude.toFixed(2), lon: +p.coords.longitude.toFixed(2) }; state.geo = "granted"; renderModebar(); },
        () => { state.coords = null; state.geo = "denied"; renderModebar(); },
        { timeout: 8000, maximumAge: 3600000 });
    } else {
      state.geo = "unsupported";
    }
  }
  render();
  warmUp();
}

function setLang(lang) {
  if (lang === state.lang) return;
  state.lang = lang;
  resetConversation();
  render();
  warmUp();
}

document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang)));
document.querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
$("#form").addEventListener("submit", (e) => { e.preventDefault(); const v = $("#prompt").value; $("#prompt").value = ""; autosize(); send(v); });
$("#prompt").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#form").requestSubmit(); } });

function autosize() {
  const ta = $("#prompt");
  ta.style.height = "auto";
  ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`;
}
$("#prompt").addEventListener("input", autosize);

// The header height changes with the language and mode texts; the sticky conversation panel uses it.
function syncHeader() {
  const bar = $(".topbar");
  const sticky = getComputedStyle(bar).position === "sticky";
  document.documentElement.style.setProperty("--sticky-top", `${sticky ? bar.offsetHeight + 16 : 12}px`);
}
window.addEventListener("resize", syncHeader);

render();
renderNetbar();
syncHeader();
warmUp();
setInterval(pollReminders, 15000);

// Installable + opens offline (https or localhost only; browsers require it).
if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}
