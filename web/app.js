"use strict";
// Al Tiempo web client: plain JS, no build step. Talks to /api/* on the same domain (CloudFront).
// Agent text is never inserted as HTML: everything goes through textContent / DOM nodes.
// The browser never calculates or extracts food-safety times: it only shows what the backend sent.

const SCENARIOS = [
  // [icon, tone, es title, es description, es prompt, en title, en description, en prompt]
  ["bell", "primary",
    "Voy a cocinar", "Antes de cocinar: hasta qué hora se puede comer y un aviso a tiempo.",
    "Voy a cocinar frijoles a las 14:00 y no tengo refri. ¿Hasta qué hora se pueden comer?",
    "I'm about to cook", "Before cooking: until when it can be eaten, and a reminder in time.",
    "I'm going to cook beans at 14:00 and I have no fridge. Until what time can we eat them?"],
  ["window", "",
    "Ya cociné", "Cocinaste y no tienes refri: te decimos hasta qué hora se puede comer.",
    "Cociné frijoles a las 12:00 y no tengo refri. ¿Hasta qué hora se pueden comer?",
    "Already cooked", "You cooked and have no fridge: find out until what time it can be eaten.",
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
    hygiene: { kicker: "Consejo de higiene", why: "Por qué:", src: "Fuente:" },
    leftover: { kicker: "¿Qué hago con ella?", why: "Por qué:", src: "Fuente:" },
    heat: {
      title: "El calor de hoy, hora por hora", line: "32 °C", window: "Ventana segura",
      note: "Arriba de 32 °C la FDA baja el límite de 2 horas a 1.",
      src: (demo) => demo ? "Pronóstico: día de prueba de 38 °C" : "Pronóstico: Open-Meteo.com (CC BY 4.0)",
      aria: (d, max) => `Gráfica del pronóstico de ${d.hourly[0][0]} a ${d.hourly[d.hourly.length - 1][0]}; máximo ${max} °C. La ventana segura va de ${d.cooked_at_hhmm} a ${d.eat_by_hhmm}.`,
    },
    mic: {
      start: "Hablar", stop: "Escuchando… toca para terminar",
      hint: "Usa el reconocimiento de voz de tu navegador (en Chrome, el audio lo procesa Google). La respuesta se lee en voz alta con Amazon Polly.",
      denied: "No pude usar el micrófono. Revisa el permiso del navegador o escribe tu pregunta.",
      none: "No te escuché. Toca Hablar e inténtalo otra vez.",
    },
    card: {
      print: "Imprimir tarjeta", title: "Tarjeta para la cocina",
      cooked: (h) => `Comida cocinada a las ${h}`, planned: (h) => `Si se cocina a las ${h}`,
      eat: "CÓMELA ANTES DE LAS", after: "Después de esa hora, TÍRALA.",
      kids: "Bebés y niños pequeños: servir al momento, sin guardar sobras.",
      plan: (n) => `Plan de cocina · ${n} personas`, batch: "Tanda", cook: "Empezar a cocinar", serve: "Servir desde",
      discard: "TIRAR a las", portions: "Porciones", done: "Hecho",
      qr: "Escanea para preguntar por otra comida.",
      foot: "Guía general de reglas oficiales de inocuidad. No es consejo médico. Emergencia: llama a tu número local.",
    },
    verdict: {
      eat: "Cómelo antes de las", toss: "Tíralo", tossSub: (h) => h ? `El límite fue a las ${h}.` : "Ya pasó el límite.",
      ask: "Falta un dato", askSub: "¿A qué hora lo cocinaste?",
      hot: "En el fuego: el tiempo no corre", hotSub: (h) => `Si apagas el fuego ahora: cómelo antes de las ${h}.`,
      plan: (h) => `Si lo cocinas a las ${h}`, wont: (h) => `No aguanta hasta las ${h}`,
      left: (m) => `Quedan ${fmtLeft(m, "es")}`, over: "Ya pasó el límite: tíralo.",
    },
    quiz: {
      kicker: "Comprobación anónima · opcional",
      q: "¿Se entendió? Toca la hora límite que te dimos arriba:",
      ok: "¡Correcto!", no: (c) => `La hora correcta es ${c}.`,
      panel: (pct, n) => `Comprensión: ${pct} % correcto (n = ${n})`,
      note: "Anónimo: solo se cuenta si acertaste, sin datos personales.",
    },
    inside: {
      summary: "Ver por dentro", forecast: "Pronóstico usado", engine: "Motor de reglas", verifier: "Verificador",
      fcDemo: "Simulado: un día guardado de 38 °C, igual para todos.",
      fcLive: (t) => `Pronóstico real por hora (Open-Meteo): máximo ${t} °C en esas horas.`,
      fcUser: (t) => `Temperatura del cuarto que nos dijiste: ${t} °C (en lugar del pronóstico de afuera).`,
      fcNone: "Sin pronóstico para esas horas: se asume más de 32 °C (el caso más seguro).",
      fcLiveAny: "Modo real: pronóstico por hora de Open-Meteo si compartiste tu ubicación; si no, se asume calor.",
      fcNotUsed: "Esta respuesta no necesitó el pronóstico.",
      tools: "Herramientas", rule: "Regla que decide", noEngine: "En esta respuesta no se calculó ninguna hora.",
      unknown: "Hora de cocción desconocida: el motor asume el peor caso.",
      vOk: "Aprobó la respuesta a la primera: no encontró horas ni límites que el motor no diera.",
      vRetry: (n) => `Pidió ${n === 1 ? "una corrección" : `${n} correcciones`} al modelo y después aprobó.`,
      vBlock: "Bloqueó la respuesta del modelo y usó la respuesta segura armada con el motor.",
      model: (i, o, ms) => `Modelo: ${i} tokens de entrada, ${o} de salida · ${ms} ms`,
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
    hygiene: { kicker: "Hygiene tip", why: "Why:", src: "Source:" },
    leftover: { kicker: "What to do with it?", why: "Why:", src: "Source:" },
    heat: {
      title: "Today's heat, hour by hour", line: "32 °C", window: "Safe window",
      note: "Above 32 °C the FDA cuts the limit from 2 hours to 1.",
      src: (demo) => demo ? "Forecast: 38 °C test day" : "Forecast: Open-Meteo.com (CC BY 4.0)",
      aria: (d, max) => `Forecast chart from ${d.hourly[0][0]} to ${d.hourly[d.hourly.length - 1][0]}; max ${max} °C. The safe window runs from ${d.cooked_at_hhmm} to ${d.eat_by_hhmm}.`,
    },
    mic: {
      start: "Speak", stop: "Listening… tap to finish",
      hint: "Uses your browser's speech recognition (in Chrome, Google processes the audio). The answer is read aloud with Amazon Polly.",
      denied: "I couldn't use the microphone. Check the browser permission or type your question.",
      none: "I didn't hear you. Tap Speak and try again.",
    },
    card: {
      print: "Print card", title: "Kitchen card",
      cooked: (h) => `Food cooked at ${h}`, planned: (h) => `If cooked at ${h}`,
      eat: "EAT IT BEFORE", after: "After that time, THROW IT AWAY.",
      kids: "Babies and young children: serve right away, keep no leftovers.",
      plan: (n) => `Cooking plan · ${n} people`, batch: "Batch", cook: "Start cooking", serve: "Serve from",
      discard: "THROW AWAY at", portions: "Portions", done: "Done",
      qr: "Scan to ask about another dish.",
      foot: "General guidance from official food-safety rules. Not medical advice. Emergency: call your local number.",
    },
    verdict: {
      eat: "Eat it before", toss: "Throw it away", tossSub: (h) => h ? `The limit was ${h}.` : "The limit has passed.",
      ask: "Missing one detail", askSub: "When did you cook it?",
      hot: "On the heat: the clock is not running", hotSub: (h) => `If you turn off the heat now: eat it before ${h}.`,
      plan: (h) => `If you cook it at ${h}`, wont: (h) => `It won't last until ${h}`,
      left: (m) => `${fmtLeft(m, "en")} left`, over: "The limit has passed: throw it away.",
    },
    quiz: {
      kicker: "Anonymous check · optional",
      q: "Was it clear? Tap the deadline we gave you above:",
      ok: "Correct!", no: (c) => `The right time is ${c}.`,
      panel: (pct, n) => `Comprehension: ${pct}% correct (n = ${n})`,
      note: "Anonymous: we only count whether you got it right, no personal data.",
    },
    inside: {
      summary: "Look inside", forecast: "Forecast used", engine: "Rules engine", verifier: "Verifier",
      fcDemo: "Simulated: a saved 38 °C day, the same for everyone.",
      fcLive: (t) => `Real hourly forecast (Open-Meteo): up to ${t} °C in those hours.`,
      fcUser: (t) => `Room temperature you told us: ${t} °C (instead of the outdoor forecast).`,
      fcNone: "No forecast for those hours: assumed above 32 °C (the safest case).",
      fcLiveAny: "Live mode: Open-Meteo hourly forecast if you shared your location; otherwise heat is assumed.",
      fcNotUsed: "This answer did not need the forecast.",
      tools: "Tools", rule: "Deciding rule", noEngine: "No time was calculated in this answer.",
      unknown: "Cooking time unknown: the engine assumes the worst case.",
      vOk: "Approved the answer on the first try: no time or limit the engine didn't produce.",
      vRetry: (n) => `Asked the model for ${n === 1 ? "one correction" : `${n} corrections`}, then approved.`,
      vBlock: "Blocked the model's answer and used the safe answer built from the engine.",
      model: (i, o, ms) => `Model: ${i} input tokens, ${o} output · ${ms} ms`,
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

function botMessage(answer, metrics, decision, hygiene, leftover) {
  const m = el("article", "msg msg-bot");
  const v = verdictBox(decision);
  if (v) m.appendChild(v);
  const body = el("div", "ans");
  renderAnswer(body, answer);
  m.appendChild(body);
  const tl = safeWindowTimeline(decision) || shelterTimeline(decision);
  if (tl) m.appendChild(tl);
  const heat = heatChart(decision);
  if (heat) m.appendChild(heat);
  const card = printCard(decision);
  if (card) m.appendChild(card);
  m.appendChild(decisionTrail(metrics));
  const tip = hygieneNote(hygiene) || hygieneNote(leftover, "leftover");
  if (tip) m.appendChild(tip);
  const quiz = quizBlock(decision);
  if (quiz) m.appendChild(quiz);
  const meta = el("div", "meta");
  const btn = el("button", "listen listen-main");
  btn.type = "button";
  btn.append(icon("speaker"), el("span", "", t("listen")));
  btn.addEventListener("click", () => speak(answer, btn));
  meta.appendChild(btn);
  if (state.voiceReply) { // asked by voice -> answer by voice (Amazon Polly)
    state.voiceReply = false;
    speak(answer, btn);
  }
  if (card) meta.appendChild(printButton(m, decision.kind === "shelter_plan" ? t("sh").print : t("card").print));
  if (metrics && metrics.api_ms) meta.appendChild(el("span", "latency", `${(metrics.api_ms / 1000).toFixed(1)} s`));
  m.appendChild(meta);
  const inside = insideView(metrics, decision);
  if (inside) m.appendChild(inside);
  return addNode(m);
}

// ---------------------------------------------------------------- hygiene tip
// Chosen by the backend's code from the user's words (rules/hygiene_tips.yaml), never by the model.
// A small note after the decision: it must not compete with the safe window.
function hygieneNote(h, kind = "hygiene") {
  if (!h || typeof h.tip !== "string" || !h.tip) return null;
  const H = t(kind);
  const box = el("aside", "hygiene");
  box.setAttribute("aria-label", H.kicker);
  box.append(el("p", "hygiene-kicker", H.kicker), el("p", "hygiene-tip", h.tip));
  if (h.why) {
    const why = el("p", "hygiene-why");
    why.append(el("span", "hygiene-k", `${H.why} `), document.createTextNode(h.why));
    box.appendChild(why);
  }
  if (h.source_name && /^https:\/\//.test(h.source_url || "")) {
    const src = el("p", "hygiene-src");
    const a = el("a", "", h.source_name.split(" - ")[0]);
    a.href = h.source_url; a.target = "_blank"; a.rel = "noopener";
    src.append(el("span", "hygiene-k", `${H.src} `), a);
    box.appendChild(src);
  }
  return box;
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

// ---------------------------------------------------------------- heat curve
// The forecast the engine used, hour by hour, with the 32 °C line and the safe window shaded.
// Data: decision.hourly (added by the backend from the same forecast; never read by the model).
function heatChart(d) {
  if (!d || d.kind !== "safe_window" || !Array.isArray(d.hourly) || d.hourly.length < 3 || !d.cooked_known) return null;
  const pts = d.hourly.filter((p) => Array.isArray(p) && HHMM.test(p[0]) && Number.isFinite(p[1]));
  if (pts.length < 3) return null;
  const H = t("heat");
  const W = 320, Ht = 130, L = 30, R = 8, T = 12, B = 22;
  const temps = pts.map((p) => p[1]);
  const lo = Math.floor(Math.min(...temps, 30) - 2), hi = Math.ceil(Math.max(...temps, 33) + 1);
  const x0 = toMin(pts[0][0]), span = ((toMin(pts[pts.length - 1][0]) - x0 + 1440) % 1440) || 60;
  const X = (hhmm) => L + (((toMin(hhmm) - x0 + 1440) % 1440) / span) * (W - L - R);
  const Y = (c) => T + (1 - (c - lo) / (hi - lo)) * (Ht - T - B);
  const NS = SVGNS, svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${Ht}`);
  svg.setAttribute("class", "heat-svg");
  svg.setAttribute("role", "img");
  const max = Math.max(...temps);
  svg.setAttribute("aria-label", H.aria(d, max));
  const add = (tag, attrs, text) => {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, String(v)));
    if (text != null) n.textContent = text;
    svg.appendChild(n);
    return n;
  };
  // safe window (cooked -> eat by), clipped to the chart
  const clip = (v) => Math.max(L, Math.min(W - R, v));
  const wx1 = clip(X(d.cooked_at_hhmm)), wx2 = clip(X(d.eat_by_hhmm));
  if (wx2 > wx1) add("rect", { x: wx1, y: T, width: wx2 - wx1, height: Ht - T - B, class: "heat-win" });
  // 32 °C line
  add("line", { x1: L, x2: W - R, y1: Y(32), y2: Y(32), class: "heat-limit" });
  add("text", { x: L + 3, y: Y(32) - 4, "text-anchor": "start", class: "heat-limit-t" }, H.line);
  // curve + points above 32 °C
  add("polyline", { points: pts.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" "), class: "heat-line" });
  pts.forEach((p) => add("circle", { cx: X(p[0]), cy: Y(p[1]), r: 2.6, class: p[1] > 32 ? "heat-pt hot" : "heat-pt" }));
  // axis labels: every other hour, and the max
  pts.forEach((p, i) => { if (i % 2 === 0) add("text", { x: X(p[0]), y: Ht - 6, "text-anchor": "middle", class: "heat-ax" }, p[0].slice(0, 2)); });
  const mp = pts[temps.indexOf(max)];
  add("text", { x: X(mp[0]), y: Y(max) - 6, "text-anchor": "middle", class: "heat-max" }, `${max} °C`);
  [lo + 1, hi - 1].forEach((c) => add("text", { x: L - 4, y: Y(c) + 3, "text-anchor": "end", class: "heat-ax" }, `${Math.round(c)}°`));
  const fig = el("figure", "heat");
  fig.append(el("figcaption", "tl-title", H.title), svg);
  const legend = el("p", "heat-legend");
  legend.append(el("span", "heat-key", ""), document.createTextNode(` ${H.window} · ${H.note}`));
  fig.append(legend, el("p", "tl-src", H.src(state.mode === "demo")));
  return fig;
}

// ---------------------------------------------------------------- printable card (hidden on screen)
// A big, plain card to stick on the kitchen wall: only engine times, the source and a QR code.
function printCard(d) {
  if (!d) return null;
  const C = t("card");
  const card = el("section", "print-card");
  card.setAttribute("aria-hidden", "true");
  // Says the mode and the date: a simulated 38 °C plan must never pass for a real one.
  const day = new Date().toLocaleDateString(state.lang === "es" ? "es-MX" : "en-US", { weekday: "long", day: "numeric", month: "long" });
  card.appendChild(el("p", "pc-brand", `Al Tiempo · ${C.title} · ${state.mode === "demo" ? t("badgeDemo") : t("badgeLive")} · ${day}`));
  if (d.kind === "safe_window") {
    if (!d.cooked_known || d.status === "discard_now" || !HHMM.test(d.eat_by_hhmm || "")) return null;
    card.appendChild(el("p", "pc-sub", d.planned ? C.planned(d.cooked_at_hhmm) : C.cooked(d.cooked_at_hhmm)));
    card.appendChild(el("p", "pc-eat", C.eat));
    card.appendChild(el("p", "pc-time", d.eat_by_hhmm));
    card.appendChild(el("p", "pc-after", C.after));
    if (d.serve_immediately) card.appendChild(el("p", "pc-sub", C.kids));
  } else if (d.kind === "shelter_plan" && Array.isArray(d.batches) && d.batches.length) {
    if (!d.batches.every((b) => HHMM.test(b.discard_hhmm || ""))) return null;
    card.appendChild(el("p", "pc-plan", C.plan(d.people || "")));
    const table = el("table", "pc-table");
    const head = el("tr");
    [C.batch, C.cook, C.serve, C.discard, C.portions, C.done].forEach((h) => head.appendChild(el("th", "", h)));
    table.appendChild(head);
    d.batches.forEach((b, i) => {
      const tr = el("tr");
      [String(i + 1), b.start_cooking_hhmm || "", b.ready_hhmm || "", b.discard_hhmm, String(b.portions ?? ""), "☐"].forEach((v, j) => tr.appendChild(el("td", j === 3 ? "pc-discard" : "", v)));
      table.appendChild(tr);
    });
    card.appendChild(table);
    if (d.hot_hold && d.batches[0].keep_above_c) card.appendChild(el("p", "pc-sub", t("sh").hot(d.batches[0].keep_above_c)));
  } else {
    return null;
  }
  const src = d.source && d.source.kind !== "policy" ? d.source.name : null;
  card.appendChild(el("p", "pc-src", (d.kind === "shelter_plan" ? t("sh") : t("tl")).by(src)));
  const qr = el("div", "pc-qr");
  const img = el("img");
  img.src = "icons/qr-demo.png"; img.alt = ""; img.width = 96; img.height = 96;
  qr.append(img, el("p", "", C.qr));
  card.append(qr, el("p", "pc-foot", C.foot));
  return card;
}

// ---------------------------------------------------------------- verdict ("traffic light")
// First thing in the answer: one colour and one big time, copied from the engine's decision.
// green = eat before HH:MM, amber = little time left / won't last until mealtime, red = throw it
// away, grey = a detail is missing. The countdown only counts down the engine's minutes_left.
const AMBER_MIN = 15;

function verdictBox(d) {
  if (!d || d.kind !== "safe_window") return null;
  const V = t("verdict");
  const box = el("section", "verdict");
  box.setAttribute("role", "status");
  const head = el("p", "v-head");
  const big = el("p", "v-big");
  const sub = el("p", "v-sub");
  let tone;
  if (!d.cooked_known) {
    tone = "grey";
    head.textContent = V.ask;
    big.textContent = V.askSub;
    big.classList.add("v-big-text");
  } else if (d.status === "discard_now") {
    tone = "red";
    head.textContent = "✕";
    big.textContent = V.toss;
    big.classList.add("v-big-word");
    sub.textContent = V.tossSub(d.eat_by_hhmm);
  } else if (d.hot_holding) {
    tone = "green";
    head.textContent = V.hot;
    big.textContent = "60 °C+";
    sub.textContent = V.hotSub(d.eat_by_hhmm);
  } else {
    tone = d.wont_last_until ? "amber" : "green";
    head.textContent = d.wont_last_until ? V.wont(d.wont_last_until) : d.planned ? V.plan(d.cooked_at_hhmm) : V.eat;
    if (d.wont_last_until || d.planned) head.textContent += ` · ${V.eat.toLowerCase()}`;
    big.textContent = d.eat_by_hhmm;
    if (Number.isInteger(d.minutes_left) && !d.planned) {
      box.dataset.deadline = String(Date.now() + d.minutes_left * 60000);
      sub.classList.add("v-left");
    }
  }
  box.classList.add(`v-${tone}`);
  box.append(head, big);
  if (sub.textContent || box.dataset.deadline) box.appendChild(sub);
  tickVerdict(box);
  return box;
}

function tickVerdict(box) {
  const deadline = Number(box.dataset.deadline);
  if (!deadline) return;
  const V = t("verdict");
  const sub = box.querySelector(".v-left");
  const left = Math.ceil((deadline - Date.now()) / 60000);
  if (left <= 0) {
    box.classList.remove("v-green", "v-amber");
    box.classList.add("v-red");
    sub.textContent = V.over;
    delete box.dataset.deadline;
    return;
  }
  sub.textContent = V.left(left);
  if (left <= AMBER_MIN && box.classList.contains("v-green")) {
    box.classList.replace("v-green", "v-amber");
  }
}

setInterval(() => document.querySelectorAll(".verdict[data-deadline]").forEach(tickVerdict), 15000);

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
    if (!d.planned) point("pt-now", T.now, d.now_hhmm);
    point("pt-rem", T.remind, d.reminder_at_hhmm);
    point("pt-limit pt-end", T.limit, d.eat_by_hhmm);
  }
  fig.appendChild(list);

  // The reason is already in the answer (the engine's summary): not repeated here.
  fig.appendChild(el("p", "tl-src", T.by(d.source && d.source.kind !== "policy" ? d.source.name : null)));
  return fig;
}

// ---------------------------------------------------------------- "Look inside" (closed by default)
// forecast used -> rules engine output -> verifier decision, for each answer. Uses only what the
// backend already returns (`metrics`, `decision`); nothing is inferred from the model's text.
const FORECAST_TOOLS = new Set(["compute_safe_window", "plan_meals", "plan_shelter_batches", "get_forecast"]);

function insideView(metrics, d) {
  if (!metrics || !Array.isArray(metrics.tools_used)) return null;
  const I = t("inside");
  const det = el("details", "inside");
  det.appendChild(el("summary", "", I.summary));
  const steps = el("ol", "inside-steps");
  const step = (title, ...lines) => {
    const li = el("li");
    li.appendChild(el("p", "inside-k", title));
    lines.filter(Boolean).forEach((x) => li.appendChild(typeof x === "string" ? el("p", "inside-v", x) : x));
    steps.appendChild(li);
  };

  // 1. Forecast
  const usedForecast = metrics.tools_used.some((x) => FORECAST_TOOLS.has(x));
  let fc = I.fcNotUsed;
  if (d && d.kind === "safe_window" && d.temp_source === "user" && Number.isFinite(d.max_temp_c)) fc = I.fcUser(Math.round(d.max_temp_c * 10) / 10);
  else if (metrics.demo && (usedForecast || d)) fc = I.fcDemo;
  else if (d && d.kind === "safe_window") fc = Number.isFinite(d.max_temp_c) ? I.fcLive(Math.round(d.max_temp_c * 10) / 10) : I.fcNone;
  else if (usedForecast || d) fc = I.fcLiveAny;
  step(I.forecast, fc);

  // 2. Rules engine: tools that ran, deciding rule + source, times exactly as the engine sent them
  const names = [...new Set(metrics.tools_used)].map((x) => t("tools")[x] || x).join(", ");
  const lines = [names ? `${I.tools}: ${names}` : null];
  if (d && (d.kind === "safe_window" || d.kind === "shelter_plan")) {
    const rule = el("p", "inside-v");
    rule.append(`${I.rule}: `);
    const ids = d.kind === "safe_window" ? [d.rule_id] : (d.rule_ids || []);
    ids.filter(Boolean).forEach((id) => { rule.append(el("code", "inside-chip", id), " "); });
    if (d.source && d.source.name) rule.append(`(${d.source.name})`);
    lines.push(rule);
    if (d.kind === "safe_window") {
      const T = t("tl");
      lines.push(d.cooked_known
        ? `${T.cooked} ${d.cooked_at_hhmm} · ${T.limit} ${d.eat_by_hhmm} (${d.limit_minutes} min)${d.reminder_at_hhmm && d.status !== "discard_now" ? ` · ${T.remind} ${d.reminder_at_hhmm}` : ""}`
        : I.unknown);
    } else {
      const S = t("sh");
      (d.batches || []).forEach((b, i) => lines.push(`${S.batch(i + 1, b.portions)}: ${S.cook} ${b.start_cooking_hhmm} · ${S.serve} ${b.ready_hhmm} · ${S.discard} ${b.discard_hhmm}`));
    }
  } else {
    lines.push(I.noEngine);
  }
  step(I.engine, ...lines);

  // 3. Verifier, from the backend's counters for this turn
  const blocked = Number(metrics.verifier_blocked) || 0, retried = Number(metrics.verifier_retried) || 0;
  const model = Number.isInteger(metrics.input_tokens) && Number.isInteger(metrics.output_tokens) && Number.isInteger(metrics.latency_ms)
    ? I.model(metrics.input_tokens, metrics.output_tokens, metrics.latency_ms) : null;
  step(I.verifier, blocked ? I.vBlock : retried ? I.vRetry(retried) : I.vOk, model);
  det.appendChild(steps);
  return det;
}

// ---------------------------------------------------------------- comprehension check
// One tap after a safe window. The 3 options and the right one come from the rules engine
// (`decision.quiz`); the browser only compares the tapped option with `quiz.correct` and sends
// true/false. Nothing else is stored: no session id, no text.
function quizBlock(d) {
  if (!d || d.kind !== "safe_window" || !d.quiz || !Array.isArray(d.quiz.options)) return null;
  const options = d.quiz.options.filter((o) => HHMM.test(o));
  if (options.length < 2 || !options.includes(d.quiz.correct)) return null;
  const Q = t("quiz");
  const box = el("div", "quiz");
  box.setAttribute("role", "group");
  const label = el("p", "quiz-q");
  label.append(el("span", "quiz-kicker", Q.kicker), el("span", "", Q.q));
  label.id = `quiz-${Math.random().toString(36).slice(2, 9)}`;
  box.setAttribute("aria-labelledby", label.id);
  const row = el("div", "quiz-opts");
  const result = el("p", "quiz-result");
  result.setAttribute("aria-live", "polite");
  options.forEach((opt) => {
    const b = el("button", "quiz-opt", opt);
    b.type = "button";
    b.addEventListener("click", async () => {
      const correct = opt === d.quiz.correct;
      row.querySelectorAll("button").forEach((x) => {
        x.disabled = true;
        if (x.textContent === d.quiz.correct) x.classList.add("is-correct");
      });
      if (!correct) b.classList.add("is-wrong");
      b.setAttribute("aria-pressed", "true");
      result.textContent = correct ? Q.ok : Q.no(d.quiz.correct);
      try {
        const { ok, data } = await api("/api/comprehension", { method: "POST", body: JSON.stringify({ correct }) });
        if (ok && Number.isInteger(data.answered) && data.answered > 0 && Number.isInteger(data.correct)) {
          box.appendChild(comprehensionPanel(data));
        }
      } catch { /* offline: the answer is still shown, nothing is stored */ }
    });
    row.appendChild(b);
  });
  box.append(label, row, result);
  return box;
}

function comprehensionPanel(s) {
  const Q = t("quiz");
  const pct = Math.round((100 * s.correct) / s.answered);
  const p = el("p", "quiz-panel");
  p.append(el("strong", "", Q.panel(pct, s.answered)), el("span", "", ` ${Q.note}`));
  return p;
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
function printButton(msg, label) {
  const b = el("button", "listen print-btn");
  b.type = "button";
  b.append(icon("print"), el("span", "", label || t("sh").print));
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
      botMessage(data.answer, data.metrics, data.decision, data.hygiene_tip, data.leftover_tip);
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
  document.dispatchEvent(new Event("langchange"));
}

document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang)));
document.querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
$("#form").addEventListener("submit", (e) => { e.preventDefault(); const v = $("#prompt").value; $("#prompt").value = ""; autosize(); send(v); });

// ---------------------------------------------------------------- voice input (browser speech recognition)
// For people who read or type little: speak, the text goes to the same chat, and the answer is
// read aloud with Amazon Polly. Only shown where the browser supports it (Chrome, Edge, Android).
// Amazon Transcribe would keep the audio in AWS, but it is not available on this account's plan.
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRec) {
  const mic = document.createElement("button");
  mic.type = "button";
  mic.id = "mic";
  mic.className = "mic";
  mic.append(icon("mic"), el("span", "mic-label", t("mic").start));
  $("#send").before(mic);
  let rec = null;
  const label = () => mic.querySelector(".mic-label");
  const setIdle = () => { rec = null; mic.classList.remove("listening"); mic.setAttribute("aria-pressed", "false"); label().textContent = t("mic").start; };
  const refreshMic = () => { mic.title = t("mic").hint; mic.setAttribute("aria-label", t("mic").start); if (!rec) label().textContent = t("mic").start; };
  refreshMic();
  document.addEventListener("langchange", refreshMic);
  mic.addEventListener("click", () => {
    if (state.busy) return;
    if (rec) { rec.stop(); return; }
    rec = new SpeechRec();
    rec.lang = state.lang === "es" ? "es-MX" : "en-US";
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    let finalText = "";
    rec.onresult = (ev) => {
      let interim = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const r = ev.results[i];
        if (r.isFinal) finalText += r[0].transcript; else interim += r[0].transcript;
      }
      $("#prompt").value = (finalText + interim).trim();
      autosize();
    };
    rec.onerror = (ev) => {
      if (ev.error === "not-allowed" || ev.error === "service-not-allowed") errorMessage(t("mic").denied, null);
    };
    rec.onend = () => {
      const text = ($("#prompt").value || "").trim();
      setIdle();
      if (finalText.trim() && text) {
        $("#prompt").value = ""; autosize();
        state.voiceReply = true;
        send(text);
      } else if (!text) {
        errorMessage(t("mic").none, null);
      }
    };
    mic.classList.add("listening");
    mic.setAttribute("aria-pressed", "true");
    label().textContent = t("mic").stop;
    rec.start();
  });
}
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
