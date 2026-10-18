import { api } from '../../api/client'

// "Request a demo" on the landing page: stored by the API (POST /api/demo-requests).
export default {
  namespaced: true,
  state: () => ({ email: '', submitted: false, sending: false, error: '' }),
  mutations: {
    setSubmitted(state, email) {
      state.email = email
      state.submitted = true
      state.error = ''
    },
    setSending(state, sending) {
      state.sending = sending
    },
    setError(state, error) {
      state.error = error
    },
  },
  actions: {
    async request({ commit }, { email, website = '' }) {
      commit('setSending', true)
      commit('setError', '')
      try {
        await api.requestDemo(email, website)
        commit('setSubmitted', email)
      } catch (e) {
        commit('setError', e.status === 429 ? 'Too many requests right now. Please try again in a minute.'
          : e.status === 400 ? 'Please enter a valid work email.'
            : 'We couldn’t send your request. Please try again, or email us directly.')
      } finally {
        commit('setSending', false)
      }
    },
  },
}
