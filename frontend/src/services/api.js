/**
 * Thin API client.
 *
 * All backend errors arrive as `{ detail: "..." }` — human-readable strings the
 * backend has already sanitised (§48). This layer never surfaces a raw stack
 * trace to the interface.
 */

const BASE = import.meta.env.VITE_API_BASE || '';
const TOKEN_KEY = 'ehm.token';
const USER_KEY = 'ehm.user';

export function getToken() {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setSession(token, user) {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    /* storage unavailable — the session simply won't persist across reloads */
  }
}

export function getStoredUser() {
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearSession() {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  } catch {
    /* ignore */
  }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const FALLBACK_MESSAGES = {
  400: 'That request could not be processed. Please check the details and try again.',
  401: 'Your session has expired. Please sign in again.',
  403: 'You do not have permission to view this information.',
  404: 'No health memory available for that request.',
  409: 'That action conflicts with the current record.',
  422: 'Unable to process document.',
  500: 'The service is temporarily unavailable. Please try again.',
};

async function request(path, { method = 'GET', body, isForm = false, signal } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json';

  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError(
      'Unable to reach the health memory service. Check that the backend is running.',
      0,
    );
  }

  if (response.status === 204) return null;

  let payload = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    if (response.status === 401) clearSession();
    const detail =
      (payload && (payload.detail || payload.message)) ||
      FALLBACK_MESSAGES[response.status] ||
      'Something went wrong. Please try again.';
    throw new ApiError(
      typeof detail === 'string' ? detail : 'That request could not be processed.',
      response.status,
    );
  }
  return payload;
}

export const api = {
  get: (path, options) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options) => request(path, { ...options, method: 'POST', body }),
  upload: (path, formData, options) =>
    request(path, { ...options, method: 'POST', body: formData, isForm: true }),
  del: (path, options) => request(path, { ...options, method: 'DELETE' }),
};

export default api;
