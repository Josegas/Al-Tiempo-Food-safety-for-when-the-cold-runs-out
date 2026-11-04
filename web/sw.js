// Al Tiempo service worker: the page opens without signal and shows the basic safety rules.
// Network first for the page itself (online = always the latest deploy), cache only as fallback.
// The API (/api/*) is never cached: answers, reminders and voice always come from the server.
const CACHE = "al-tiempo-v1";
const SHELL = [
  "./", "index.html", "app.js", "styles.css", "manifest.json",
  "fonts/atkinson-regular.woff2", "fonts/atkinson-bold.woff2",
  "fonts/fraunces-display.woff2", "fonts/altiempo-mono-medium.woff2",
  "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req, { ignoreSearch: true })
        .then((hit) => hit || (req.mode === "navigate" ? caches.match("index.html") : Response.error()))),
  );
});
