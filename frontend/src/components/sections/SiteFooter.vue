<script setup>
import PoweredBy from '../ui/PoweredBy.vue'
import BrandStamp from '../ui/BrandStamp.vue'

const links = [
  { label: 'Process', href: '#process' },
  { label: 'Checks', href: '#checks' },
  { label: 'Principles', href: '#principles' },
  { label: 'Contact', href: '#contact' },
  { label: 'Terms', to: '/terms' },
  { label: 'Privacy', to: '/privacy' },
]
const sheet = [
  { label: 'SHEET', value: '10 OF 10' },
  { label: 'REV.', value: 'A' },
  { label: 'DATE', value: '2026-10-17' },
]
</script>

<template>
  <footer class="border-t border-ink font-mono text-xs">
    <div class="wrap flex flex-wrap justify-between gap-x-10 gap-y-7 pt-8 pb-7">
      <div class="flex max-w-[460px] flex-col gap-2">
        <span class="flex items-center gap-2.5">
          <BrandStamp class="size-11" />
          <span class="font-sans text-[28px] leading-none font-black tracking-[0.06em] [font-stretch:115%]">HIBANAKO</span>        </span>
        <span class="font-sans text-[15px] font-bold">Every weld, every cert, one thread.</span>
        <span class="text-muted">QUALITY TRACEABILITY SYSTEM / REV. A</span>
        <span class="leading-relaxed text-muted">
          Hibanako — from hibana, spark. Built with Google Gemini · Deployed on Google Cloud.
        </span>
      </div>
      <dl class="m-0 flex flex-wrap gap-x-8 gap-y-4">
        <div v-for="s in sheet" :key="s.label" class="flex flex-col gap-1">
          <dt class="text-[10px] text-muted">{{ s.label }}</dt>
          <dd class="m-0 font-bold">{{ s.value }}</dd>
        </div>
      </dl>
    </div>
    <div class="wrap flex flex-wrap items-center justify-between gap-4 pb-8">
      <nav aria-label="Footer" class="flex flex-wrap gap-5">
        <template v-for="l in links" :key="l.label">
          <RouterLink v-if="l.to" :to="l.to" class="underline-offset-[3px]">{{ l.label }}</RouterLink>
          <a v-else :href="l.href" class="underline-offset-[3px]">{{ l.label }}</a>
        </template>
      </nav>
      <div class="flex flex-wrap items-center gap-5 text-muted">
        <span>© 2026 HIBANAKO</span>
        <PoweredBy />
      </div>
    </div>
  </footer>
</template>
