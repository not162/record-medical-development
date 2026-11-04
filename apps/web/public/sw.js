// Service Worker - Web Klinik (PWA)
// v3: offline fallback, cache-first untuk aset statis immutable,
// dan NOL cache untuk data klinis/chat/auth (UU PDP No. 27/2022).
const VERSION = 'klinik-v3';
const STATIC_CACHE = `${VERSION}-static`;
const OFFLINE_URL = '/offline.html';
const PRECACHE = [
  OFFLINE_URL,
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/icon-maskable-192.png',
  '/icons/icon-maskable-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});

function isStaticAsset(url) {
  return (
    url.pathname.startsWith('/_next/static/') ||
    url.pathname.startsWith('/icons/') ||
    /\.(?:woff2?|ttf|otf|png|jpg|jpeg|svg|webp|ico)$/.test(url.pathname)
  );
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return; // POST/PUT/PATCH/DELETE selalu langsung ke jaringan

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // API, SSE, dan data privat: jangan disentuh sama sekali (tidak pernah dicache)
  if (
    url.pathname.startsWith('/api/') ||
    (req.headers.get('accept') || '').includes('text/event-stream')
  ) {
    return;
  }

  // Navigasi halaman: network-first, fallback ke halaman offline. HTML tidak dicache
  // karena halaman chat/admin/profil dapat berisi data pribadi.
  if (req.mode === 'navigate') {
    event.respondWith(fetch(req).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  // Aset statis ber-hash: cache-first
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(req).then(
        (cached) =>
          cached ||
          fetch(req).then((res) => {
            if (res && res.status === 200 && res.type === 'basic') {
              const copy = res.clone();
              caches.open(STATIC_CACHE).then((c) => c.put(req, copy));
            }
            return res;
          })
      )
    );
  }
});
