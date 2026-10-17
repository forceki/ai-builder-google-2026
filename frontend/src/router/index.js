import { createRouter, createWebHistory } from 'vue-router'
import { session } from '../api/client'
import LandingView from '../views/LandingView.vue'

const signedIn = { requiresAuth: true }

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
    { path: '/terms', name: 'terms', component: () => import('../views/LegalView.vue'), props: { doc: 'terms' } },
    { path: '/privacy', name: 'privacy', component: () => import('../views/LegalView.vue'), props: { doc: 'privacy' } },
    { path: '/projects', name: 'projects', component: () => import('../views/ProjectsView.vue'), meta: signedIn },
    { path: '/projects/:no', name: 'workspace', component: () => import('../views/WorkspaceView.vue'), meta: signedIn },
    { path: '/projects/:no/report', name: 'report', component: () => import('../views/ReportView.vue'), meta: signedIn },
  ],
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash }
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !session.token) return { name: 'login', query: { next: to.fullPath } }
})

export default router
