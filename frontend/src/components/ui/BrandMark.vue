<script setup>
import BrandStamp from './BrandStamp.vue'

defineProps({
  to: { type: [String, Object], default: '/' },
})
</script>

<template>
  <RouterLink :to="to" class="flex items-center gap-2.5 no-underline sm:gap-3" aria-label="Hibanako home">
    <BrandStamp class="size-10 sm:size-12" />
    <span class="flex flex-col gap-[3px]">
      <span class="text-lg leading-none sm:text-2xl font-black tracking-[0.06em] [font-stretch:115%]">HIBANAKO</span>
      <span class="font-mono text-[8.5px] tracking-[0.04em] whitespace-nowrap text-muted sm:text-[10px] sm:tracking-[0.08em]">QUALITY TRACEABILITY SYSTEM<span class="max-sm:hidden"> / REV. A</span></span>
    </span>
  </RouterLink>
</template>
