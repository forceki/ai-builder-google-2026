import { createApp } from 'vue'
import App from './App.vue'
import { session } from './api/client'
import { reportError } from './composables/useErrors'
import router from './router'
import store from './store'
import './style.css'

session.onUnauthorized(() => {
  store.commit('auth/signedOut')
  store.commit('projects/setList', [])
  const here = router.currentRoute.value
  if (here.meta.requiresAuth) router.replace({ name: 'login', query: { next: here.fullPath } })
})
store.dispatch('auth/restore')

// Nothing may fail silently: uncaught errors and rejected promises are shown in the error banner.
window.addEventListener('unhandledrejection', (e) => reportError(e.reason, 'request'))
window.addEventListener('error', (e) => reportError(e.error || e.message, 'page'))
router.onError((err) => reportError(err, 'navigation'))

// Hibanako does not use a service worker. One left on this origin by another app (e.g. on localhost:5173) intercepts
// requests and breaks them ("Failed to convert value to 'Response'"), so remove it.
navigator.serviceWorker?.getRegistrations().then(
  (regs) =>
    regs.forEach((r) => {
      console.warn('Removing a service worker this app does not use:', r.scope)
      r.unregister()
    }),
  (err) => reportError(err, 'service worker'),
)

const app = createApp(App)
app.config.errorHandler = (err, _instance, info) => reportError(err, info)
app.use(store).use(router).mount('#app')
