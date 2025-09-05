# Create sw.js (basic service worker)
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open('tiktok-clone-v1').then(cache => {
      return cache.addAll([
        '/',
        '/feed',
        '/upload',
        '/explore'
      ]);
    })
  );
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(response => {
      return response || fetch(e.request);
    })
  );
});
