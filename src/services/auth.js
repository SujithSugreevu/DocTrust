/**
 * DocTrust Authentication Service
 * Handles session-based authentication with Django backend and CSRF management.
 */

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
export async function getCsrfToken() {
  const existingCookie = getCookie('csrftoken')
  if (existingCookie) {
    return existingCookie
  }

  try {
    const response = await fetch('/api/auth/csrf/', {
      method: 'GET',
      credentials: 'include',
    })
    if (!response.ok) {
      throw new Error('Unable to establish secure CSRF session.')
    }
    const data = await response.json()
    return data.csrfToken || getCookie('csrftoken') || ''
  } catch (error) {
    console.error('CSRF fetch error:', error)
    return getCookie('csrftoken') || ''
  }
}

/**
 * Authenticates user credentials via Django session auth.
 * Accepts username or email, password, rememberMe flag, and expectedRole ('ADMIN' | 'EMPLOYEE').
 */
export async function login({ username, password, rememberMe = false, expectedRole = 'ADMIN' }) {
  const csrfToken = await getCsrfToken()

  const response = await fetch('/api/auth/login/', {
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

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const errorMessage =
      data.detail ||
      (data.errors && Object.values(data.errors).flat().join(' ')) ||
      'Invalid username/email or password.'
    throw new Error(errorMessage)
  }

  return data
}

/**
 * Initiates a password-reset request by sending instructions to the given email.
 */
export async function requestPasswordReset(email) {
  const csrfToken = await getCsrfToken()

  const response = await fetch('/api/auth/password-reset/', {
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
  const csrfToken = await getCsrfToken()

  const response = await fetch('/api/auth/password-reset/confirm/', {
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
  const csrfToken = await getCsrfToken()

  try {
    const response = await fetch('/api/auth/logout/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      credentials: 'include',
    })
    return response.ok
  } catch (error) {
    console.error('Logout error:', error)
    return false
  }
}

/**
 * Retrieves the currently logged-in user profile, or null if unauthenticated.
 */
export async function getCurrentUser() {
  try {
    const response = await fetch('/api/auth/me/', {
      method: 'GET',
      credentials: 'include',
    })

    if (response.status === 401 || response.status === 403) {
      return null
    }

    if (!response.ok) {
      return null
    }

    return await response.json()
  } catch {
    return null
  }
}

/**
 * Fetch 2FA status for the current user.
 */
export async function getTwoFactorStatus() {
  const response = await fetch('/api/auth/2fa/status/', {
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
  const csrfToken = await getCsrfToken()
  const response = await fetch('/api/auth/2fa/enroll/', {
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
  const csrfToken = await getCsrfToken()
  const response = await fetch('/api/auth/2fa/verify-enroll/', {
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
  const csrfToken = await getCsrfToken()
  const response = await fetch('/api/auth/2fa/disable/', {
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
  const csrfToken = await getCsrfToken()
  const response = await fetch('/api/auth/2fa/verify-login/', {
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
  return data
}

/**
 * Setup 2FA during login when mandatory policy applies.
 */
export async function setupLoginTwoFactor({ mfaToken, action = 'verify', code = '' }) {
  const csrfToken = await getCsrfToken()
  const response = await fetch('/api/auth/2fa/setup-login/', {
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
  return data
}
