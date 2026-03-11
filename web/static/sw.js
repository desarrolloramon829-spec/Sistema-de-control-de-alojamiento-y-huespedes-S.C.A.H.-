const STATIC_CACHE = 'scah-static-v2';
const RUNTIME_CACHE = 'scah-runtime-v2';
const OFFLINE_URL = '/static/offline.html';
const MODULE_FALLBACKS = {
  '/dashboard': '/static/offline-dashboard.html',
  '/huespedes': '/static/offline-guests.html',
  '/importar': '/static/offline-imports.html',
};

const PRECACHE_URLS = [
  OFFLINE_URL,
  '/static/offline-dashboard.html',
  '/static/offline-guests.html',
  '/static/offline-imports.html',
  '/static/manifest.json',
  '/static/css/custom.css',
  '/static/js/app.js',
  '/static/img/icon-app.svg',
  '/static/img/icon-maskable.svg',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches
      .keys()
      .then(keys =>
        Promise.all(
          keys
            .filter(key => ![STATIC_CACHE, RUNTIME_CACHE].includes(key))
            .map(key => caches.delete(key))
        )
      )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const { request } = event;

  if (request.method !== 'GET') {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(request));
    return;
  }

  const url = new URL(request.url);
  const isStaticAsset =
    url.origin === self.location.origin && url.pathname.startsWith('/static/');
  const isCdnAsset = url.origin !== self.location.origin;

  if (isStaticAsset || isCdnAsset) {
    event.respondWith(cacheFirst(request));
  }
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || '/alertas/';
  event.waitUntil(
    clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        for (const client of windowClients) {
          if ('focus' in client) {
            client.navigate(targetUrl);
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(targetUrl);
        }
      })
  );
});

async function networkFirstNavigation(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(RUNTIME_CACHE);
    cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    return caches.match(resolveOfflineFallback(request.url));
  }
}

function resolveOfflineFallback(requestUrl) {
  const pathname = new URL(requestUrl).pathname;

  for (const prefix in MODULE_FALLBACKS) {
    if (pathname.startsWith(prefix)) {
      return MODULE_FALLBACKS[prefix];
    }
  }

  return OFFLINE_URL;
}

async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  const response = await fetch(request);
  const cache = await caches.open(RUNTIME_CACHE);
  cache.put(request, response.clone());
  return response;
}
