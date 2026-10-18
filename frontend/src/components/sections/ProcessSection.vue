<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import SectionLabel from '../ui/SectionLabel.vue'

const steps = [
  { title: 'Upload', role: 'ENGINEER', text: 'Certificates, weld logs, NDT reports and production records. PDF or scan.' },
  { title: 'Extract', role: 'AI', text: 'Reads scanned and digital documents and pulls out heat numbers, weld IDs, procedures and inspection results, each linked to its source page.' },
  { title: 'Map', role: 'RULES', text: 'Material → part → weld → inspection, linked into one traceability map.' },
  { title: 'Verify', role: 'RULES', text: 'Deterministic rules check every link against your project requirements.' },
  { title: 'Explain', role: 'AI', text: 'Describes each issue in plain language and suggests the next verification step.' },
  { title: 'Report', role: 'ENGINEER', text: 'A ranked release-readiness report, ready for engineer sign-off.' },
]

const docs = [
  { id: 'MTC-0457', kind: 'EN 10204 3.1', title: 'Mill test certificate', page: 'p.1 / 2',
    lines: [{ top: 80, text: 'HEAT NO. 4A7721' }, { top: 120, text: 'P-112 · PIPE 4" SCH40' }],
    bars: [{ top: 160, widths: [100, 80, 90, 60, 75] }] },
  { id: 'WELD-LOG-07', kind: 'SCAN', title: 'Weld log', page: 'p.1 / 1',
    lines: [{ top: 80, text: 'W-14 · WPS-07 · FILLET 6' }, { top: 140, text: 'W-15 · WPS-07 · BUTT' }],
    bars: [{ top: 108, widths: [70] }, { top: 180, widths: [100, 85, 65] }] },
  { id: 'NDT-UT-022', kind: 'PDF', title: 'Ultrasonic test report', page: 'p.1 / 1',
    lines: [{ top: 80, text: 'UT-022 · W-15 · ACCEPT' }],
    bars: [{ top: 120, widths: [90, 70, 100, 55] }] },
]

const nodes = [
  { k: 'A', cat: 'MTC-0457 p.1', text: 'HEAT NO. 4A7721', stamp: 'PASS' },
  { k: 'B', cat: 'MTC-0457 p.1', text: 'P-112 · PIPE 4" SCH40', stamp: 'PASS' },
  { k: 'C', cat: 'WELD-LOG-07 row 14', text: 'W-14 · WPS-07 · FILLET 6', stamp: 'HOLD' },
  { k: 'D', cat: 'WELD-LOG-07 row 15', text: 'W-15 · WPS-07 · BUTT', stamp: 'PASS' },
  null,
  { k: 'F', cat: 'NDT-UT-022 p.1', text: 'UT-022 · W-15 · ACCEPT', stamp: 'PASS' },
]

const rows = [
  { n: '01', text: 'W-14: no matching UT record', hold: true },
  { n: '02', text: 'Heat 4A7721 matched to P-112' },
  { n: '03', text: 'W-14, W-15 linked to WPS-07' },
  { n: '04', text: 'W-15 UT accepted' },
]

const links = [
  { d: 'M215 213 C245 213 245 213 275 213' },
  { d: 'M450 213 C480 213 480 153 510 153' },
  { d: 'M450 213 C480 213 480 273 510 273' },
  { d: 'M685 153 C715 153 715 153 745 153', hot: true },
  { d: 'M685 273 C715 273 715 273 745 273' },
]

const EXPLANATION =
  'W-14 needs an ultrasonic test under ITP-03 §4.2, but no NDT report in the dossier references it. Next step: request the UT report from the NDT contractor, or schedule the test.'

const root = ref(null)
let E = null
let lens = []
let ctx = null
let raf = null
let step = -1

const cl = (v) => Math.max(0, Math.min(1, v))
const seg = (p, a, b) => cl((p - a) / (b - a))
const lerp = (a, b, t) => a + (b - a) * t
const oCub = (t) => 1 - Math.pow(1 - t, 3)
const oBack = (t) => 1 + 2.7 * Math.pow(t - 1, 3) + 1.7 * Math.pow(t - 1, 2)
const ioExp = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2)

function shadeRgba(a) {
  const shade = getComputedStyle(document.documentElement).getPropertyValue('--shade').trim() || '17 17 17'
  return `rgba(${shade.split(/\s+/).join(',')},${a})`
}

function update() {
  raf = null
  if (!E) return
  const header = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--site-header-h')) || 0
  const r = E.flow.getBoundingClientRect()
  const p = cl((header - r.top) / (r.height - innerHeight + header))

  const cw = E.wrap.clientWidth
  const ch = E.wrap.clientHeight
  const s = Math.min(cw / 960, ch / 600) * 0.96
  E.stage.style.transform = `translate(${(cw - 960 * s) / 2}px,${(ch - 600 * s) / 2}px) scale(${s})`

  const B = [0, 0.15, 0.35, 0.54, 0.71, 0.85, 1.0001]
  let st = 0
  while (p >= B[st + 1]) st++
  const sf = seg(p, B[st], B[st + 1])
  if (st !== step) {
    step = st
    E.steps.forEach((li, i) => {
      li.style.opacity = i === st ? 1 : i < st ? 0.7 : 0.4
      li.toggleAttribute('data-active', i === st)
      const num = li.querySelector('[data-num]')
      num.style.background = i === st ? 'var(--color-signal)' : i < st ? 'var(--color-ink)' : 'var(--color-white)'
      num.style.color = i < st ? 'var(--color-paper)' : 'var(--color-ink)'
      li.querySelector('[data-desc]').style.display = i === st ? 'block' : 'none'
    })
  }
  E.bar.style.transform = `scaleX(${p})`
  E.readout.textContent = `STEP 0${st + 1}/06 · ${Math.round(p * 100)}%`

  ctx.setTransform(2, 0, 0, 2, 0, 0)
  ctx.clearRect(0, 0, 960, 600)
  const dim = shadeRgba(0.16)
  const cx = [140, 400, 480, 600, 830, 480][st]
  const cy = [230, 230, 210, 210, 360, 300][st]
  const R = ioExp(sf) * 1100
  for (let y = 15; y < 600; y += 30) {
    for (let x = 15; x < 960; x += 30) {
      const k = Math.exp(-Math.pow(Math.hypot(x - cx, y - cy) - R, 2) / 3200)
      ctx.fillStyle = k > 0.3 ? `rgba(255,79,0,${(0.25 + k * 0.5).toFixed(2)})` : dim
      ctx.beginPath()
      ctx.arc(x, y, 1 + k * 2.6, 0, 6.283)
      ctx.fill()
    }
  }

  const toSrc = ioExp(seg(p, 0.36, 0.46))
  E.docs.forEach((d, i) => {
    const e = seg(p, 0.02 + i * 0.035, 0.1 + i * 0.035)
    const b = oBack(e)
    const x = lerp(60 + i * 300, 40 + i * 92, toSrc)
    const y = lerp(70 - (1 - b) * 140, 450, toSrc)
    const rot = (1 - b) * (-10 + i * 10) + (1 - toSrc) * (i - 1) * 1.2
    d.style.opacity = Math.min(1, e * 2)
    d.style.transform = `translate(${x}px,${y}px) rotate(${rot}deg) scale(${lerp(1, 0.3, toSrc)})`
  })
  E.src.style.opacity = toSrc

  const scan = seg(p, 0.16, 0.31)
  const by = lerp(70, 400, scan)
  E.beam.style.transform = `translateY(${by}px)`
  E.beam.style.opacity = scan > 0 && scan < 1 ? 1 : 0

  const N = [[[74, 146], [40, 185]], [[74, 186], [275, 185]], [[374, 146], [510, 125]], [[374, 206], [510, 245]], null, [[674, 146], [745, 245]]]
  N.forEach((n, i) => {
    const el = E.nodes[i]
    if (!n || !el) return
    const hl = scan > 0 ? cl((by - n[0][1]) / 30) : 0
    const m = ioExp(seg(p, 0.37 + i * 0.012, 0.46 + i * 0.012))
    el.style.opacity = Math.max(hl, m > 0 ? 1 : 0)
    el.style.transform = `translate(${lerp(n[0][0], n[1][0], m)}px,${lerp(n[0][1], n[1][1], m)}px)`
    el.style.width = `${lerp(212, 175, m)}px`
    el.style.height = `${lerp(26, 56, m)}px`
    el.style.background = m > 0.5 ? 'var(--color-white)' : `rgba(255,79,0,${(0.12 * hl).toFixed(3)})`
    el.style.borderColor = m > 0.5 ? 'var(--color-ink)' : 'var(--color-signal)'
    el.style.boxShadow = m > 0.5 ? `0 2px 0 ${shadeRgba(0.12)}` : 'none'
    el.children[1].style.opacity = m > 0.02 ? 1 : 0
    const cat = el.querySelector('[data-cat]')
    cat.style.opacity = seg(m, 0.6, 1)
    cat.style.height = m > 0.6 ? 'auto' : '0'
  })
  const eE = seg(p, 0.47, 0.51)
  E.missing.style.opacity = eE
  E.missing.style.transform = `scale(${lerp(0.85, 1, oBack(eE))})`
  E.heads.style.opacity = seg(p, 0.42, 0.5)

  E.links.forEach((l, j) => {
    l.style.strokeDashoffset = lens[j] * (1 - oCub(seg(p, 0.44 + j * 0.012, 0.5 + j * 0.012)))
  })
  E.pulses.forEach((pc, j) => {
    const t = seg(p, 0.555 + j * 0.022, 0.6 + j * 0.022)
    const pt = E.links[j].getPointAtLength(t * lens[j])
    pc.setAttribute('cx', pt.x)
    pc.setAttribute('cy', pt.y)
    pc.setAttribute('opacity', t > 0 && t < 1 ? 1 : 0)
  })
  const order = [0, 1, 3, 4, 2, 5]
  const rots = [-4, 3, -5, 2, 4, -3]
  E.stamps.forEach((sEl, i) => {
    const t = seg(p, 0.6 + order[i] * 0.017, 0.62 + order[i] * 0.017)
    sEl.style.opacity = t > 0 ? 1 : 0
    sEl.style.transform = `scale(${lerp(1.9, 1, oCub(t))}) rotate(${rots[i]}deg)`
  })

  const ca = seg(p, 0.72, 0.75)
  E.callout.style.opacity = ca
  E.callout.style.transform = `translateY(${(1 - oCub(ca)) * 16}px)`
  E.conn.setAttribute('opacity', ca)
  E.ctext.textContent = EXPLANATION.slice(0, Math.round(seg(p, 0.74, 0.83) * EXPLANATION.length))

  const rp = ioExp(seg(p, 0.86, 0.92))
  E.map.style.opacity = lerp(1, 0.14, rp)
  E.map.style.transform = `scale(${lerp(1, 0.94, rp)})`
  E.report.style.opacity = rp > 0 ? 1 : 0
  E.report.style.transform = `translateY(${lerp(640, 50, rp)}px)`
  E.rows.forEach((row, i) => {
    const t = seg(p, 0.9 + i * 0.012, 0.92 + i * 0.012)
    row.style.opacity = t
    row.style.transform = `translateX(${(1 - oCub(t)) * -14}px)`
  })
  E.sig.style.clipPath = `inset(0 ${100 - seg(p, 0.93, 0.965) * 100}% 0 0)`
  const rs = seg(p, 0.96, 0.985)
  E.rstamp.style.opacity = rs > 0 ? 1 : 0
  E.rstamp.style.transform = `scale(${lerp(2, 1, oCub(rs))}) rotate(-6deg)`
}

const request = () => {
  if (!raf) raf = requestAnimationFrame(update)
}

onMounted(() => {
  const el = root.value
  const q = (k) => el.querySelector(`[data-k="${k}"]`)
  E = {
    flow: q('flow'), wrap: q('wrap'), stage: q('stage'), map: q('maplayer'), heads: q('heads'), src: q('srclabel'),
    beam: q('beam'), missing: q('nE'), conn: q('conn'), callout: q('callout'), ctext: q('ctext'), report: q('report'),
    rstamp: q('rstamp'), sig: q('sig'), bar: q('bar'), readout: q('readout'),
    docs: [...el.querySelectorAll('[data-doc]')],
    nodes: ['A', 'B', 'C', 'D', 'E', 'F'].map((k) => q(`n${k}`)),
    stamps: ['A', 'B', 'C', 'D', 'E', 'F'].map((k) => q(`s${k}`)),
    links: [...el.querySelectorAll('[data-link]')],
    pulses: [...el.querySelectorAll('[data-pulse]')],
    rows: [...el.querySelectorAll('[data-row]')],
    steps: [...el.querySelectorAll('[data-step]')],
  }
  lens = E.links.map((l) => {
    const n = l.getTotalLength()
    l.style.strokeDasharray = n
    l.style.strokeDashoffset = n
    return n
  })
  ctx = q('dots').getContext('2d')
  addEventListener('scroll', request, { passive: true })
  addEventListener('resize', request)
  update()
})

onBeforeUnmount(() => {
  removeEventListener('scroll', request)
  removeEventListener('resize', request)
  cancelAnimationFrame(raf)
  E = null
})

const stampStyle = (hold) =>
  `position:absolute;right:-10px;top:-12px;padding:2px 7px;border:2px solid var(--color-ink);border-radius:3px;background:${hold ? 'var(--color-signal)' : 'var(--color-paper)'};font-size:10px;font-weight:700;letter-spacing:0.1em;opacity:0;`
</script>

<template>
  <section id="process" ref="root" aria-labelledby="proc-h">
    <div class="wrap flex flex-wrap items-end justify-between gap-5 pb-[clamp(32px,4vw,56px)]">
      <div class="flex flex-col gap-6">
        <SectionLabel num="04" label="PROCESS" />
        <h2 id="proc-h" class="h-section">Six steps to release.</h2>
      </div>
      <span class="font-mono text-xs text-muted">SCROLL TO RUN ONE DOSSIER ↓</span>
    </div>

    <div data-k="flow" aria-label="Animated walkthrough of the Hibanako process" class="relative h-[720vh]">
      <div
        class="sticky flex flex-col overflow-hidden border-y md:flex-row border-ink bg-paper"
        style="top: var(--site-header-h, 0px); height: calc(100vh - var(--site-header-h, 0px))"
      >
        <aside
          class="box-border flex min-w-0 flex-none flex-col justify-between gap-3 border-b border-ink bg-paper px-[clamp(20px,3vw,32px)] py-4 md:max-w-[400px] md:flex-[1_1_300px] md:gap-5 md:border-r md:border-b-0 md:py-[clamp(20px,3vw,36px)]"
        >
          <ol class="m-0 flex list-none flex-col gap-1.5 p-0 max-md:min-h-[136px]">
            <li v-for="(s, i) in steps" :key="s.title" :data-step="i" :data-active="i ? null : ''" class="flex flex-col gap-2 py-2 max-md:[&:not([data-active])]:hidden" :style="{ opacity: i ? 0.4 : 1 }">
              <div class="flex items-center gap-3">
                <span
                  data-num
                  class="flex size-[34px] flex-none items-center justify-center rounded-[3px] border border-ink font-mono text-xs font-bold"
                  :style="{ background: i ? 'var(--color-white)' : 'var(--color-signal)' }"
                >{{ String(i + 1).padStart(2, '0') }}</span>
                <span class="text-xl font-extrabold tracking-[-0.02em]">{{ s.title }}</span>
                <span
                  class="border border-ink px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-[0.08em]"
                  :class="s.role === 'AI' ? 'bg-ink text-paper' : ''"
                >{{ s.role }}</span>
              </div>
              <p data-desc class="m-0 ml-[46px] font-read text-[15px] leading-[1.5]" :style="{ display: i ? 'none' : 'block' }">{{ s.text }}</p>
            </li>
          </ol>
          <div class="flex flex-col gap-2.5 font-mono text-[11px] tracking-[0.06em]">
            <div class="relative h-1 overflow-hidden border border-ink/30 bg-panel">
              <div data-k="bar" class="absolute inset-0 origin-left scale-x-0 bg-signal"></div>
            </div>
            <span data-k="readout" class="text-muted">STEP 01/06 · 0%</span>
          </div>
        </aside>

        <div data-k="wrap" class="relative min-h-0 min-w-0 flex-1 overflow-hidden bg-paper md:flex-[3_1_520px]">
          <div data-k="stage" class="absolute top-0 left-0 h-[600px] w-[960px] origin-top-left">
            <canvas data-k="dots" width="1920" height="1200" class="absolute top-0 left-0 h-[600px] w-[960px]"></canvas>

            <div data-k="maplayer" class="absolute inset-0" style="transform-origin: 480px 300px">
              <div data-k="heads" class="absolute top-[92px] left-0 h-5 w-[960px] font-mono text-[11px] tracking-[0.08em] text-muted opacity-0">
                <span class="absolute left-[40px]">MATERIAL</span><span class="absolute left-[275px]">PART</span>
                <span class="absolute left-[510px]">WELD</span><span class="absolute left-[745px]">INSPECTION</span>
              </div>
              <svg width="960" height="600" viewBox="0 0 960 600" class="absolute top-0 left-0 overflow-visible" fill="none">
                <path
                  v-for="(l, i) in links"
                  :key="i"
                  data-link
                  :d="l.d"
                  :class="l.hot ? 'stroke-signal' : 'stroke-ink'"
                  :stroke-width="l.hot ? 2 : 1.5"
                />
                <line data-k="conn" x1="832" y1="181" x2="832" y2="340" class="stroke-ink" stroke-width="1" stroke-dasharray="3 3" opacity="0" />
                <circle v-for="i in 5" :key="`p${i}`" data-pulse r="5" class="fill-signal stroke-ink" opacity="0" />
              </svg>
              <span data-k="srclabel" class="absolute top-[428px] left-[40px] font-mono text-[11px] tracking-[0.08em] text-muted opacity-0">
                SOURCES · 3 DOCUMENTS
              </span>

              <div
                v-for="d in docs"
                :key="d.id"
                data-doc
                class="absolute top-0 left-0 box-border h-[320px] w-[240px] origin-top-left border border-ink/35 bg-white p-4 font-mono opacity-0"
                :style="`box-shadow: 0 2px 0 rgb(var(--shade) / 0.08)`"
              >
                <div class="flex justify-between text-[10px] text-muted"><span>{{ d.id }}</span><span>{{ d.kind }}</span></div>
                <div class="mt-2 font-sans text-[15px] font-extrabold">{{ d.title }}</div>
                <div v-for="l in d.lines" :key="l.text" class="absolute left-4 text-[11px] font-bold" :style="{ top: `${l.top}px` }">{{ l.text }}</div>
                <div v-for="b in d.bars" :key="b.top" class="absolute right-4 left-4 flex flex-col gap-2.5" :style="{ top: `${b.top}px` }">
                  <span v-for="(w, i) in b.widths" :key="i" class="h-1.5 bg-ink/10" :style="{ width: `${w}%` }"></span>
                </div>
                <div class="absolute bottom-3.5 left-4 text-[10px] text-muted">{{ d.page }}</div>
              </div>

              <div
                data-k="beam"
                class="absolute top-0 left-[40px] h-0.5 w-[880px] bg-signal opacity-0"
                style="box-shadow: 0 0 0 1px rgba(255, 79, 0, 0.2), 0 -18px 24px -12px rgba(255, 79, 0, 0.35)"
              ></div>

              <template v-for="n in nodes" :key="n?.k ?? 'E'">
                <div
                  v-if="n"
                  :data-k="`n${n.k}`"
                  class="absolute top-0 left-0 box-border flex flex-col justify-center gap-[3px] rounded-[3px] px-2.5 font-mono opacity-0"
                  style="border: 1.5px solid var(--color-signal)"
                >
                  <span data-cat class="h-0 overflow-hidden text-[9px] tracking-[0.08em] text-muted opacity-0">{{ n.cat }}</span>
                  <span class="text-[11px] font-bold whitespace-nowrap">{{ n.text }}</span>
                  <span :data-k="`s${n.k}`" :style="stampStyle(n.stamp === 'HOLD')">{{ n.stamp }}</span>
                </div>
                <div
                  v-else
                  data-k="nE"
                  class="absolute top-[125px] left-[745px] box-border flex h-14 w-[175px] flex-col justify-center gap-[3px] rounded-[3px] px-2.5 font-mono opacity-0"
                  style="border: 1.5px dashed var(--color-signal); background: color-mix(in srgb, var(--color-signal) 7%, var(--color-white))"
                >
                  <span class="text-[9px] tracking-[0.08em] text-muted">REQUIRED BY ITP-03 §4.2</span>
                  <span class="text-[11px] font-bold whitespace-nowrap">UT · W-14 · NO RECORD</span>
                  <span data-k="sE" :style="stampStyle(true)">HOLD</span>
                </div>
              </template>

              <div
                data-k="callout"
                class="absolute top-[340px] left-[470px] box-border flex w-[450px] flex-col gap-2 rounded-[3px] border border-ink bg-white px-4 py-3.5 opacity-0"
                :style="`box-shadow: 0 3px 0 rgb(var(--shade) / 0.12)`"
              >
                <div class="flex items-center justify-between font-mono text-[10px] tracking-[0.08em]">
                  <span class="flex items-center gap-1.5"><span class="bg-ink px-[5px] py-px font-bold text-paper">AI</span>EXPLANATION</span>
                  <span class="text-muted">FINDING 01</span>
                </div>
                <p data-k="ctext" class="m-0 min-h-[66px] font-read text-[15px] leading-[1.5]"></p>
                <div class="font-mono text-[10px] text-muted">SRC: WELD-LOG-07 row 14 / ITP-03 §4.2</div>
              </div>
            </div>

            <article
              data-k="report"
              class="absolute top-0 left-[270px] box-border flex w-[420px] flex-col gap-3.5 border border-ink bg-white p-[22px] font-mono opacity-0"
              :style="`box-shadow: 0 4px 0 rgb(var(--shade) / 0.12)`"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="flex flex-col gap-[3px]">
                  <span class="font-sans text-xl font-black">Release readiness report</span>
                  <span class="text-[10px] text-muted">HBK-2026-041 · PS-3 PIPE SUPPORT</span>
                </div>
                <span
                  data-k="rstamp"
                  class="inline-block rounded-[3px] border-2 border-ink bg-signal px-3 py-[5px] text-[15px] font-bold tracking-[0.14em] opacity-0 outline outline-1 outline-offset-2 outline-ink"
                >HOLD</span>
              </div>
              <div class="flex gap-4 border-y border-ink py-2 text-[11px]"><span>6 RECORDS</span><span>4 PASS</span><span>2 HOLD</span></div>
              <div
                v-for="row in rows"
                :key="row.n"
                data-row
                class="grid grid-cols-[22px_minmax(0,1fr)_auto] items-center gap-2.5 border-b border-dashed border-ink/30 pb-2.5 opacity-0"
              >
                <span class="text-[11px] text-muted">{{ row.n }}</span>
                <span class="font-sans text-sm font-bold">{{ row.text }}</span>
                <span class="rounded-[3px] border-2 border-ink px-[7px] py-0.5 text-[10px] font-bold" :class="row.hold ? 'bg-signal' : ''">
                  {{ row.hold ? 'HOLD' : 'PASS' }}
                </span>
              </div>
              <div data-row class="flex flex-col gap-1.5 pt-1 text-[10px] text-muted opacity-0">
                <span>APPROVED BY (QUALITY ENGINEER)</span>
                <span class="relative h-10 border-b border-ink">
                  <span
                    data-k="sig"
                    class="absolute bottom-[-6px] left-1.5 text-[40px] leading-none whitespace-nowrap"
                    style="font-family: 'Mrs Saint Delafield', cursive; color: #2b4bb8; clip-path: inset(0 100% 0 0)"
                  >Hibanako</span>
                </span>
                <span class="flex justify-between text-ink"><span>HIBANAKO</span><span>2026-10-18</span></span>
              </div>
            </article>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
