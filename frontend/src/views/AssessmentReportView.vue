<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'

// A printable A4 document: always black on white, whatever the app theme.
const TONE = { ink: 'text-[#111111]', pass: 'text-[#1F6B3A]', warn: 'text-[#B34700]', reject: 'text-[#C4271B]', muted: 'text-[#6E6E6E]' }
const BORDER = { pass: 'border-[#1F6B3A]', warn: 'border-[#B34700]', reject: 'border-[#C4271B]', muted: 'border-[#6E6E6E]' }

const route = useRoute()
const projectNo = computed(() => route.params.no)
const rep = ref(null)
const error = ref('')

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
const printReport = () => window.print()
</script>

<template>
  <div class="report min-h-screen bg-[#E6E6E6] font-sans text-[#111111] print:bg-white">
    <div class="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 border-b border-[#111111] bg-[#F2F2F2] px-6 py-2.5 print:hidden">
      <RouterLink :to="`/projects/${projectNo}`" class="font-mono text-xs font-bold tracking-[0.06em] text-[#111111]">← BACK TO ASSESSMENT</RouterLink>
      <button v-if="rep" type="button" class="btn-hard bg-[#FF4F00] px-4 py-2 text-xs tracking-[0.06em] text-[#111111] uppercase" @click="printReport">
        Print / save PDF
      </button>
    </div>

    <p v-if="error" class="mx-auto my-16 max-w-[560px] px-6 text-center font-mono text-sm text-[#C4271B]">{{ error }}</p>
    <p v-else-if="!rep" class="my-16 text-center font-mono text-xs text-[#6E6E6E]">BUILDING REPORT…</p>

    <!-- The table's head and foot repeat on every printed page. -->
    <article
      v-else
      class="mx-auto my-8 box-border w-[210mm] max-w-[calc(100%-32px)] bg-white px-[18mm] py-[14mm] shadow-[0_2px_12px_rgba(0,0,0,0.12)] max-sm:px-5 print:m-0 print:w-auto print:max-w-none print:p-0 print:shadow-none"
    >
      <table class="w-full border-collapse">
        <thead>
          <tr>
            <td class="p-0">
              <div class="flex items-end justify-between gap-3 border-b-2 border-[#111111] pb-2 whitespace-nowrap">
                <span class="flex items-center gap-2 text-[12pt] font-black tracking-[-0.01em] [font-stretch:115%]">
                  <span class="size-[9px] border border-[#111111] bg-[#FF4F00]"></span>HIBANAKO
                </span>
                <span class="font-mono text-[8pt] tracking-[0.04em]">{{ rep.report_no }} · REV. A · {{ rep.mode }}</span>
              </div>
            </td>
          </tr>
        </thead>
        <tfoot>
          <tr>
            <td class="p-0 pt-6">
              <div class="flex justify-between gap-3 border-t border-[#111111] pt-1.5 font-mono text-[7.5pt] tracking-[0.03em] whitespace-nowrap text-[#555555] max-sm:flex-col">
                <span>{{ rep.rule_set }}</span><span>©2026 Shoyupuro · Hibanako</span>
              </div>
            </td>
          </tr>
        </tfoot>
        <tbody>
          <tr>
            <td class="p-0">
              <h1 class="m-0 pt-[22px] text-[24pt] leading-[1.05] font-extrabold tracking-[-0.025em]">{{ rep.title }}</h1>
              <p class="mt-1.5 mb-1 text-[11.5pt]">{{ rep.subtitle }}</p>
              <p class="m-0 mb-[18px] font-mono text-[9pt] font-bold tracking-[0.06em]">{{ rep.mode_line }}</p>
              <p v-if="rep.stale" class="m-0 mb-2 border-2 border-[#B34700] px-2 py-1.5 text-[9pt] font-bold text-[#B34700]">
                {{ rep.stale_reasons.join(' · ') }} after this run. Re-run the assessment before issuing this report.
              </p>
              <p v-if="rep.sample_data" class="m-0 mb-2 border border-dashed border-[#BBBBBB] px-2 py-1.5 font-mono text-[8pt] text-[#555555]">
                SAMPLE DATA · Results come from the sample dossier until document extraction feeds the assessment.
              </p>

              <div v-for="k in rep.info" :key="k.title" class="break-inside-avoid">
                <h2 class="h-band">{{ k.title }}</h2>
                <table class="w-full border-collapse text-[9.5pt]">
                  <tbody>
                    <tr v-for="row in k.rows" :key="row.label">
                      <th scope="row" class="cell w-[42%] bg-[#F2F2F2] text-left font-semibold">{{ row.label }}</th>
                      <td class="cell">{{ row.value }}</td>
                      <td class="cell w-[12%] font-mono text-[8.5pt] text-[#555555]">{{ row.unit }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-for="sec in r.sections" :key="sec.id">
                <h2 class="h-band mb-1">{{ sec.title }}</h2>
                <p class="m-0 mb-1.5 text-[8.5pt] leading-[1.45] text-[#555555]">{{ sec.note }}</p>
                <div v-if="sec.rows" class="overflow-x-auto print:overflow-visible">
                  <table class="w-full border-collapse text-[8.5pt]">
                    <thead>
                      <tr class="bg-[#F2F2F2] text-left">
                        <th v-for="h in sec.headers" :key="h" scope="col" class="cell-sm font-bold">{{ h }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, i) in sec.rows" :key="i" class="break-inside-avoid">
                        <td v-for="(cl, j) in row" :key="j" class="cell-sm align-top" :class="[TONE[cl.tone], cl.bold ? 'font-bold' : '']">{{ cl.v }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p v-else class="m-0 border border-dashed border-[#BBBBBB] px-2 py-1.5 font-mono text-[8.5pt] text-[#555555]">
                  NOT ASSESSED · {{ sec.missing }}
                </p>
              </div>

              <h2 class="h-band">Assessment Results</h2>
              <h3 class="mt-2 mb-1.5 text-[10.5pt] font-bold">Assessment Criteria</h3>
              <table class="w-full border-collapse text-[9.5pt]">
                <tbody>
                  <tr v-for="c in r.criteria" :key="c.label">
                    <th scope="row" class="cell w-[76%] bg-[#F2F2F2] text-left font-semibold">{{ c.label }}</th>
                    <td class="cell font-mono font-bold" :class="TONE[c.tone]">{{ c.status }}</td>
                  </tr>
                </tbody>
              </table>
              <template v-if="r.findings.length">
                <h3 class="mt-3.5 mb-1.5 text-[10.5pt] font-bold">
                  Findings · {{ r.counts.fail }} FAIL · {{ r.counts.warn }} WARN · {{ r.counts.waived }} waived
                </h3>
                <table class="w-full border-collapse text-[8.5pt]">
                  <thead>
                    <tr class="bg-[#F2F2F2] text-left">
                      <th scope="col" class="cell-sm">ID</th><th scope="col" class="cell-sm">Rule</th>
                      <th scope="col" class="cell-sm">Severity</th><th scope="col" class="cell-sm">Item</th>
                      <th scope="col" class="cell-sm w-[46%]">Finding</th><th scope="col" class="cell-sm">Clause</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="f in r.findings" :key="f.key" class="break-inside-avoid">
                      <td class="cell-sm align-top whitespace-nowrap">{{ f.id }}</td>
                      <td class="cell-sm align-top font-bold whitespace-nowrap">{{ f.rule_id }}</td>
                      <td class="cell-sm align-top font-bold" :class="f.status === 'waived' ? 'text-[#6E6E6E]' : f.severity === 'FAIL' ? TONE.reject : TONE.warn">
                        {{ f.status === 'waived' ? `${f.severity} · WAIVED` : f.severity }}
                      </td>
                      <td class="cell-sm align-top">{{ f.item }}</td>
                      <td class="cell-sm align-top">
                        {{ f.statement }}
                        <div class="mt-1 text-[#555555]">Documents: {{ f.documents.join(', ') || '—' }}</div>
                        <div class="text-[#555555]">Fix: {{ f.fix }}</div>
                        <div v-if="f.waiver" class="text-[#555555]">Waived by {{ f.waiver.by }}: {{ f.waiver.reason }}</div>
                      </td>
                      <td class="cell-sm align-top">{{ f.clause }}</td>
                    </tr>
                  </tbody>
                </table>
              </template>
              <div class="mt-4 flex break-inside-avoid items-center justify-between gap-3.5 border-2 px-3.5 py-3" :class="BORDER[r.verdict_tone]">
                <span class="text-[10pt] font-semibold">{{ rep.conclusion_label }}</span>
                <span class="font-mono text-[12pt] font-bold tracking-[0.08em]" :class="TONE[r.verdict_tone]">{{ r.verdict }}</span>
              </div>
              <p class="mt-2 mb-0 text-[10pt] leading-[1.55]">{{ rep.conclusion }}</p>

              <h2 class="h-band mt-[22px]">Comments and Assumptions</h2>
              <p class="m-0 text-[9.5pt] leading-[1.55]">{{ rep.comments }}</p>

              <h2 class="h-band mt-[22px]">Warnings</h2>
              <p class="m-0 text-[9.5pt] leading-[1.55]">{{ rep.warnings }}</p>

              <h2 class="h-band mt-[22px]">Traceability</h2>
              <table class="w-full border-collapse text-[9pt]">
                <tbody>
                  <tr v-for="row in rep.traceability" :key="row.label">
                    <th scope="row" class="cell w-[30%] bg-[#F2F2F2] text-left font-semibold">{{ row.label }}</th>
                    <td class="cell">{{ row.value }}</td>
                  </tr>
                </tbody>
              </table>

              <h2 class="h-band mt-[22px]">References</h2>
              <ol class="m-0 pl-[18px] text-[9.5pt] leading-[1.55]">
                <li v-for="ref in rep.references" :key="ref">{{ ref }}</li>
              </ol>

              <div class="break-inside-avoid">
                <h2 class="h-band mt-[22px]">Approval</h2>
                <table class="w-full border-collapse text-[9.5pt]">
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
                      <td class="cell py-1.5">{{ a.role }}</td>
                      <td class="cell py-1.5">{{ a.name }}</td>
                      <td class="cell h-10"></td>
                      <td class="cell py-1.5">{{ a.date }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
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
  @apply mt-[18px] mb-1.5 bg-[#111111] px-2 py-[5px] text-[10.5pt] font-bold tracking-[0.02em] text-white;
}
.cell {
  @apply border border-[#BBBBBB] px-2 py-[5px];
}
.cell-sm {
  @apply border border-[#BBBBBB] px-1.5 py-[5px];
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
