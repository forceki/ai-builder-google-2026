<script setup>
import { STAMP } from '../../lib/status'

defineProps({
  status: { type: String, required: true }, // PASS | HOLD | REJECT
})
</script>

<template>
  <span class="inline-block border-2 font-mono font-bold" :class="STAMP[status]">{{ status }}</span>
</template>
