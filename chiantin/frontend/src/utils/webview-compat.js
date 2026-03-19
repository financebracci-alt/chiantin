/**
 * WebView Polyfills & Compatibility Layer
 * Ensures the app works in restricted environments like Telegram, Instagram, Facebook WebViews
 */

// ============================================
// 1. BROWSER DETECTION UTILITIES
// ============================================

/**
 * Detect if running in a restricted in-app browser/WebView
 */
export const isRestrictedBrowser = () => {
  try {
    if (typeof window === 'undefined' || typeof navigator === 'undefined') {
      return true; // Server-side or no window - be safe
    }
    
    const ua = navigator.userAgent || '';
    
    // In-app browser detection patterns
    const inAppPatterns = [
      'FBAN',           // Facebook App
      'FBAV',           // Facebook App Version
      'Instagram',      // Instagram
      'Twitter',        // Twitter
      'TelegramBot',    // Telegram Bot
      'Telegram',       // Telegram
      'Line/',          // Line
      'KAKAOTALK',      // KakaoTalk
      'WhatsApp',       // WhatsApp
      'Snapchat',       // Snapchat
      'Pinterest',      // Pinterest
      'LinkedIn',       // LinkedIn
      'Slack',          // Slack
      'Discord',        // Discord
    ];
    
    // Check UA string patterns
    const isInAppUA = inAppPatterns.some(pattern => ua.includes(pattern));
    
    // Check for generic WebView indicators
    const isAndroidWebView = ua.includes('wv') && ua.includes('Android');
    const isIOSWebView = /(iPhone|iPod|iPad).*AppleWebKit(?!.*Safari)/i.test(ua);
    
    // Check for Telegram-specific objects
    const hasTelegramObjects = 
      typeof window.TelegramWebviewProxy !== 'undefined' ||
      typeof window.Telegram !== 'undefined' ||
      typeof window.TelegramWebviewProxyProto !== 'undefined';
    
    return isInAppUA || isAndroidWebView || isIOSWebView || hasTelegramObjects;
  } catch (e) {
    // If detection fails, assume restricted for safety
    return true;
  }
};

/**
 * Check if service worker should be enabled
 */
export const shouldEnableServiceWorker = () => {
  try {
    if (typeof navigator === 'undefined') return false;
    if (!('serviceWorker' in navigator)) return false;
    if (isRestrictedBrowser()) return false;
    return true;
  } catch (e) {
    return false;
  }
};

// ============================================
// 2. POLYFILLS FOR MISSING APIS
// ============================================

/**
 * Apply all necessary polyfills for WebView compatibility
 */
export const applyPolyfills = () => {
  try {
    // ---- crypto.randomUUID polyfill ----
    if (typeof crypto !== 'undefined' && !crypto.randomUUID) {
      crypto.randomUUID = function() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
          const r = Math.random() * 16 | 0;
          const v = c === 'x' ? r : (r & 0x3 | 0x8);
          return v.toString(16);
        });
      };
    }
    
    // ---- crypto.getRandomValues polyfill (basic fallback) ----
    if (typeof crypto === 'undefined') {
      window.crypto = {};
    }
    if (typeof crypto.getRandomValues !== 'function') {
      crypto.getRandomValues = function(array) {
        for (let i = 0; i < array.length; i++) {
          array[i] = Math.floor(Math.random() * 256);
        }
        return array;
      };
    }
    
    // ---- structuredClone polyfill ----
    if (typeof structuredClone !== 'function') {
      window.structuredClone = function(obj) {
        try {
          return JSON.parse(JSON.stringify(obj));
        } catch (e) {
          // Fallback for circular references or non-serializable data
          return obj;
        }
      };
    }
    
    // ---- TextEncoder/TextDecoder polyfill ----
    if (typeof TextEncoder === 'undefined') {
      window.TextEncoder = class TextEncoder {
        encode(str) {
          const utf8 = unescape(encodeURIComponent(str));
          const result = new Uint8Array(utf8.length);
          for (let i = 0; i < utf8.length; i++) {
            result[i] = utf8.charCodeAt(i);
          }
          return result;
        }
      };
    }
    
    if (typeof TextDecoder === 'undefined') {
      window.TextDecoder = class TextDecoder {
        decode(bytes) {
          let str = '';
          for (let i = 0; i < bytes.length; i++) {
            str += String.fromCharCode(bytes[i]);
          }
          return decodeURIComponent(escape(str));
        }
      };
    }
    
    // ---- URL polyfill check ----
    // Most WebViews support URL, but ensure URLSearchParams works
    if (typeof URLSearchParams === 'undefined') {
      window.URLSearchParams = class URLSearchParams {
        constructor(init) {
          this._params = {};
          if (typeof init === 'string') {
            init.replace(/^\?/, '').split('&').forEach(pair => {
              const [key, value] = pair.split('=');
              if (key) {
                this._params[decodeURIComponent(key)] = decodeURIComponent(value || '');
              }
            });
          }
        }
        get(name) { return this._params[name] || null; }
        set(name, value) { this._params[name] = String(value); }
        has(name) { return name in this._params; }
        delete(name) { delete this._params[name]; }
        toString() {
          return Object.entries(this._params)
            .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
            .join('&');
        }
      };
    }
    
    // ---- globalThis polyfill ----
    if (typeof globalThis === 'undefined') {
      window.globalThis = window;
    }
    
    // ---- Array.prototype.at polyfill ----
    if (!Array.prototype.at) {
      Array.prototype.at = function(index) {
        const len = this.length;
        const relativeIndex = Number(index);
        const k = relativeIndex >= 0 ? relativeIndex : len + relativeIndex;
        return (k < 0 || k >= len) ? undefined : this[k];
      };
    }
    
    // ---- String.prototype.replaceAll polyfill ----
    if (!String.prototype.replaceAll) {
      String.prototype.replaceAll = function(search, replace) {
        return this.split(search).join(replace);
      };
    }
    
    // ---- Object.hasOwn polyfill ----
    if (!Object.hasOwn) {
      Object.hasOwn = function(obj, prop) {
        return Object.prototype.hasOwnProperty.call(obj, prop);
      };
    }
    
    // ---- Promise.allSettled polyfill ----
    if (!Promise.allSettled) {
      Promise.allSettled = function(promises) {
        return Promise.all(
          promises.map(p =>
            Promise.resolve(p)
              .then(value => ({ status: 'fulfilled', value }))
              .catch(reason => ({ status: 'rejected', reason }))
          )
        );
      };
    }
    
    // ---- queueMicrotask polyfill ----
    if (typeof queueMicrotask !== 'function') {
      window.queueMicrotask = function(callback) {
        Promise.resolve().then(callback).catch(e => 
          setTimeout(() => { throw e; }, 0)
        );
      };
    }
    
    console.log('[Polyfills] Applied WebView compatibility polyfills');
  } catch (e) {
    console.warn('[Polyfills] Error applying polyfills:', e);
  }
};

// ============================================
// 3. GLOBAL ERROR HANDLING
// ============================================

/**
 * Setup global error capturing for debugging in restricted environments
 */
export const setupGlobalErrorHandling = () => {
  try {
    const errorLog = [];
    const MAX_ERRORS = 50;
    
    // Capture runtime errors
    const originalOnError = window.onerror;
    window.onerror = function(message, source, lineno, colno, error) {
      const errorInfo = {
        type: 'runtime',
        message: String(message),
        source: source,
        line: lineno,
        column: colno,
        stack: error?.stack || 'No stack',
        userAgent: navigator.userAgent,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        isRestrictedBrowser: isRestrictedBrowser()
      };
      
      errorLog.push(errorInfo);
      if (errorLog.length > MAX_ERRORS) errorLog.shift();
      
      console.error('[GlobalError] Runtime error:', errorInfo);
      
      // Call original handler if exists
      if (typeof originalOnError === 'function') {
        return originalOnError.apply(this, arguments);
      }
      
      // Return true to prevent default browser error handling in WebViews
      // This can help avoid the generic "Script error" message
      return true;
    };
    
    // Capture unhandled promise rejections
    window.addEventListener('unhandledrejection', function(event) {
      const errorInfo = {
        type: 'unhandledrejection',
        message: event.reason?.message || String(event.reason),
        stack: event.reason?.stack || 'No stack',
        userAgent: navigator.userAgent,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        isRestrictedBrowser: isRestrictedBrowser()
      };
      
      errorLog.push(errorInfo);
      if (errorLog.length > MAX_ERRORS) errorLog.shift();
      
      console.error('[GlobalError] Unhandled rejection:', errorInfo);
      
      // Prevent the error from bubbling up in WebViews
      event.preventDefault();
    });
    
    // Expose error log for debugging
    window.__APP_ERROR_LOG__ = errorLog;
    window.__GET_ERROR_LOG__ = () => JSON.stringify(errorLog, null, 2);
    
    console.log('[GlobalError] Error handling initialized. Access via window.__GET_ERROR_LOG__()');
  } catch (e) {
    console.warn('[GlobalError] Failed to setup error handling:', e);
  }
};

// ============================================
// 4. SERVICE WORKER MANAGEMENT
// ============================================

/**
 * Conditionally register service worker (not in restricted browsers)
 */
export const registerServiceWorkerSafe = () => {
  try {
    if (!shouldEnableServiceWorker()) {
      console.log('[SW] Service Worker disabled (restricted browser or unsupported)');
      return Promise.resolve(null);
    }
    
    return new Promise((resolve) => {
      window.addEventListener('load', () => {
        navigator.serviceWorker
          .register('/sw.js', { scope: '/' })
          .then((registration) => {
            console.log('[SW] Service Worker registered:', registration.scope);
            resolve(registration);
          })
          .catch((error) => {
            console.warn('[SW] Service Worker registration failed:', error);
            resolve(null);
          });
      });
    });
  } catch (e) {
    console.warn('[SW] Error registering service worker:', e);
    return Promise.resolve(null);
  }
};

/**
 * Unregister all service workers (useful for clearing stale caches)
 */
export const unregisterAllServiceWorkers = async () => {
  try {
    if (!('serviceWorker' in navigator)) return;
    
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (const registration of registrations) {
      await registration.unregister();
      console.log('[SW] Unregistered service worker');
    }
  } catch (e) {
    console.warn('[SW] Error unregistering service workers:', e);
  }
};

// ============================================
// 5. INITIALIZATION
// ============================================

/**
 * Initialize all WebView compatibility features
 * Call this at the very start of your app, before React renders
 */
export const initWebViewCompatibility = () => {
  try {
    // 1. Apply polyfills first (before any other code runs)
    applyPolyfills();
    
    // 2. Setup global error handling
    setupGlobalErrorHandling();
    
    // 3. Register service worker conditionally
    registerServiceWorkerSafe();
    
    // Log environment info
    console.log('[WebView] Compatibility initialized', {
      isRestrictedBrowser: isRestrictedBrowser(),
      serviceWorkerEnabled: shouldEnableServiceWorker(),
      userAgent: navigator.userAgent
    });
  } catch (e) {
    console.warn('[WebView] Initialization error:', e);
  }
};

export default {
  isRestrictedBrowser,
  shouldEnableServiceWorker,
  applyPolyfills,
  setupGlobalErrorHandling,
  registerServiceWorkerSafe,
  unregisterAllServiceWorkers,
  initWebViewCompatibility
};
