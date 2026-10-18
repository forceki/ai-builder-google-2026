<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import EvidenceSnap from '../components/assessment/EvidenceSnap.vue'

// A printable A4 document: always black on white, whatever the app theme. Short by design: the conclusion, the
// nonconformances in Pareto order and the sign-off; evidence, documents and check details are appendices.
const TONE = { ink: 'text-[#111111]', pass: 'text-[#1F6B3A]', warn: 'text-[#B34700]', reject: 'text-[#C4271B]', muted: 'text-[#6E6E6E]' }
const BORDER = { pass: 'border-[#1F6B3A]', warn: 'border-[#B34700]', reject: 'border-[#C4271B]', muted: 'border-[#6E6E6E]' }
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
  <div class="report min-h-screen bg-white font-sans text-[#111111]">
    <div class="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 border-b border-[#111111] bg-white px-6 py-2.5 print:hidden">
      <RouterLink :to="`/projects/${projectNo}/review`" class="text-xs font-bold tracking-[0.06em] text-[#111111]">← BACK TO REVIEW</RouterLink>
      <div v-if="rep" class="flex flex-wrap items-center gap-4">
        <label class="flex cursor-pointer items-center gap-2 text-xs">
          <input v-model="details" type="checkbox" class="size-3.5 accent-[#111111]" /> Include check details (appendix C)
        </label>
        <button type="button" class="btn-hard bg-[#FF4F00] px-4 py-2 text-xs tracking-[0.06em] text-[#111111] uppercase" @click="printReport">
          Print / save PDF
        </button>
      </div>
    </div>

    <p v-if="error" class="mx-auto my-16 max-w-[560px] px-6 text-center text-sm text-[#C4271B]">{{ error }}</p>
    <p v-else-if="!rep" class="my-16 text-center text-xs text-[#6E6E6E]">Building report…</p>

    <!-- The table's head and foot repeat on every printed page. -->
    <article
      v-else
      class="mx-auto my-8 box-border w-[210mm] max-w-[calc(100%-32px)] border border-[#DDDDDD] bg-white px-[18mm] py-[14mm] text-[9.5pt] leading-[1.45] max-sm:px-5 print:m-0 print:w-auto print:max-w-none print:border-0 print:p-0"
    >
      <table class="w-full border-collapse">
        <thead>
          <tr>
            <td class="p-0">
              <div class="flex items-end justify-between gap-3 border-b-2 border-[#111111] pb-2 whitespace-nowrap">
                <span class="flex items-center gap-2 text-[11pt] font-bold">
                  <span class="size-[9px] border border-[#111111] bg-[#FF4F00]"></span>HIBANAKO
                </span>
                <span class="text-[8pt]">{{ rep.report_no }} · Rev. A · {{ rep.mode === 'PLAN' ? 'Plan review' : 'As-built' }}</span>
              </div>
            </td>
          </tr>
        </thead>
        <tfoot>
          <tr>
            <td class="p-0 pt-5">
              <div class="border-t border-[#111111] pt-1.5 text-[7.5pt] text-[#555555]">{{ rep.footer }}</div>
            </td>
          </tr>
        </tfoot>
        <tbody>
          <tr>
            <td class="p-0">
              <h1 class="m-0 pt-5 text-[18pt] leading-tight font-bold">{{ rep.title }}</h1>
              <p class="mt-1 mb-3.5 text-[10pt] text-[#333333]">{{ rep.subtitle }}</p>

              <p v-if="rep.stale" class="m-0 mb-2.5 border-l-4 border-[#B34700] bg-[#FFF4EC] px-2.5 py-1.5 font-bold text-[#B34700]">
                {{ rep.stale_reasons.join(', ') }} after this run. Re-run before issuing.
              </p>
              <p v-if="rep.sample_data" class="m-0 mb-2.5 border-l-4 border-[#BBBBBB] px-2.5 py-1.5 text-[#555555]">
                Sample data, not an issued assessment.
              </p>

              <table class="mb-4 w-full border-collapse">
                <tbody>
                  <tr v-for="(row, i) in rep.header" :key="row.label" :class="i % 2 ? '' : 'bg-[#F7F7F7]'">
                    <th scope="row" class="w-[22%] border-y border-[#DDDDDD] px-2 py-1 text-left font-semibold">{{ row.label }}</th>
                    <td class="border-y border-[#DDDDDD] px-2 py-1">{{ row.value }}</td>
                  </tr>
                </tbody>
              </table>

              <div class="mb-1 flex break-inside-avoid items-stretch border-2" :class="BORDER[rep.verdict_tone]">
                <div class="flex w-[34%] flex-none items-center px-3 py-2.5 text-[12pt] font-bold" :class="TONE[rep.verdict_tone]">
                  {{ rep.verdict }}
                </div>
                <div class="flex flex-col justify-center gap-0.5 border-l border-[#DDDDDD] px-3 py-2">
                  <span class="font-semibold">{{ rep.conclusion }}</span>
                  <span class="text-[8.5pt] text-[#555555]">
                    {{ rep.counts.nc }} nonconformance(s) · {{ rep.counts.obs }} observation(s) · {{ rep.counts.waived }} waived
                  </span>
                </div>
              </div>

              <h2 class="h-band">1 · Nonconformances</h2>
              <p v-if="!rep.issues.length" class="m-0 text-[#555555]">None.</p>
              <table v-else class="w-full border-collapse text-[8.5pt]">
                <thead>
                  <tr class="bg-[#F2F2F2] text-left">
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
                      <div class="text-[7.5pt] text-[#6E6E6E]">{{ i.area }} · {{ i.rule_id }}</div>
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
                      <td class="cell align-top">{{ i.waiver?.reason }} <span class="text-[#6E6E6E]">({{ i.waiver?.by }})</span></td>
                    </tr>
                  </tbody>
                </table>
              </template>

              <h2 class="h-band">3 · Results by check area</h2>
              <table v-if="rep.areas.length" class="w-full border-collapse text-[8.5pt]">
                <thead>
                  <tr class="bg-[#F2F2F2] text-left">
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
                      <span class="block h-2 bg-[#C4271B]" :style="{ width: `${(a.nc / maxNc) * 100}%` }"></span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-if="rep.clean_checks.length" class="mt-1.5 mb-0 text-[8.5pt] text-[#555555]">
                No issues: {{ rep.clean_checks.join('; ') }}.
              </p>

              <div class="break-inside-avoid">
                <h2 class="h-band">Approval</h2>
                <table class="w-full border-collapse">
                  <thead>
                    <tr class="bg-[#F2F2F2] text-left">
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
                <p class="mt-1.5 mb-0 text-[8pt] text-[#555555]">Codes: {{ rep.references.join(', ') }}.</p>
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
                      <th scope="row" class="cell w-[24%] bg-[#F7F7F7] text-left font-semibold">{{ d.slot }}</th>
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
                      <tr class="bg-[#F2F2F2] text-left">
                        <th v-for="h in sec.headers" :key="h" scope="col" class="cell font-bold">{{ h }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, k) in sec.rows" :key="k" class="break-inside-avoid">
                        <td v-for="(cl, j) in row" :key="j" class="cell align-top" :class="[TONE[cl.tone], cl.bold ? 'font-bold' : '']">{{ cl.v }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <p v-else class="m-0 text-[8pt] text-[#555555]">Not assessed: {{ sec.missing }}</p>
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

/* Formal document: one plain office typeface throughout, including the app's mono and display text. */
.report,
.report :deep(*) {
  font-family: Arial, Helvetica, 'Liberation Sans', sans-serif !important;
  font-stretch: normal !important;
}
.h-band {
  @apply mt-4 mb-1.5 border-b border-[#111111] pb-1 text-[10.5pt] font-bold;
}
.cell {
  @apply border border-[#CCCCCC] px-1.5 py-1;
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
