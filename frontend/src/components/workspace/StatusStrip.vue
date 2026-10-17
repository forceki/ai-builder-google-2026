<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()
const ws = computed(() => store.state.workspace)
const g = store.getters

const text = computed(() => {
  const phase = g['workspace/phase']
  if (ws.value.loading) return 'LOADING…'
  if (phase === 'empty') return '0 DOCUMENTS · AWAITING UPLOAD · CHECKS: NOT RUN'
  if (phase === 'processing')
    return `READING ${g['workspace/doneDocs'].length}/${ws.value.docs.length} DOCUMENTS · CHECKS: PENDING`
  const s = ws.value.result?.summary ?? {}
  const reading = g['workspace/pendingDocs'].length
  return [
    `${ws.value.docs.length} DOCUMENTS`,
    reading ? `${reading} READING` : null,
    `${s.fields ?? 0} FIELDS EXTRACTED`,
    `${s.welds ?? 0} WELDS`,
    g['workspace/running'] ? 'CHECKS: RUNNING' : `CHECKS: ${g['workspace/countText']} · LAST RUN ${g['workspace/lastRun']}`,
  ]
    .filter(Boolean)
    .join(' · ')
})

const open = computed(() => g['workspace/openKeys'].length)
const readiness = computed(() =>
  !g['workspace/isReview'] ? 'NO RELEASE DATA' : open.value ? `NOT READY FOR RELEASE · ${open.value} OPEN` : 'READY FOR SIGN-OFF',
)
const light = computed(() => (!g['workspace/isReview'] ? 'bg-faint' : open.value ? 'bg-reject' : 'bg-pass'))
</script>

<template>
  <footer class="flex flex-wrap items-center justify-between gap-x-5 gap-y-1.5 bg-ink px-3.5 py-[7px] font-mono text-[11px] tracking-[0.05em] text-paper">
    <span aria-live="polite" class="min-w-0">{{ text }}</span>
    <span class="flex items-center gap-2 font-bold">
      <span aria-hidden="true" class="size-2.5 rounded-full border border-paper" :class="light"></span>{{ readiness }}
    </span>
  </footer>
</template>
