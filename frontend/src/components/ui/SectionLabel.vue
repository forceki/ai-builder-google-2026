<script setup>
defineProps({
  label: { type: String, required: true },
  inverted: { type: Boolean, default: false },
  labelId: { type: String, default: undefined },
})
</script>

<template>
  <p :id="labelId" class="m-0 text-sm font-semibold text-signal" data-trace-node :data-trace-label="label">{{ label }}</p>
</template>
