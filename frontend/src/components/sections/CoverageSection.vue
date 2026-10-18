<script setup>
import SectionLabel from '../ui/SectionLabel.vue'

const sectors = [
  {
    id: 'A', name: 'Plant', dot: 'border-ink bg-signal',
    text: 'Pressure vessels, refinery and petrochemical piping, power boilers, pipelines.',
    governing: ['ASME VIII-1', 'ASME B31.3', 'ASME I', 'ASME B31.1', 'API 1104'],
    qualification: 'ASME IX · ASME V',
    supplementary: 'NACE MR0103 · NACE MR0175 / ISO 15156 · Lethal service · Impact tested',
  },
  {
    id: 'B', name: 'Shipbuilding', dot: 'border-ink bg-ink',
    text: 'Commercial hulls under class rules, and naval ship and submarine structures.',
    governing: ['IACS Rec. 47', 'ABS · DNV · LR', 'MIL-STD-1689', 'NAVSEA 009-12'],
    qualification: 'ISO 9606-1 · AWS D1.1 · class NDE plan',
    supplementary: 'ISO 3834-2 · ISO 5817 level B · Impact tested',
  },
  {
    id: 'C', name: 'Manufacturing', dot: 'border-ink/40 bg-pending',
    text: 'Structural steel, machinery and heavy equipment, cranes, rail vehicles, general fabrication.',
    governing: ['AWS D1.1', 'EN 1090-2', 'AWS D14.1', 'AWS D14.3', 'EN 15085', 'ISO 3834'],
    qualification: 'ISO 15614-1 · ISO 9606-1 · AWS D1.1 · ISO 5817',
    supplementary: 'EN 1090-2 EXC3 · ISO 5817 level B · Cyclically loaded · AWS D1.8 seismic',
  },
]
</script>

<template>
  <section id="coverage" aria-labelledby="cov-h" class="wrap flex flex-col gap-[clamp(32px,4vw,48px)] pb-[clamp(64px,10vw,140px)]">
    <div class="flex flex-wrap items-end justify-between gap-6">
      <div class="flex max-w-[720px] flex-col gap-6">
        <SectionLabel num="05·B" label="ALL WELDING" />
        <h2 id="cov-h" class="h-section text-balance">Plant, ship or shop floor. Checked to your code.</h2>
        <p class="m-0 max-w-[600px] text-lg leading-normal text-pretty">
          Pick where the work is used and the governing standard. Hibanako checks each WPS, WPQ and mill certificate against
          that standard and any supplementary requirement you add.
        </p>
      </div>
      <RouterLink
        to="/projects"
        class="inline-flex items-center gap-3 rounded border border-ink bg-white px-[22px] py-3.5 font-mono text-[13px] font-bold tracking-[0.08em] whitespace-nowrap text-ink uppercase no-underline shadow-[inset_0_-4px_0_rgb(var(--shade)/0.12)] hover:text-ink"
      >
        Start an assessment →
      </RouterLink>
    </div>

    <div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] gap-4">
      <article
        v-for="s in sectors"
        :key="s.id"
        data-reveal
        class="flex flex-col gap-[18px] rounded border border-ink/15 bg-panel p-7 shadow-[inset_0_-3px_0_rgb(var(--shade)/0.08)]"
      >
        <div class="flex items-center justify-between font-mono text-xs tracking-[0.06em] text-muted">
          <span>SECTOR {{ s.id }}</span><span aria-hidden="true" class="size-[9px] rounded-full border" :class="s.dot"></span>
        </div>
        <h3 class="m-0 text-[30px] font-extrabold tracking-[-0.025em]">{{ s.name }}</h3>
        <p class="m-0 text-[15px] leading-[1.55] text-muted">{{ s.text }}</p>
        <div class="flex flex-col gap-2 border-t border-dashed border-ink/30 pt-3.5 font-mono">
          <span class="text-xs tracking-[0.06em] text-muted">GOVERNING</span>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="g in s.governing"
              :key="g"
              class="rounded-[3px] border border-ink bg-white px-2 py-[3px] text-xs font-bold whitespace-nowrap"
            >{{ g }}</span>
          </div>
          <span class="pt-1.5 text-xs tracking-[0.06em] text-muted">QUALIFICATION · NDE</span>
          <span class="text-[12.5px]">{{ s.qualification }}</span>
          <span class="pt-1.5 text-xs tracking-[0.06em] text-muted">SUPPLEMENTARY</span>
          <span class="text-[12.5px] leading-normal">{{ s.supplementary }}</span>
        </div>
      </article>
    </div>
  </section>
</template>
