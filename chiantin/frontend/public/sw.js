/* Service Worker for Chiantin PWA */
/* WebView-safe with minimal caching */

const CACHE_NAME = 'chiantin-pwa-v3';

// Minimal shell for offline support - only static assets
const SHELL_FILES = [
  '/offline.html',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

// Detect if this is likely a WebView (limited detection in SW context)
const isLikelyWebView = () => {
  // In service worker, we have limited access - check clients if possible
  return false; // Default to false, let the main thread handle WebView detection
};

// Install: cache minimal shell, skip waiting immediately
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Chiantin service worker v3...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching minimal shell');
        // Use individual catches to not fail entire install if one asset fails
        return Promise.allSettled(
          SHELL_FILES.map(file => 
            cache.add(file).catch(err => console.warn('[SW] Failed to cache:', file, err))
          )
        );
      })
      .then(() => {
        console.log('[SW] Skip waiting');
        return self.skipWaiting();
      })
      .catch(err => {
        console.warn('[SW] Install error:', err);
      })
  );
});

// Activate: cleanup old caches, take control immediately
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name.startsWith('Chiantin-') && name !== CACHE_NAME)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[SW] Claiming clients');
        return self.clients.claim();
      })
      .catch(err => {
        console.warn('[SW] Activate error:', err);
      })
  );
});

// Fetch: Network-first for everything, minimal caching
self.addEventListener('fetch', (event) => {
  const { request } = event;
  
  try {
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
      return;
    }

    // Skip cross-origin requests
    if (url.origin !== location.origin) {
      return;
    }

    // Never cache API calls
    if (url.pathname.startsWith('/api')) {
      event.respondWith(
        fetch(request).catch(() => {
          return new Response(JSON.stringify({ error: 'Network error' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          });
        })
      );
      return;
    }

    // Navigation requests: network-first, fallback to offline page
    if (request.mode === 'navigate') {
      event.respondWith(
        fetch(request)
          .catch(() => {
            console.log('[SW] Network failed for navigation, serving offline page');
            return caches.match('/offline.html').then(response => {
              return response || new Response('Offline', { status: 503 });
            });
          })
      );
      return;
    }

    // Static assets (icons only): cache with network fallback
    if (url.pathname.startsWith('/icons/')) {
      event.respondWith(
        caches.match(request)
          .then((cachedResponse) => {
            if (cachedResponse) {
              // Return cached, but also update cache in background
              fetch(request)
                .then((response) => {
                  if (response.ok) {
                    caches.open(CACHE_NAME)
                      .then((cache) => cache.put(request, response));
                  }
                })
                .catch(() => {});
              return cachedResponse;
            }
            return fetch(request);
          })
          .catch(() => caches.match(request))
      );
      return;
    }

    // All other requests: network only, no caching
    // This prevents stale JS/CSS bundles from being served
    event.respondWith(
      fetch(request).catch(() => {
        // For HTML-like requests, try offline page
        if (request.headers.get('accept')?.includes('text/html')) {
          return caches.match('/offline.html');
        }
        return new Response('Network error', { status: 503 });
      })
    );
  } catch (err) {
    console.warn('[SW] Fetch handler error:', err);
  }
});

// Handle messages from the app
self.addEventListener('message', (event) => {
  try {
    if (event.data === 'skipWaiting') {
      self.skipWaiting();
    }
    if (event.data === 'clearCache') {
      caches.keys().then(names => {
        names.forEach(name => caches.delete(name));
      });
    }
  } catch (err) {
    console.warn('[SW] Message handler error:', err);
  }
});

// Log any errors
self.addEventListener('error', (event) => {
  console.error('[SW] Error:', event.error);
});

self.addEventListener('unhandledrejection', (event) => {
  console.error('[SW] Unhandled rejection:', event.reason);
});
