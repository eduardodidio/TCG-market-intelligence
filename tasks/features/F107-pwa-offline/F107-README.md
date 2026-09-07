# F107 - PWA & Offline Support

## Summary

Adds Progressive Web App (PWA) capabilities and offline support to the TEDHC Market frontend.

## Tasks

### Wave 0 - PWA Infrastructure

- **T01: manifest.json + icons** - Created `public/manifest.json` with app metadata, generated 192x192 and 512x512 placeholder PNG icons (slate-900 background with indigo "T"), added manifest link and meta tags to `index.html`.

- **T02: Service Worker (vite-plugin-pwa)** - Installed `vite-plugin-pwa`, configured workbox with `NetworkFirst` caching for API calls (24h TTL, 200 entries) and `CacheFirst` for images (7d TTL, 500 entries). Created `UpdatePrompt` component that notifies users of new versions.

### Wave 1 - Offline Data + Install Prompt

- **T03: Offline collection (IndexedDB)** - Installed `idb-keyval`, created `useOfflineCollection` hook that caches collection data to IndexedDB and falls back to cache when offline. Created `OfflineBanner` component that shows amber warning when `navigator.onLine` is false.

- **T04: Install prompt** - Created `InstallPrompt` component that captures `beforeinstallprompt` event and shows a discrete install banner to authenticated users. Respects 30-day dismiss cooldown and standalone detection.

## Files Created

- `frontend/public/manifest.json` - PWA manifest
- `frontend/public/icons/icon-192.png` - App icon 192x192
- `frontend/public/icons/icon-512.png` - App icon 512x512
- `frontend/src/components/UpdatePrompt.tsx` - SW update notification
- `frontend/src/components/OfflineBanner.tsx` - Offline status indicator
- `frontend/src/components/InstallPrompt.tsx` - PWA install prompt
- `frontend/src/hooks/useOfflineCollection.ts` - IndexedDB-backed collection cache

## Files Modified

- `frontend/index.html` - Added manifest link, theme-color, apple-mobile-web-app-capable
- `frontend/vite.config.ts` - Added VitePWA plugin with workbox config
- `frontend/package.json` - Added vite-plugin-pwa (dev), idb-keyval dependencies
- `frontend/src/vite-env.d.ts` - Added vite-plugin-pwa type reference
- `frontend/src/components/Layout.tsx` - Integrated OfflineBanner, InstallPrompt, UpdatePrompt
- `frontend/src/i18n/locales/en.json` - Added `pwa.*` keys
- `frontend/src/i18n/locales/pt-BR.json` - Added `pwa.*` keys

## Tests Created

- `frontend/tests/components/OfflineBanner.test.tsx` - 5 tests
- `frontend/tests/components/InstallPrompt.test.tsx` - 6 tests
- `frontend/tests/components/UpdatePrompt.test.tsx` - 5 tests
- `frontend/tests/hooks/useOfflineCollection.test.tsx` - 3 tests
- `frontend/tests/i18n/pwa-keys.test.tsx` - 4 tests

Total: 23 new tests, all passing.
