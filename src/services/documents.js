/**
 * DocTrust Documents Service
 * Handles all document and folder API calls against the Django backend.
 * Uses session-based auth with CSRF tokens.
 */

import { getCsrfToken } from './auth.js'
import { fetchWithTabSession } from './tabSession.js'

const BASE = '/api/documents'

/**
 * Low-level fetch helper for JSON endpoints.
 * Throws an Error with a user-readable message on non-2xx responses.
 */
async function apiFetch(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const requiresCsrf = !['GET', 'HEAD', 'OPTIONS'].includes(method)
  const csrfToken = requiresCsrf ? await getCsrfToken({ forceRefresh: true }) : ''
  if (requiresCsrf && !csrfToken) {
    throw new Error('Unable to establish a secure session. Refresh the page and try again.')
  }
  const response = await fetchWithTabSession(url, {
    ...options,
    credentials: 'include',
    headers: {
      ...options.headers,
      ...(requiresCsrf ? { 'X-CSRFToken': csrfToken } : {}),
    },
  })

  if (response.status === 204) return null

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message =
      data.detail ||
      (data.errors && Object.values(data.errors).flat().join(' ')) ||
      (response.status === 404 ? 'Resource not found.' : `Unable to complete request (${response.status})`)
    throw new Error(message)
  }

  return data
}

// ─────────────────────────────────────────────────────────────────────────────
// Folder API
// ─────────────────────────────────────────────────────────────────────────────

/**
 * List all folders owned by the current user.
 * Returns array of { id, name, created_at, document_count }
 */
export async function listFolders() {
  return apiFetch(`${BASE}/folders/`)
}

/**
 * Create a new folder.
 * @param {string} name
 */
export async function createFolder(name) {
  return apiFetch(`${BASE}/folders/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

/**
 * Rename a folder.
 * @param {string} id   UUID of the folder
 * @param {string} name New name
 */
export async function renameFolder(id, name) {
  return apiFetch(`${BASE}/folders/${id}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

/**
 * Delete an empty folder.
 * @param {string} id UUID of the folder
 */
export async function deleteFolder(id) {
  return apiFetch(`${BASE}/folders/${id}/`, { method: 'DELETE' })
}

// ─────────────────────────────────────────────────────────────────────────────
// Document API
// ─────────────────────────────────────────────────────────────────────────────

/**
 * List documents with optional filters.
 * @param {object} params  Query params: status, search, folder, file_type, ordering, page, page_size
 * Returns { count, page, page_size, results: [...] }
 */
export async function listDocuments(params = {}) {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.search) qs.set('search', params.search)
  if (params.folder !== undefined) qs.set('folder', params.folder)
  if (params.file_type) qs.set('file_type', params.file_type)
  if (params.ordering) qs.set('ordering', params.ordering)
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  const query = qs.toString() ? `?${qs}` : ''
  return apiFetch(`${BASE}/${query}`)
}

/**
 * Upload a document. Sends multipart/form-data.
 * @param {File}   file         The File object
 * @param {object} meta         { name?, description?, folder? (UUID string or null) }
 * @param {function} onProgress Optional callback (not supported by fetch; reserved)
 */
export async function uploadDocument(file, meta = {}) {
  const body = new FormData()
  body.append('file', file)
  if (meta.name) body.append('name', meta.name)
  if (meta.description) body.append('description', meta.description)
  if (meta.folder) body.append('folder', meta.folder)

  return apiFetch(`${BASE}/`, {
    method: 'POST',
    body,
  })
}

/**
 * Get full metadata for a single document.
 * @param {string} id UUID
 */
export async function getDocument(id) {
  return apiFetch(`${BASE}/${id}/`)
}

/**
 * Update document name, description, or folder.
 * @param {string} id   UUID
 * @param {object} data { name?, description?, folder? (UUID or null) }
 */
export async function updateDocument(id, data) {
  return apiFetch(`${BASE}/${id}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/**
 * Trigger a browser download for a document.
 * Navigates to the download URL directly so the browser handles the stream.
 * @param {object} doc  Document object with id and name
 */
export async function downloadDocument(doc) {
  const response = await fetchWithTabSession(`${BASE}/${doc.id}/download/`, {
    credentials: 'include',
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || `Document download failed (HTTP ${response.status}).`)
  }

  const objectUrl = URL.createObjectURL(await response.blob())
  const anchor = window.document.createElement('a')
  anchor.href = objectUrl
  anchor.download = doc.name
  anchor.style.display = 'none'
  window.document.body.appendChild(anchor)
  anchor.click()
  window.document.body.removeChild(anchor)
  URL.revokeObjectURL(objectUrl)
}

/** Open the original document through the authorized inline-view endpoint. */
export async function viewDocument(doc) {
  const popup = typeof window !== 'undefined' && window.open ? window.open('', '_blank') : null
  if (popup) {
    popup.opener = null
  }
  try {
    const blob = await getDocumentViewBlob(doc)
    if (popup) {
      popup.location.href = URL.createObjectURL(blob)
    }
    return blob
  } catch (error) {
    if (popup) popup.close()
    throw error
  }
}

/** Fetch original document blob through authorized inline-view endpoint for preview display. */
export async function getDocumentViewBlob(doc) {
  const docId = doc?.id || doc?.rawDoc?.id
  if (!docId) {
    throw new Error('Invalid document ID for preview.')
  }
  const response = await fetchWithTabSession(`${BASE}/${docId}/view/`, {
    credentials: 'include',
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || `Document preview failed (HTTP ${response.status}).`)
  }
  return response.blob()
}

export async function getStorageUsage() {
  return apiFetch(`${BASE}/storage/`)
}

export async function listSharedDocuments() {
  return apiFetch(`${BASE}/shared/`)
}

export async function listShareRecipients() {
  return apiFetch(`${BASE}/share-recipients/`)
}

export async function listDocumentShares(id) {
  return apiFetch(`${BASE}/${id}/shares/`)
}

/** List all non-self access grants on the current employee's active documents. */
export async function listOwnedDocumentShares() {
  return apiFetch(`${BASE}/owned-shares/`)
}

export async function createDocumentShare(id, data) {
  return apiFetch(`${BASE}/${id}/shares/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
}

export async function updateDocumentShare(id, shareId, data) {
  return apiFetch(`${BASE}/${id}/shares/${shareId}/`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
}

export async function revokeDocumentShare(id, shareId) {
  return apiFetch(`${BASE}/${id}/shares/${shareId}/`, { method: 'DELETE' })
}

export async function listEmployeeActivity() {
  return apiFetch(`${BASE}/activity/`)
}

/** Return the authenticated employee's persisted notification inbox. */
export async function listEmployeeNotifications() {
  return apiFetch(`${BASE}/notifications/`)
}

/** Mark one notification as read. */
export async function markEmployeeNotificationRead(id) {
  return apiFetch(`${BASE}/notifications/${id}/read/`, { method: 'POST' })
}

/** Mark every unread notification for the signed-in employee as read. */
export async function markAllEmployeeNotificationsRead() {
  return apiFetch(`${BASE}/notifications/read-all/`, { method: 'POST' })
}

/**
 * Soft-delete a document.
 * @param {string} id UUID
 */
export async function deleteDocument(id) {
  return apiFetch(`${BASE}/${id}/delete/`, { method: 'DELETE' })
}

/**
 * Archive an active document.
 * @param {string} id UUID
 */
export async function archiveDocument(id) {
  return apiFetch(`${BASE}/${id}/archive/`, { method: 'POST' })
}

/**
 * Restore an archived document to active.
 * @param {string} id UUID
 */
export async function restoreDocument(id) {
  return apiFetch(`${BASE}/${id}/restore/`, { method: 'POST' })
}

/**
 * Permanently purge the file bytes of a soft-deleted document.
 * @param {string} id UUID
 */
export async function purgeDocument(id) {
  return apiFetch(`${BASE}/${id}/purge/`, { method: 'POST' })
}
