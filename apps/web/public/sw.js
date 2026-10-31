// Service Worker for RSUKT AI Clinical Suite (PWA & MWA)
// Versi 2: Kepatuhan UU PDP No. 27/2022 & ISO 27001 - Nol Cache untuk Data Klinis/Chat Pasien
const CACHE_NAME = 'rsukt-ai-v2';
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Hanya proses GET
  if (event.request.method !== 'GET') return;

  const url = event.request.url;
  const acceptHeader = event.request.headers.get('accept') || '';

  // 1. Bypass Service Worker secara mutlak untuk SSE streams, chat endpoints, auth, dan data klinis pasien
  // Kebijakan UU PDP: Data rekam medis dan dialog konsultasi dilarang disimpan di local HTTP cache storage
  const isChatOrPrivateData =
    url.includes('/api/v1/chat') ||
    url.includes('/chat/sessions') ||
    url.includes('/chat/messages') ||
    url.includes('/chat/quota') ||
    url.includes('/chat/feedback') ||
    url.includes('/api/v1/auth') ||
    url.includes('/stream') ||
    url.includes('/realtime') ||
    acceptHeader.includes('text/event-stream');

  if (isChatOrPrivateData) {
    // Selalu teruskan langsung ke network tanpa cache intercept
    event.respondWith(fetch(event.request));
    return;
  }

  // 2. API lainnya: Network-only tanpa menyimpan ke Cache Storage
  if (url.includes('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // 3. Stale-while-revalidate khusus static app shell dan ikon (non-data)
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (
          networkResponse &&
          networkResponse.status === 200 &&
          networkResponse.type === 'basic' &&
          !url.includes('/chat')
        ) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
