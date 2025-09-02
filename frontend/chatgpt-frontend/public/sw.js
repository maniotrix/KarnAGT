// Minimal service worker for PWA installability
const CACHE_NAME = 'karnagt-v1';

// Install - activate immediately
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

// Activate - take control immediately  
self.addEventListener('activate', (event) => {
  self.clients.claim();
});

// Fetch - basic pass-through (required for PWA)
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
