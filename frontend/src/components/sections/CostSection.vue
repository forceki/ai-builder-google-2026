<script setup>
import { computed, reactive } from 'vue'
import SectionLabel from '../ui/SectionLabel.vue'

// Illustrative comparison for one 40-joint pressure-vessel document package (about 120 files).
const rows = [
  { label: 'Reconciliation time', today: '2–3 engineer days of cross-checking', after: 'Under 2 hours reviewing flagged exceptions' },
  { label: 'When gaps surface', today: 'At final inspection or the customer audit', after: 'At plan review, before the first weld is made' },
  { label: 'Evidence trail', today: 'Spreadsheets, folders and memory', after: 'Every finding linked to its document and page' },
  { label: 'Consistency', today: 'Depends on who checks and how busy they are', after: 'The same code rules on every document package' },
  { label: 'Cost of a late miss', today: 'Cut-out, re-weld, re-inspection and a delayed shipment', after: 'A welder or procedure changed before welding' },
]

// Calculator: every input is the visitor's own figure, including the time saved.
const inputs = reactive({ documents: 8, hours: 20, rate: 55, saved: 70 })
const fields = [
  { key: 'documents', label: 'Documents released per month', min: 1, max: 60, step: 1, fmt: (v) => v },
  { key: 'hours', label: 'Engineer hours per document today', min: 2, max: 60, step: 1, fmt: (v) => `${v} h` },
  { key: 'rate', label: 'Loaded engineer cost per hour', min: 15, max: 150, step: 5, fmt: (v) => `$${v}` },
  { key: 'saved', label: 'Time saved on reconciliation', min: 20, max: 90, step: 5, fmt: (v) => `${v}%` },
]
const hoursYear = computed(() => Math.round(inputs.documents * 12 * inputs.hours * (inputs.saved / 100)))
const costYear = computed(() => hoursYear.value * inputs.rate)
const weeks = computed(() => (hoursYear.value / 40).toFixed(1))
const money = (v) => '$' + v.toLocaleString('en-US')
</script>

<template>
  <section id="cost" aria-labelledby="cost-h" class="wrap flex flex-col gap-[clamp(40px,5vw,64px)] pb-[clamp(64px,10vw,140px)]">
    <div class="flex max-w-[720px] flex-col gap-6">
      <SectionLabel label="The cost case" />
      <h2 id="cost-h" class="h-section text-balance">Less time on paperwork. Fewer surprises at audit.</h2>
      <p class="m-0 max-w-[560px] text-[17px] leading-[1.5]">
        An example: one 40-joint pressure-vessel document package, about 120 files, checked by hand and checked with Hibanako.
      </p>
    </div>

    <div class="overflow-hidden rounded border border-ink/15 bg-panel">
      <div class="grid grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)_minmax(0,1fr)] text-sm font-semibold max-md:hidden">
        <span class="px-5 py-3.5 text-muted">Example document</span>
        <span class="border-l border-ink/15 px-5 py-3.5 text-muted">Today</span>
        <span class="border-l border-ink bg-ink px-5 py-3.5 text-paper">With Hibanako</span>
      </div>
      <div
        v-for="r in rows"
        :key="r.label"
        data-reveal
        class="grid grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)_minmax(0,1fr)] border-t border-ink/15 max-md:grid-cols-1"
      >
        <span class="px-5 pt-4 pb-1 text-[15px] font-bold md:py-4">{{ r.label }}</span>
        <span class="px-5 py-1 text-[15px] leading-[1.45] text-muted md:border-l md:border-ink/15 md:py-4">
          <span class="font-semibold text-ink md:hidden">Today: </span>{{ r.today }}
        </span>
        <span class="bg-white px-5 pt-1 pb-4 text-[15px] leading-[1.45] font-semibold md:border-l md:border-ink md:py-4">
          <span class="text-signal md:hidden">With Hibanako: </span>{{ r.after }}
        </span>
      </div>
    </div>

    <div class="flex flex-wrap gap-x-[clamp(32px,5vw,72px)] gap-y-10 rounded border border-ink/15 bg-panel p-[clamp(20px,3vw,36px)]">
      <form class="flex min-w-0 flex-[1_1_340px] flex-col gap-6" aria-label="Savings estimate inputs" @submit.prevent>
        <h3 class="m-0 text-xl font-semibold tracking-[-0.01em]">Estimate your savings</h3>
        <label v-for="f in fields" :key="f.key" class="flex flex-col gap-2">
          <span class="flex justify-between gap-3 text-[15px]">
            <span>{{ f.label }}</span><strong class="tabular-nums">{{ f.fmt(inputs[f.key]) }}</strong>
          </span>
          <input v-model.number="inputs[f.key]" type="range" :min="f.min" :max="f.max" :step="f.step" class="w-full accent-signal" />
        </label>
      </form>

      <div class="flex min-w-0 flex-[1_1_280px] flex-col justify-between gap-8 rounded-[3px] border border-ink bg-white p-[clamp(20px,3vw,32px)]">
        <div class="flex flex-col gap-2" aria-live="polite">
          <span class="text-sm font-medium text-muted">Estimated saving per year</span>
          <span class="text-[clamp(40px,5vw,60px)] leading-none font-semibold tracking-[-0.04em] tabular-nums">{{ money(costYear) }}</span>
          <span class="text-base leading-[1.45]">
            <strong>{{ hoursYear.toLocaleString('en-US') }} engineer hours</strong> returned to quality work, about {{ weeks }} working weeks.
          </span>
        </div>
        <p class="m-0 text-xs leading-relaxed text-muted">
          Labour only. Excludes avoided rework, re-inspection and late-delivery costs. An estimate from your inputs, not a
          guarantee.
        </p>
      </div>
    </div>
  </section>
</template>
