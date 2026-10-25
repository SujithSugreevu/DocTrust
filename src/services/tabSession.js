const TAB_SESSION_KEY = 'doctrustTabSession'

export function getTabSessionKey() {
  return window.sessionStorage.getItem(TAB_SESSION_KEY)
}

export function setTabSessionKey(key) {
  if (typeof key !== 'string' || !key) {
    throw new Error('The server did not issue a valid tab session.')
  }
  window.sessionStorage.setItem(TAB_SESSION_KEY, key)
}

export function clearTabSessionKey() {
  window.sessionStorage.removeItem(TAB_SESSION_KEY)
}

export function fetchWithTabSession(url, options = {}) {
  const sessionKey = getTabSessionKey()
  const headers = new Headers(options.headers || {})

  if (sessionKey) {
    headers.set('X-DocTrust-Session', sessionKey)
  }

  return fetch(url, { ...options, headers })
}
