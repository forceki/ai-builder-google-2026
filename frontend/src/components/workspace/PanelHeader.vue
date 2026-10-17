<script setup>
defineProps({
  title: { type: String, required: true },
  meta: { type: String, default: '' },
})
</script>

<template>
  <div class="flex justify-between gap-3 border-b border-ink px-3.5 py-2 font-mono text-[11px] tracking-[0.08em]">
    <span class="font-bold">{{ title }}</span><span class="text-faint">{{ meta }}</span>
  </div>
</template>
