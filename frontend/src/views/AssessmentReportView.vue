<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import EvidenceSnap from '../components/assessment/EvidenceSnap.vue'

// A printable A4 document: black on white in print; on screen it follows the app theme. Short by design: the conclusion, the
// nonconformances in Pareto order and the sign-off; evidence, documents and check details are appendices.
const TONE = { ink: 'text-(--r-ink)', pass: 'text-(--r-pass)', warn: 'text-(--r-warn)', reject: 'text-(--r-reject)', muted: 'text-(--r-muted)' }
const BORDER = { pass: 'border-(--r-pass)', warn: 'border-(--r-warn)', reject: 'border-(--r-reject)', muted: 'border-(--r-muted)' }
const isSheet = (name) => /\.(xlsx|xlsm|csv)$/i.test(name)

const route = useRoute()
const projectNo = computed(() => route.params.no)
const rep = ref(null)
const error = ref('')
const details = ref(false)

watch(
  projectNo,
  (no) => {
    rep.value = null
    error.value = ''
    api.assessment.report(no).then(
      (r) => {
        rep.value = r
        document.title = `${r.report_no} · ${r.title}`
      },
      (e) => (error.value = e.message || 'Could not build the report'),
    )
  },
  { immediate: true },
)

const r = computed(() => rep.value?.result)
const evidenceIssues = computed(() =>
  rep.value && !rep.value.sample_data
    ? [...rep.value.issues, ...rep.value.observations].filter((i) => i.evidence.some((e) => !isSheet(e.file)))
    : [],
)
const maxNc = computed(() => Math.max(1, ...(rep.value?.areas ?? []).map((a) => a.nc)))
const printReport = () => window.print()
</script>

<template>
  <div class="report min-h-screen bg-(--r-page) font-sans text-(--r-ink)">
    <div class="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 border-b border-(--r-ink) bg-(--r-page) px-6 py-2.5 print:hidden">
      <RouterLink :to="`/projects/${projectNo}/review`" class="text-xs font-bold tracking-[0.06em] text-(--r-ink)">← BACK TO REVIEW</RouterLink>
      <div v-if="rep" class="flex flex-wrap items-center gap-4">
        <label class="flex cursor-pointer items-center gap-2 text-xs">
          <input v-model="details" type="checkbox" class="size-3.5 accent-(--r-ink)" /> Include check details (appendix C)
        </label>
        <button type="button" class="btn-hard bg-(--r-signal) px-4 py-2 text-xs tracking-[0.06em] text-[#111111] uppercase" @click="printReport">
          Print / save PDF
        </button>
      </div>
    </div>

    <p v-if="error" class="mx-auto my-16 max-w-[560px] px-6 text-center text-sm text-(--r-reject)">{{ error }}</p>
    <p v-else-if="!rep" class="my-16 text-center text-xs text-(--r-muted)">Building report…</p>

    <!-- The table's head and foot repeat on every printed page. -->
    <article
      v-else
      class="mx-auto my-8 box-border w-[210mm] max-w-[calc(100%-32px)] border border-(--r-line) bg-(--r-sheet) px-[18mm] py-[14mm] text-[9.5pt] leading-[1.45] max-sm:px-5 print:m-0 print:w-auto print:max-w-none print:border-0 print:p-0"
    >
      <table class="w-full border-collapse">
        <thead>
          <tr>
            <td class="p-0">
              <div class="flex items-end justify-between gap-3 border-b-2 border-(--r-ink) pb-2 whitespace-nowrap">
                <span class="flex items-center gap-2 text-[11pt] font-bold">
                  <span class="size-[9px] border border-(--r-ink) bg-(--r-signal)"></span>HIBANAKO
                </span>
                <span class="text-[8pt]">{{ rep.report_no }} · Rev. A · {{ rep.mode === 'PLAN' ? 'Plan review' : 'As-built' }}</span>
              </div>
            </td>
          </tr>
        </thead>
        <tfoot>
          <tr>
            <td class="p-0 pt-5">
              <div class="border-t border-(--r-ink) pt-1.5 text-[7.5pt] text-(--r-sub)">{{ rep.footer }}</div>
            </td>
          </tr>
        </tfoot>
        <tbody>
          <tr>
            <td class="p-0">
              <h1 class="m-0 pt-5 text-[18pt] leading-tight font-bold">{{ rep.title }}</h1>
              <p class="mt-1 mb-3.5 text-[10pt] text-(--r-sub)">{{ rep.subtitle }}</p>

              <p v-if="rep.stale" class="m-0 mb-2.5 border-l-4 border-(--r-warn) bg-(--r-warn-bg) px-2.5 py-1.5 font-bold text-(--r-warn)">
                {{ rep.stale_reasons.join(', ') }} after this run. Re-run before issuing.
              </p>
              <p v-if="rep.sample_data" class="m-0 mb-2.5 border-l-4 border-(--r-line) px-2.5 py-1.5 text-(--r-sub)">
                Sample data, not an issued assessment.
              </p>

              <table class="mb-4 w-full border-collapse">
                <tbody>
                  <tr v-for="(row, i) in rep.header" :key="row.label" :class="i % 2 ? '' : 'bg-(--r-band)'">
                    <th scope="row" class="w-[22%] border-y border-(--r-line) px-2 py-1 text-left font-semibold">{{ row.label }}</th>
                    <td class="border-y border-(--r-line) px-2 py-1">{{ row.value }}</td>
                  </tr>
                </tbody>
              </table>

              <div class="mb-1 flex break-inside-avoid items-stretch border-2" :class="BORDER[rep.verdict_tone]">
                <div class="flex w-[34%] flex-none items-center px-3 py-2.5 text-[12pt] font-bold" :class="TONE[rep.verdict_tone]">
                  {{ rep.verdict }}
                </div>
                <div class="flex flex-col justify-center gap-0.5 border-l border-(--r-line) px-3 py-2">
                  <span class="font-semibold">{{ rep.conclusion }}</span>
                  <span class="text-[8.5pt] text-(--r-sub)">
                    {{ rep.counts.nc }} nonconformance(s) · {{ rep.counts.obs }} observation(s) · {{ rep.counts.waived }} waived
                  </span>
                </div>
              </div>

              <h2 class="h-band">1 · Nonconformances</h2>
              <p v-if="!rep.issues.length" class="m-0 text-(--r-sub)">None.</p>
              <table v-else class="w-full border-collapse text-[8.5pt]">
                <thead>
                  <tr class="bg-(--r-band) text-left">
                    <th scope="col" class="cell w-[4%]">#</th>
                    <th scope="col" class="cell w-[11%]">Item</th>
                    <th scope="col" class="cell w-[37%]">Finding</th>
                    <th scope="col" class="cell w-[20%]">Requirement</th>
                    <th scope="col" class="cell">Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="i in rep.issues" :key="i.no" class="break-inside-avoid">
                    <td class="cell align-top font-bold">{{ i.no }}</td>
                    <td class="cell align-top">{{ i.items.join(', ') }}</td>
                    <td class="cell align-top">
                      {{ i.finding }}
                      <div class="text-[7.5pt] text-(--r-muted)">{{ i.area }} · {{ i.rule_id }}</div>
                    </td>
                    <td class="cell align-top">{{ i.requirement }}</td>
                    <td class="cell align-top">{{ i.action }}</td>
                  </tr>
                </tbody>
              </table>

              <template v-if="rep.observations.length">
                <h2 class="h-band">2 · Observations</h2>
                <table class="w-full border-collapse text-[8.5pt]">
                  <tbody>
                    <tr v-for="i in rep.observations" :key="i.no" class="break-inside-avoid">
                      <td class="cell w-[4%] align-top font-bold">{{ i.no }}</td>
                      <td class="cell w-[11%] align-top">{{ i.items.join(', ') }}</td>
                      <td class="cell w-[57%] align-top">{{ i.finding }}</td>
                      <td class="cell align-top">{{ i.action }}</td>
                    </tr>
                  </tbody>
                </table>
              </template>

              <template v-if="rep.waived.length">
                <h2 class="h-band">Waived</h2>
                <table class="w-full border-collapse text-[8.5pt]">
                  <tbody>
                    <tr v-for="i in rep.waived" :key="i.no" class="break-inside-avoid">
                      <td class="cell w-[4%] align-top font-bold">{{ i.no }}</td>
                      <td class="cell w-[11%] align-top">{{ i.items.join(', ') }}</td>
                      <td class="cell w-[45%] align-top">{{ i.finding }}</td>
                      <td class="cell align-top">{{ i.waiver?.reason }} <span class="text-(--r-muted)">({{ i.waiver?.by }})</span></td>
                    </tr>
                  </tbody>
                </table>
              </template>

              <h2 class="h-band">3 · Results by check area</h2>
              <table v-if="rep.areas.length" class="w-full border-collapse text-[8.5pt]">
                <thead>
                  <tr class="bg-(--r-band) text-left">
                    <th scope="col" class="cell w-[38%]">Area</th>
                    <th scope="col" class="cell w-[9%] text-right">NC</th>
                    <th scope="col" class="cell w-[9%] text-right">Obs.</th>
                    <th scope="col" class="cell w-[10%] text-right">Cum. %</th>
                    <th scope="col" class="cell"><span class="sr-only">Share</span></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="a in rep.areas" :key="a.area">
                    <td class="cell">{{ a.area }}</td>
                    <td class="cell text-right font-bold" :class="a.nc ? TONE.reject : ''">{{ a.nc }}</td>
                    <td class="cell text-right">{{ a.obs }}</td>
                    <td class="cell text-right">{{ a.cum_pct ?? '—' }}</td>
                    <td class="cell">
                      <span class="block h-2 bg-(--r-reject)" :style="{ width: `${(a.nc / maxNc) * 100}%` }"></span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-if="rep.clean_checks.length" class="mt-1.5 mb-0 text-[8.5pt] text-(--r-sub)">
                No issues: {{ rep.clean_checks.join('; ') }}.
              </p>

              <div class="break-inside-avoid">
                <h2 class="h-band">Reviewer notes</h2>
                <template v-if="rep.notes">
                  <p class="m-0 text-[9.5pt] leading-[1.45] whitespace-pre-line">{{ rep.notes.text }}</p>
                  <p class="mt-1 mb-0 text-[8.5pt] text-(--r-sub)">{{ rep.notes.by }} · {{ rep.notes.at.slice(0, 10) }}</p>
                </template>
                <template v-else>
                  <!-- No notes saved: ruled lines to write on after printing. -->
                  <p class="m-0 text-[8.5pt] text-(--r-sub)">No notes recorded in Hibanako. Add them on the review page, or write them here.</p>
                  <div v-for="i in 3" :key="i" class="h-[7mm] border-b border-(--r-line)"></div>
                </template>
              </div>

              <div class="break-inside-avoid">
                <h2 class="h-band">Approval</h2>
                <table class="w-full border-collapse">
                  <thead>
                    <tr class="bg-(--r-band) text-left">
                      <th scope="col" class="cell">Role</th>
                      <th scope="col" class="cell">Name</th>
                      <th scope="col" class="cell w-[34%]">Signature</th>
                      <th scope="col" class="cell">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="a in rep.approval" :key="a.role">
                      <td class="cell">{{ a.role }}</td>
                      <td class="cell">{{ a.name }}</td>
                      <td class="cell h-10"></td>
                      <td class="cell">{{ a.date }}</td>
                    </tr>
                  </tbody>
                </table>
                <p class="mt-1.5 mb-0 text-[8pt] text-(--r-sub)">Codes: {{ rep.references.join(', ') }}.</p>
              </div>

              <section v-if="evidenceIssues.length" class="break-before-page">
                <h2 class="h-band">Appendix A · Evidence</h2>
                <div v-for="i in evidenceIssues" :key="i.no" class="mb-3 break-inside-avoid">
                  <p class="m-0 mb-1 font-semibold">{{ i.no }} · {{ i.items.join(', ') }} · {{ i.finding }}</p>
                  <div class="flex flex-wrap gap-2">
                    <EvidenceSnap
                      v-for="(e, k) in i.evidence.filter((x) => !isSheet(x.file))"
                      :key="k"
                      class="w-[48%]"
                      :project-no="projectNo"
                      :evidence="e"
                      paper
                    />
                  </div>
                </div>
              </section>

              <section class="break-inside-avoid">
                <h2 class="h-band">Appendix B · Documents assessed</h2>
                <table class="w-full border-collapse text-[8.5pt]">
                  <tbody>
                    <tr v-for="d in rep.documents" :key="d.slot">
                      <th scope="row" class="cell w-[24%] bg-(--r-band) text-left font-semibold">{{ d.slot }}</th>
                      <td class="cell">{{ d.files.join(', ') }}</td>
                    </tr>
                  </tbody>
                </table>
              </section>

              <section v-if="details">
                <h2 class="h-band">Appendix C · Check details</h2>
                <div v-for="sec in r.sections" :key="sec.id" class="mb-2">
                  <h3 class="mt-2 mb-1 text-[9.5pt] font-bold">{{ sec.title }}</h3>
                  <table v-if="sec.rows" class="w-full border-collapse text-[8pt]">
                    <thead>
                      <tr class="bg-(--r-band) text-left">
                        <th v-for="h in sec.headers" :key="h" scope="col" class="cell font-bold">{{ h }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, k) in sec.rows" :key="k" class="break-inside-avoid">
                        <td v-for="(cl, j) in row" :key="j" class="cell align-top" :class="[TONE[cl.tone], cl.bold ? 'font-bold' : '']">{{ cl.v }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <p v-else class="m-0 text-[8pt] text-(--r-sub)">Not assessed: {{ sec.missing }}</p>
                </div>
              </section>
            </td>
          </tr>
        </tbody>
      </table>
    </article>
  </div>
</template>

<style scoped>
@reference "../style.css";

/* Document colours: black on white, and a dark sheet on screen in the dark theme. Print always uses the light set. */
.report {
  --r-page: #ffffff;
  --r-sheet: #ffffff;
  --r-ink: #111111;
  --r-sub: #555555;
  --r-muted: #6e6e6e;
  --r-line: #cccccc;
  --r-band: #f4f4f4;
  --r-pass: #1f6b3a;
  --r-warn: #b34700;
  --r-warn-bg: #fff4ec;
  --r-reject: #c4271b;
  --r-signal: #ff4f00;
}
@media screen {
  :global(html[data-hm-theme='dark']) .report {
    --r-page: #0d0d0d;
    --r-sheet: #161616;
    --r-ink: #ececec;
    --r-sub: #b5b5b5;
    --r-muted: #8c8c8c;
    --r-line: #3a3a3a;
    --r-band: #1f1f1f;
    --r-pass: #4cc274;
    --r-warn: #ff9a4d;
    --r-warn-bg: #2a1a10;
    --r-reject: #ff5c50;
    --r-signal: #ff5a1a;
  }
}

/* Formal document: one plain office typeface throughout, including the app's mono and display text. */
.report,
.report :deep(*) {
  font-family: Arial, Helvetica, 'Liberation Sans', sans-serif !important;
  font-stretch: normal !important;
}
.h-band {
  @apply mt-4 mb-1.5 border-b border-(--r-ink) pb-1 text-[10.5pt] font-bold;
}
.cell {
  @apply border border-(--r-line) px-1.5 py-1;
}

@media print {
  @page {
    size: A4;
    margin: 14mm 18mm;
  }
  .report {
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }
}
</style>
