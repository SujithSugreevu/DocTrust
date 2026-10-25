/**
 * DocTrust System Settings Service
 * Handles communication with the /api/admin/system-settings/ endpoints.
 */

import { getCsrfToken } from './auth.js'
import { fetchWithTabSession } from './tabSession.js'

/**
 * Fetch all system settings along with live health and capability indicators.
 * @returns {Promise<Object>}
 */
export async function getSystemSettings() {
  const response = await fetchWithTabSession('/api/admin/system-settings/', {
    method: 'GET',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  })

  if (response.status === 401 || response.status === 403) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Administrative privileges required.')
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `Failed to fetch system settings (HTTP ${response.status}).`)
  }

  return response.json()
}

/**
 * Update system settings partially (PATCH).
 * @param {Object} partialUpdates - Key-value map of changed fields
 * @returns {Promise<Object>} Updated settings object
 */
export async function updateSystemSettings(partialUpdates) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })

  const response = await fetchWithTabSession('/api/admin/system-settings/', {
    method: 'PATCH',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify(partialUpdates),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    // If backend returned field-specific errors
    if (response.status === 400) {
      const error = new Error('Validation failed.')
      error.fieldErrors = data
      throw error
    }
    throw new Error(data.detail || `Failed to save system settings (HTTP ${response.status}).`)
  }

  return data
}

/**
 * Reset all system settings to safe defaults.
 * @returns {Promise<Object>} Default settings object
 */
export async function resetSystemSettings() {
  const csrfToken = await getCsrfToken({ forceRefresh: true })

  const response = await fetchWithTabSession('/api/admin/system-settings/reset/', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      'X-CSRFToken': csrfToken,
    },
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.detail || `Failed to reset system settings (HTTP ${response.status}).`)
  }

  return data
}
