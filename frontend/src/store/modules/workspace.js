// Workspace for one project, backed by the API. Polls while documents are being read or a
// rule run is in progress. Field notes and "marked resolved" flags are local to this browser.
import { api } from '../../api/client'
import { clockTime, worst } from '../../lib/status'

const POLL_MS = 1500
const LIVE_POLL_MS = 8000
const RETRY_MAX_MS = 10_000

let pollTimer = null
let socket = null
let retryTimer = null
let retryMs = 1000
let refreshTimer = null

function stopPolling() {
  clearTimeout(pollTimer)
  pollTimer = null
}

function closeSocket() {
  clearTimeout(retryTimer)
  clearTimeout(refreshTimer)
  retryTimer = null
  if (socket) {
    socket.onclose = null
    socket.close()
    socket = null
  }
}

const isPending = (d) => d.status === 'queued' || d.status === 'reading'
const runPending = (run) => run && (run.status === 'queued' || run.status === 'running')
const RUN_WAIT_MS = 60_000

function awaitingRun(s) {
  if (!s.docs.length || s.docs.some(isPending)) return false
  const lastRead = Math.max(...s.docs.map((d) => Date.parse(d.updated_at ?? d.created_at)))
  if (Date.now() - lastRead > RUN_WAIT_MS) return false
  return !s.run || Date.parse(s.run.created_at) < lastRead
}

const fresh = () => ({
  projectNo: null,
  project: null,
  docs: [],
  items: [],
  links: [],
  run: null, // latest run, possibly still queued/running
  result: null, // latest completed run: what the screens show
  loading: false,
  live: false,
  error: null,
  sel: null,
  drawer: false,
  resolved: {}, // item key -> true
  notes: {}, // item key -> [{ meta, text }]
})

export default {
  namespaced: true,
  state: fresh,
  getters: {
    // empty: no documents | processing: reading, map not built yet | review: map available
    phase: (s) => {
      if (!s.docs.length) return 'empty'
      const hasMap = s.items.length > 0 || !!s.result
      return !hasMap ? 'processing' : 'review'
    },
    isReview: (s, g) => g.phase === 'review',
    running: (s) => runPending(s.run),
    checking: (s) => runPending(s.run) || awaitingRun(s),
    awaitingRun: (s) => !runPending(s.run) && awaitingRun(s),
    docTypes: (s) => new Set(s.docs.filter((d) => d.status !== 'failed').map((d) => d.doc_type ?? d.suggested_type)),
    explaining: (s) => !!s.result?.summary?.explaining,
    pendingDocs: (s) => s.docs.filter(isPending),
    doneDocs: (s) => s.docs.filter((d) => !isPending(d)),
    findings: (s) => s.result?.findings ?? [],
    findingsFor: (s, g) => (key) => g.findings.filter((f) => f.item_key === key),
    statusOf: (s, g) => (key) => worst(g.findingsFor(key).map((f) => f.status)),
    itemByKey: (s) => Object.fromEntries(s.items.map((i) => [i.key, i])),
    itemById: (s) => Object.fromEntries(s.items.map((i) => [i.id, i])),
    openKeys: (s, g) => [...new Set(g.findings.map((f) => f.item_key))],
    counts: (s) => s.result?.summary?.counts ?? { pass: 0, hold: 0, reject: 0 },
    countText: (s, g) => `${g.counts.pass} PASS / ${g.counts.hold} HOLD / ${g.counts.reject} REJECT`,
    lastRun: (s) => (s.result?.finished_at ? clockTime(new Date(s.result.finished_at)) : '—'),
    // 0 UPLOAD, 1 EXTRACT, 2 MAP, 3 VERIFY
    stage: (s, g) => (g.phase === 'empty' ? 0 : g.phase === 'processing' ? 1 : s.result ? 3 : 2),
  },
  mutations: {
    reset(state, projectNo) {
      Object.assign(state, fresh(), { projectNo })
    },
    set(state, patch) {
      Object.assign(state, patch)
    },
    addDoc(state, doc) {
      state.docs.push(doc)
    },
    select(state, key) {
      state.sel = key
    },
    setDrawer(state, open) {
      state.drawer = open
    },
    toggleResolved(state, key) {
      state.resolved[key] = !state.resolved[key]
    },
    addNote(state, { key, text, time, kind = 'NOTE' }) {
      ;(state.notes[key] ||= []).push({ meta: `R. LINDQVIST · ${time} · ${kind}`, text })
    },
  },
  actions: {
    async load({ state, commit, dispatch, getters }, projectNo) {
      stopPolling()
      commit('reset', projectNo)
      commit('set', { loading: true })
      try {
        const [project, docs, run, result, trace] = await Promise.all([
          api.projects.get(projectNo),
          api.documents.list(projectNo),
          api.checks.latest(projectNo),
          api.checks.latestComplete(projectNo),
          api.trace(projectNo),
        ])
        if (state.projectNo !== projectNo) return
        commit('set', { project, docs, run, result, items: trace.items, links: trace.links })
        // Open on the worst open item, as a starting point.
        const first = [...getters.findings].sort((a, b) => (a.status === 'REJECT' ? -1 : 1) - (b.status === 'REJECT' ? -1 : 1))[0]
        commit('select', first?.item_key ?? trace.items[0]?.key ?? null)
        dispatch('connect', projectNo)
        dispatch('pollIfNeeded')
      } catch (e) {
        commit('set', { error: e.message })
      } finally {
        commit('set', { loading: false })
      }
    },

    teardown({ commit }) {
      stopPolling()
      closeSocket()
      commit('reset', null)
    },

    connect({ state, commit, dispatch }, projectNo) {
      closeSocket()
      if (state.projectNo !== projectNo) return
      let ws
      try {
        ws = api.events(projectNo)
      } catch {
        return
      }
      socket = ws
      ws.onopen = () => {
        retryMs = 1000
        commit('set', { live: true })
      }
      ws.onmessage = (e) => {
        let msg
        try {
          msg = JSON.parse(e.data)
        } catch {
          return
        }
        if (msg.event === 'ping') return
        clearTimeout(refreshTimer)
        refreshTimer = setTimeout(async () => {
          await dispatch('refresh')
          dispatch('pollIfNeeded')
        }, 120)
      }
      ws.onclose = () => {
        if (socket !== ws) return
        socket = null
        commit('set', { live: false })
        dispatch('pollIfNeeded')
        if (state.projectNo !== projectNo) return
        retryTimer = setTimeout(() => dispatch('connect', projectNo), retryMs)
        retryMs = Math.min(retryMs * 2, RETRY_MAX_MS)
      }
    },

    pollIfNeeded({ state, getters, dispatch }) {
      if (pollTimer || !state.projectNo) return
      if (!getters.pendingDocs.length && !getters.checking && !getters.explaining) return
      pollTimer = setTimeout(async () => {
        pollTimer = null
        await dispatch('refresh')
        dispatch('pollIfNeeded')
      }, state.live ? LIVE_POLL_MS : POLL_MS)
    },

    async refresh({ state, commit }) {
      const no = state.projectNo
      if (!no) return
      try {
        const [docs, run, project] = await Promise.all([api.documents.list(no), api.checks.latest(no), api.projects.get(no)])
        if (state.projectNo !== no) return
        const finished = run?.status === 'complete' && state.result?.id !== run.id
        commit('set', { docs, run, project })
        if (!finished && run?.status === 'complete' && state.result?.summary?.explaining) {
          commit('set', { result: run })
        }
        if (finished) {
          const trace = await api.trace(no)
          commit('set', { result: run, items: trace.items, links: trace.links, resolved: {} })
          if (!state.sel || !trace.items.some((i) => i.key === state.sel)) commit('select', trace.items[0]?.key ?? null)
        }
      } catch (e) {
        commit('set', { error: e.message })
      }
    },

    async upload({ state, commit, dispatch }, { file, docType, evidenceFor }) {
      const doc = await api.documents.upload(state.projectNo, { file, docType, evidenceFor })
      commit('addDoc', doc)
      if (evidenceFor) {
        commit('addNote', {
          key: evidenceFor,
          time: clockTime(),
          kind: 'EVIDENCE',
          text: `Added ${doc.filename} as evidence. Checks re-run automatically once it has been read.`,
        })
        commit('select', evidenceFor)
      }
      dispatch('pollIfNeeded')
      return doc
    },

    async deleteDoc({ state, commit, dispatch }, doc) {
      const run = await api.documents.remove(state.projectNo, doc.id)
      commit('set', { docs: state.docs.filter((d) => d.id !== doc.id), run })
      dispatch('pollIfNeeded')
    },

    async runChecks({ state, commit, dispatch }) {
      commit('setDrawer', true)
      try {
        const run = await api.checks.run(state.projectNo)
        commit('set', { run })
        dispatch('pollIfNeeded')
      } catch (e) {
        commit('set', { error: e.message })
      }
    },
  },
}
