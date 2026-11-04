"use strict";
// Al Tiempo web client: plain JS, no build step. Talks to /api/* on the same domain (CloudFront).

const I18N = {
  es: {
    tagline: "¿Hasta qué hora se puede comer? Reglas oficiales + el calor de hoy.",
    modeDemo: "Demo", modeLive: "En vivo",
    bannerDemo: "Modo demo: día simulado de 38 °C y reloj fijo a las 12:00, para que los resultados sean iguales para todos. Los recordatorios llegan en ~1 minuto.",
    bannerLive: "Modo en vivo: usa tu hora real y, si lo permites, tu ubicación para el pronóstico de calor.",
    tryTitle: "Pruébalo en 1 minuto",
    placeholder: "Escribe qué cocinaste y a qué hora…",
    send: "Enviar", thinking: "Revisando las reglas oficiales…", listen: "🔊 Escuchar",
    disclaimer: "Al Tiempo da orientación general de inocuidad basada en fuentes oficiales (OMS, FDA, CDC, NHS). No es consejo médico. En una emergencia, llama a tu número local de emergencias.",
    sources: "Fuentes y métricas en el repositorio",
    reminder: "⏰ Recordatorio",
    error: "No pude responder. Si tienes duda, tira la comida.",
    scenarios: [
      ["Ventana segura", "Cociné frijoles a las 12:00 y no tengo refri. ¿Hasta qué hora se pueden comer?"],
      ["Bebé + arroz", "¿Le doy a mi bebé el arroz que cociné hace 5 horas? Estuvo fuera del refri."],
      ["Apagón", "Se fue la luz a las 06:00, no he abierto el refri y el congelador está lleno. ¿Qué hago?"],
      ["Albergue (120 personas)", "Coordino un albergue con 120 personas. La comida es de 13:00 a 15:00, arroz y frijoles, sin forma de mantenerla caliente."],
      ["Planear comidas", "Somos 5 en casa, comemos a las 14:00 y cenamos a las 20:00. ¿A qué hora cocino?"],
      ["Señales de alarma", "Mi hija de 2 años tiene diarrea, está muy dormida y casi no quiere beber. Estamos en México."],
      ["Recordatorio", "Cociné pollo a las 12:00. Prográmame un recordatorio para comerlo a tiempo."],
    ],
  },
  en: {
    tagline: "Until what time is it safe to eat? Official rules + today's heat.",
    modeDemo: "Demo", modeLive: "Live",
    bannerDemo: "Demo mode: simulated 38 °C day and the clock fixed at 12:00, so everyone gets the same results. Reminders arrive in ~1 minute.",
    bannerLive: "Live mode: uses your real time and, if you allow it, your location for the heat forecast.",
    tryTitle: "Try it in 1 minute",
    placeholder: "Type what you cooked and when…",
    send: "Send", thinking: "Checking the official rules…", listen: "🔊 Listen",
    disclaimer: "Al Tiempo gives general food-safety guidance from official sources (WHO, FDA, CDC, NHS). It is not medical advice. In an emergency, call your local emergency number.",
    sources: "Sources and metrics in the repository",
    reminder: "⏰ Reminder",
    error: "I could not answer. If in doubt, throw the food away.",
    scenarios: [
      ["Safe window", "I cooked beans at 12:00 and I have no fridge. Until what time can we eat them?"],
      ["Baby + rice", "Can I give my baby the rice I cooked 5 hours ago? It was out of the fridge."],
      ["Power outage", "The power went out at 06:00. I haven't opened the fridge and the freezer is full. What do I do?"],
      ["Shelter (120 people)", "I run a shelter with 120 people. Lunch is 13:00 to 15:00, rice and beans, no way to keep food hot."],
      ["Plan meals", "We are 5 at home, lunch at 14:00 and dinner at 20:00. When should I cook?"],
      ["Danger signs", "My 2-year-old daughter has diarrhea, she is very sleepy and barely drinks. We are in Mexico."],
      ["Reminder", "I cooked chicken at 12:00. Schedule a reminder so we eat it in time."],
    ],
  },
};

const state = {
  lang: (navigator.language || "es").toLowerCase().startsWith("es") ? "es" : "en",
  mode: "demo",
  sessionId: newSessionId(),
  coords: null,
  seenReminders: new Set(),
  busy: false,
};

function newSessionId() {
  const rnd = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now());
  return `web-${rnd}-${Date.now()}`; // >= 33 chars (AgentCore requirement)
}

const $ = (sel) => document.querySelector(sel);
const t = (key) => I18N[state.lang][key];

function render() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("#prompt").placeholder = t("placeholder");
  document.querySelectorAll("[data-lang]").forEach((b) => b.classList.toggle("active", b.dataset.lang === state.lang));
  document.querySelectorAll("[data-mode]").forEach((b) => b.classList.toggle("active", b.dataset.mode === state.mode));
  const banner = $("#banner");
  banner.textContent = state.mode === "demo" ? t("bannerDemo") : t("bannerLive");
  banner.classList.toggle("live", state.mode === "live");
  const box = $("#scenario-buttons");
  box.innerHTML = "";
  for (const [label, prompt] of t("scenarios")) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.title = prompt;
    b.addEventListener("click", () => send(prompt));
    box.appendChild(b);
  }
}

function addMessage(kind, text, extra) {
  const div = document.createElement("div");
  div.className = `msg ${kind}`;
  div.textContent = text;
  if (extra) div.appendChild(extra);
  $("#chat").appendChild(div);
  div.scrollIntoView({ behavior: "smooth", block: "end" });
  return div;
}

function botMeta(answer, metrics) {
  const meta = document.createElement("div");
  meta.className = "meta";
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = t("listen");
  btn.addEventListener("click", () => speak(answer, btn));
  meta.appendChild(btn);
  if (metrics && metrics.api_ms) {
    const span = document.createElement("span");
    span.textContent = `${(metrics.api_ms / 1000).toFixed(1)} s · ${(metrics.tools_used || []).join(", ") || "—"}`;
    meta.appendChild(span);
  }
  return meta;
}

async function api(path, options) {
  const res = await fetch(path, { headers: { "content-type": "application/json" }, ...options });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

async function send(prompt) {
  prompt = (prompt || "").trim();
  if (!prompt || state.busy) return;
  state.busy = true;
  $("#send").disabled = true;
  addMessage("user", prompt);
  const typing = addMessage("bot typing", t("thinking"));
  if (/recordatorio|reminder/i.test(prompt) && "Notification" in window && Notification.permission === "default") {
    Notification.requestPermission().catch(() => {});
  }
  const body = {
    prompt, language: state.lang, session_id: state.sessionId, demo: state.mode === "demo",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    ...(state.mode === "live" && state.coords ? { lat: state.coords.lat, lon: state.coords.lon } : {}),
  };
  try {
    const { data } = await api("/api/chat", { method: "POST", body: JSON.stringify(body) });
    typing.remove();
    const answer = data.answer || t("error");
    const msg = addMessage(data.error ? "bot error" : "bot", answer, botMeta(answer, data.metrics));
    if (data.error) msg.title = data.error;
  } catch (e) {
    typing.remove();
    addMessage("bot error", t("error"));
  } finally {
    state.busy = false;
    $("#send").disabled = false;
  }
}

async function speak(text, btn) {
  btn.disabled = true;
  try {
    const { ok, data } = await api("/api/voice", { method: "POST", body: JSON.stringify({ text, language: state.lang }) });
    if (ok && data.audio_base64) await new Audio(`data:audio/mpeg;base64,${data.audio_base64}`).play();
  } finally { btn.disabled = false; }
}

async function pollReminders() {
  try {
    const { ok, data } = await api(`/api/reminders?session_id=${encodeURIComponent(state.sessionId)}`, { method: "GET" });
    if (!ok) return;
    for (const r of data.reminders || []) {
      if (state.seenReminders.has(r.reminder_id)) continue;
      state.seenReminders.add(r.reminder_id);
      const text = `${t("reminder")} (${r.at_local}): ${r.message}`;
      addMessage("reminder", text);
      if ("Notification" in window && Notification.permission === "granted") new Notification("Al Tiempo", { body: text });
    }
  } catch (e) { /* offline: try again later */ }
}

function setMode(mode) {
  state.mode = mode;
  state.sessionId = newSessionId(); // new conversation when switching mode
  if (mode === "live" && !state.coords && navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (p) => { state.coords = { lat: +p.coords.latitude.toFixed(2), lon: +p.coords.longitude.toFixed(2) }; },
      () => { state.coords = null; }, { timeout: 8000, maximumAge: 3600000 });
  }
  render();
}

document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => { state.lang = b.dataset.lang; state.sessionId = newSessionId(); render(); }));
document.querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
$("#form").addEventListener("submit", (e) => { e.preventDefault(); const v = $("#prompt").value; $("#prompt").value = ""; send(v); });
$("#prompt").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#form").requestSubmit(); } });

render();
setInterval(pollReminders, 15000);
