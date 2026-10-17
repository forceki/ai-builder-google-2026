<script setup>
import { computed, inject, ref } from 'vue'
import { useStore } from 'vuex'
import { EVIDENCE_GROUP } from '../../data/workspace'
import RuleStamp from '../ui/RuleStamp.vue'

const emit = defineEmits(['show-item'])

const store = useStore()
const openUpload = inject('openUpload')

const ws = computed(() => store.state.workspace)
const running = computed(() => store.getters['workspace/running'])
const findings = computed(() => store.getters['workspace/findings'])
const runText = computed(() =>
  running.value ? 'RUNNING…' : `COMPLETE · ${store.getters['workspace/lastRun']} · ${store.getters['workspace/countText']}`,
)

const openCheck = ref(findings.value[0]?.check_id ?? null)

// Evidence uploaded for an item that the last run has not yet taken into account.
const pendingEvidence = (key) => {
  const runAt = ws.value.result?.created_at ?? ''
  return ws.value.docs.find((d) => d.evidence_for === key && d.status !== 'failed' && d.created_at > runAt)
}

const checks = computed(() =>
  (ws.value.result?.summary?.checks ?? []).map((c) => ({
    ...c,
    issuesText: `${c.issues} ${c.issues === 1 ? 'ISSUE' : 'ISSUES'}`,
    items: findings.value.filter((f) => f.check_id === c.check).map((f) => ({ ...f, evidence: pendingEvidence(f.item_key) })),
  })),
)

const fixLabel = (rule) => ({ mtc: 'Upload certificate', ndt: 'Upload NDT report', weld: 'Upload weld record', prod: 'Upload production record' })[EVIDENCE_GROUP[rule]] ?? 'Upload evidence'
</script>

<template>
  <div
    role="region"
    aria-label="Rule checks"
    class="absolute inset-x-0 bottom-0 z-[6] flex h-[62%] flex-col border-t border-ink bg-white [animation:hm-slide_.28s_cubic-bezier(.2,0,0,1)_both]"
  >
    <div class="flex items-center gap-4 border-b border-ink px-3.5 py-2 font-mono text-[11px] tracking-[0.08em]">
      <span class="font-bold">D / RULE CHECKS</span>
      <span class="text-faint">RULE SET {{ ws.result?.rule_set ?? '—' }}</span>
      <span class="flex-1" aria-live="polite">{{ runText }}</span>
      <button
        type="button"
        aria-label="Close rule checks"
        class="size-[26px] cursor-pointer border border-ink bg-white text-xs"
        @click="store.commit('workspace/setDrawer', false)"
      >✕</button>
    </div>

    <div v-if="running" class="flex flex-col gap-3 px-4 py-7 font-mono text-xs">
      <span>RUNNING 4 CHECKS AND WRITING EXPLANATIONS…</span>
      <span aria-hidden="true" class="relative block h-1.5 overflow-hidden border border-ink">
        <span class="absolute inset-y-0 w-[30%] bg-signal [animation:hm-bar_1s_linear_infinite]"></span>
      </span>
    </div>

    <div v-else class="min-h-0 flex-1 overflow-auto">
      <p class="m-0 border-b border-ink bg-white px-3.5 py-2.5 text-sm leading-[1.4]">
        <strong>How to clear a check:</strong> open it, upload the missing evidence for each item, then run checks again.
        The rules set the new status.
      </p>
      <p v-if="ws.run?.status === 'failed'" class="m-0 border-b border-ink px-3.5 py-2.5 font-mono text-xs text-reject">
        The last run failed: {{ ws.run.error }}
      </p>
      <div v-for="c in checks" :key="c.check" class="border-b border-ink">
        <button
          type="button"
          :aria-expanded="openCheck === c.check"
          class="grid w-full cursor-pointer grid-cols-[44px_minmax(0,1fr)_minmax(0,1.5fr)_80px_84px_18px] items-center gap-3 bg-transparent px-3.5 py-[11px] text-left"
          @click="openCheck = openCheck === c.check ? null : c.check"
        >
          <span class="font-mono text-[11px] text-faint">{{ c.check }}</span>
          <span class="text-[15px] font-bold">{{ c.name }}</span>
          <span class="text-[13px] leading-[1.35]">{{ c.question }}</span>
          <span class="font-mono text-[11px]">{{ c.issuesText }}</span>
          <RuleStamp
            :status="c.status"
            class="-rotate-3 justify-self-start px-2 py-[3px] text-[11px] tracking-[0.1em] [animation:hm-stamp_.25s_ease-out_both]"
          />
          <span aria-hidden="true" class="font-mono text-xs">{{ openCheck === c.check ? '▾' : '▸' }}</span>
        </button>
        <ul v-if="openCheck === c.check" class="m-0 flex list-none flex-col gap-1 pr-3.5 pb-3 pl-[70px]">
          <li
            v-for="it in c.items"
            :key="it.id"
            class="flex flex-col gap-2 border border-ink bg-white p-3 outline-offset-1"
            :class="ws.sel === it.item_key ? 'outline-2 outline-signal' : ''"
          >
            <div class="flex items-baseline gap-3">
              <span class="w-[72px] flex-none font-mono text-xs font-bold">{{ it.item_key }}</span>
              <span class="text-sm leading-[1.4]">{{ it.message }}</span>
            </div>
            <div class="flex items-baseline gap-3">
              <span class="w-[72px] flex-none font-mono text-[10.5px] font-bold tracking-[0.06em] text-muted">TO FIX</span>
              <span class="font-read text-[14px] leading-[1.55]">{{ it.next_step || 'Upload the record that clears this finding, then run checks again.' }}</span>
            </div>
            <div v-if="it.evidence" class="flex items-baseline gap-3">
              <span class="w-[72px] flex-none font-mono text-[10.5px] font-bold tracking-[0.06em] text-muted">STATUS</span>
              <span class="font-mono text-xs">{{ it.evidence.filename }} added · {{ it.evidence.status.replace('_', ' ') }}</span>
            </div>
            <div class="flex flex-wrap gap-1.5 pl-[84px]">
              <button
                v-if="!it.evidence"
                type="button"
                class="btn-hard bg-signal px-3 py-[7px] text-[11.5px] tracking-[0.04em]"
                @click="openUpload({ group: EVIDENCE_GROUP[it.rule_id], id: it.item_key })"
              >{{ fixLabel(it.rule_id) }}</button>
              <button
                v-else
                type="button"
                class="btn-hard bg-signal px-3 py-[7px] text-[11.5px] tracking-[0.04em]"
                @click="store.dispatch('workspace/runChecks')"
              >Run checks again</button>
              <button
                type="button"
                class="btn-hard bg-white px-3 py-[7px] text-[11.5px] tracking-[0.04em] hover:bg-paper"
                @click="emit('show-item', it.item_key)"
              >Show in inspector →</button>
            </div>
          </li>
          <li v-if="!c.items.length" class="py-1 font-mono text-[11px] text-faint">NO ISSUES ON THE LAST RUN</li>
        </ul>
      </div>
      <p class="m-0 px-3.5 py-2.5 font-mono text-[10.5px] text-faint">Statuses are set by rules. The quality engineer signs off the release.</p>
    </div>
  </div>
</template>
