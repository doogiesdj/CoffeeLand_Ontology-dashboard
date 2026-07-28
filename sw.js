const CACHE_NAME = 'coffeeland-dashboard-v2';
const PRECACHE_URLS = [
  './dashboard.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

// Network-first for same-origin requests so data/dashboard updates are picked up
// as soon as they're online, with an offline cache fallback.
//
// cache: 'no-cache' forces this fetch to revalidate with the server (conditional
// GET) instead of silently returning whatever GitHub Pages' Cache-Control:
// max-age=600 has sitting in the browser's HTTP cache. Without this, "network-first"
// wasn't actually reaching the network for up to 10 minutes after each deploy,
// so updates could take a while to show up even though the site itself was live.
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    fetch(request, { cache: 'no-cache' })
      .then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        return response;
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match('./dashboard.html')))
  );
});
