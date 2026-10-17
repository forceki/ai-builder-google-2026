// Sign-in is simulated until there is a backend: busy for a moment, then done.
const FAKE_DELAY_MS = 1400

export default {
  namespaced: true,
  state: () => ({ phase: 'idle', via: null }), // phase: idle | busy | done
  getters: {
    busy: (state) => state.phase === 'busy',
    signedIn: (state) => state.phase === 'done',
  },
  mutations: {
    setPhase(state, { phase, via = state.via }) {
      state.phase = phase
      state.via = via
    },
  },
  actions: {
    async signIn({ commit }, { via }) {
      commit('setPhase', { phase: 'busy', via })
      await new Promise((resolve) => setTimeout(resolve, FAKE_DELAY_MS))
      commit('setPhase', { phase: 'done' })
    },
  },
}
