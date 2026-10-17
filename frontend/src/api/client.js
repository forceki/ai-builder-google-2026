// Thin client for the Heatmark backend (/api, proxied to the Litestar app in development).

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed (${status})`)
    this.status = status
  }
}

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

async function request(method, path, { json, form } = {}) {
  const headers = {}
  if (json) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`/api${path}`, {
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

// Resolves to null instead of throwing when the resource does not exist yet.
const orNull = (promise) => promise.catch((e) => (e instanceof ApiError && e.status === 404 ? null : Promise.reject(e)))

const p = (no) => `/projects/${encodeURIComponent(no)}`

export const api = {
  auth: {
    login: (email, password) => request('POST', '/auth/login', { json: { email, password } }),
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
  events(no) {
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
    return new WebSocket(`${scheme}://${location.host}/api${p(no)}/events`, ['heatmark', token])
  },
  signoff: {
    get: (no) => request('GET', `${p(no)}/signoff`),
    sign: (no, data) => request('POST', `${p(no)}/signoff`, { json: data }),
    revoke: (no) => request('DELETE', `${p(no)}/signoff`),
  },
}
