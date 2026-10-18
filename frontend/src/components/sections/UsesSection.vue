<script setup>
import SectionLabel from '../ui/SectionLabel.vue'

// The two purposes an assessment can be run for (step 1, "What is this assessment for?"). Rows line up across the
// two cards so they read as a comparison; the sample results come from example-docs/not-acceptable.
const ROWS = ['Asks', 'When', 'Welder qualification', 'What decides it', 'Outcome']

const uses = [
  {
    n: '01',
    key: 'production',
    title: 'Production release',
    lead: 'New fabrication, checked before the first weld and again before it ships.',
    rows: {
      Asks: 'Can this ship?',
      When: 'Plan review before fabrication, then the as-built record before release.',
      'Welder qualification': 'Mandatory. No WPQ is a high alert: the work is deemed rejected.',
      'What decides it': 'Every rule of the governing code, on every joint: material, WPS, welders, PWHT, NDE, hydrotest.',
      Outcome: 'Acceptable, acceptable with notes or not acceptable, ready for sign-off.',
    },
    wpq: 'MANDATORY',
    sample: { stamp: 'DEEMED REJECTED', tone: 'reject', rule: 'S-WPQ-00', text: 'Production welds without any welder qualification (WPQ).' },
    cta: 'Start a production release',
  },
  {
    n: '02',
    key: 'investigation',
    title: 'Failure investigation',
    lead: 'Equipment already built or in service, where something leaked, cracked or failed a test.',
    rows: {
      Asks: 'Why did it fail?',
      When: 'After a failure, an audit finding or a third-party query on equipment that exists.',
      'Welder qualification': 'Optional. The welds are made; a welder issue is recorded as a possible contributing cause.',
      'What decides it': 'The evidence that explains failures: material and toughness, PWHT and heat treatment, mechanical results, NDE.',
      Outcome: 'The candidate causes, ranked, each with the clause it breaks and the page it was read from.',
    },
    wpq: 'OPTIONAL',
    sample: { stamp: 'CANDIDATE CAUSE', tone: 'signal', rule: 'X-15', text: 'Load L-01 held 35 min at 620 °C; 48 min required for 20 mm.' },
    cta: 'Start an investigation',
  },
]
</script>

<template>
  <section id="uses" aria-labelledby="uses-h" class="wrap flex flex-col gap-[clamp(32px,4vw,56px)] pb-[clamp(64px,10vw,140px)]">
    <div class="flex flex-wrap items-end justify-between gap-x-10 gap-y-5">
      <div class="flex max-w-[680px] flex-col gap-6">
        <SectionLabel label="Two ways to use it" />
        <h2 id="uses-h" class="h-section text-balance">Release new work. Investigate a failure.</h2>
      </div>
      <p class="m-0 max-w-[440px] text-[17px] leading-[1.5] text-muted">
        The same rules and the same documents, asked a different question. Pick the purpose when you set the conditions;
        Hibanako changes what it requires and what decides the result.
      </p>
    </div>

    <div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,420px),1fr))] gap-x-4 gap-y-6">
      <article
        v-for="u in uses"
        :key="u.key"
        data-reveal
        :aria-labelledby="`use-${u.key}`"
        class="row-span-7 grid grid-rows-subgrid gap-y-0 overflow-hidden rounded border bg-panel shadow-[inset_0_-3px_0_rgb(var(--shade)/0.08)]"
        :class="u.key === 'production' ? 'border-ink' : 'border-ink/15'"
      >
        <header class="flex flex-col gap-3 border-b border-ink/15 p-6" :class="u.key === 'production' ? 'bg-ink text-paper' : ''">
          <div class="flex items-center justify-between font-mono text-[11px] tracking-[0.08em]" :class="u.key === 'production' ? 'opacity-70' : 'text-muted'">
            <span>PURPOSE {{ u.n }}</span>
            <span>WPQ · {{ u.wpq }}</span>
          </div>
          <h3 :id="`use-${u.key}`" class="m-0 text-[26px] leading-[1.1] font-semibold tracking-[-0.02em]">{{ u.title }}</h3>
          <p class="m-0 text-[15.5px] leading-[1.45]" :class="u.key === 'production' ? 'opacity-85' : 'text-muted'">{{ u.lead }}</p>
        </header>

        <dl class="contents">
          <div
            v-for="r in ROWS"
            :key="r"
            class="grid grid-cols-[minmax(0,150px)_minmax(0,1fr)] gap-4 border-b border-dashed border-ink/20 px-6 py-3.5 max-sm:grid-cols-1 max-sm:gap-1"
          >
            <dt class="font-mono text-[11px] leading-[1.6] font-bold tracking-[0.06em] text-muted uppercase">{{ r }}</dt>
            <dd class="m-0 text-[15px] leading-[1.45]" :class="r === 'Asks' ? 'font-semibold' : ''">{{ u.rows[r] }}</dd>
          </div>
        </dl>

        <div class="flex flex-col gap-2.5 px-6 pt-5 pb-6">
          <span class="font-mono text-[10.5px] tracking-[0.08em] text-muted">SAMPLE RESULT · V-110 SKID</span>
          <div class="flex flex-wrap items-center gap-3 rounded-[3px] border border-ink/20 bg-white px-3.5 py-3">
            <span
              class="-rotate-2 border-2 px-2 py-0.5 font-mono text-[11px] font-bold tracking-[0.08em] whitespace-nowrap"
              :class="u.sample.tone === 'reject' ? 'border-reject text-reject' : 'border-signal text-signal'"
            >{{ u.sample.stamp }}</span>
            <span class="min-w-[200px] flex-1 text-[14px] leading-[1.4]">
              <span class="font-mono text-[11.5px] font-bold">{{ u.sample.rule }}</span> · {{ u.sample.text }}
            </span>
          </div>
          <RouterLink to="/projects" class="mt-2 self-start text-[15px] font-semibold underline-offset-4">{{ u.cta }} →</RouterLink>
        </div>
      </article>
    </div>
  </section>
</template>
