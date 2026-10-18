<script setup>
import BrandStamp from './BrandStamp.vue'

defineProps({
  to: { type: [String, Object], default: '/' },
})
</script>

<template>
  <RouterLink :to="to" class="flex items-center gap-2.5 no-underline sm:gap-3" aria-label="Hibanako home">
    <BrandStamp class="size-10 sm:size-12" />
    <span class="text-lg leading-none sm:text-2xl font-black tracking-[0.06em] [font-stretch:115%]">HIBANAKO</span>
  </RouterLink>
</template>
