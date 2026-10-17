<script setup>
import BrandStamp from './BrandStamp.vue'

defineProps({
  to: { type: [String, Object], default: '/' },
})
</script>

<template>
  <RouterLink :to="to" class="flex items-center gap-3 no-underline" aria-label="Hibanako home">
    <BrandStamp class="size-12" />
    <span class="flex flex-col gap-[3px]">
      <span class="text-2xl leading-none font-black tracking-[0.06em] [font-stretch:115%]">HIBANAKO</span>
      <span class="font-mono text-[10px] tracking-[0.08em] text-muted">QUALITY TRACEABILITY SYSTEM / REV. A</span>
    </span>
  </RouterLink>
</template>
