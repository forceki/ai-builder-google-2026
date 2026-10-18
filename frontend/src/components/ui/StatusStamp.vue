<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true }, // PASS | HOLD | REJECT | PENDING | FAIL
  rot: { type: Number, default: 0 },
  size: { type: String, default: 'md' }, // sm | md | lg
})

const tone = computed(() => ({
  PASS: '',
  HOLD: 'bg-signal',
  REJECT: 'bg-ink text-paper',
  PENDING: 'bg-signal',
  FAIL: 'bg-ink text-paper',
}[props.status] ?? ''))

const sizing = computed(() => ({
  sm: 'px-2.5 py-1 text-xs tracking-[0.12em]',
  md: 'px-2.5 py-1 text-[13px] tracking-[0.12em]',
  lg: 'px-3.5 py-1.5 text-[15px] tracking-[0.14em] outline outline-1 outline-offset-2 outline-ink',
}[props.size]))
</script>

<template>
  <span
    data-stamp
    :data-rot="rot"
    class="inline-block rounded-[3px] border-2 border-ink font-mono font-bold"
    :class="[tone, sizing]"
    :style="{ transform: `rotate(${rot}deg)` }"
  >{{ status }}</span>
</template>
