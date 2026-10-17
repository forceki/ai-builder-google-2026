<script setup>
defineProps({
  num: { type: String, required: true },
  label: { type: String, required: true },
  inverted: { type: Boolean, default: false },
  labelId: { type: String, default: undefined },
})
</script>

<template>
  <div class="flex items-center gap-3 font-mono text-xs tracking-[0.08em]" data-trace-node :data-trace-num="num" :data-trace-label="label">
    <span class="font-bold">{{ num }}</span>
    <span class="h-px w-8" :class="inverted ? 'bg-paper' : 'bg-ink'"></span>
    <span :id="labelId" :class="inverted ? 'text-paper/65' : 'text-muted'">{{ label }}</span>
  </div>
</template>
