/* The Harbour Chronicle — keep the leaf in hand when the wire is down. */
const VERSION = "chronicle-v1";
const SHELL = [
  "./",
  "./index.html",
  "./world.html",
  "./hong-kong.html",
  "./business.html",
  "./sport.html",
  "./culture.html",
  "./science.html",
  "./opinion.html",
  "./article.html",
  "./about.html",
  "./404.html",
  "./css/press.css",
  "./css/desks.css",
  "./js/press.js",
  "./js/edition.js",
  "./data/news.json",
  "./assets/crest.svg",
  "./assets/images/paper-rag.jpg",
  "./assets/images/paper-warm.jpg",
  "./assets/images/paper-cool.jpg",
  "./assets/images/paper-science.jpg",
  "./assets/images/plate-grain.png",
  "./assets/images/plate-fallback.jpg",
  "./assets/icons/icon-192.png",
  "./assets/icons/icon-512.png",
  "./manifest.webmanifest"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

function isEdition(url) {
  return /\/(js\/edition\.js|data\/news\.json)$/.test(url.pathname);
}

function isShell(url) {
  return url.origin === self.location.origin;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  let url;
  try { url = new URL(req.url); } catch (e) { return; }

  // Fresh news when the wire is up; last good leaf when it is not.
  if (isShell(url) && isEdition(url)) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(VERSION).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  if (isShell(url)) {
    event.respondWith(
      caches.match(req).then((hit) => {
        const fetched = fetch(req)
          .then((res) => {
            if (res && res.ok) {
              const copy = res.clone();
              caches.open(VERSION).then((c) => c.put(req, copy));
            }
            return res;
          })
          .catch(() => hit);
        return hit || fetched;
      })
    );
  }
});
