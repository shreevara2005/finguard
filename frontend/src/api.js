const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch (_) {
      // ignore JSON parse failure, use default message
    }
    throw new Error(detail)
  }
  return res.json()
}

export async function register(username, password) {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return handleResponse(res)
}

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return handleResponse(res)
}

export async function optimizeAllocation(token, payload) {
  const res = await fetch(`${API_BASE}/api/v1/optimize-allocation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
  return handleResponse(res)
}
