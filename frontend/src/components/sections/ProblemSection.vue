<script setup>
import SectionLabel from '../ui/SectionLabel.vue'

const problems = [
  { code: 'P-01 RELEASE DELAYS', text: 'Finished parts wait while someone confirms that every cert and report is on file.' },
  { code: 'P-02 MISSING EVIDENCE', text: 'A weld without an NDT record gets found at the customer audit instead of before shipment.' },
  { code: 'P-03 ADMIN WORKLOAD', text: 'Quality engineers spend days cross-referencing registers and certificates by hand.' },
  { code: 'P-04 REWORK COST', text: 'Late findings mean cutting out welds and re-inspecting parts that were already finished.' },
]
</script>

<template>
  <section aria-labelledby="prob-h" class="wrap flex flex-wrap gap-x-[clamp(40px,6vw,96px)] gap-y-10 pb-[clamp(64px,10vw,140px)]">
    <div class="flex max-w-[560px] min-w-0 flex-[1_1_340px] flex-col gap-6">
      <SectionLabel num="03" label="THE PROBLEM" />
      <h2 id="prob-h" class="h-section text-balance">Release decisions shouldn't depend on a folder hunt.</h2>
    </div>
    <dl class="m-0 grid min-w-0 flex-[1.2_1_420px] grid-cols-[repeat(auto-fit,minmax(min(100%,240px),1fr))] gap-10 pt-[clamp(0px,4vw,64px)]">
      <div v-for="p in problems" :key="p.code" data-reveal class="flex flex-col gap-2.5">
        <dt class="flex items-center gap-2.5 font-mono text-xs font-bold tracking-[0.06em]">
          <span aria-hidden="true" class="size-2 rounded-full bg-ink"></span>{{ p.code }}
        </dt>
        <dd class="m-0 text-[17px] leading-[1.45]">{{ p.text }}</dd>
      </div>
    </dl>
  </section>
</template>
