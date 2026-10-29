/**
 * Resolve API requests for both same-origin rewrites and separately hosted
 * frontends. Leave the value unset when Vercel's /api rewrite or Vite's local
 * proxy is configured; set VITE_API_BASE_URL to a direct backend /api URL for
 * a Render static frontend.
 */
const configuredBase = String(import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
const apiRoot = configuredBase
  ? (configuredBase.endsWith('/api') ? configuredBase : `${configuredBase}/api`)
  : ''

export function apiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  if (!apiRoot) return normalizedPath
  const backendPath = normalizedPath.startsWith('/api')
    ? normalizedPath.slice('/api'.length)
    : normalizedPath
  return `${apiRoot}${backendPath || '/'}`
}
