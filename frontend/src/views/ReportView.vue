<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useStore } from 'vuex'
import AppBar from '../components/app/AppBar.vue'
import Breadcrumb from '../components/app/Breadcrumb.vue'
import RuleStamp from '../components/ui/RuleStamp.vue'
import { heatText } from '../data/workspace'
import { clockTime, isoDate, worst } from '../lib/status'

const route = useRoute()
const store = useStore()

const projectNo = computed(() => route.params.no)
const workspaceLink = computed(() => `/projects/${projectNo.value}`)
const reportNo = computed(() => `HM-RR-${projectNo.value.split('-').pop()}`)
const crumbs = computed(() => [
  { label: 'PROJECTS', to: '/projects' },
  { label: projectNo.value, to: workspaceLink.value },
  { label: `RELEASE REPORT ${reportNo.value}` },
])

watch(projectNo, (no) => no && store.dispatch('release/load', no), { immediate: true })

const r = computed(() => store.state.release)
const run = computed(() => (r.value.run?.status === 'complete' ? r.value.run : null))
const summary = computed(() => run.value?.summary ?? {})
const counts = computed(() => summary.value.counts ?? { pass: 0, hold: 0, reject: 0 })
const findings = computed(() =>
  [...(run.value?.findings ?? [])].sort((a, b) => (b.status === 'REJECT') - (a.status === 'REJECT') || a.check_id.localeCompare(b.check_id)),
)
const checkName = computed(() => Object.fromEntries((summary.value.checks ?? []).map((c) => [c.check, c.name])))
const overall = computed(() => worst(findings.value.map((f) => f.status)))
const nReject = computed(() => findings.value.filter((f) => f.status === 'REJECT').length)
const nHold = computed(() => findings.value.length - nReject.value)

const when = (iso) => (iso ? `${isoDate(new Date(iso))} · ${clockTime(new Date(iso))}` : '—')

const meta = computed(() => [
  { label: 'PROJECT NO.', value: projectNo.value },
  { label: 'REPORT NO.', value: reportNo.value },
  { label: 'DATE', value: when(run.value?.finished_at) },
  { label: 'INSPECTOR', value: (store.state.auth.user?.name ?? '—').toUpperCase() },
  { label: 'RULE SET', value: run.value?.rule_set ?? '—' },
  { label: 'SCOPE', value: r.value.project?.scope ?? '—' },
])

const tiles = computed(() => [
  { value: summary.value.documents ?? 0, label: 'DOCUMENTS' },
  { value: summary.value.fields ?? 0, label: 'FIELDS READ' },
  { value: summary.value.welds ?? 0, label: 'WELDS' },
  { value: counts.value.pass, label: 'PASS', tone: 'text-pass font-bold' },
  { value: counts.value.hold, label: 'HOLD', tone: 'bg-signal font-bold' },
  { value: counts.value.reject, label: 'REJECT', tone: 'text-reject font-bold' },
])

const summaryText = computed(() => {
  if (!findings.value.length) return 'All critical checks passed on the last run. The assembly is ready for engineer sign-off.'
  const parts = []
  if (nReject.value) parts.push(`${nReject.value} rejected ${nReject.value === 1 ? 'item must' : 'items must'} be corrected`)
  if (nHold.value) parts.push(`${nHold.value} ${nHold.value === 1 ? 'record is' : 'records are'} missing, unconfirmed or unsigned`)
  return `The assembly cannot be released: ${parts.join(' and ')}. Each item is listed in section 03 with its source document.`
})

// One row per weld: parts, heats and NDT reports, at the worst status of anything involved.
const trace = computed(() => {
  const byKey = Object.fromEntries(r.value.items.map((i) => [i.key, i]))
  const statusOf = (k) => worst(findings.value.filter((f) => f.item_key === k).map((f) => f.status))
  const ndts = r.value.items.filter((i) => i.kind === 'ndt')
  return r.value.items
    .filter((i) => i.kind === 'weld')
    .sort((a, b) => a.key.localeCompare(b.key, undefined, { numeric: true }))
    .map((w) => {
      const parts = w.attributes.parts ?? []
      const heats = [...new Set(parts.flatMap((p) => byKey[p]?.attributes.heat_nos ?? []))]
      const reports = ndts.filter((n) => n.attributes.welds?.includes(w.key)).map((n) => n.key)
      return {
        weld: w.key,
        part: parts.join(' / ') || '—',
        heat: heatText(parts, byKey),
        wps: w.attributes.wps ?? '—',
        welder: w.attributes.welder ?? '—',
        ndt: reports.join(' · ') || '— MISSING',
        status: worst([w.key, ...parts, ...heats, ...reports].map(statusOf)),
      }
    })
})

const DECISIONS = computed(() => [
  { key: 'hold', label: 'Do not release', note: 'Keep the assembly on hold until the open findings are closed.' },
  { key: 'concession', label: 'Release with concession', note: 'Release under a documented deviation. Add the concession reference in the comment.' },
  findings.value.length
    ? { key: 'release', label: 'Release', note: `Blocked: ${nReject.value} REJECT and ${nHold.value} HOLD findings are open.`, disabled: true }
    : { key: 'release', label: 'Release', note: 'All critical checks passed on the last run.' },
])
const decisionLabel = (key) => DECISIONS.value.find((d) => d.key === key)?.label.toUpperCase() ?? key

const signature = computed(() => r.value.signature)
const decision = ref('hold')
const comment = ref('')
const name = ref(store.state.auth.user?.name ?? '')
watch(
  () => store.state.auth.user?.name,
  (n) => {
    if (n && !name.value) name.value = n
  },
)
const reviewed = ref(false)
const signing = ref(false)
const signError = ref('')
const canSign = computed(() => reviewed.value && name.value.trim() && run.value && !signing.value)

const act = async (fn) => {
  signing.value = true
  signError.value = ''
  try {
    await fn()
  } catch (e) {
    signError.value = e.message
  } finally {
    signing.value = false
  }
}
const sign = () =>
  canSign.value && act(() => store.dispatch('release/sign', { decision: decision.value, name: name.value, comment: comment.value }))
const revoke = () =>
  act(async () => {
    reviewed.value = false
    await store.dispatch('release/revoke')
  })
const print = () => window.print()

const section = 'flex flex-col gap-3.5 border-b border-ink px-[clamp(20px,4vw,40px)] py-6'
const h2 = 'm-0 font-mono text-xs tracking-[0.08em]'
</script>

<template>
  <div class="flex min-h-screen flex-col bg-paper font-sans text-ink print:block print:min-h-0 print:bg-white">
    <AppBar data-noprint class="sticky top-0 z-[5]" :avatar="false">
      <template #title>
        <Breadcrumb :items="crumbs" class="flex-[1_1_220px]" />
      </template>
      <template #status>
        <span class="flex items-center gap-2 px-2 font-mono text-[11px] tracking-[0.06em]">
          <span aria-hidden="true" class="size-[9px] rounded-full border border-ink" :class="signature ? 'bg-ink' : 'bg-signal'"></span>
          {{ signature ? `SIGNED · ${decisionLabel(signature.decision)}` : 'AWAITING SIGN-OFF' }}
        </span>
      </template>
      <template #actions>
        <RouterLink :to="workspaceLink" class="btn-hard bg-white px-3.5 py-2 text-xs tracking-[0.06em] uppercase no-underline">← Workspace</RouterLink>
        <button type="button" class="btn-hard flex items-center gap-2 bg-signal px-3.5 py-2 text-xs tracking-[0.06em] uppercase" @click="print">
          <span aria-hidden="true" class="size-[7px] bg-ink"></span>Print / Save PDF
        </button>
      </template>
    </AppBar>

    <main class="flex-1 px-[clamp(12px,3vw,32px)] py-[clamp(16px,4vw,48px)] print:p-0">
      <p v-if="r.loading" class="mx-auto max-w-[920px] font-mono text-xs text-faint">LOADING REPORT…</p>
      <p v-else-if="r.error" class="mx-auto max-w-[920px] font-mono text-xs text-reject">COULD NOT LOAD THE REPORT · {{ r.error }}</p>
      <div v-else-if="!run" class="mx-auto flex max-w-[920px] flex-col items-start gap-3 border border-ink bg-white p-8">
        <span class="font-mono text-[11px] tracking-[0.08em] text-faint">NO COMPLETED RULE RUN</span>
        <p class="m-0 text-lg">Upload the project's documents and run the checks in the workspace to produce this report.</p>
        <RouterLink :to="workspaceLink" class="font-mono text-[13px] underline-offset-4">Open the workspace →</RouterLink>
      </div>

      <article v-else aria-label="Release readiness report" class="mx-auto max-w-[920px] border border-ink bg-white print:max-w-none print:border-0">
        <div class="flex flex-wrap items-start justify-between gap-5 border-b-2 border-ink px-[clamp(20px,4vw,40px)] pt-7 pb-6">
          <div class="flex flex-col gap-2">
            <span class="font-mono text-[11px] tracking-[0.08em] text-faint">HEATMARK · FORM HM-RR-01 · REV. A</span>
            <h1 class="m-0 text-[clamp(30px,4vw,44px)] leading-[0.95] font-extrabold tracking-[-0.035em]">Release readiness report</h1>
            <span class="text-base">{{ r.project?.name }} · {{ projectNo }}</span>
          </div>
          <div class="flex flex-col items-end gap-2.5">
            <RuleStamp
              :status="overall"
              class="-rotate-6 border-[3px] px-[18px] py-2 text-2xl tracking-[0.16em] outline outline-offset-[3px] [animation:hm-stamp_.3s_.2s_ease-out_both]"
            />
            <span class="pt-1.5 font-mono text-xs font-bold tracking-[0.06em]">
              {{ findings.length ? 'NOT READY FOR RELEASE' : 'READY FOR SIGN-OFF' }}
            </span>
          </div>
        </div>

        <dl class="m-0 grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] border-b border-ink font-mono">
          <div v-for="m in meta" :key="m.label" class="-mb-px flex flex-col gap-1 border-r border-b border-ink px-4 py-3 last:border-r-0">
            <dt class="text-[10px] tracking-[0.08em] text-faint">{{ m.label }}</dt>
            <dd class="m-0 text-[13px] font-bold">{{ m.value }}</dd>
          </div>
        </dl>

        <section aria-labelledby="sum-h" :class="section">
          <h2 id="sum-h" :class="h2">01 / SUMMARY</h2>
          <div class="grid grid-cols-[repeat(auto-fit,minmax(110px,1fr))] border border-ink">
            <div v-for="s in tiles" :key="s.label" class="flex flex-col gap-1 border-r border-ink p-3.5 font-mono last:border-r-0" :class="s.tone">
              <span class="text-[28px] leading-none font-bold">{{ s.value }}</span>
              <span class="text-[10.5px] tracking-[0.06em]" :class="s.tone ? '' : 'text-muted'">{{ s.label }}</span>
            </div>
          </div>
          <p class="m-0 max-w-[680px] text-[15px] leading-normal">{{ summaryText }}</p>
        </section>

        <section aria-labelledby="chk-h" :class="section">
          <h2 id="chk-h" :class="h2">02 / CRITICAL CHECKS</h2>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[600px] border-collapse border border-ink">
              <thead>
                <tr class="bg-ink text-left font-mono text-[10.5px] tracking-[0.08em] text-paper">
                  <th scope="col" class="px-3 py-[9px]">NO.</th>
                  <th scope="col" class="px-3 py-[9px]">CHECK</th>
                  <th scope="col" class="px-3 py-[9px]">QUESTION</th>
                  <th scope="col" class="px-3 py-[9px]">ISSUES</th>
                  <th scope="col" class="px-3 py-[9px]">RESULT</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in summary.checks" :key="c.check" class="border-b border-ink break-inside-avoid">
                  <td class="p-3 font-mono text-xs text-muted">{{ c.check }}</td>
                  <td class="p-3 text-[15px] font-bold">{{ c.name }}</td>
                  <td class="p-3 text-sm leading-[1.4]">{{ c.question }}</td>
                  <td class="p-3 font-mono text-xs">{{ c.issues }} {{ c.issues === 1 ? 'ISSUE' : 'ISSUES' }}</td>
                  <td class="px-3 py-2.5"><RuleStamp :status="c.status" class="-rotate-3 bg-white px-[9px] py-[3px] text-[11.5px] tracking-[0.1em]" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="fnd-h" :class="section">
          <div class="flex flex-wrap justify-between gap-2">
            <h2 id="fnd-h" :class="h2">03 / FINDINGS, RANKED BY RELEASE IMPACT</h2>
            <span class="font-mono text-[11px] text-muted">{{ findings.length }} OPEN</span>
          </div>
          <ol v-if="findings.length" class="m-0 list-none border-t border-ink p-0">
            <li
              v-for="(f, i) in findings"
              :key="f.id"
              class="grid grid-cols-[36px_minmax(0,1fr)_auto] gap-x-4 gap-y-1.5 border-b border-ink py-4 break-inside-avoid"
            >
              <span class="font-mono text-[13px] font-bold">{{ String(i + 1).padStart(2, '0') }}</span>
              <div class="flex min-w-0 flex-col gap-1.5">
                <span class="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
                  <span class="font-mono text-[13px] font-bold">{{ f.item_key }}</span>
                  <span class="text-base font-bold">{{ checkName[f.check_id] }}</span>
                </span>
                <span class="font-read text-[15px] leading-[1.6]">{{ f.explanation || f.message }}</span>
                <span v-if="f.next_step" class="font-read text-[14px] leading-[1.55]">
                  <span class="font-mono text-[11px] font-bold tracking-[0.06em]">NEXT STEP · </span>{{ f.next_step }}
                </span>
                <span class="font-mono text-[11px] text-muted">
                  SRC: {{ f.sources.map((s) => `${s.document}${s.page ? ` p.${s.page}` : ''}`).join(' / ') }} · RULE {{ f.rule_id }}
                </span>
              </div>
              <RuleStamp :status="f.status" class="rotate-3 self-start bg-white px-[9px] py-[3px] text-[11.5px] tracking-[0.1em]" />
            </li>
          </ol>
          <p v-else class="m-0 text-[15px]">No open findings.</p>
          <p class="m-0 font-mono text-[11px] leading-normal text-muted">
            Explanations are AI-written from the source documents for review. Statuses come from rule set {{ run.rule_set }}.
          </p>
        </section>

        <section aria-labelledby="trc-h" :class="section">
          <h2 id="trc-h" :class="h2">04 / TRACEABILITY · PART → HEAT → WELD → NDT</h2>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[640px] border-collapse border border-ink font-mono text-xs">
              <thead>
                <tr class="bg-ink text-left text-[10.5px] tracking-[0.08em] text-paper">
                  <th scope="col" class="px-3 py-[9px]">PART</th>
                  <th scope="col" class="px-2.5 py-[9px]">HEAT NO.</th>
                  <th scope="col" class="px-2.5 py-[9px]">WELD</th>
                  <th scope="col" class="px-2.5 py-[9px]">WPS</th>
                  <th scope="col" class="px-2.5 py-[9px]">WELDER</th>
                  <th scope="col" class="px-2.5 py-[9px]">NDT</th>
                  <th scope="col" class="px-3 py-[9px]">STATUS</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in trace" :key="t.weld" class="border-b border-ink break-inside-avoid">
                  <td class="px-3 py-2.5">{{ t.part }}</td>
                  <td class="p-2.5">{{ t.heat }}</td>
                  <td class="p-2.5 font-bold">{{ t.weld }}</td>
                  <td class="p-2.5">{{ t.wps }}</td>
                  <td class="p-2.5">{{ t.welder }}</td>
                  <td class="p-2.5">{{ t.ndt }}</td>
                  <td class="px-3 py-2"><RuleStamp :status="t.status" class="bg-white px-2 py-0.5 text-[11px] tracking-[0.1em]" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="sig-h" class="flex flex-col gap-4 px-[clamp(20px,4vw,40px)] pt-6 pb-8">
          <h2 id="sig-h" :class="h2">05 / ENGINEER SIGN-OFF</h2>

          <form v-if="!signature || !signature.current" class="flex flex-col gap-4" @submit.prevent="sign">
            <fieldset class="m-0 flex flex-col gap-2 border-0 p-0">
              <legend class="pb-2 font-mono text-[11px] tracking-[0.08em] text-muted">DECISION</legend>
              <label
                v-for="d in DECISIONS"
                :key="d.key"
                class="flex items-start gap-3 border px-3.5 py-3"
                :class="[
                  decision === d.key ? 'border-ink bg-paper' : 'border-pending bg-white',
                  d.disabled ? 'cursor-not-allowed opacity-55' : 'cursor-pointer',
                ]"
              >
                <input v-model="decision" type="radio" name="decision" :value="d.key" :disabled="d.disabled" class="mt-[3px] accent-ink" />
                <span class="flex flex-col gap-[3px]">
                  <span class="text-[15px] font-bold">{{ d.label }}</span>
                  <span class="text-[13.5px] leading-[1.4] text-muted">{{ d.note }}</span>
                </span>
              </label>
            </fieldset>
            <label class="flex flex-col gap-1.5">
              <span class="font-mono text-[11px] tracking-[0.08em] text-muted">COMMENT</span>
              <textarea
                v-model="comment"
                rows="3"
                placeholder="Reason for the decision, actions agreed, concession reference…"
                class="resize-y border border-ink bg-white p-2.5 text-[14.5px] leading-[1.4] outline-none focus:outline-2 focus:outline-signal"
              ></textarea>
            </label>
            <div class="flex flex-wrap items-end gap-4">
              <label class="flex flex-[1_1_240px] flex-col gap-1.5">
                <span class="font-mono text-[11px] tracking-[0.08em] text-muted">NAME · QUALITY ENGINEER</span>
                <input
                  v-model="name"
                  type="text"
                  required
                  class="border-0 border-b border-ink bg-transparent p-2.5 font-mono text-[15px] outline-none focus:border-b-2 focus:border-signal"
                />
              </label>
              <label class="flex flex-[2_1_300px] cursor-pointer items-start gap-2.5 text-sm leading-[1.4]">
                <input v-model="reviewed" type="checkbox" class="mt-0.5 size-4 accent-ink" />
                I have reviewed the findings and their source documents.
              </label>
            </div>
            <div data-noprint class="flex flex-wrap items-center gap-3.5">
              <button
                type="submit"
                :disabled="!canSign"
                class="flex cursor-pointer items-center gap-2.5 border border-b-4 border-ink border-b-black bg-ink px-5 py-3 font-mono text-[13px] font-bold tracking-[0.06em] text-paper uppercase active:translate-y-[3px] active:border-b disabled:cursor-not-allowed disabled:opacity-40"
              >
                <span aria-hidden="true" class="size-2 bg-signal"></span>{{ signing ? 'Signing…' : 'Sign report' }}
              </button>
              <span class="font-mono text-[11px]" :class="signError ? 'text-reject' : 'text-muted'">
                {{ signError || (canSign ? 'Your signature is recorded with the date and decision.' : 'Confirm the review to enable signing.') }}
              </span>
            </div>
          </form>

          <p v-if="signature && !signature.current" role="note" class="m-0 border-l-2 border-signal pl-3 font-read text-[14px] leading-snug">
            The documents changed after the sign-off below, so it no longer covers this dossier. It stays on record.
            Review the current result and sign again above.
          </p>
          <div
            v-if="signature"
            class="flex flex-wrap items-center gap-6 border p-5"
            :class="signature.current ? 'border-ink' : 'border-dashed border-ink/50 opacity-75'"
          >
            <span
              class="inline-block -rotate-6 border-[3px] px-4 py-2 font-mono text-xl font-bold tracking-[0.16em] outline outline-offset-[3px] [animation:hm-stamp_.3s_ease-out_both]"
              :class="signature.current ? 'border-ink outline-ink' : 'border-signal text-signal outline-signal'"
            >{{ signature.current ? 'SIGNED' : 'OUTDATED' }}</span>
            <dl class="m-0 grid flex-[1_1_280px] grid-cols-[120px_minmax(0,1fr)] gap-x-3 gap-y-1.5 font-mono text-[12.5px]">
              <dt class="text-muted">DECISION</dt><dd class="m-0 font-bold">{{ decisionLabel(signature.decision) }}</dd>
              <dt class="text-muted">SIGNED BY</dt><dd class="m-0 font-bold">{{ signature.name }} · QUALITY ENGINEER</dd>
              <dt class="text-muted">DATE</dt><dd class="m-0">{{ when(signature.signed_at) }}</dd>
              <dt class="text-muted">COMMENT</dt><dd class="m-0 font-sans text-sm leading-[1.4]">{{ signature.comment || '—' }}</dd>
            </dl>
            <div v-if="signature.current" data-noprint class="flex flex-col items-start gap-1.5">
              <button type="button" :disabled="signing" class="btn-hard bg-white px-3 py-2 text-[11.5px]" @click="revoke">Revoke signature</button>
              <span v-if="signError" class="font-mono text-[11px] text-reject">{{ signError }}</span>
            </div>
          </div>
        </section>

        <div class="flex flex-wrap justify-between gap-2 border-t-2 border-ink px-[clamp(20px,4vw,40px)] py-2.5 font-mono text-[10.5px] tracking-[0.06em] text-muted print:break-before-avoid">
          <span>HEATMARK · {{ reportNo }} · REV. A</span><span>SHEET 1 OF 1</span><span>POWERED BY SHOYUPURO</span>
        </div>
      </article>
    </main>
  </div>
</template>
