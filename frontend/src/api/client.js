// Thin client for the Hibanako backend (/api, proxied to the Litestar app in development).

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed (${status})`)
    this.status = status
  }
}

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
const TOKEN_KEY = 'hm-token'
let token = null
try {
  token = localStorage.getItem(TOKEN_KEY)
} catch {
  token = null
}
let onUnauthorized = () => {}

export const session = {
  get token() {
    return token
  },
  setToken(value) {
    token = value
    try {
      if (value) localStorage.setItem(TOKEN_KEY, value)
      else localStorage.removeItem(TOKEN_KEY)
    } catch {
      return
    }
  },
  onUnauthorized(handler) {
    onUnauthorized = handler
  },
}

// fetch, but a request that never reaches the server says so instead of a bare "Failed to fetch".
async function reach(url, init) {
  try {
    return await fetch(url, init)
  } catch (e) {
    throw new ApiError(0, `Could not reach the server for ${(init.method || 'GET').toUpperCase()} ${url.replace(/^.*?\/api/, '/api')}: ${e.message}. Check that the backend is running and that no browser extension or old service worker is blocking it.`)
  }
}

async function request(method, path, { json, form } = {}) {
  const headers = {}
  if (json) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await reach(`${API_URL}/api${path}`, {
    method,
    headers,
    body: json ? JSON.stringify(json) : form,
  })
  if (res.status === 204) return null
  const body = await res.json().catch(() => null)
  if (res.status === 401 && token) onUnauthorized()
  if (!res.ok) throw new ApiError(res.status, body?.detail)
  return body
}

// Binary responses (e.g. evidence snapshots) as an object URL; the caller revokes it.
async function blobUrl(path) {
  const res = await reach(`${API_URL}/api${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (res.status === 401 && token) onUnauthorized()
  if (!res.ok) throw new ApiError(res.status, (await res.json().catch(() => null))?.detail)
  return URL.createObjectURL(await res.blob())
}

// Resolves to null instead of throwing when the resource does not exist yet.
const orNull = (promise) => promise.catch((e) => (e instanceof ApiError && e.status === 404 ? null : Promise.reject(e)))

const p = (no) => `/projects/${encodeURIComponent(no)}`

export const api = {
  auth: {
    login: (email, password) => request('POST', '/auth/login', { json: { email, password } }),
    google: (credential) => request('POST', '/auth/google', { json: { credential } }),
    me: () => request('GET', '/auth/me'),
  },
  projects: {
    list: () => request('GET', '/projects'),
    get: (no) => request('GET', p(no)),
    create: (data) => request('POST', '/projects', { json: data }),
    update: (no, data) => request('PATCH', p(no), { json: data }),
    remove: (no) => request('DELETE', p(no)),
  },
  documents: {
    list: (no) => request('GET', `${p(no)}/documents`),
    link: (no, id) => request('GET', `${p(no)}/documents/${id}/link`),
    remove: (no, id) => request('DELETE', `${p(no)}/documents/${id}`),
    upload(no, { file, docType, evidenceFor }) {
      const form = new FormData()
      form.append('file', file)
      if (docType) form.append('doc_type', docType)
      if (evidenceFor) form.append('evidence_for', evidenceFor)
      return request('POST', `${p(no)}/documents`, { form })
    },
  },
  checks: {
    run: (no) => request('POST', `${p(no)}/checks`),
    latest: (no) => orNull(request('GET', `${p(no)}/checks/latest`)),
    latestComplete: (no) => orNull(request('GET', `${p(no)}/checks/latest?complete=true`)),
  },
  trace: (no) => request('GET', `${p(no)}/trace`),
  assessment: {
    catalog: () => request('GET', '/assessment/catalog'),
    get: (no) => request('GET', `${p(no)}/assessment`),
    setConditions: (no, conditions) => request('PUT', `${p(no)}/assessment/conditions`, { json: conditions }),
    addFiles: (no, names, slot) => request('POST', `${p(no)}/assessment/files`, { json: { names, slot } }),
    removeFiles(no, { name, slot } = {}) {
      const q = new URLSearchParams()
      if (name) q.set('name', name)
      if (slot) q.set('slot', slot)
      return request('DELETE', `${p(no)}/assessment/files?${q}`)
    },
    loadSamples: (no, slot) => request('POST', `${p(no)}/assessment/samples`, { json: { slot } }),
    upload(no, file, slot) {
      const form = new FormData()
      form.append('file', file)
      if (slot) form.append('slot', slot)
      return request('POST', `${p(no)}/assessment/documents`, { form })
    },
    report: (no) => request('GET', `${p(no)}/assessment/report`),
    snapshot(no, { file, page, box }) {
      const q = new URLSearchParams({ file, page: String(page || 1) })
      if (box) q.set('box', box.join(','))
      return blobUrl(`${p(no)}/assessment/snapshot?${q}`)
    },
    run: (no) => request('POST', `${p(no)}/assessment/runs`),
    setWaiver: (no, key, status, reason = '') =>
      request('PATCH', `${p(no)}/assessment/findings/${encodeURIComponent(key)}`, { json: { status, reason } }),
  },
  events(no) {
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
    const base = API_URL ? API_URL.replace(/^http/, 'ws') : `${scheme}://${location.host}`
    return new WebSocket(`${base}/api${p(no)}/events`, ['hibanako', token])
  },
  signoff: {
    get: (no) => request('GET', `${p(no)}/signoff`),
    sign: (no, data) => request('POST', `${p(no)}/signoff`, { json: data }),
    revoke: (no) => request('DELETE', `${p(no)}/signoff`),
  },
}
