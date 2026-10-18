<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import SectionLabel from '../ui/SectionLabel.vue'

// Three sample runs the hero cycles through: AI reads and sorts five documents, then the rules check them.
const HERO = [
  { label: 'PLANT', equip: 'Pressure vessel', gov: 'ASME VIII-1 · IX · V', short: 'ASME VIII-1', supp: 'NACE MR0103', mode: 'PLAN REVIEW', dwg: '/drawings/dwg-vessel.png',
    docs: [
      { slot: 'MTC', f: 'MTC_4A7721.pdf', v: 'SA-516 Gr.70 · 40 mm', ch: [['HEAT', '4A7721'], ['GRADE', 'SA-516 70'], ['T', '40 mm']] },
      { slot: 'WPS', f: 'WPS-07_PQR-07.pdf', v: 'GTAW+SMAW · PWHT', ch: [['PROC', 'GTAW+SMAW'], ['RANGE', '5–50 mm'], ['PWHT', '620 °C']] },
      { slot: 'WPQ', f: 'WPQ-118.pdf', v: 'Welder 118 · 6G', ch: [['WELDER', '118'], ['POS', '6G'], ['LAST USE', '18 d']] },
      { slot: 'DWG', f: 'HBK-PV-110_WeldMap.pdf', v: '3 joints', ch: [['JOINTS', 'W-11 W-12 W-14'], ['NDE', 'RT 100%']] },
      { slot: 'ASB', f: '— not submitted', v: 'Plan review', skip: true, ch: [['AS-BUILT', 'none'], ['MODE', 'PLAN']] },
    ],
    checks: [['Material', 'PASS'], ['PWHT', 'REQUIRED'], ['WPS', 'PASS'], ['Welder', 'PASS'], ['MR0103', 'PASS']],
    verdict: 'ACCEPTABLE', text: '40 mm exceeds 38 mm, so PWHT is required (UCS-56). WPS-07 is qualified with PWHT. Fabrication may proceed.' },
  { label: 'SHIPBUILDING', equip: 'Hull block', gov: 'IACS Rec. 47 + ABS', short: 'IACS REC. 47', supp: 'ISO 5817 B', mode: 'AS-BUILT', dwg: '/drawings/dwg-hull.png',
    docs: [
      { slot: 'MTC', f: 'MTC_3C0954.pdf', v: 'S355J2+N · 12 mm', ch: [['HEAT', '3C0954'], ['CVN', '48 J @ -20 °C']] },
      { slot: 'WPS', f: 'WPS-09_PQR-09.pdf', v: 'FCAW · 5–20 mm', ch: [['PROC', 'FCAW'], ['RANGE', '5–20 mm']] },
      { slot: 'WPQ', f: 'WPQ-204.pdf', v: 'Welder 204 · 2G', ch: [['WELDER', '204'], ['POS', 'F, H only']] },
      { slot: 'DWG', f: 'BLK-07_WeldMap.pdf', v: '2 joints', ch: [['JOINTS', 'W-17 W-22'], ['W-22', '4F overhead']] },
      { slot: 'ASB', f: 'ASB_BLK-07.pdf', v: 'Welders logged', ch: [['W-22', 'welder 204'], ['VT', '100%']] },
    ],
    checks: [['Material', 'PASS'], ['PWHT', 'N/A'], ['WPS', 'PASS'], ['Welder', 'FAIL'], ['ISO 5817', 'PASS']],
    verdict: 'NOT ACCEPTABLE', text: 'W-22 is an overhead fillet (4F). Welder 204 is qualified for flat and horizontal only.' },
  { label: 'MANUFACTURING', equip: 'Steel frame', gov: 'AWS D1.1', short: 'AWS D1.1', supp: 'EN 1090-2 EXC3', mode: 'PLAN REVIEW', dwg: '/drawings/dwg-frame.png',
    docs: [
      { slot: 'MTC', f: 'MTC_7D1180.pdf', v: 'A572 Gr.50 · 16 mm', ch: [['HEAT', '7D1180'], ['CE', '0.41']] },
      { slot: 'WPS', f: 'WPS-12_PQR-12.pdf', v: 'GMAW · 3–32 mm', ch: [['PROC', 'GMAW'], ['RANGE', '3–32 mm']] },
      { slot: 'WPQ', f: 'WQ-310.pdf', v: 'Welder 310 · 3G+4G', ch: [['WELDER', '310'], ['POS', '3G + 4G']] },
      { slot: 'DWG', f: 'FR-220_WeldMap.pdf', v: '4 joints', ch: [['JOINTS', '4'], ['NDE', 'VT · UT 10%']] },
      { slot: 'ERR', f: 'IMG_4471.jpg', v: 'Not a standard document', err: true, ch: [['TEXT', 'not legible'], ['TYPE', 'unknown']] },
    ],
    checks: [['Material', 'PASS'], ['PWHT', 'N/A'], ['WPS', 'PASS'], ['Welder', 'PASS'], ['EXC3', 'PENDING']],
    verdict: 'INCOMPLETE', text: 'IMG_4471.jpg was flagged: no legible text. The ISO 3834-2 certificate needed for EXC3 is missing.' },
]
const RESULT = { PASS: 'var(--color-pass)', FAIL: 'var(--color-reject)', REQUIRED: 'var(--color-ink)', 'N/A': 'var(--color-faint)', PENDING: 'var(--color-faint)' }
const SLOTS = [['MTC', 'Mill certificate'], ['WPS', 'WPS / PQR'], ['WPQ', 'Welder qual.'], ['DWG', 'Weld drawing'], ['ASB', 'As-built'], ['ERR', 'Flagged']]
const TICKS = 25

const hc = ref(0)
const ht = ref(0)
let timer = null

function start() {
  clearInterval(timer)
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    ht.value = 99
    return
  }
  timer = setInterval(() => {
    if (ht.value >= TICKS) {
      ht.value = 0
      hc.value = (hc.value + 1) % HERO.length
    } else ht.value++
  }, 450)
}
function pick(i) {
  hc.value = i
  ht.value = 0
  start()
}
onMounted(() => {
  start()
  // Warm the weld-map drawings so the DWG page doesn't paint blank on its first pass.
  HERO.forEach((c) => (new Image().src = c.dwg))
})
onBeforeUnmount(() => clearInterval(timer))

const H = computed(() => HERO[hc.value])
// Ticks 0–14 read one document every three ticks (lift, scan, file away); 15–19 run the checks; 20+ stamps the verdict.
const docPhase = computed(() => ht.value < 15)
const di = computed(() => (docPhase.value ? Math.floor(ht.value / 3) : 3))
const sub = computed(() => (docPhase.value ? ht.value % 3 : 1))
const doc = computed(() => H.value.docs[di.value])
// The weld drawing page shows the category's sample drawing instead of placeholder text lines.
const drawing = computed(() => (doc.value.slot === 'DWG' ? H.value.dwg : null))
const stamped = computed(() => ht.value >= 20)
const checksOn = computed(() => Math.max(0, Math.min(5, ht.value - 14)))

const docType = computed(() => {
  const d = doc.value
  return d.err ? 'UNKNOWN FILE' : d.skip ? 'AS-BUILT' : SLOTS.find((s) => s[0] === d.slot)[1].toUpperCase()
})
const paperStyle = computed(() => ({
  transform:
    sub.value === 0 && docPhase.value ? 'translateY(-10px) rotate(-1.5deg)' : sub.value === 2 ? 'translate(60px,-4px) rotate(5deg) scale(0.92)' : 'none',
  opacity: sub.value === 2 ? 0 : 1,
}))
const scanStyle = computed(() => ({
  top: sub.value >= 1 ? '100%' : '0%',
  opacity: docPhase.value && sub.value < 2 ? 1 : 0,
  transition: sub.value === 1 && docPhase.value ? 'top .9s linear, height .9s linear' : 'none',
}))
const scanFill = computed(() => ({ ...scanStyle.value, top: 0, height: scanStyle.value.top }))

const slots = computed(() =>
  SLOTS.map(([k, label]) => {
    const i = H.value.docs.findIndex((d) => d.slot === k)
    const d = H.value.docs[i]
    const on = i >= 0 && ht.value >= 3 * i + 2
    const landing = i >= 0 && ht.value === 3 * i + 2
    if (on && k === 'ERR') return { k, v: d.f, mark: '✕', state: 'err', landing }
    if (on && d.skip) return { k, v: 'None · plan review', mark: '—', state: 'skip', landing: false }
    return { k, v: on ? d.v : label, mark: on ? '✓' : '', state: on ? 'on' : 'off', landing }
  }),
)
const checks = computed(() =>
  H.value.checks.map(([l, v], j) => {
    const on = j < checksOn.value
    return { l, v: on ? v : '···', on, result: v, pop: on && j === checksOn.value - 1 && !stamped.value }
  }),
)
const railW = computed(() => (checksOn.value <= 1 ? 0 : ((checksOn.value - 1) / 4) * 80) + '%')
const verdictColor = computed(() =>
  RESULT[H.value.verdict === 'ACCEPTABLE' ? 'PASS' : H.value.verdict === 'NOT ACCEPTABLE' ? 'FAIL' : 'PENDING'],
)
const verdictText = computed(() =>
  stamped.value
    ? H.value.text
    : docPhase.value
      ? `Reading ${doc.value.f.replace('— ', '')}…`
      : `Applying ${H.value.short} rules to each joint…`,
)
</script>

<template>
  <section
    id="top"
    aria-labelledby="hero-h"
    class="wrap flex flex-wrap items-center gap-[clamp(40px,5vw,72px)] pt-[clamp(40px,7vw,96px)] pb-[clamp(64px,10vw,140px)]"
  >
    <div class="flex min-w-0 flex-[1_1_420px] flex-col gap-7">
      <SectionLabel label="Weld quality assurance" />
      <h1 id="hero-h" class="m-0 text-[clamp(40px,5.2vw,68px)] leading-[1.05] font-semibold tracking-[-0.035em] text-balance">
        Release decisions for when trust matters.
      </h1>
      <p data-reveal class="m-0 max-w-[500px] text-[clamp(17px,1.4vw,19px)] leading-[1.6] text-pretty">
        Hibanako checks every joint in a welding document package against your governing code: mill certificates, WPS and PQR,
        welder qualifications and PWHT. Use it for production release, from plan review to the as-built record, or for
        failure investigation, to find the cause in the records.
      </p>
      <div class="flex flex-wrap items-center gap-6 pt-2">
        <a href="#contact" class="btn-cta">Request a demo</a>
        <a href="#cost" class="text-[15px] font-semibold underline-offset-4">See how it helps →</a>
      </div>
      <span class="text-sm text-muted">
        For plant, shipbuilding and manufacturing teams. <a href="#coverage" class="font-medium">See supported codes</a>
      </span>
    </div>

    <figure
      aria-label="Live prototype: Hibanako reads weld documents, sorts them, checks them against the governing standard and stamps a verdict"
      class="relative m-0 flex min-w-0 flex-[1.25_1_520px] flex-col gap-3.5 rounded border border-ink/18 bg-panel p-[18px] shadow-[inset_0_-3px_0_rgb(var(--shade)/0.1)]"
    >
      <div
        role="tablist"
        aria-label="Category"
        class="flex overflow-hidden rounded-[3px] border border-ink bg-white font-mono text-xs font-bold tracking-[0.05em]"
      >
        <button
          v-for="(c, i) in HERO"
          :key="c.label"
          type="button"
          role="tab"
          :aria-selected="i === hc"
          class="relative flex-1 cursor-pointer overflow-hidden border-0 px-2 py-2.5 whitespace-nowrap max-sm:px-1 max-sm:text-[10px]"
          :class="[i === hc ? 'bg-ink text-paper' : 'bg-white text-ink', i ? 'border-l border-ink' : '']"
          @click="pick(i)"
        >
          {{ c.label }}
          <span
            aria-hidden="true"
            class="absolute bottom-0 left-0 h-[3px] bg-signal transition-[width] duration-[450ms] ease-linear"
            :style="{ width: i === hc ? Math.min(100, (ht / TICKS) * 100) + '%' : '0%' }"
          ></span>
        </button>
      </div>

      <div class="flex flex-wrap gap-x-4 gap-y-1 px-0.5 font-mono text-[11px] tracking-[0.03em]">
        <span><span class="text-faint">EQUIPMENT </span>{{ H.equip }}</span>
        <span><span class="text-faint">GOVERNING </span><strong>{{ H.gov }}</strong></span>
        <span><span class="text-faint">+ </span>{{ H.supp }}</span>
      </div>

      <div class="flex flex-wrap items-stretch gap-3.5">
        <div class="relative flex min-h-[260px] min-w-0 flex-[1_1_230px] items-center justify-center px-2 py-3.5">
          <div aria-hidden="true" class="absolute top-7 h-[220px] w-[72%] translate-x-[-10px] translate-y-1.5 -rotate-5 rounded-[2px] border border-ink/18 bg-white"></div>
          <div aria-hidden="true" class="absolute top-6 h-[220px] w-[72%] translate-x-2 translate-y-0.5 rotate-3 rounded-[2px] border border-ink/20 bg-white"></div>
          <div
            class="relative box-border flex h-[236px] w-[78%] max-w-[250px] flex-col gap-2 overflow-hidden rounded-[2px] border border-ink bg-white p-3 shadow-[0_10px_24px_rgb(var(--shade)/0.14)] transition-[transform,opacity] duration-[350ms,250ms] ease-[cubic-bezier(.3,0,.2,1)]"
            :style="paperStyle"
          >
            <div class="flex justify-between gap-2 font-mono text-[9.5px] tracking-[0.06em]">
              <span class="font-bold">{{ docType }}</span><span class="text-faint">{{ di + 1 }} / 5</span>
            </div>
            <span class="truncate font-mono text-[11px] font-bold">{{ doc.f }}</span>
            <div v-if="drawing" aria-hidden="true" class="drawing absolute inset-x-3 top-[58px] bottom-3" :style="{ '--dwg': `url(${drawing})` }"></div>
            <div v-else aria-hidden="true" class="flex flex-col gap-1.5 pt-0.5">
              <span v-for="w in [92, 70, 84, 58, 76, 64]" :key="w" class="h-[5px] bg-pending/60" :style="{ width: w + '%' }"></span>
            </div>
            <div class="relative mt-auto flex flex-col gap-[5px]">
              <span
                v-for="c in doc.ch"
                :key="c[0]"
                class="flex gap-1.5 self-start border px-[7px] py-[3px] font-mono text-[10.5px] transition-[opacity,transform] duration-250"
                :class="[doc.err ? 'border-reject chip-err' : 'border-ink chip-ok', sub >= 1 ? 'opacity-100' : '-translate-x-2 opacity-0']"
              >
                <span class="text-faint">{{ c[0] }}</span><strong>{{ c[1] }}</strong>
              </span>
            </div>
            <span aria-hidden="true" class="absolute right-0 left-0 h-0.5 bg-signal shadow-[0_0_14px_4px_rgba(255,79,0,0.35)]" :style="scanStyle"></span>
            <span aria-hidden="true" class="absolute right-0 left-0 bg-signal/5" :style="scanFill"></span>
          </div>
          <div
            aria-hidden="true"
            class="absolute top-1/2 left-1/2 border-[3px] bg-white/90 px-3.5 py-1.5 font-mono text-[19px] font-bold tracking-[0.1em] whitespace-nowrap transition-[opacity,transform] duration-[150ms,220ms] ease-[cubic-bezier(.3,1.6,.5,1)]"
            :style="{
              borderColor: verdictColor,
              color: verdictColor,
              opacity: stamped ? 1 : 0,
              transform: `translate(-50%,-50%) rotate(-9deg) scale(${stamped ? 1 : 1.8})`,
            }"
          >
            {{ H.verdict }}
          </div>
        </div>

        <div class="flex min-w-0 flex-[1_1_200px] flex-col gap-1.5">
          <span class="font-mono text-[10px] font-bold tracking-[0.08em] text-muted">SORTED BY TYPE</span>
          <div
            v-for="s in slots"
            :key="s.k"
            class="flex items-center gap-[9px] rounded-[2px] px-[9px] py-[7px] transition-[background,color,transform] duration-250 ease-[cubic-bezier(.3,1.5,.5,1)]"
            :class="{
              'border border-dashed border-ink/30 text-faint': s.state === 'off',
              'border border-ink bg-ink text-paper': s.state === 'on',
              'border border-dashed border-ink bg-white text-muted': s.state === 'skip',
              'chip-err border-[1.5px] border-reject text-reject': s.state === 'err',
              'scale-[1.04]': s.landing,
            }"
          >
            <span class="w-11 flex-none font-mono text-[10px] font-bold tracking-[0.05em]">{{ s.k }}</span>
            <span class="min-w-0 flex-1 truncate text-xs">{{ s.v }}</span>
            <span aria-hidden="true" class="flex-none font-mono text-[11px] font-bold">{{ s.mark }}</span>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-2.5 rounded-[3px] border border-ink/22 bg-white px-3.5 pt-3.5 pb-3">
        <div class="flex justify-between gap-2.5 font-mono text-[10px] font-bold tracking-[0.08em] text-muted">
          <span>RULE CHECK · {{ H.short }}</span><span>{{ H.mode }}</span>
        </div>
        <div class="relative grid grid-cols-5 gap-1">
          <span aria-hidden="true" class="absolute top-1.5 right-[10%] left-[10%] h-0.5 bg-pending"></span>
          <span aria-hidden="true" class="absolute top-1.5 left-[10%] h-0.5 bg-ink transition-[width] duration-[450ms] ease-linear" :style="{ width: railW }"></span>
          <div v-for="k in checks" :key="k.l" class="relative flex flex-col items-center gap-1.5 text-center">
            <span
              aria-hidden="true"
              class="size-3 rounded-full border-[1.5px] border-ink transition-[background,transform] duration-250 ease-[cubic-bezier(.3,1.8,.5,1)]"
              :class="[!k.on ? 'bg-white' : k.result === 'FAIL' ? 'bg-reject' : k.result === 'PASS' ? 'bg-ink' : 'bg-white', k.pop ? 'scale-[1.35]' : '']"
            ></span>
            <span class="text-[11.5px] leading-[1.2] font-semibold max-sm:text-[10px]">{{ k.l }}</span>
            <span class="font-mono text-[10px] font-bold max-sm:text-[9px]" :style="{ color: k.on ? RESULT[k.result] : 'var(--color-pending)' }">{{ k.v }}</span>
          </div>
        </div>
        <span class="min-h-[2.9em] text-[12.5px] leading-[1.45] text-muted">{{ verdictText }}</span>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-2.5 px-1 font-mono text-[11px] tracking-[0.06em] text-muted">
        <figcaption>SAMPLE RUN · CHECKED TO CODE</figcaption>
        <RouterLink to="/projects" class="font-bold text-ink">TRY THE ASSESSMENT →</RouterLink>
      </div>
    </figure>
  </section>
</template>

<style scoped>
.chip-ok {
  background: color-mix(in srgb, var(--color-signal) 8%, var(--color-white));
}
.chip-err {
  background: color-mix(in srgb, var(--color-reject) 7%, var(--color-white));
}
/* Drawing PNGs are ink-as-alpha masks, so the line work takes the theme's ink colour. */
.drawing {
  background: var(--color-ink);
  opacity: 0.8;
  -webkit-mask: var(--dwg) center top / contain no-repeat;
  mask: var(--dwg) center top / contain no-repeat;
}
</style>
