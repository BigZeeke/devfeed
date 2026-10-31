/**
 * Helpers for calling the DevFeed REST API from the React app.
 *
 * All requests go through fetchJson(), so error handling lives in one place.
 */

// Vite replaces import.meta.env values at build time, not at runtime.
// - VITE_API_URL, if set, wins (production sets it to "" so requests go to
//   /api/ on the same origin, where NGINX proxies them to Django).
// - Otherwise the dev server talks to the local runserver, and a production
//   build falls back to the same origin.
const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

// Matches PAGE_SIZE in the Django REST Framework settings.
export const ARTICLES_PAGE_SIZE = 20

// An error carrying the HTTP status, so pages can show a useful message.
export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * GET a JSON response from the API.
 * Throws ApiError for non-2xx responses; a network failure throws the
 * browser's TypeError, and an aborted request throws an AbortError.
 */
export async function fetchJson(path, { signal } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw new ApiError(response.status, `The API returned status ${response.status}.`)
  }

  return response.json()
}

/**
 * GET one page of articles: { count, next, previous, results }.
 */
export function fetchArticlesPage(pageNumber, { signal } = {}) {
  return fetchJson(`/api/articles/?page=${pageNumber}`, { signal })
}
