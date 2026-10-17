// Release readiness report for one project: latest rule run, map items and the engineer's sign-off.
import { api } from '../../api/client'

export default {
  namespaced: true,
  state: () => ({ projectNo: null, project: null, run: null, items: [], signature: null, loading: false, error: null }),
  mutations: {
    set(state, patch) {
      Object.assign(state, patch)
    },
  },
  actions: {
    async load({ commit }, no) {
      commit('set', { projectNo: no, project: null, run: null, items: [], signature: null, loading: true, error: null })
      try {
        const [project, run, trace, signature] = await Promise.all([
          api.projects.get(no),
          api.checks.latestComplete(no),
          api.trace(no),
          api.signoff.get(no),
        ])
        commit('set', { project, run, items: trace.items, signature })
      } catch (e) {
        commit('set', { error: e.message })
      } finally {
        commit('set', { loading: false })
      }
    },
    async sign({ state, commit }, { decision, name, comment }) {
      const signature = await api.signoff.sign(state.projectNo, { decision, name, comment, reviewed: true })
      commit('set', { signature })
    },
    async revoke({ state, commit }) {
      await api.signoff.revoke(state.projectNo)
      commit('set', { signature: null })
    },
  },
}
