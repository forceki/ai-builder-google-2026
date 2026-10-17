<script setup>
// Four decorative "screw heads" in the corners of a relatively positioned panel.
const bolts = [
  { pos: 'top-2.5 left-2.5', rot: 45 },
  { pos: 'top-2.5 right-2.5', rot: -30 },
  { pos: 'bottom-2.5 left-2.5', rot: 80 },
  { pos: 'bottom-2.5 right-2.5', rot: 15 },
]
</script>

<template>
  <span
    v-for="b in bolts"
    :key="b.pos"
    aria-hidden="true"
    class="absolute flex size-[9px] items-center justify-center rounded-full border border-ink/45 bg-bolt"
    :class="b.pos"
  >
    <span class="h-px w-[5px] bg-ink/60" :style="{ transform: `rotate(${b.rot}deg)` }"></span>
  </span>
</template>
