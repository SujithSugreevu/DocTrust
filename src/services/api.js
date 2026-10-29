/**
 * Resolve every browser request through the current frontend origin.
 *
 * Vite proxies /api locally and Vercel rewrites /api to Render in production.
 * Keeping the browser URL relative means CSRF and session cookies belong to
 * the frontend origin instead of relying on JavaScript reading a Render-domain
 * cookie or on a Vercel build-time API URL.
 */
export function apiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return normalizedPath
}
