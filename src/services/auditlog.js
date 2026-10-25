/**
 * DocTrust Audit Log Service
 * Handles communication with the /api/audit/ endpoints.
 */

import { getCsrfToken } from './auth.js'
import { fetchWithTabSession } from './tabSession.js'

const API_BASE = '/api/audit'

/**
 * Build query string from filter params object.
 * Skips empty/null/undefined values.
 */
function buildQueryString(params) {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.set(key, String(value))
    }
  }
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

/**
 * Fetch paginated audit events for a given role tab.
 * @param {'admin'|'employee'} role
 * @param {Object} filters - { search, start_date, end_date, user, action_type, outcome, page, page_size }
 * @returns {Promise<{ results: Array, total_count: number, page: number, page_size: number, total_pages: number }>}
 */
export async function getAuditEvents(role, filters = {}) {
  const url = `${API_BASE}/${role}/${buildQueryString(filters)}`

  const response = await fetchWithTabSession(url, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (response.status === 401 || response.status === 403) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'Administrative privileges required.')
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || `Failed to fetch audit events (HTTP ${response.status}).`)
  }

  return response.json()
}

/**
 * Fetch a single audit event detail.
 * @param {number} eventId
 * @returns {Promise<Object>}
 */
export async function getAuditEventDetail(eventId) {
  const response = await fetchWithTabSession(`${API_BASE}/events/${eventId}/`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || `Failed to fetch event detail (HTTP ${response.status}).`)
  }

  return response.json()
}

/**
 * Export audit events to CSV. Returns a Blob download.
 * @param {'admin'|'employee'} role
 * @param {Object} filters - Same filter params as getAuditEvents
 */
export async function exportAuditCSV(role, filters = {}) {
  const url = `${API_BASE}/${role}/export/${buildQueryString(filters)}`

  const response = await fetchWithTabSession(url, {
    method: 'GET',
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error(`Failed to export audit logs (HTTP ${response.status}).`)
  }

  const blob = await response.blob()
  const contentDisposition = response.headers.get('Content-Disposition') || ''
  const filenameMatch = contentDisposition.match(/filename="?(.+?)"?$/)
  const filename = filenameMatch ? filenameMatch[1] : `doctrust_${role}_audit.csv`

  // Trigger browser download
  const downloadUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(downloadUrl)
}

/**
 * Fetch available action types for filter dropdown.
 * @returns {Promise<Array<{ value: string, label: string }>>}
 */
export async function getActionTypes() {
  const response = await fetchWithTabSession(`${API_BASE}/action-types/`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || `Failed to load audit action types (HTTP ${response.status}).`)
  }

  const data = await response.json()
  return data.action_types || []
}

/**
 * Fetch distinct actor usernames for user filter dropdown.
 * @param {string} [role] - Optional role filter ('ADMIN' or 'EMPLOYEE')
 * @returns {Promise<string[]>}
 */
export async function getAuditUsers(role) {
  const params = role ? `?role=${role}` : ''
  const response = await fetchWithTabSession(`${API_BASE}/users/${params}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || `Failed to load audit users (HTTP ${response.status}).`)
  }

  const data = await response.json()
  return data.users || []
}

/**
 * Fetch security alerts with optional filters.
 * @param {Object} filters - { scope, status, severity, search }
 */
export async function getSecurityAlerts(filters = {}) {
  const url = `${API_BASE}/security-alerts/${buildQueryString(filters)}`
  const response = await fetchWithTabSession(url, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to fetch security alerts.')
  }

  return response.json()
}

/**
 * Resolve or reopen a security alert.
 * @param {number} alertId
 */
export async function resolveSecurityAlert(alertId) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession(`${API_BASE}/security-alerts/${alertId}/resolve/`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to update alert resolution.')
  }

  return response.json()
}

/**
 * Fetch live administrator dashboard stats, charts, recent activities and alerts.
 * @param {string} range - 'Today' | '7 days' | '30 days' | '90 days'
 */
export async function getDashboardStats(range = '7 days') {
  const qs = range ? `?range=${encodeURIComponent(range)}` : ''
  const response = await fetchWithTabSession(`${API_BASE}/dashboard-stats/${qs}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to load dashboard statistics.')
  }

  return response.json()
}

/**
 * Fetch activity summary metrics (total events, success rate, active users count).
 */
export async function getActivitySummary() {
  const response = await fetchWithTabSession(`${API_BASE}/activity-summary/`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || `Failed to load activity summary (HTTP ${response.status}).`)
  }

  return response.json()
}

/**
 * Fetch document overview records with administrative permission enforcement.
 * @param {Object} filters - { search, status }
 */
export async function getDocumentOverview(filters = {}) {
  const url = `${API_BASE}/documents-overview/${buildQueryString(filters)}`
  const response = await fetchWithTabSession(url, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to load document overview.')
  }

  return response.json()
}
