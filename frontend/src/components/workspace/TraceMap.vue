<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useStore } from 'vuex'
import { COLUMN_KINDS, itemSub } from '../../data/workspace'
import { LED } from '../../lib/status'

const props = defineProps({
  q: { type: String, default: '' },
})
const zoom = defineModel('zoom', { type: Number, default: 1 })
const emit = defineEmits(['open-inspector'])

// Layout: one column per kind (heat -> part -> weld -> NDT), items stacked in key order.
const COLX = [40, 310, 580, 850]
const NW = 170
const NH = 54
const CW = 1080
const TOP = 70
const ROW = 100

const store = useStore()
const ws = computed(() => store.state.workspace)
const sel = computed(() => ws.value.sel)
const statusOf = (key) => store.getters['workspace/statusOf'](key)
const findingsFor = (key) => store.getters['workspace/findingsFor'](key)
const select = (key) => store.commit('workspace/select', key)

const canvas = ref(null)

const columns = computed(() =>
  COLUMN_KINDS.map((kind) =>
    ws.value.items.filter((i) => i.kind === kind).sort((a, b) => a.key.localeCompare(b.key, undefined, { numeric: true })),
  ),
)
const CH = computed(() => Math.max(580, TOP + Math.max(1, ...columns.value.map((c) => c.length)) * ROW + 30))

// item id -> { item, col, x, y }
const nodes = computed(() => {
  const out = {}
  columns.value.forEach((items, col) => {
    // Centre shorter columns against the tallest one.
    const offset = ((Math.max(...columns.value.map((c) => c.length)) - items.length) * ROW) / 2
    items.forEach((item, row) => (out[item.id] = { item, col, x: COLX[col], y: TOP + offset + row * ROW }))
  })
  return out
})
const nodeByKey = computed(() => Object.fromEntries(Object.values(nodes.value).map((n) => [n.item.key, n])))

const pathLinks = computed(() => {
  const start = nodeByKey.value[sel.value]?.item.id
  const on = new Set()
  if (!start) return on
  const walk = (id, from, to) => {
    for (const [i, l] of ws.value.links.entries()) {
      if (l[from] === id && !on.has(i)) {
        on.add(i)
        walk(l[to], from, to)
      }
    }
  }
  walk(start, 'to_item_id', 'from_item_id')
  walk(start, 'from_item_id', 'to_item_id')
  return on
})

const edges = computed(() =>
  ws.value.links
    .map((l, i) => {
      const a = nodes.value[l.from_item_id]
      const b = nodes.value[l.to_item_id]
      if (!a || !b) return null
      const x1 = a.x + NW
      const y1 = a.y + NH / 2
      const x2 = b.x - 3
      const y2 = b.y + NH / 2
      const bend = (x2 - x1) * 0.45
      const d = `M${x1} ${y1} C${x1 + bend} ${y1} ${x2 - bend} ${y2} ${x2} ${y2}`
      const on = pathLinks.value.has(i)
      const dim = !!sel.value && !on
      return l.kind === 'conflict'
        ? { key: i, conflict: true, d, on, dim, label: { x: (x1 + x2) / 2, y: (y1 + y2) / 2 - 8 } }
        : { key: i, d, on, dim, delay: a.col * 0.22 }
    })
    .filter(Boolean),
)

const TAGS = {
  'R-MAT-01': (f) => (f.message.startsWith('No heat number') ? 'NO HEAT NO.' : 'NO MTC'),
  'R-MAT-02': () => '≠ HEAT NO.',
  'R-WLD-01': (f) => (f.message.includes('has no WPS') ? 'NO WPS' : 'WPS NOT IN DOSSIER'),
  'R-WLD-02': (f) => (f.message.includes('no welder') ? 'NO WELDER' : 'WELDER NOT QUALIFIED'),
  'R-WLD-03': () => 'NO PART LINK',
  'R-NDT-04': () => 'NDT REJECTED',
  'R-DOS-02': () => 'NO PWHT RECORD',
  'R-DOS-04': () => 'NOT SIGNED',
}
const tags = computed(() =>
  Object.values(nodes.value)
    .map((n) => {
      const fs = findingsFor(n.item.key).filter((f) => TAGS[f.rule_id])
      if (!fs.length) return null
      const text = [...new Set(fs.map((f) => TAGS[f.rule_id](f)))].join(' · ')
      return { key: n.item.key, x: n.x, y: n.y + NH + 4, text, reject: fs.some((f) => f.status === 'REJECT') }
    })
    .filter(Boolean),
)

// Welds with a missing-NDT finding get a dashed lead and a HOLD stamp in the NDT column.
const missingNdt = computed(() =>
  Object.values(nodes.value)
    .filter((n) => n.item.kind === 'weld' && findingsFor(n.item.key).some((f) => f.rule_id === 'R-NDT-03'))
    .map((n) => ({ key: n.item.key, y: n.y + NH / 2 })),
)

const matches = (i) => {
  const q = props.q.trim().toLowerCase()
  return !q || `${i.label} ${i.key} ${itemSub(i)}`.toLowerCase().includes(q)
}

function fit() {
  const el = canvas.value
  if (!el) return
  const z = Math.min((el.clientWidth - 28) / CW, (el.clientHeight - 28) / CH.value)
  zoom.value = Math.max(0.4, Math.min(1.6, Math.round(z * 100) / 100))
}

function focusNode(key) {
  nextTick(() => document.getElementById(`hm-node-${key}`)?.focus())
}

function onKey(e) {
  const a = document.activeElement
  const curKey = a?.id?.startsWith('hm-node-') ? a.id.slice(8) : sel.value
  const cur = nodeByKey.value[curKey]
  if (!cur) return
  let next = null
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    const col = columns.value[cur.col]
    const i = col.findIndex((x) => x.key === cur.item.key) + (e.key === 'ArrowDown' ? 1 : -1)
    next = col[Math.max(0, Math.min(col.length - 1, i))]
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    const c = cur.col + (e.key === 'ArrowRight' ? 1 : -1)
    const col = columns.value[c] ?? []
    next = col.reduce((b, x) => (!b || Math.abs(nodeByKey.value[x.key].y - cur.y) < Math.abs(nodeByKey.value[b.key].y - cur.y) ? x : b), null)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    select(cur.item.key)
    emit('open-inspector')
    return
  }
  if (next) {
    e.preventDefault()
    select(next.key)
    focusNode(next.key)
  }
}

function findFirst() {
  const m = ws.value.items.find(matches)
  if (m) {
    select(m.key)
    focusNode(m.key)
  }
}

onMounted(() => setTimeout(fit, 80))
defineExpose({ fit, focusNode, findFirst })
</script>

<template>
  <div class="relative min-h-0 flex-1 bg-paper">
    <div
      ref="canvas"
      role="group"
      aria-label="Traceability graph. Arrow keys move between items, Enter opens the inspector."
      class="absolute inset-0 overflow-auto"
      @keydown="onKey"
    >
      <div class="relative m-3" :style="{ width: `${Math.round(CW * zoom)}px`, height: `${Math.round(CH * zoom)}px` }">
        <div
          class="absolute top-0 left-0 origin-top-left border border-ink bg-white bg-[linear-gradient(rgb(var(--shade)/0.06)_1px,transparent_1px),linear-gradient(90deg,rgb(var(--shade)/0.06)_1px,transparent_1px)] bg-size-[20px_20px]"
          :style="{ width: `${CW}px`, height: `${CH}px`, transform: `scale(${zoom})` }"
        >
          <div
            v-for="(label, c) in ['01 MATERIAL / HEAT', '02 PART', '03 WELD', '04 INSPECTION / NDT']"
            :key="label"
            aria-hidden="true"
            class="absolute top-[22px] w-[170px] border-b border-ink pb-1 font-mono text-[10px] tracking-[0.08em]"
            :style="{ left: `${COLX[c]}px` }"
          >{{ label }}</div>

          <svg :width="CW" :height="CH" :viewBox="`0 0 ${CW} ${CH}`" aria-hidden="true" class="pointer-events-none absolute top-0 left-0 overflow-visible font-mono">
            <defs>
              <marker id="hmArrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M0 0 L8 4 L0 8 Z" class="fill-ink"/>
              </marker>
            </defs>
            <template v-for="e in edges" :key="e.key">
              <template v-if="e.conflict">
                <path :d="e.d" fill="none" :stroke-width="e.on ? 2.5 : 1.5" :stroke-opacity="e.dim ? 0.35 : 1" stroke-dasharray="6 4" style="animation: hm-fade 0.6s 0.3s ease-out both" class="stroke-reject"/>
                <text :x="e.label.x" :y="e.label.y" text-anchor="middle" font-size="10" font-weight="700" style="animation: hm-fade 0.6s 0.4s both" class="fill-reject">≠ HEAT NO.</text>
              </template>
              <path
                v-else
                :d="e.d"
                fill="none"
               
                :stroke-width="e.on ? 2 : 1"
                :stroke-opacity="e.on ? 1 : e.dim ? 0.18 : 0.55"
                pathLength="1"
                stroke-dasharray="1"
                marker-end="url(#hmArrow)"
                :style="{ animation: `hm-draw 0.8s ${e.delay}s ease-out both` }" class="stroke-ink"/>
            </template>

            <template v-for="m in missingNdt" :key="m.key">
              <path
                :d="`M${COLX[2] + NW} ${m.y} H${COLX[3] - 2}`"
                fill="none"
               
                :stroke-width="sel === m.key ? 2.5 : 2"
                stroke-dasharray="6 4"
                style="animation: hm-fade 0.5s 0.6s both" class="stroke-signal"/>
              <g
                class="pointer-events-auto cursor-pointer"
                style="transform-box: fill-box; transform-origin: center; animation: hm-stamp 0.28s 0.9s ease-out both"
                @click="select(m.key)"
              >
                <g :transform="`rotate(-5 ${COLX[3] + 48} ${m.y})`">
                  <rect :x="COLX[3]" :y="m.y - 17" width="96" height="34" stroke-width="1.5" class="fill-signal stroke-ink"/>
                  <rect :x="COLX[3] + 4" :y="m.y - 13" width="88" height="26" fill="none" stroke-width="0.8" class="stroke-ink"/>
                  <text :x="COLX[3] + 48" :y="m.y + 6" text-anchor="middle" font-size="16" font-weight="700" letter-spacing="2" class="fill-ink">HOLD</text>
                </g>
                <text :x="COLX[3]" :y="m.y + 34" font-size="10" class="fill-ink">NO NDT RECORD FOR {{ m.key }}</text>
              </g>
            </template>
          </svg>

          <button
            v-for="n in nodes"
            :id="`hm-node-${n.item.key}`"
            :key="n.item.id"
            type="button"
            :aria-pressed="n.item.key === sel"
            :aria-label="`${n.item.label}, ${statusOf(n.item.key)}`"
            class="absolute box-border flex h-[54px] w-[170px] cursor-pointer items-center gap-2 border border-ink bg-white px-2.5 text-left outline-offset-2 transition-opacity duration-200 [animation:hm-fade_.4s_ease-out_both]"
            :class="[n.item.key === sel ? 'outline-2 outline-signal' : '', matches(n.item) ? 'opacity-100' : 'opacity-25']"
            :style="{ left: `${n.x}px`, top: `${n.y}px` }"
            @click="select(n.item.key)"
          >
            <span class="flex min-w-0 flex-1 flex-col gap-[3px]">
              <span class="font-mono text-[12.5px] font-bold whitespace-nowrap">{{ n.item.label }}</span>
              <span class="truncate font-mono text-[9.5px] text-faint">{{ itemSub(n.item) }}</span>
            </span>
            <span aria-hidden="true" class="size-[9px] flex-none border border-ink" :class="LED[statusOf(n.item.key)]"></span>
          </button>

          <span
            v-for="t in tags"
            :key="`tag-${t.key}`"
            aria-hidden="true"
            class="pointer-events-none absolute max-w-[170px] truncate border px-1.5 py-px font-mono text-[9.5px] font-bold tracking-[0.04em] [animation:hm-fade_.4s_.5s_ease-out_both]"
            :class="t.reject ? 'border-reject bg-white text-reject' : 'border-ink bg-signal text-ink'"
            :style="{ left: `${t.x}px`, top: `${t.y}px` }"
          >{{ t.text }}</span>
        </div>
      </div>
    </div>

    <div
      aria-label="Map legend"
      class="pointer-events-none absolute right-5 bottom-7 flex flex-col gap-1 border border-ink bg-white/95 px-2.5 py-2 font-mono text-[9.5px] tracking-[0.04em]"
    >
      <span class="flex items-center gap-2"><span class="size-[9px] border border-ink" :class="LED.PASS"></span>VERIFIED</span>
      <span class="flex items-center gap-2"><span class="size-[9px] border border-ink" :class="LED.HOLD"></span>ISSUE · HOLD</span>
      <span class="flex items-center gap-2"><span class="size-[9px] border border-ink" :class="LED.REJECT"></span>REJECT</span>
      <span class="flex items-center gap-2">
        <svg width="18" height="6" aria-hidden="true"><path d="M0 3 H18" stroke-width="1.5" class="stroke-ink"/></svg>LINKED BY DOCUMENTS
      </span>
      <span class="flex items-center gap-2">
        <svg width="18" height="6" aria-hidden="true"><path d="M0 3 H18" stroke-width="1.5" stroke-dasharray="4 3" class="stroke-reject"/></svg>VALUES CONFLICT
      </span>
      <span class="flex items-center gap-2">
        <svg width="18" height="6" aria-hidden="true"><path d="M0 3 H18" stroke-width="2" stroke-dasharray="4 3" class="stroke-signal"/></svg>RECORD MISSING
      </span>
    </div>
    <span aria-hidden="true" class="pointer-events-none absolute bottom-1.5 left-2 font-mono text-[9.5px] text-faint">⌖ X000 Y000</span>
    <span aria-hidden="true" class="pointer-events-none absolute right-2 bottom-1.5 font-mono text-[9.5px] text-faint">
      X{{ CW }} Y{{ CH }} · {{ ws.items.length }} ITEMS · {{ columns[2].length }} WELDS
    </span>
  </div>
</template>
