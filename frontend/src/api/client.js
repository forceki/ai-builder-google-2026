// Thin client for the Heatmark backend (/api, proxied to the Litestar app in development).

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed (${status})`)
    this.status = status
  }
}

async function request(method, path, { json, form } = {}) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: json ? { 'Content-Type': 'application/json' } : undefined,
    body: json ? JSON.stringify(json) : form,
  })
  if (res.status === 204) return null
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, body?.detail)
  return body
}

// Resolves to null instead of throwing when the resource does not exist yet.
const orNull = (promise) => promise.catch((e) => (e instanceof ApiError && e.status === 404 ? null : Promise.reject(e)))

const p = (no) => `/projects/${encodeURIComponent(no)}`

export const api = {
  projects: {
    list: () => request('GET', '/projects'),
    get: (no) => request('GET', p(no)),
    create: (data) => request('POST', '/projects', { json: data }),
  },
  documents: {
    list: (no) => request('GET', `${p(no)}/documents`),
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
  signoff: {
    get: (no) => request('GET', `${p(no)}/signoff`),
    sign: (no, data) => request('POST', `${p(no)}/signoff`, { json: data }),
    revoke: (no) => request('DELETE', `${p(no)}/signoff`),
  },
}
