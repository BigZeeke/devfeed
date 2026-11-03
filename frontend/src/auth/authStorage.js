/**
 * Reads and writes the logged-in session (API token and username) in localStorage.
 *
 * localStorage keeps the user logged in across page reloads. Every access is
 * wrapped in try/catch because some browsers (for example with storage
 * disabled) throw instead of returning null.
 */

const TOKEN_STORAGE_KEY = 'devfeed_auth_token'
const USERNAME_STORAGE_KEY = 'devfeed_auth_username'

// Returns { token, username }, or null when no complete session is stored.
export function readStoredSession() {
  try {
    const token = window.localStorage.getItem(TOKEN_STORAGE_KEY)
    const username = window.localStorage.getItem(USERNAME_STORAGE_KEY)
    return token && username ? { token, username } : null
  } catch {
    return null
  }
}

// Saves both values together, so a stored token always has its username.
export function saveStoredSession({ token, username }) {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
    window.localStorage.setItem(USERNAME_STORAGE_KEY, username)
  } catch {
    // Storage unavailable: the session still works until the page reloads.
  }
}

// Removes the stored session, for log-out and for a rejected token.
export function clearStoredSession() {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY)
    window.localStorage.removeItem(USERNAME_STORAGE_KEY)
  } catch {
    // Nothing stored or storage unavailable: nothing to remove.
  }
}
