/* Offline support: pictures and the page shell are cached; news data is always fetched fresh when online. */
const CACHE = 'news-desk-v6';
self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./', 'index.html', 'shim.js', 'manifest.webmanifest', 'icon-192.png']))); self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); });
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.includes('/img/')) {                 // pictures never change: cache first
    e.respondWith(caches.open(CACHE).then(c => c.match(e.request).then(hit => hit || fetch(e.request).then(r => { if (r.ok) c.put(e.request, r.clone()); return r; }))));
    return;
  }
  // everything else: network first, always asking the server whether there is a newer version (GitHub lets browsers keep pages 10 minutes)
  e.respondWith(fetch(e.request, { cache: 'no-cache' }).then(r => {
    if (r.ok && !url.pathname.includes('/data/')) caches.open(CACHE).then(c => c.put(e.request, r.clone()));
    return r;
  }).catch(() => caches.match(e.request, { ignoreSearch: true })));
});
