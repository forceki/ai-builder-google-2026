<script setup>
import { computed, inject, ref } from 'vue'
import { useStore } from 'vuex'
import { GROUPS, docStatusLabel, guess } from '../../data/workspace'
import PanelHeader from './PanelHeader.vue'

const store = useStore()
const openUpload = inject('openUpload')

const ws = computed(() => store.state.workspace)
const phase = computed(() => store.getters['workspace/phase'])
const statusOf = (key) => store.getters['workspace/statusOf'](key)

const filter = ref('all')
const closed = ref({})
const dragOver = ref(false)

const filters = [
  { key: 'all', label: 'All' },
  { key: 'review', label: 'Needs review' },
  { key: 'issues', label: 'Issues' },
]

// Items each document is a source for, by file name.
const itemsByDoc = computed(() => {
  const map = {}
  for (const item of ws.value.items) for (const s of item.sources) (map[s.document] ||= []).push(item.key)
  return map
})
const docItems = (d) => itemsByDoc.value[d.filename] ?? []

const matches = (d) =>
  filter.value === 'all'
    ? true
    : filter.value === 'review'
      ? d.status === 'needs_review' || d.status === 'failed'
      : docItems(d).some((k) => statusOf(k) !== 'PASS')

const groups = computed(() => {
  const typed = GROUPS.map(([key, label]) => ({ key, label, all: ws.value.docs.filter((d) => (d.doc_type ?? d.suggested_type) === key) }))
  const untyped = ws.value.docs.filter((d) => !(d.doc_type ?? d.suggested_type))
  if (untyped.length) typed.push({ key: 'none', label: 'UNCLASSIFIED', all: untyped })
  return typed.map((g) => ({ ...g, count: g.all.length, docs: g.all.filter(matches), open: !closed.value[g.key] }))
})

const LED = { queued: 'bg-pending', reading: 'bg-signal', extracted: 'bg-pass', needs_review: 'bg-signal', failed: 'bg-reject' }
const tag = (d) => d.filename.split('.').pop().toUpperCase()
const linked = (d) => !!ws.value.sel && docItems(d).includes(ws.value.sel)

const pickDoc = (d) => {
  const keys = docItems(d)
  if (!keys.length) return
  store.commit('workspace/select', keys.includes(ws.value.sel) ? ws.value.sel : keys[0])
}

const onDrop = (e) => {
  dragOver.value = false
  const f = e.dataTransfer?.files?.[0]
  openUpload(f ? { file: f, group: guess(f.name) } : undefined)
}

const latest = computed(() => {
  const reading = ws.value.docs.find((d) => d.status === 'reading')
  return reading ? `READING ${reading.filename}` : null
})

const corners = [
  'top-[-1px] left-[-1px] border-t-2 border-l-2',
  'top-[-1px] right-[-1px] border-t-2 border-r-2',
  'bottom-[-1px] left-[-1px] border-b-2 border-l-2',
  'bottom-[-1px] right-[-1px] border-b-2 border-r-2',
]
</script>

<template>
  <aside aria-label="Documents" class="flex min-h-0 flex-col border-r border-ink bg-white">
    <PanelHeader title="A / DOCUMENTS" :meta="`${ws.docs.length} FILES`" />

    <div class="flex flex-col gap-2.5 border-b border-ink px-3.5 py-3" :class="phase === 'empty' ? 'flex-auto' : 'flex-none'">
      <button
        type="button"
        class="relative flex min-h-24 flex-1 cursor-pointer flex-col items-center justify-center gap-1.5 border border-dashed border-ink p-4 text-center"
        :class="dragOver ? 'bg-white' : 'bg-transparent'"
        @click="openUpload()"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop.prevent="onDrop"
      >
        <span v-for="c in corners" :key="c" aria-hidden="true" class="absolute size-2.5 border-ink" :class="c"></span>
        <span aria-hidden="true" class="font-mono text-lg leading-none">+</span>
        <span class="text-[15px] font-bold">Drop files or <span class="underline underline-offset-[3px]">browse</span></span>
        <span class="font-mono text-[10px] tracking-[0.04em] text-faint">PDF · JPG · PNG · XLSX — MAX 50 MB</span>
        <span class="text-xs text-muted">You'll confirm the document type next.</span>
      </button>
      <div v-if="latest" aria-live="polite" class="truncate font-mono text-[10px] tracking-[0.02em]">
        <span class="text-signal">▶</span> {{ latest }}
      </div>
    </div>

    <template v-if="phase !== 'empty'">
      <div role="radiogroup" aria-label="Filter documents" class="flex border-b border-ink font-mono text-[11px]">
        <button
          v-for="f in filters"
          :key="f.key"
          type="button"
          role="radio"
          :aria-checked="filter === f.key"
          class="flex-1 cursor-pointer border-r border-ink px-1.5 py-2"
          :class="filter === f.key ? 'bg-ink text-paper' : 'bg-transparent'"
          @click="filter = f.key"
        >{{ f.label }}</button>
      </div>
      <div class="min-h-0 flex-1 overflow-auto">
        <div v-for="g in groups" :key="g.key" class="border-b border-ink">
          <button
            type="button"
            :aria-expanded="g.open"
            class="flex w-full cursor-pointer items-center gap-2 bg-transparent px-3.5 py-[9px] text-left font-mono text-[10.5px] font-bold tracking-[0.06em] hover:bg-paper"
            @click="closed[g.key] = g.open"
          >
            <span aria-hidden="true" class="w-2.5">{{ g.open ? '▾' : '▸' }}</span>
            <span class="flex-1">{{ g.label }}</span>
            <span class="text-faint">({{ g.count }})</span>
          </button>
          <ul v-if="g.open" class="m-0 list-none p-0 pb-1.5">
            <li v-for="d in g.docs" :key="d.id">
              <button
                type="button"
                :title="d.error || undefined"
                class="flex w-full cursor-pointer flex-col gap-[5px] py-[7px] pr-3.5 pl-8 text-left -outline-offset-2 hover:bg-paper"
                :class="linked(d) ? 'bg-white outline-2 outline-signal' : 'bg-transparent'"
                @click="pickDoc(d)"
              >
                <span class="flex w-full items-center gap-2">
                  <span class="flex-none border border-ink px-1 py-px font-mono text-[9px] font-bold">{{ tag(d) }}</span>
                  <span class="min-w-0 flex-1 truncate font-mono text-[11.5px]">{{ d.filename }}</span>
                </span>
                <span
                  class="flex items-center gap-1.5 font-mono text-[9.5px] tracking-[0.04em]"
                  :class="d.status === 'queued' ? 'text-faint' : d.status === 'failed' ? 'text-reject' : 'text-ink'"
                >
                  <span aria-hidden="true" class="size-1.5" :class="LED[d.status]"></span>{{ docStatusLabel(d.status) }}
                  <template v-if="d.status === 'reading'"> · {{ d.pages }} {{ d.pages === 1 ? 'PAGE' : 'PAGES' }}</template>
                  <template v-if="d.evidence_for"> · FOR {{ d.evidence_for }}</template>
                </span>
                <span v-if="d.status === 'failed' && d.error" class="line-clamp-2 font-mono text-[9.5px] text-reject">{{ d.error }}</span>
                <span v-if="d.status === 'reading'" aria-hidden="true" class="relative block h-[3px] w-full overflow-hidden bg-[#E0E0E0]">
                  <span class="absolute inset-y-0 w-[30%] bg-ink [animation:hm-bar_1s_linear_infinite]"></span>
                </span>
              </button>
            </li>
            <li v-if="!g.docs.length" class="pt-1 pr-3.5 pb-1.5 pl-8 font-mono text-[10.5px] text-faint">NO MATCHING FILES</li>
          </ul>
        </div>
      </div>
    </template>

    <ul v-else class="m-0 flex list-none flex-col gap-2 p-3.5 font-mono text-[10.5px] tracking-[0.04em] text-faint">
      <li v-for="[key, label] in GROUPS" :key="key">{{ label }} (0)</li>
    </ul>
  </aside>
</template>
