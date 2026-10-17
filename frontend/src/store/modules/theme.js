const STORAGE_KEY = 'hm-theme'

function readInitial() {
  return document.documentElement.getAttribute('data-hm-theme') === 'dark'
}

export default {
  namespaced: true,
  state: () => ({ dark: readInitial() }),
  getters: {
    label: (state) => (state.dark ? 'LIGHT' : 'DARK'),
  },
  mutations: {
    setDark(state, value) {
      state.dark = value
    },
  },
  actions: {
    toggle({ state, commit }) {
      const dark = !state.dark
      commit('setDark', dark)
      if (dark) document.documentElement.setAttribute('data-hm-theme', 'dark')
      else document.documentElement.removeAttribute('data-hm-theme')
      try {
        localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
      } catch (e) {}
    },
  },
}
