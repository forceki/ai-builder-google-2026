export default {
  namespaced: true,
  state: () => ({ email: '', submitted: false }),
  mutations: {
    setSubmitted(state, email) {
      state.email = email
      state.submitted = true
    },
  },
  actions: {
    // No backend yet — record the request locally.
    async request({ commit }, email) {
      commit('setSubmitted', email)
    },
  },
}
