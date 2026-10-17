import { api, session } from '../../api/client'

export const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL || 'demo@heatmark.app'
export const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || 'heatmark-demo'

export default {
  namespaced: true,
  state: () => ({ phase: session.token ? 'done' : 'idle', via: null, error: null, user: null }),
  getters: {
    busy: (state) => state.phase === 'busy',
    signedIn: (state) => state.phase === 'done',
    initials: (state) =>
      (state.user?.name ?? '')
        .split(/\s+/)
        .filter(Boolean)
        .map((w) => w[0])
        .join('')
        .slice(0, 2)
        .toUpperCase(),
  },
  mutations: {
    setPhase(state, { phase, via = state.via }) {
      state.phase = phase
      state.via = via
    },
    setError(state, error) {
      state.error = error
    },
    setUser(state, user) {
      state.user = user
    },
    signedOut(state) {
      session.setToken(null)
      Object.assign(state, { phase: 'idle', via: null, user: null })
    },
  },
  actions: {
    async signIn({ commit }, { email, password, via = 'email' }) {
      commit('setError', null)
      commit('setPhase', { phase: 'busy', via })
      try {
        const res = await api.auth.login(email, password)
        session.setToken(res.token)
        commit('setUser', res.user)
        commit('setPhase', { phase: 'done' })
      } catch (e) {
        commit('setPhase', { phase: 'idle' })
        commit('setError', e.status === 401 ? 'Wrong email or password.' : e.message)
        throw e
      }
    },
    signInDemo({ dispatch }) {
      return dispatch('signIn', { email: DEMO_EMAIL, password: DEMO_PASSWORD, via: 'demo' })
    },
    async restore({ commit, state }) {
      if (!session.token || state.user) return
      try {
        commit('setUser', await api.auth.me())
      } catch {
        return
      }
    },
    signOut({ commit }) {
      commit('signedOut')
    },
  },
}
