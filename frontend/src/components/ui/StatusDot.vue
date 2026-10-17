<script setup>
defineProps({
  status: { type: String, default: 'PASS' }, // PASS | HOLD | REJECT
  size: { type: String, default: 'size-[9px]' },
})
</script>

<template>
  <span
    aria-hidden="true"
    class="inline-block rounded-full border"
    :class="[
      size,
      status === 'HOLD' ? 'border-ink bg-signal' : status === 'REJECT' ? 'border-ink bg-ink' : 'border-ink/40 bg-pending',
    ]"
  ></span>
</template>
