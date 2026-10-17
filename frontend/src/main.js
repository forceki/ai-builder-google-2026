import { createApp } from 'vue'
import App from './App.vue'
import { session } from './api/client'
import router from './router'
import store from './store'
import './style.css'

session.onUnauthorized(() => {
  store.commit('auth/signedOut')
  const here = router.currentRoute.value
  if (here.meta.requiresAuth) router.replace({ name: 'login', query: { next: here.fullPath } })
})
store.dispatch('auth/restore')

createApp(App).use(store).use(router).mount('#app')
