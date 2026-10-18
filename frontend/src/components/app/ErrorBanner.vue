<script setup>
import { dismissError, errors } from '../../composables/useErrors'

const time = (d) => d.toLocaleTimeString(undefined, { timeStyle: 'short' })
</script>

<template>
  <div v-if="errors.length" role="alert" class="fixed right-4 bottom-4 z-50 flex w-[min(440px,calc(100vw-32px))] flex-col gap-2 print:hidden">
    <div
      v-for="e in errors"
      :key="e.id"
      class="flex items-start gap-3 border-2 border-reject bg-white px-3.5 py-3 shadow-[0_6px_18px_rgb(var(--shade)/0.18)]"
    >
      <span aria-hidden="true" class="mt-1 size-2.5 flex-none bg-reject"></span>
      <div class="flex min-w-0 flex-1 flex-col gap-0.5">
        <span class="font-mono text-[10.5px] font-bold tracking-[0.06em] text-reject">
          ERROR{{ e.context ? ` · ${e.context.toUpperCase()}` : '' }} · {{ time(e.at) }}
        </span>
        <span class="text-[13.5px] leading-[1.4] break-words">{{ e.message }}</span>
      </div>
      <button
        type="button"
        :aria-label="`Dismiss: ${e.message}`"
        class="size-6 flex-none cursor-pointer border border-ink/30 bg-white text-[11px] hover:border-ink"
        @click="dismissError(e.id)"
      >✕</button>
    </div>
  </div>
</template>
