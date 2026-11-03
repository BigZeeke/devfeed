/**
 * Helpers for calling the DevFeed REST API from the React app.
 *
 * All requests go through fetchJson(), so the auth header, error handling,
 * and the app-wide 401 rule live in one place.
 */
import { readStoredSession } from './auth/authStorage.js'

// Vite replaces import.meta.env values at build time, not at runtime.
// - VITE_API_URL, if set, wins (production sets it to "" so requests go to
//   /api/ on the same origin, where NGINX proxies them to Django).
// - Otherwise the dev server talks to the local runserver, and a production
//   build falls back to the same origin.
const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

// Matches PAGE_SIZE in the Django REST Framework settings.
export const ARTICLES_PAGE_SIZE = 20

// An error carrying the HTTP status and the parsed response body (or null),
// so pages can show a useful message and forms can show field errors.
export class ApiError extends Error {
  constructor(status, message, responseBody = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.responseBody = responseBody
  }
}

// Called when a request that sent a token gets 401. The AuthProvider sets it,
// so this file doesn't need to know about React state or routing.
let unauthorizedHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

// Parses the JSON body, or returns null for empty bodies (204) and non-JSON.
async function readResponseBody(response) {
  if (response.status === 204) {
    return null
  }
  try {
    return await response.json()
  } catch {
    return null
  }
}

/**
 * Sends a request to the API and returns the parsed JSON body (null for 204).
 *
 * Options:
 * - method: HTTP method, GET by default.
 * - body: an object sent as JSON.
 * - signal: an AbortController signal.
 * - sendAuthToken: false for register and log-in. DRF's TokenAuthentication
 *   rejects a stale token with 401 even on those open endpoints.
 * - reportUnauthorized: false for log-out, which handles its own 401.
 *
 * Throws ApiError for non-2xx responses; a network failure throws the
 * browser's TypeError, and an aborted request throws an AbortError.
 */
export async function fetchJson(
  path,
  { method = 'GET', body, signal, sendAuthToken = true, reportUnauthorized = true } = {},
) {
  const storedSession = sendAuthToken ? readStoredSession() : null
  const requestHeaders = { Accept: 'application/json' }
  if (body !== undefined) {
    requestHeaders['Content-Type'] = 'application/json'
  }
  if (storedSession) {
    requestHeaders.Authorization = `Token ${storedSession.token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })

  // A 401 on a request that sent a token means the token is no longer valid.
  if (response.status === 401 && storedSession && reportUnauthorized && unauthorizedHandler) {
    unauthorizedHandler()
  }

  const responseBody = await readResponseBody(response)
  if (!response.ok) {
    throw new ApiError(
      response.status,
      `The API returned status ${response.status}.`,
      responseBody,
    )
  }
  return responseBody
}

/**
 * GET one page of articles: { count, next, previous, results }.
 */
export function fetchArticlesPage(pageNumber, { signal } = {}) {
  return fetchJson(`/api/articles/?page=${pageNumber}`, { signal })
}

/**
 * POST a new account. Returns { username, token } with status 201.
 */
export function registerUser({ username, email, password }) {
  return fetchJson('/api/auth/register/', {
    method: 'POST',
    body: { username, email, password },
    sendAuthToken: false,
  })
}

/**
 * POST credentials. Returns { token }; wrong credentials return 400.
 */
export function logInUser({ username, password }) {
  return fetchJson('/api/auth/token/', {
    method: 'POST',
    body: { username, password },
    sendAuthToken: false,
  })
}

/**
 * POST with the stored token; the server deletes it and returns 204.
 */
export function logOutUser() {
  return fetchJson('/api/auth/logout/', { method: 'POST', reportUnauthorized: false })
}
