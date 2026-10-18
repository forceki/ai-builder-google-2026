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
      ['HOLD', 'PENDING'].includes(status) ? 'border-ink bg-signal' : ['REJECT', 'FAIL'].includes(status) ? 'border-ink bg-ink' : 'border-ink/40 bg-pending',
    ]"
  ></span>
</template>
