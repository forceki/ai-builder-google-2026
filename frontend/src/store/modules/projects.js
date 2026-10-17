// Project register, loaded from the API.
import { api } from '../../api/client'
import { formatUpdated } from '../../lib/status'

export const STAGES = ['UPLOAD', 'EXTRACT', 'MAP', 'VERIFY']

export const RELEASE = {
  NOT_READY: 'NOT READY',
  EXTRACTING: 'EXTRACTING',
  READY: 'READY · SIGN-OFF',
  RELEASED: 'RELEASED',
  NO_DOCUMENTS: 'NO DOCUMENTS',
}

// Filter bucket a project falls into: open | ready | released
export function projectGroup(p) {
  if (p.release === RELEASE.RELEASED) return 'released'
  if (p.release === RELEASE.READY) return 'ready'
  return 'open'
}

// API ProjectOut -> the row shape the register renders.
const toRow = (p) => ({
  no: p.no,
  name: p.name,
  scope: p.scope,
  stage: p.stage,
  docs: p.docs,
  pass: p.checks?.pass,
  hold: p.checks?.hold,
  reject: p.checks?.reject,
  release: p.release,
  updated: formatUpdated(p.updated_at),
})

export default {
  namespaced: true,
  state: () => ({ list: [], loading: false, error: null }),
  getters: {
    countBy: (state) => (group) =>
      group === 'all' ? state.list.length : state.list.filter((p) => projectGroup(p) === group).length,
    byNo: (state) => (no) => state.list.find((p) => p.no === no),
  },
  mutations: {
    setList(state, list) {
      state.list = list
    },
    upsert(state, row) {
      const i = state.list.findIndex((p) => p.no === row.no)
      if (i >= 0) state.list.splice(i, 1, row)
      else state.list.unshift(row)
    },
    setLoading(state, loading) {
      state.loading = loading
    },
    setError(state, error) {
      state.error = error
    },
  },
  actions: {
    async fetchAll({ commit }) {
      commit('setLoading', true)
      commit('setError', null)
      try {
        commit('setList', (await api.projects.list()).map(toRow))
      } catch (e) {
        commit('setError', e.message)
      } finally {
        commit('setLoading', false)
      }
    },
    async fetchOne({ commit }, no) {
      const row = toRow(await api.projects.get(no))
      commit('upsert', row)
      return row
    },
    async create({ commit }) {
      const row = toRow(await api.projects.create({ name: 'Untitled project' }))
      commit('upsert', row)
      return row
    },
  },
}
