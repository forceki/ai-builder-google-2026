import { createRouter, createWebHistory } from 'vue-router'
import { session } from '../api/client'
import { applySeo } from '../lib/seo'
import LandingView from '../views/LandingView.vue'

const signedIn = { requiresAuth: true }

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'landing', component: LandingView, meta: { seo: { index: true } } },
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { seo: { title: 'Log in' } } },
    {
      path: '/terms',
      name: 'terms',
      component: () => import('../views/LegalView.vue'),
      props: { doc: 'terms' },
      meta: { seo: { index: true, title: 'Terms and conditions', description: 'Terms of use for Hibanako, the AI weld quality documentation and traceability service.' } },
    },
    {
      path: '/privacy',
      name: 'privacy',
      component: () => import('../views/LegalView.vue'),
      props: { doc: 'privacy' },
      meta: { seo: { index: true, title: 'Privacy policy', description: 'How Hibanako collects, uses and protects your account data and uploaded welding documents.' } },
    },
    { path: '/projects', name: 'projects', component: () => import('../views/ProjectsView.vue'), meta: signedIn },
    // Each assessment step has its own URL, so a refresh keeps the user on it. Opening a project asks for the review;
    // the view moves back to the furthest step that is open (conditions for a new project).
    { path: '/projects/:no', redirect: (to) => ({ name: 'assessment', params: { no: to.params.no, step: 'review' } }) },
    { path: '/projects/:no/report', name: 'report', component: () => import('../views/AssessmentReportView.vue'), meta: signedIn },
    {
      path: '/projects/:no/:step(conditions|documents|review)',
      name: 'assessment',
      component: () => import('../views/AssessmentView.vue'),
      meta: signedIn,
    },
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
router.afterEach(applySeo)

export default router
