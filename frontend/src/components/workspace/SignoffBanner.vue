<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'
import { clockTime, isoDate } from '../../lib/status'

const DECISION = { hold: 'DO NOT RELEASE', concession: 'RELEASE WITH CONCESSION', release: 'RELEASE' }

const store = useStore()
const ws = computed(() => store.state.workspace)
const signoff = computed(() => ws.value.project?.signoff ?? null)
const busy = computed(() => store.getters['workspace/pendingDocs'].length > 0 || store.getters['workspace/checking'])
const when = computed(() => {
  const d = signoff.value && new Date(signoff.value.signed_at)
  return d ? `${isoDate(d)} ${clockTime(d)}` : ''
})
const reportLink = computed(() => `/projects/${ws.value.projectNo}/report`)
</script>

<template>
  <div
    v-if="signoff"
    role="status"
    class="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-l-[6px] border-b-ink py-2 pr-3.5 pl-2.5 text-[13px]"
    :class="signoff.current ? 'border-l-pass bg-pass/12' : 'border-l-signal bg-signal/20'"
  >
    <span
      class="flex items-center gap-1.5 border px-2 py-[3px] font-mono text-[11px] font-bold tracking-[0.1em]"
      :class="signoff.current ? 'border-pass bg-pass text-[#fff]' : 'border-ink bg-signal text-ink'"
    >
      <span aria-hidden="true">{{ signoff.current ? '✓' : '!' }}</span>{{ signoff.current ? 'SIGNED' : 'SIGNATURE OUTDATED' }}
    </span>

    <span v-if="signoff.current" class="min-w-0 flex-1 font-read leading-snug">
      <b>{{ DECISION[signoff.decision] ?? signoff.decision }}</b> · signed by {{ signoff.name }} on {{ when }}.
      Adding, replacing or deleting documents makes this signature outdated.
    </span>
    <span v-else class="min-w-0 flex-1 font-read leading-snug">
      Documents changed after {{ signoff.name }} signed <b>{{ DECISION[signoff.decision] ?? signoff.decision }}</b> on {{ when }}.
      The earlier sign-off stays on record, but no longer covers this dossier.
      {{ busy ? 'Sign again once the checks have finished.' : 'Review the new result and sign again.' }}
    </span>

    <RouterLink
      :to="reportLink"
      class="btn-hard flex-none px-3 py-1.5 text-[11px] tracking-[0.04em] no-underline"
      :class="signoff.current ? 'bg-white' : 'bg-signal'"
    >
      {{ signoff.current ? 'View report →' : 'Sign again →' }}
    </RouterLink>
  </div>
</template>
