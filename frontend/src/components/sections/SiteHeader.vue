<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useStore } from 'vuex'
import BrandMark from '../ui/BrandMark.vue'
import ThemeToggle from '../ui/ThemeToggle.vue'

const store = useStore()
const signedIn = computed(() => store.getters['auth/signedIn'])

const scrolled = ref(false)
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
  <header class="wrap flex flex-wrap items-center justify-between gap-x-8 gap-y-3 py-3">
    <BrandMark :to="{ path: '/', hash: '#top' }" />

    <nav aria-label="Primary" class="flex flex-wrap gap-x-7 gap-y-1.5 font-mono text-[13px]">
      <a v-for="item in nav" :key="item.href" :href="item.href" class="flex gap-1.5 no-underline hover:underline">
        <span class="text-muted">{{ item.num }}</span>{{ item.label }}
      </a>
    </nav>

    <div class="flex items-center gap-5">
      <ThemeToggle />
      <RouterLink v-if="signedIn" to="/projects" class="font-mono text-[13px] underline-offset-4">Projects →</RouterLink>
      <RouterLink v-else to="/login" class="font-mono text-[13px] underline-offset-4">Log in</RouterLink>
      <a
        href="#contact"
        class="inline-flex items-center gap-2.5 rounded bg-graphite px-4 py-[11px] font-mono text-xs font-bold tracking-[0.08em] text-paper uppercase no-underline shadow-[inset_0_-3px_0_#000] hover:text-paper active:translate-y-0.5 active:shadow-[inset_0_-1px_0_#000]"
      >
        <span aria-hidden="true" class="size-[7px] rounded-full bg-signal"></span>Request demo
      </a>
    </div>
  </header>
  </div>
</template>
