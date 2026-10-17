<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useStore } from 'vuex'

const store = useStore()
const ws = computed(() => store.state.workspace)
const done = computed(() => store.getters['workspace/doneDocs'].length)
const checking = computed(() => done.value === ws.value.docs.length && store.getters['workspace/checking'])
const cell = (d) => (d.status === 'queued' ? 'bg-transparent' : d.status === 'reading' ? 'bg-signal' : d.status === 'failed' ? 'bg-reject' : 'bg-ink')

// Status log built from the documents' states.
const log = computed(() =>
  ws.value.docs.map((d) => {
    if (d.status === 'queued') return `QUEUED   ${d.filename}`
    if (d.status === 'reading') return `READING  ${d.filename} — ${d.pages} ${d.pages === 1 ? 'PAGE' : 'PAGES'}`
    if (d.status === 'failed') return `FAILED   ${d.filename} — ${d.error ?? 'unknown error'}`
    return `${d.status === 'needs_review' ? 'REVIEW ' : 'DONE   '}  ${d.filename}`
  }),
)

const started = ref(0)
const now = ref(Date.now())
let timer = null
watch(
  checking,
  (on) => {
    clearInterval(timer)
    if (!on) return
    started.value = Date.now()
    now.value = started.value
    timer = setInterval(() => (now.value = Date.now()), 500)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearInterval(timer))
const elapsed = computed(() => Math.max(0, Math.floor((now.value - started.value) / 1000)))

const waitingForFiles = computed(() => store.getters['workspace/awaitingRun'])
const runNow = () => store.dispatch('workspace/runChecks')

const steps = computed(() => {
  const run = ws.value.run
  const queued = waitingForFiles.value || !run || run.status === 'queued'
  return [
    { label: 'Documents read', state: 'done' },
    { label: waitingForFiles.value ? 'Waiting in case more files are added' : 'Check run queued', state: queued ? 'active' : 'done' },
    { label: 'Building the traceability map', state: queued ? 'waiting' : 'active' },
    { label: 'Running checks C-01 to C-04', state: queued ? 'waiting' : 'active' },
  ]
})
const MARK = { done: '■', active: '▶', waiting: '·' }
</script>

<template>
  <div class="bg-grid flex min-h-0 flex-1 flex-col gap-6 overflow-auto px-[clamp(20px,3vw,40px)] py-8">
    <div class="flex flex-col gap-2">
      <span class="font-mono text-[11px] tracking-[0.08em] text-faint">{{ checking ? 'STAGE 03 / MAP + CHECK' : 'STAGE 02 / EXTRACT' }}</span>
      <h2 class="m-0 text-[34px] leading-none font-extrabold tracking-[-0.03em]">
        {{ checking ? 'Building the map' : 'Reading documents' }}
      </h2>
      <span class="font-mono text-xs">
        {{ done }} / {{ ws.docs.length }} DOCUMENTS READ<template v-if="checking"> · CHECKING FOR {{ elapsed }}s</template>
      </span>
    </div>

    <div v-if="checking" class="flex flex-col gap-3">
      <span aria-hidden="true" class="relative block h-[5px] w-full max-w-[520px] overflow-hidden border border-ink bg-white">
        <span class="absolute inset-y-0 w-[30%] bg-ink [animation:hm-bar_1s_linear_infinite]"></span>
      </span>
      <ol aria-live="polite" class="m-0 flex list-none flex-col gap-1.5 p-0 font-mono text-[12px]">
        <li v-for="s in steps" :key="s.label" class="flex items-center gap-2.5" :class="s.state === 'waiting' ? 'text-faint' : 'text-ink'">
          <span aria-hidden="true" class="w-3" :class="s.state === 'active' ? 'animate-blink text-signal' : ''">{{ MARK[s.state] }}</span>
          <span :class="{ 'font-bold': s.state === 'active' }">{{ s.label }}</span>
        </li>
      </ol>
      <div v-if="waitingForFiles" class="flex flex-wrap items-center gap-3">
        <span class="font-mono text-[11px] text-muted">Checks start about 15 s after the last file is read, so adding files one by one doesn't re-run them each time.</span>
        <button type="button" class="btn-hard bg-signal px-3 py-1.5 text-[11px] tracking-[0.04em]" @click="runNow">Run checks now</button>
      </div>
      <span v-else class="font-mono text-[11px] text-muted">The map opens as soon as the checks finish. Finding explanations are added after that.</span>
    </div>

    <div v-else aria-hidden="true" class="flex flex-wrap gap-[3px]">
      <span v-for="d in ws.docs" :key="d.id" class="box-border h-[26px] w-3.5 border border-ink" :class="cell(d)"></span>
    </div>

    <div aria-live="polite" class="flex min-h-60 flex-col gap-[5px] border border-ink bg-ink px-4 py-3.5 font-mono text-[11.5px] whitespace-pre text-paper">
      <span class="pb-1.5 text-[10px] tracking-[0.08em] text-paper/65">EXTRACTION LOG</span>
      <span v-for="(line, i) in log" :key="i" class="truncate">{{ line }}</span>
    </div>
  </div>
</template>
