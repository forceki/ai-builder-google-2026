<script setup>
defineProps({
  to: { type: [String, Object], default: '/' },
})
</script>

<template>
  <RouterLink :to="to" class="flex items-center gap-3.5 no-underline">
    <span aria-hidden="true" class="size-3 rounded-full border border-ink bg-signal"></span>
    <span class="flex flex-col gap-[3px]">
      <span class="text-2xl leading-none font-black tracking-[-0.02em] [font-stretch:115%]">HEATMARK</span>
      <span class="font-mono text-[10px] tracking-[0.08em] text-muted">QUALITY TRACEABILITY SYSTEM / REV. A</span>
    </span>
  </RouterLink>
</template>
