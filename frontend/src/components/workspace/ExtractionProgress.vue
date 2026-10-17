<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()
const ws = computed(() => store.state.workspace)
const done = computed(() => store.getters['workspace/doneDocs'].length)
const running = computed(() => store.getters['workspace/running'])
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
</script>

<template>
  <div class="bg-grid flex min-h-0 flex-1 flex-col gap-6 overflow-auto px-[clamp(20px,3vw,40px)] py-8">
    <div class="flex flex-col gap-2">
      <span class="font-mono text-[11px] tracking-[0.08em] text-faint">STAGE 02 / EXTRACT</span>
      <h2 class="m-0 text-[34px] leading-none font-extrabold tracking-[-0.03em]">
        {{ done === ws.docs.length && running ? 'Building the map' : 'Reading documents' }}
      </h2>
      <span class="font-mono text-xs">{{ done }} / {{ ws.docs.length }} DOCUMENTS READ</span>
    </div>
    <div aria-hidden="true" class="flex flex-wrap gap-[3px]">
      <span v-for="d in ws.docs" :key="d.id" class="box-border h-[26px] w-3.5 border border-ink" :class="cell(d)"></span>
    </div>
    <div aria-live="polite" class="flex min-h-60 flex-col gap-[5px] border border-ink bg-ink px-4 py-3.5 font-mono text-[11.5px] whitespace-pre text-paper">
      <span class="pb-1.5 text-[10px] tracking-[0.08em] text-[#ADADAD]">EXTRACTION LOG</span>
      <span v-for="(line, i) in log" :key="i" class="truncate">{{ line }}</span>
    </div>
  </div>
</template>
