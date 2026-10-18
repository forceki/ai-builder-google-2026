<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useStore } from 'vuex'
import BrandMark from '../ui/BrandMark.vue'
import ThemeToggle from '../ui/ThemeToggle.vue'

const store = useStore()
const signedIn = computed(() => store.getters['auth/signedIn'])

const scrolled = ref(false)
const open = ref(false)
const bar = ref(null)
const onScroll = () => (scrolled.value = window.scrollY > 8)
let sizer = null
onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  sizer = new ResizeObserver(([entry]) =>
    document.documentElement.style.setProperty('--site-header-h', `${Math.round(entry.target.offsetHeight)}px`),
  )
  sizer.observe(bar.value)
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  sizer?.disconnect()
  document.documentElement.style.removeProperty('--site-header-h')
})

const nav = [
  { num: '04', label: 'Process', href: '#process' },
  { num: '05', label: 'Checks', href: '#checks' },
  { num: '08', label: 'Principles', href: '#principles' },
  { num: '09', label: 'Contact', href: '#contact' },
]
</script>

<template>
  <div
    ref="bar"
    class="sticky top-0 z-40 border-b bg-paper transition-[padding,border-color] duration-200"
    :class="scrolled ? 'border-ink py-0' : 'border-transparent py-2'"
  >
  <header class="wrap flex flex-wrap items-center justify-between gap-x-4 gap-y-3 py-3 lg:gap-x-8">
    <BrandMark :to="{ path: '/', hash: '#top' }" />

    <button
      type="button"
      class="flex size-10 items-center justify-center rounded border border-ink lg:hidden"
      :aria-expanded="open"
      aria-controls="site-menu"
      aria-label="Menu"
      @click="open = !open"
    >
      <svg width="18" height="14" viewBox="0 0 18 14" fill="none" class="stroke-ink" stroke-width="2">
        <path v-if="open" d="M3 1l12 12M15 1L3 13" />
        <path v-else d="M0 1h18M0 7h18M0 13h18" />
      </svg>
    </button>

    <div
      id="site-menu"
      class="w-full flex-col gap-5 border-t border-ink pt-4 pb-2 lg:contents"
      :class="open ? 'flex' : 'hidden'"
      @click="(e) => e.target.closest('a') && (open = false)"
    >
    <nav aria-label="Primary" class="flex flex-col gap-3 font-mono text-[15px] lg:flex-row lg:flex-wrap lg:gap-x-7 lg:gap-y-1.5 lg:text-[13px]">
      <a v-for="item in nav" :key="item.href" :href="item.href" class="flex gap-1.5 no-underline hover:underline">
        <span class="text-muted">{{ item.num }}</span>{{ item.label }}
      </a>
    </nav>

    <div class="flex items-center gap-5">
      <ThemeToggle />
      <RouterLink v-if="signedIn" to="/projects" class="font-mono text-[13px] underline-offset-4">Projects →</RouterLink>
      <RouterLink v-else to="/login" class="font-mono text-[13px] underline-offset-4">Log in</RouterLink>
    </div>
    </div>
  </header>
  </div>
</template>
