<script setup>
import BrandStamp from '../ui/BrandStamp.vue'

const links = [
  { label: 'Contact', href: '#contact' },
  { label: 'Terms', to: '/terms' },
  { label: 'Privacy', to: '/privacy' },
]
</script>

<template>
  <footer class="border-t border-ink/15 text-sm">
    <div class="wrap flex flex-wrap items-start justify-between gap-x-10 gap-y-6 pt-10 pb-6">
      <div class="flex max-w-[420px] flex-col gap-3">
        <span class="flex items-center gap-2.5">
          <BrandStamp class="size-9" />
          <span class="text-xl leading-none font-bold tracking-[-0.01em]">Hibanako</span>
        </span>
        <span class="text-muted">Weld quality assurance for when trust matters.</span>
      </div>
      <nav aria-label="Footer" class="flex flex-wrap gap-6 font-medium">
        <template v-for="l in links" :key="l.label">
          <RouterLink v-if="l.to" :to="l.to" class="no-underline hover:underline">{{ l.label }}</RouterLink>
          <a v-else :href="l.href" class="no-underline hover:underline">{{ l.label }}</a>
        </template>
      </nav>
    </div>
    <div class="wrap flex flex-wrap justify-between gap-3 border-t border-ink/10 pt-5 pb-8 text-[13px] text-muted">
      <span>© 2026 Hibanako. All rights reserved.</span>
      <span>Powered by Shoyupuro</span>
    </div>
  </footer>
</template>
