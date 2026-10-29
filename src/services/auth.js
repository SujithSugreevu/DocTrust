/**
 * DocTrust Authentication Service
 * Handles per-tab Django sessions and CSRF management.
 */

import {
  clearTabSessionKey,
  fetchWithTabSession,
  getTabSessionKey,
  setTabSessionKey,
} from './tabSession.js'
import { apiUrl } from './api.js'

// A route guard, page-level data loader, and React Strict Mode can all ask for
// the current user at once. Keep that normal navigation burst to one request
// and reuse the verified result briefly for the same tab session.
const SESSION_USER_CACHE_MS = 5_000
const AUTH_SERVICE_UNAVAILABLE_MESSAGE = 'Authentication service is temporarily unavailable. Please try again in a moment.'
let currentUserCache = null
let currentUserRequest = null
let sessionRetryNotBefore = 0

function clearCurrentUserCache() {
  currentUserCache = null
  currentUserRequest = null
  sessionRetryNotBefore = 0
}

function getRetryAfterSeconds(response, data) {
  const headerSeconds = Number(response.headers.get('Retry-After'))
  if (Number.isFinite(headerSeconds) && headerSeconds > 0) {
    return Math.ceil(headerSeconds)
  }
  const bodySeconds = Number(data?.wait)
  return Number.isFinite(bodySeconds) && bodySeconds > 0 ? Math.ceil(bodySeconds) : 0
}

function throttledSessionError(seconds) {
  const error = new Error(
    seconds
      ? `Session verification is temporarily limited. Try again in ${seconds} seconds.`
      : 'Session verification is temporarily limited. Please try again shortly.',
  )
  error.status = 429
  error.retryAfterSeconds = seconds
  return error
}

function getCookie(name) {
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

/**
 * Fetches the CSRF cookie and token from the backend.
 */
export async function getCsrfToken({ forceRefresh = false } = {}) {
  const existingCookie = getCookie('csrftoken')
  if (existingCookie && !forceRefresh) {
    return existingCookie
  }

  try {
    const response = await fetch(apiUrl('/api/auth/csrf/'), {
      method: 'GET',
      credentials: 'include',
    })
    if (!response.ok) {
      const error = new Error(
        response.status >= 500
          ? AUTH_SERVICE_UNAVAILABLE_MESSAGE
          : 'Unable to establish secure CSRF session.',
      )
      error.status = response.status
      throw error
    }
    const data = await response.json()
    return data.csrfToken || getCookie('csrftoken') || ''
  } catch (error) {
    console.error('CSRF fetch error:', error)
    if (error?.status || error?.message === AUTH_SERVICE_UNAVAILABLE_MESSAGE) {
      throw error
    }
    throw new Error(AUTH_SERVICE_UNAVAILABLE_MESSAGE, { cause: error })
  }
}

/**
 * Authenticates user credentials via Django session auth.
 * Accepts username or email, password, rememberMe flag, and expectedRole ('ADMIN' | 'EMPLOYEE').
 */
export async function login({ username, password, rememberMe = false, expectedRole = 'ADMIN' }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })

  let response
  try {
    response = await fetch(apiUrl('/api/auth/login/'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      credentials: 'include',
      body: JSON.stringify({
        username: username.trim(),
        password,
        expected_role: expectedRole,
        remember_me: Boolean(rememberMe),
      }),
    })
  } catch (error) {
    console.error('Login request error:', error)
    throw new Error(AUTH_SERVICE_UNAVAILABLE_MESSAGE, { cause: error })
  }

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const errorMessage =
      data.detail ||
      (data.errors && Object.values(data.errors).flat().join(' ')) ||
      (response.status >= 500
        ? AUTH_SERVICE_UNAVAILABLE_MESSAGE
        : 'Invalid username/email or password.')
    const error = new Error(errorMessage)
    error.status = response.status
    throw error
  }

  if (!data.mfa_required) {
    clearCurrentUserCache()
    setTabSessionKey(data.tab_session_key)
  }
  return data
}

/**
 * Initiates a password-reset request by sending instructions to the given email.
 */
export async function requestPasswordReset(email) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })

  const response = await fetch(apiUrl('/api/auth/password-reset/'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({ email: email.trim() }),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const errorMessage =
      data.detail ||
      (data.errors && Object.values(data.errors).flat().join(' ')) ||
      'Unable to process password reset request.'
    throw new Error(errorMessage)
  }

  return data
}

/**
 * Confirms a password reset with token, uid, new password, and confirmation.
 */
export async function confirmPasswordReset({ uid, token, newPassword, confirmPassword }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })

  const response = await fetch(apiUrl('/api/auth/password-reset/confirm/'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({
      uid,
      token,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const errorDetails = data.errors
      ? (Array.isArray(data.errors) ? data.errors.join(' ') : Object.values(data.errors).flat().join(' '))
      : ''
    const errorMessage = errorDetails
      ? `${data.detail ? data.detail + ' ' : ''}${errorDetails}`
      : data.detail || 'Failed to reset password.'
    throw new Error(errorMessage)
  }

  return data
}

/**
 * Logs out the current user and terminates the server session.
 */
export async function logout() {
  const csrfToken = await getCsrfToken({ forceRefresh: true })

  try {
    const response = await fetchWithTabSession('/api/auth/logout/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      credentials: 'include',
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.detail || 'Unable to terminate the server session.')
    }
    clearTabSessionKey()
    clearCurrentUserCache()
    return response.ok
  } catch (error) {
    console.error('Logout error:', error)
    throw error
  }
}

/**
 * Retrieves the currently logged-in user profile, or null if unauthenticated.
 */
export async function getCurrentUser() {
  const sessionKey = getTabSessionKey()
  if (!sessionKey) {
    clearCurrentUserCache()
    return null
  }

  const now = Date.now()
  if (
    currentUserCache?.sessionKey === sessionKey &&
    currentUserCache.expiresAt > now
  ) {
    return currentUserCache.user
  }

  if (sessionRetryNotBefore > now) {
    throw throttledSessionError(Math.ceil((sessionRetryNotBefore - now) / 1_000))
  }

  if (currentUserRequest?.sessionKey === sessionKey) {
    return currentUserRequest.promise
  }

  const request = (async () => {
    const response = await fetchWithTabSession('/api/auth/me/', {
      method: 'GET',
      credentials: 'include',
    })

    if (response.status === 401 || response.status === 403) {
      clearTabSessionKey()
      clearCurrentUserCache()
      return null
    }

    const data = await response.json().catch(() => ({}))
    if (response.status === 429) {
      const retryAfterSeconds = getRetryAfterSeconds(response, data)
      sessionRetryNotBefore = Date.now() + retryAfterSeconds * 1_000
      throw throttledSessionError(retryAfterSeconds)
    }
    if (!response.ok) {
      const error = new Error(data.detail || `Unable to verify the current session (HTTP ${response.status}).`)
      error.status = response.status
      throw error
    }

    sessionRetryNotBefore = 0
    currentUserCache = {
      sessionKey,
      user: data,
      expiresAt: Date.now() + SESSION_USER_CACHE_MS,
    }
    return data
  })()

  currentUserRequest = { sessionKey, promise: request }
  try {
    return await request
  } finally {
    if (currentUserRequest?.promise === request) {
      currentUserRequest = null
    }
  }
}

/**
 * Fetch 2FA status for the current user.
 */
export async function getTwoFactorStatus() {
  const response = await fetchWithTabSession('/api/auth/2fa/status/', {
    method: 'GET',
    credentials: 'include',
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to fetch 2FA status.')
  }
  return response.json()
}

/**
 * Start 2FA enrollment (generates candidate secret, URI, and SVG QR code).
 */
export async function enrollTwoFactor() {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession('/api/auth/2fa/enroll/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to initiate 2FA enrollment.')
  }
  return data
}

/**
 * Verify candidate code to complete 2FA enrollment.
 */
export async function verifyEnrollTwoFactor(code) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession('/api/auth/2fa/verify-enroll/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({ code }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Verification failed.')
  }
  return data
}

/**
 * Disable 2FA requiring current password and valid TOTP / recovery code.
 */
export async function disableTwoFactor({ password, code }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession('/api/auth/2fa/disable/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({ password, code }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Failed to disable 2FA.')
  }
  return data
}

/**
 * Verify 2FA code during login.
 */
export async function verifyLoginTwoFactor({ mfaToken, code }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetch(apiUrl('/api/auth/2fa/verify-login/'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({ mfa_token: mfaToken, code }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Verification failed.')
  }
  clearCurrentUserCache()
  setTabSessionKey(data.tab_session_key)
  return data
}

/**
 * Setup 2FA during login when mandatory policy applies.
 */
export async function setupLoginTwoFactor({ mfaToken, action = 'verify', code = '' }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetch(apiUrl('/api/auth/2fa/setup-login/'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({ mfa_token: mfaToken, action, code }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Setup failed.')
  }
  if (action !== 'start') {
    clearCurrentUserCache()
    setTabSessionKey(data.tab_session_key)
  }
  return data
}

/**
 * Update current user's profile (name, email).
 */
export async function updateProfile({ name, email }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession('/api/auth/me/', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({ name, email }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Failed to update profile.')
  }
  return data
}

/**
 * Change current user's password.
 */
export async function changePassword({ currentPassword, newPassword, confirmPassword }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession('/api/auth/password-change/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Failed to change password.')
  }
  return data
}

/**
 * List all users with filtering, search, and pagination (admin only).
 */
export async function listUsers(params = {}) {
  const qs = new URLSearchParams()
  if (params.search) qs.set('search', params.search)
  if (params.role) qs.set('role', params.role)
  if (params.status) qs.set('status', params.status)
  if (params.page) qs.set('page', params.page)
  if (params.pageSize) qs.set('pageSize', params.pageSize)

  const response = await fetchWithTabSession(`/api/admin/users/?${qs.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.detail || 'Failed to fetch users.')
    error.status = response.status
    throw error
  }
  return data
}

/**
 * Create a new user account (admin only).
 */
export async function createUser({ name, email, role, password }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession('/api/admin/users/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({ name, email, role, password }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Failed to create user.')
  }
  return data
}

/**
 * Update an existing user's details (admin only).
 */
export async function updateUser(id, { name, email, role }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession(`/api/admin/users/${id}/`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({ name, email, role }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Failed to update user.')
  }
  return data
}

/**
 * Suspend a user account, indefinitely when no duration is provided (admin only).
 */
export async function suspendUser(id, { duration_days, duration_hours, suspension_end, reason }) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession(`/api/admin/users/${id}/suspend/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    body: JSON.stringify({ duration_days, duration_hours, suspension_end, reason }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Failed to suspend user.')
  }
  return data
}

/**
 * Reactivate / early unsuspend a user account (admin only).
 */
export async function unsuspendUser(id) {
  const csrfToken = await getCsrfToken({ forceRefresh: true })
  const response = await fetchWithTabSession(`/api/admin/users/${id}/unsuspend/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || (data.errors && Object.values(data.errors).flat().join(' ')) || 'Failed to reactivate user.')
  }
  return data
}
