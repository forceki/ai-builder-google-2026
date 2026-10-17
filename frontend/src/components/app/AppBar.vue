<script setup>
import ThemeToggle from '../ui/ThemeToggle.vue'

defineProps({
  title: { type: String, default: '' },
  avatar: { type: Boolean, default: true },
})
</script>

<template>
  <header class="flex flex-wrap items-center gap-x-5 gap-y-2.5 border-b border-ink bg-paper px-4 py-2">
    <RouterLink to="/" class="flex flex-none items-center gap-2.5 no-underline">
      <span aria-hidden="true" class="size-2.5 border border-ink bg-signal"></span>
      <span class="text-xl leading-none font-black tracking-[-0.02em] [font-stretch:115%]">HEATMARK</span>
    </RouterLink>
    <slot name="title">
      <span class="flex-[1_1_160px] font-mono text-[11px] font-bold tracking-[0.06em]">{{ title }}</span>
    </slot>
    <div class="flex flex-none flex-wrap items-center gap-2">
      <slot name="status" />
      <ThemeToggle />
      <slot name="actions" />
      <span
        v-if="avatar"
        title="R. Lindqvist, Quality Engineer"
        class="flex size-8 items-center justify-center bg-ink font-mono text-xs font-bold text-paper"
      >RL</span>
    </div>
  </header>
</template>
