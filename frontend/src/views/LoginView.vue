<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { DEMO_EMAIL, DEMO_PASSWORD } from '../store/modules/auth'
import BrandMark from '../components/ui/BrandMark.vue'
import ThemeToggle from '../components/ui/ThemeToggle.vue'
import PanelBolts from '../components/ui/PanelBolts.vue'
import PoweredBy from '../components/ui/PoweredBy.vue'
import SectionLabel from '../components/ui/SectionLabel.vue'

const store = useStore()
const route = useRoute()
const router = useRouter()
const phase = computed(() => store.state.auth.phase)
const busy = computed(() => store.getters['auth/busy'])
const signedIn = computed(() => store.getters['auth/signedIn'])

const statusText = computed(() => ({ idle: 'READY', busy: 'CONNECTING…', done: 'AUTHENTICATED' }[phase.value]))

const email = ref('')
const password = ref('')

const demoLabel = computed(() =>
  busy.value && store.state.auth.via === 'demo' ? 'Signing in to the demo…' : 'Try the demo',
)
const error = computed(() => store.state.auth.error)
const userName = computed(() => store.state.auth.user?.name)

const next = computed(() => {
  const n = route.query.next
  return typeof n === 'string' && n.startsWith('/') && !n.startsWith('//') ? n : '/projects'
})

const signIn = async (credentials) => {
  try {
    await store.dispatch('auth/signIn', credentials)
  } catch {
    return
  }
  router.push(next.value)
}

const onGoogle = () => store.commit('auth/setError', 'Google sign-in is not set up yet. Use email, or try the demo.')
const onEmail = () => signIn({ email: email.value, password: password.value, via: 'email' })
const onDemo = () => {
  email.value = DEMO_EMAIL
  password.value = DEMO_PASSWORD
  return signIn({ email: DEMO_EMAIL, password: DEMO_PASSWORD, via: 'demo' })
}
const onSignOut = () => store.dispatch('auth/signOut')
</script>

<template>
  <div class="flex min-h-screen flex-col bg-paper font-sans text-ink">
    <header class="wrap box-border flex w-full flex-wrap items-center justify-between gap-4 py-5">
      <BrandMark />
      <div class="flex items-center gap-4">
        <ThemeToggle />
        <RouterLink to="/" class="font-mono text-[13px] underline-offset-4">← Back to site</RouterLink>
      </div>
    </header>

    <main class="wrap box-border flex w-full flex-1 flex-wrap items-center gap-x-[clamp(40px,6vw,96px)] gap-y-12 py-[clamp(32px,6vw,80px)]">
      <div class="flex min-w-0 flex-[1_1_360px] flex-col gap-6">
        <SectionLabel num="00" label="OPERATOR LOGIN" />
        <h1 class="m-0 text-[clamp(44px,6vw,88px)] leading-[0.92] font-extrabold tracking-[-0.045em] text-balance">
          Pick up the thread.
        </h1>
        <p class="m-0 max-w-[420px] text-lg leading-[1.45]">Sign in to review open findings and sign off releases.</p>
      </div>

      <form
        class="relative box-border flex max-w-[520px] min-w-0 flex-[1_1_400px] flex-col gap-5 rounded border border-ink/18 bg-panel px-[clamp(20px,4vw,40px)] py-[clamp(28px,4vw,40px)] shadow-[inset_0_-3px_0_rgb(var(--shade)/0.1)]"
        @submit.prevent="onEmail"
      >
        <PanelBolts />

        <div class="flex items-center justify-between gap-3 font-mono text-[11px] tracking-[0.08em] text-muted">
          <span class="flex items-center gap-2">
            <span
              aria-hidden="true"
              class="inline-block size-2 rounded-full border"
              :class="[phase === 'idle' ? 'border-ink/40 bg-pending' : 'border-ink bg-signal', { 'animate-blink': busy }]"
            ></span>
            <span aria-live="polite">{{ statusText }}</span>
          </span>
          <span>FORM HM-LG-01</span>
        </div>

        <div v-if="signedIn" role="status" class="flex flex-col items-start gap-4 py-6">
          <span
            class="inline-block -rotate-4 rounded-[3px] border-2 border-ink px-3.5 py-1.5 font-mono text-base font-bold tracking-[0.14em] outline outline-1 outline-offset-2 outline-ink"
          >SIGNED IN</span>
          <p class="m-0 text-[17px] leading-[1.45]">Welcome back{{ userName ? `, ${userName}` : '' }}.</p>
          <div class="flex flex-wrap items-center gap-5">
            <RouterLink :to="next" class="font-mono text-[13px] underline-offset-4">Open projects →</RouterLink>
            <button type="button" class="cursor-pointer font-mono text-[13px] text-muted underline underline-offset-4" @click="onSignOut">
              Sign out
            </button>
          </div>
        </div>

        <template v-else>
          <button
            type="button"
            :disabled="busy"
            class="flex w-full cursor-pointer items-center justify-center gap-3.5 rounded border border-ink bg-white px-5 py-4 font-mono text-sm font-bold tracking-[0.04em] text-ink shadow-[inset_0_-4px_0_rgb(var(--shade)/0.14)] active:translate-y-[3px] active:shadow-[inset_0_-1px_0_rgb(var(--shade)/0.14)] disabled:cursor-wait"
            @click="onGoogle"
          >
            <span
              aria-hidden="true"
              class="flex size-[22px] flex-none items-center justify-center rounded-full border border-ink/35 bg-white font-sans text-[13px] font-extrabold"
            >G</span>
            Continue with Google
          </button>

          <div aria-hidden="true" class="flex items-center gap-3.5 font-mono text-[11px] tracking-[0.08em] text-muted">
            <span class="h-px flex-1 bg-ink/30"></span>OR WITH EMAIL<span class="h-px flex-1 bg-ink/30"></span>
          </div>

          <label class="flex flex-col gap-2">
            <span class="font-mono text-[11px] text-muted">WORK EMAIL</span>
            <input v-model="email" type="email" name="email" required autocomplete="email" placeholder="name@company.com" class="field" />
          </label>
          <label class="flex flex-col gap-2">
            <span class="flex justify-between gap-3 font-mono text-[11px] text-muted">
              <span>PASSWORD</span>
              <a href="#" class="underline-offset-[3px]">Forgot?</a>
            </span>
            <input
              v-model="password"
              type="password"
              name="password"
              required
              autocomplete="current-password"
              placeholder="••••••••"
              class="field"
            />
          </label>

          <p v-if="error" role="alert" class="m-0 border-l-2 border-reject pl-2.5 font-mono text-xs text-reject">{{ error }}</p>

          <button type="submit" :disabled="busy" class="btn-primary w-full justify-center disabled:cursor-wait">
            <span aria-hidden="true" class="size-[9px] rounded-full bg-ink"></span>Sign in
          </button>

          <div aria-hidden="true" class="flex items-center gap-3.5 font-mono text-[11px] tracking-[0.08em] text-muted">
            <span class="h-px flex-1 bg-ink/30"></span>OR EXPLORE<span class="h-px flex-1 bg-ink/30"></span>
          </div>

          <div class="flex flex-col gap-2">
            <button
              type="button"
              :disabled="busy"
              class="btn-hard flex w-full items-center justify-center gap-2.5 bg-signal px-5 py-3.5 text-sm tracking-[0.04em] disabled:cursor-wait"
              @click="onDemo"
            >
              <span aria-hidden="true" class="size-[8px] bg-ink"></span>{{ demoLabel }}
            </button>
            <p class="m-0 font-mono text-[11px] leading-relaxed text-muted">
              Signs in as the demo account. Three sample dossiers: one released, one on hold, one rejected.
            </p>
          </div>

          <p class="m-0 font-mono text-[11px] leading-relaxed text-muted">
            By signing in you agree to the
            <RouterLink to="/terms" class="text-ink underline-offset-[3px]">Terms</RouterLink> and
            <RouterLink to="/privacy" class="text-ink underline-offset-[3px]">Privacy policy</RouterLink>.
          </p>
          <p class="m-0 font-mono text-xs leading-relaxed text-muted">
            No account?
            <RouterLink :to="{ path: '/', hash: '#contact' }" class="text-ink underline-offset-[3px]">Request a demo</RouterLink>
          </p>
        </template>
      </form>
    </main>

    <footer class="border-t border-ink font-mono text-xs">
      <div class="wrap flex flex-wrap items-center justify-between gap-4 py-[18px] text-muted">
        <span>SHEET 00 · REV. A · © 2026 HEATMARK</span>
        <PoweredBy />
      </div>
    </footer>
  </div>
</template>
