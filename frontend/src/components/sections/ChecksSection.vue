<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'
import SectionLabel from '../ui/SectionLabel.vue'
import StatusStamp from '../ui/StatusStamp.vue'
import StatusDot from '../ui/StatusDot.vue'

const store = useStore()
const checks = computed(() => store.state.report.checks)
</script>

<template>
  <section id="checks" aria-labelledby="chk-h" class="wrap flex flex-wrap gap-x-[clamp(40px,5vw,72px)] gap-y-10 py-[clamp(64px,10vw,140px)]">
    <div class="flex max-w-[420px] min-w-0 flex-[1_1_300px] flex-col gap-6">
      <SectionLabel label="Critical checks" />
      <h2 id="chk-h" class="h-section">Four checks. Most of the risk.</h2>
      <p class="m-0 text-[17px] leading-[1.55] text-muted">We focus on the few checks behind most release delays, and run them on every document package.</p>
    </div>
    <div class="grid min-w-0 flex-[2_1_560px] grid-cols-[repeat(auto-fit,minmax(min(100%,270px),1fr))] gap-4">
      <article
        v-for="c in checks"
        :key="c.id"
        data-reveal
        class="relative flex flex-col gap-3.5 rounded border border-ink/15 bg-panel p-6 shadow-[inset_0_-3px_0_rgb(var(--shade)/0.08)]"
      >
        <div class="flex items-center justify-between font-mono text-[11px] tracking-[0.08em] text-muted">
          <span>CHECK {{ c.id }}</span>
          <StatusDot :status="c.status" />
        </div>
        <h3 class="m-0 text-xl font-semibold tracking-[-0.015em]">{{ c.title }}</h3>
        <p class="m-0 flex-1 text-base leading-[1.45]">{{ c.question }}</p>
        <div class="flex items-center gap-3 border-t border-dashed border-ink/30 pt-3 font-mono text-xs">
          <StatusStamp :status="c.status" :rot="c.rot" />{{ c.note }}
        </div>
      </article>
    </div>
  </section>
</template>
