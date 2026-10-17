<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'
import SectionLabel from '../ui/SectionLabel.vue'
import StatusStamp from '../ui/StatusStamp.vue'

const store = useStore()
const sample = computed(() => store.state.report.sample)
</script>

<template>
  <section
    aria-labelledby="rep-h"
    class="wrap flex flex-wrap-reverse items-start gap-x-[clamp(40px,6vw,96px)] gap-y-10 pb-[clamp(64px,10vw,140px)]"
  >
    <div class="relative min-w-0 flex-[2_1_560px] rounded border border-ink/15 bg-panel px-[clamp(12px,3vw,32px)] pt-5 pb-[clamp(24px,3vw,36px)]">
      <div class="flex items-center justify-between gap-3 px-1 pb-3.5 font-mono text-[11px] tracking-[0.08em] text-muted">
        <span class="flex items-center gap-2">
          <span aria-hidden="true" class="size-2 rounded-full border border-ink bg-signal"></span>OUTPUT
        </span>
        <span>SPECIMEN — PLACEHOLDER DATA</span>
      </div>
      <div aria-hidden="true" class="h-2 rounded bg-graphite"></div>

      <article
        aria-label="Sample release-readiness report"
        class="mx-[clamp(8px,2vw,20px)] flex flex-col gap-[22px] border border-t-0 border-ink/20 bg-white p-[clamp(18px,3vw,32px)] font-mono"
      >
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="flex flex-col gap-1">
            <span class="font-sans text-[22px] font-black tracking-[-0.01em]">Release readiness report</span>
            <span class="text-[11px] text-muted">FORM HM-RR-01</span>
          </div>
          <StatusStamp :status="sample.status" :rot="-5" size="lg" />
        </div>

        <dl class="m-0 grid grid-cols-[repeat(auto-fit,minmax(130px,1fr))] gap-x-5 gap-y-3.5 text-xs">
          <div v-for="m in sample.meta" :key="m.label" class="flex flex-col gap-[3px]">
            <dt class="text-[10px] text-muted">{{ m.label }}</dt>
            <dd class="m-0 font-bold">{{ m.value }}</dd>
          </div>
        </dl>

        <div class="flex flex-wrap gap-x-5 gap-y-2 border-y border-ink py-2.5 text-xs">
          <span v-for="t in sample.totals" :key="t">{{ t }}</span>
        </div>

        <ol class="m-0 flex list-none flex-col p-0">
          <li
            v-for="(f, i) in sample.findings"
            :key="f.title"
            class="grid grid-cols-[32px_minmax(0,1fr)_auto] items-start gap-x-3.5 gap-y-1 py-3.5"
            :class="{ 'border-b border-dashed border-ink/30': i < sample.findings.length - 1 }"
          >
            <span class="text-xs text-muted">{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="flex flex-col gap-1">
              <span class="font-sans text-base font-bold">{{ f.title }}</span>
              <span class="text-xs leading-normal">{{ f.detail }}</span>
              <span class="text-[11px] text-muted">{{ f.source }}</span>
            </span>
            <StatusStamp :status="f.status" :rot="f.rot" size="sm" />
          </li>
        </ol>

        <div class="flex flex-wrap items-end gap-x-8 gap-y-5 pt-1.5 text-[11px]">
          <span class="flex-[1_1_200px] leading-normal text-muted">Status set by rule set RS-2.1. Explanations generated for review.</span>
          <span class="flex flex-[1_1_200px] flex-col gap-1.5">
            <span class="text-muted">APPROVED BY (QUALITY ENGINEER)</span>
            <span class="h-7 border-b border-ink"></span>
          </span>
        </div>
      </article>
    </div>

    <div class="flex max-w-[440px] min-w-0 flex-[1_1_300px] flex-col gap-6 pt-[clamp(0px,3vw,40px)]">
      <SectionLabel num="07" label="SAMPLE REPORT" />
      <h2 id="rep-h" class="h-section">The release-readiness report.</h2>
      <p class="m-0 text-[17px] leading-[1.45]">Findings ranked by release impact, each with the document and page it came from.</p>
    </div>
  </section>
</template>
