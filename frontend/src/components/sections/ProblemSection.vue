<script setup>
import SectionLabel from '../ui/SectionLabel.vue'

const problems = [
  { code: 'Release delays', text: 'Finished work waits while an engineer re-checks every joint against its procedure, welder and material.' },
  { code: 'Problems found too late', text: 'A welder outside their qualified position, or a WPS outside its thickness range, is found at the customer audit instead of before welding.' },
  { code: 'Admin workload', text: 'Engineers read code clauses and cross-check WPS, WPQ and mill certificates by hand, joint by joint.' },
  { code: 'Rework cost', text: 'A missed PWHT requirement or a lapsed welder qualification means cutting out welds that were already finished.' },
]
const stats = [
  { value: '83%', text: 'of engineers spend at least 4 hours a week on procurement and supplier-related work.', source: 'Fictiv Manufacturing Survey, 2026' },
  { value: '52%', text: 'of manufacturing leaders call supplier quality, reliability and compliance a significant challenge.', source: 'Fictiv Manufacturing Survey, 2025' },
  { value: '33%', text: 'of manufacturers have invested in a unified data platform for their records.', source: 'Dun & Bradstreet Manufacturing Pulse, 2025' },
]
</script>

<template>
  <section aria-labelledby="prob-h" class="wrap flex flex-col gap-[clamp(48px,6vw,80px)] pb-[clamp(64px,10vw,140px)]">
    <div class="flex flex-wrap gap-x-[clamp(40px,6vw,96px)] gap-y-10">
      <div class="flex max-w-[560px] min-w-0 flex-[1_1_340px] flex-col gap-6">
        <SectionLabel label="The problem" />
        <h2 id="prob-h" class="h-section text-balance">Release decisions shouldn't depend on a folder hunt.</h2>
      </div>
      <dl class="m-0 grid min-w-0 flex-[1.2_1_420px] grid-cols-[repeat(auto-fit,minmax(min(100%,240px),1fr))] gap-10 pt-[clamp(0px,4vw,64px)]">
        <div v-for="p in problems" :key="p.code" data-reveal class="flex flex-col gap-2.5">
          <dt class="text-lg font-semibold tracking-[-0.01em]">{{ p.code }}</dt>
          <dd class="m-0 text-base leading-[1.55] text-muted">{{ p.text }}</dd>
        </div>
      </dl>
    </div>

    <ul class="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(min(100%,260px),1fr))] border-y border-ink p-0">
      <li
        v-for="(s, i) in stats"
        :key="s.value"
        data-reveal
        class="flex flex-col gap-3 py-7 sm:px-6"
        :class="{ 'border-ink/20 max-sm:border-t sm:border-l': i }"
      >
        <span class="text-[clamp(40px,4.4vw,56px)] leading-none font-semibold tracking-[-0.04em]">{{ s.value }}</span>
        <span class="text-base leading-[1.45]">{{ s.text }}</span>
        <span class="text-xs text-muted">{{ s.source }}</span>
      </li>
    </ul>
  </section>
</template>
