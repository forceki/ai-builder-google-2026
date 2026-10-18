<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import AppBar from '../components/app/AppBar.vue'
import Breadcrumb from '../components/app/Breadcrumb.vue'
import EvidenceSnap from '../components/assessment/EvidenceSnap.vue'

// Conditions, sorted files and the review all live on the backend (/api/projects/:no/assessment).
const SAMPLE_BATCH = [
  'MTC_4A7721.pdf', 'MTC_5B2210.pdf', 'MTC_3C0954.pdf', 'WPS-07_PQR-07.pdf', 'WPS-09_PQR-09.pdf', 'WPQ-118.pdf', 'WPQ-204.pdf',
  'HBK-PV-110_RevB_WeldMap.pdf', 'MTC_9Z0001_EN10204-2.1.pdf', 'WPS-11_draft.docx', 'IMG_4471.jpg', 'Invoice_PO-2231.pdf',
]
const TYPE_TITLE = { plant: 'B · WHAT PLANT?', ship: 'B · WHAT KIND OF SHIP WORK?', mfg: 'B · WHAT PRODUCT?' }
const TONE = { ink: 'text-ink', pass: 'text-pass', warn: 'text-signal', reject: 'text-reject', muted: 'text-faint' }
const BORDER = { pass: 'border-pass', warn: 'border-signal', reject: 'border-reject', muted: 'border-faint' }
const SEVERITY = { FAIL: 'bg-reject text-white', WARN: 'bg-signal text-ink', INFO: 'bg-panel text-ink' }
const STEPS = ['1 · CONDITIONS', '2 · DOCUMENTS', '3 · REVIEW']
const uploadModes = [
  { id: 'single', label: 'Single document', desc: 'Upload each document into its own slot: mill certificate, WPS, WPQ, welding drawing, as-built.' },
  { id: 'batch', label: 'Batch upload', desc: 'Drop all documents at once. Each file is identified and sorted; non-standard documents are flagged.' },
]

const route = useRoute()
const projectNo = computed(() => route.params.no)
const crumbs = computed(() => [{ label: 'PROJECTS', to: '/projects' }, { label: projectNo.value }, { label: 'ASSESSMENT' }])

const cat = ref(null)
const st = ref(null)
const error = ref('')
const STEP_PATHS = ['conditions', 'documents', 'review']
const router = useRouter()
const step = computed({
  get: () => Math.max(0, STEP_PATHS.indexOf(route.params.step)),
  set: (i) => router.push({ name: 'assessment', params: { no: projectNo.value, step: STEP_PATHS[i] } }),
})

// Calls run one after another so a fast click can't overwrite a newer state with an older reply. Each call is bound
// to the project it was made for; a reply that arrives after switching projects is dropped, never shown.
let chain = Promise.resolve()
let poll = null
function call(fn) {
  const forProject = projectNo.value
  chain = chain
    .then(() => (forProject === projectNo.value ? fn(forProject) : null))
    .then((out) => {
      if (!out || forProject !== projectNo.value || out.project_no !== forProject) return
      st.value = out
      error.value = ''
    })
    .catch((e) => {
      if (forProject === projectNo.value) error.value = e.message || 'Request failed'
    })
  return chain
}

watch(
  projectNo,
  () => {
    clearTimeout(poll)
    st.value = null
    error.value = ''
    call((no) => api.assessment.get(no))
  },
  { immediate: true },
)
api.assessment.catalog().then((c) => (cat.value = c), (e) => (error.value = e.message))

const ready = computed(() => !!(cat.value && st.value))
const c = computed(() => st.value.conditions)
const profile = computed(() => cat.value.profiles.find((p) => p.id === c.value.profile))
const sectorId = computed(() => profile.value?.sector ?? 'plant')
const types = computed(() => cat.value.profiles.filter((p) => p.sector === sectorId.value))
const govs = computed(() => cat.value.governing.filter((g) => g.sector === sectorId.value))
const g = computed(() => cat.value.governing.find((x) => x.id === c.value.governing))
const supps = computed(() => cat.value.supplementary.filter((s) => s.sectors.includes(sectorId.value)))
const uploadMode = computed(() => c.value.upload_mode || 'batch')
const purpose = computed(() => c.value.purpose || 'production')
const run = computed(() => st.value.run)
const r = computed(() => run.value?.result)
// An investigation separates candidate causes (breaches found in the records) from evidence gaps (records missing).
const findingGroups = computed(() => {
  const all = r.value?.findings ?? []
  const n = (k, one, many) => `${k} ${k === 1 ? one : many}`
  if (r.value?.purpose !== 'investigation') {
    return all.length ? [{ title: `${n(all.length, 'FINDING', 'FINDINGS')} · FAIL FIRST, THEN WARN`, note: '', items: all }] : []
  }
  const causes = all.filter((f) => f.kind !== 'gap')
  const gaps = all.filter((f) => f.kind === 'gap')
  return [
    { title: `${n(causes.length, 'CANDIDATE CAUSE', 'CANDIDATE CAUSES')}`, note: 'Breaches of the governing standard found in the records', items: causes },
    { title: `${n(gaps.length, 'EVIDENCE GAP', 'EVIDENCE GAPS')}`, note: 'Records not submitted; their checks could not be made', items: gaps },
  ].filter((g) => g.items.length)
})
const mode = computed(() => st.value.mode)
const reviewMode = computed(() => run.value?.mode ?? mode.value)
// Step 2 opens only after step 1 is confirmed with "Next: documents"; older assessments with files or a run count as confirmed.
const confirmed = computed(() => !!(st.value?.conditions.confirmed || st.value?.files.length || st.value?.run))
const canReview = computed(() => confirmed.value && !!(st.value?.run || st.value?.ready))
const stepLocked = (i) => (i === 1 && !confirmed.value) || (i === 2 && !canReview.value)
// A locked step opened by URL (bookmark, refresh, typed link) moves to the furthest step that is open.
watch([st, step], () => {
  if (!st.value || !stepLocked(step.value)) return
  const open = canReview.value ? 2 : confirmed.value ? 1 : 0
  router.replace({ name: 'assessment', params: { no: projectNo.value, step: STEP_PATHS[open] } })
})
async function confirmConditions() {
  if (!c.value.confirmed) await setCond({ confirmed: true })
  if (!error.value) step.value = 1
}

function setCond(patch) {
  const next = { ...c.value, ...patch }
  st.value = { ...st.value, conditions: next } // show the choice right away
  return call((p) => api.assessment.setConditions(p, next))
}
function setProfile(id) {
  const p = cat.value.profiles.find((x) => x.id === id)
  const fits = (sid) => cat.value.supplementary.find((s) => s.id === sid)?.sectors.includes(p.sector)
  setCond({ profile: id, governing: p.governing, supplementary: c.value.supplementary.filter(fits) })
}
const toggleSupp = (id) => {
  const cur = c.value.supplementary
  setCond({ supplementary: cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id] })
}

// Every slot is optional: the assessment runs on what is submitted and leaves the other checks pending.
const docsHint = computed(() => {
  const checked = st.value.slots.filter((s) => s.id !== 'other')
  const empty = checked.filter((s) => !s.files.length).map((s) => s.label)
  if (empty.length === checked.length) return 'Upload any of the documents below. Each is identified and read; the checks run on what you submit.'
  if (!empty.length) return 'Every document type is in. Each one has been identified and matched to the conditions.'
  return c.value.complete_set
    ? `Not submitted: ${empty.join(', ')}. Assessed as missing, ranked by risk.`
    : `Not submitted yet: ${empty.join(', ')}. Checks that need them stay pending.`
})

const head = computed(() => {
  const suppText = c.value.supplementary.length
    ? ` + ${c.value.supplementary.map((id) => cat.value.supplementary.find((s) => s.id === id)?.label).join(', ')}`
    : ''
  return [
    ['STEP 1 OF 3', 'Set the conditions', 'Pick where the equipment will be used and which standards apply. Every document is checked against these.'],
    ['STEP 2 OF 3', 'Submit the documents', docsHint.value],
    [`STEP 3 OF 3 · ${reviewMode.value}`, reviewMode.value === 'PLAN' ? 'Plan review' : 'As-built review', `WPS and WPQ checked against the welding drawing under ${(run.value?.conditions ?? c.value).governing}${suppText}.`],
  ][step.value]
})

// Documents
const addFiles = (names, slot) => names.length && call((p) => api.assessment.addFiles(p, names, slot))
// Real files are uploaded one by one; the backend sorts each by content and reads it in the background.
// `sending` lists files still on their way up; `target` remembers the slot each file was uploaded into, so a file
// shows in its slot card from the moment it is picked (uploading → reading) and stays there if it is rejected.
const sending = ref([])
const target = ref({})
let sendId = 0
const uploadFiles = (list, slot) =>
  Array.from(list || []).forEach((file) => {
    const id = ++sendId
    sending.value = [...sending.value, { id, name: file.name, slot: slot ?? null }]
    if (slot) target.value = { ...target.value, [file.name]: slot }
    call((p) => api.assessment.upload(p, file, slot)).then(() => (sending.value = sending.value.filter((e) => e.id !== id)))
  })
const isSending = (name) => sending.value.some((e) => e.name === name)
// Files on their way into a slot, or rejected from it: [{ name, state: uploading | reading | error, text }]
const slotPending = (id) => [
  ...sending.value.filter((e) => e.slot === id).map((e) => ({ name: e.name, state: 'uploading', text: 'Uploading…' })),
  ...st.value.files
    .filter((f) => !isSending(f.name) && (f.slot ?? target.value[f.name]) === id && (f.status === 'reading' || !f.slot))
    .map((f) => (f.status === 'reading'
      ? { name: f.name, state: 'reading', text: 'Reading…' }
      : { name: f.name, state: 'error', text: f.reason || 'Could not be read.' })),
]
// Single-document mode has no batch list: files whose slot isn't known (e.g. after a reload) are listed above the slots.
const unplaced = computed(() => st.value.files.filter((f) => !f.slot && !target.value[f.name]))
const uploaded = computed(() => !st.value.sample_data)
// Every new state while files are being read schedules the next check (watching the count alone stops polling as
// soon as two replies in a row have the same number of files reading).
watch(st, (s) => {
  clearTimeout(poll)
  if (s?.reading.length) poll = setTimeout(() => call((p) => api.assessment.get(p)), 2500)
})
onBeforeUnmount(() => clearTimeout(poll))
const loadSample = (slot) => call((p) => api.assessment.loadSamples(p, slot))
const removeFiles = (q) => call((p) => api.assessment.removeFiles(p, q))
const onSlotFile = (slot, e) => {
  uploadFiles(e.target.files, slot)
  e.target.value = ''
}
const drag = ref(false)
const onDrop = (e) => {
  drag.value = false
  uploadFiles(e.dataTransfer?.files)
}
const onBatch = (e) => {
  uploadFiles(e.target.files)
  e.target.value = ''
}
const slotLabel = (id) => st.value.slots.find((s) => s.id === id)?.label ?? id
const rejected = computed(() => st.value.files.filter((f) => !f.slot && f.status !== 'reading'))
const clearRejected = () => rejected.value.forEach((f) => removeFiles({ name: f.name }))

// Running stores a new run on the server; the review always shows the latest run.
const running = ref(false)
async function runAssessment() {
  running.value = true
  await call((p) => api.assessment.run(p))
  running.value = false
  if (!error.value) step.value = 2
}
const waiving = ref(null) // finding key whose reason box is open
const waiveReason = ref('')
function openWaive(key) {
  waiving.value = key
  waiveReason.value = ''
}
async function setWaiver(key, status) {
  await call((p) => api.assessment.setWaiver(p, key, status, waiveReason.value))
  if (!error.value) waiving.value = null
}
const fmtTime = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })

// Open an uploaded file in a new tab through a short-lived signed link. The tab opens first, on the click, so the
// browser doesn't block it as a pop-up while the link is fetched.
const docId = (name) => st.value.files.find((f) => f.name === name && f.document_id)?.document_id
async function openDoc(name) {
  const id = docId(name)
  if (!id) return
  const tab = window.open('', '_blank')
  try {
    const { url } = await api.documents.link(projectNo.value, id)
    if (tab) tab.location.href = url
    else window.open(url, '_blank')
  } catch (e) {
    tab?.close()
    error.value = e.message || 'Could not open the document'
  }
}

// Reviewer notes belong to the latest run; the draft follows it when a new run arrives.
const notesDraft = ref('')
const savingNotes = ref(false)
watch(
  () => [st.value?.run?.number, st.value?.run?.notes?.text],
  () => (notesDraft.value = st.value?.run?.notes?.text ?? ''),
  { immediate: true },
)
const notesDirty = computed(() => notesDraft.value.trim() !== (st.value?.run?.notes?.text ?? ''))
async function saveNotes() {
  savingNotes.value = true
  await call((p) => api.assessment.setNotes(p, notesDraft.value))
  savingNotes.value = false
}
// The report prints the saved notes, so save what was typed before going there.
async function openReport() {
  if (notesDirty.value) await saveNotes()
  router.push(`/projects/${projectNo.value}/report`)
}

const optClass = (on) => (on ? 'bg-ink text-paper' : 'bg-white text-ink')
</script>

<template>
  <div class="flex min-h-screen flex-col bg-paper font-sans text-ink">
    <AppBar class="min-h-10 print:hidden">
      <template #title>
        <Breadcrumb :items="crumbs" />
        <ol aria-label="Steps" class="m-0 flex flex-none list-none border border-ink p-0 font-mono text-[11px] font-bold tracking-[0.05em]">
          <li v-for="(label, i) in STEPS" :key="label">
            <button
              type="button"
              :aria-current="i === step ? 'step' : undefined"
              :disabled="stepLocked(i)"
              :title="stepLocked(i) ? (i === 1 ? 'Set the conditions and press Next first' : 'Submit the required documents first') : ''"
              class="cursor-pointer border-0 px-3.5 py-2 whitespace-nowrap disabled:cursor-not-allowed disabled:text-faint"
              :class="[i === step ? 'bg-signal' : 'bg-white', { 'border-l border-ink': i }]"
              @click="step = i"
            >{{ label }}</button>
          </li>
        </ol>
      </template>
    </AppBar>

    <p v-if="error" role="alert" class="m-0 border-b border-reject bg-white px-6 py-2.5 font-mono text-xs text-reject">{{ error }}</p>
    <main v-if="!ready" class="flex flex-1 items-center justify-center font-mono text-xs text-faint">LOADING ASSESSMENT…</main>
    <main v-else class="mx-auto box-border flex w-full max-w-[1180px] flex-1 flex-col gap-6 px-6 pt-9 pb-12 max-sm:px-4">
      <section class="flex flex-wrap items-end justify-between gap-5">
        <div class="flex min-w-0 flex-col gap-2.5">
          <RouterLink to="/projects" class="mb-2 self-start font-mono text-xs font-bold tracking-[0.06em] underline-offset-4 print:hidden">← ALL PROJECTS</RouterLink>
          <span class="font-mono text-[11px] tracking-[0.08em] text-faint">{{ head[0] }}</span>
          <h1 class="m-0 text-[clamp(30px,4vw,44px)] leading-[1.02] font-extrabold tracking-[-0.03em]">{{ head[1] }}</h1>
          <span class="max-w-[64ch] text-[15px] leading-[1.45] text-muted">{{ head[2] }}</span>
        </div>
        <div class="flex flex-none flex-wrap gap-2 whitespace-nowrap print:hidden">
          <button v-if="step > 0" type="button" class="btn-hard bg-white px-4 py-[11px] text-xs tracking-[0.06em] uppercase" @click="step--">
            ← Back
          </button>
          <button
            v-if="step === 0"
            type="button"
            class="btn-hard bg-signal px-4 py-[11px] text-xs tracking-[0.06em] uppercase"
            @click="confirmConditions"
          >Next: documents →</button>
          <button
            v-else-if="step === 1"
            type="button"
            :disabled="!st.ready || running"
            :title="st.ready ? '' : 'Submit at least one document, wait for reading to finish and resolve rejected files first'"
            class="btn-hard bg-signal px-4 py-[11px] text-xs tracking-[0.06em] uppercase"
            @click="st.state === 'complete' ? (step = 2) : runAssessment()"
          >{{ running ? 'Running…' : st.state === 'complete' ? 'View review →' : st.run ? 'Re-run assessment →' : 'Run assessment →' }}</button>
          <RouterLink
            v-else-if="run"
            :to="`/projects/${projectNo}/report`"
            class="btn-hard bg-signal px-4 py-[11px] text-xs tracking-[0.06em] text-ink uppercase no-underline"
            @click.prevent="openReport"
          >Generate report →</RouterLink>
        </div>
      </section>

      <!-- 1 · CONDITIONS -->
      <div v-if="step === 0" class="flex flex-col gap-4">
        <section class="flex flex-wrap gap-x-9 gap-y-[18px] border border-ink bg-white p-5">
          <div class="flex flex-col gap-2">
            <span class="font-mono text-[11px] font-bold tracking-[0.08em]">A · WHERE WILL IT BE USED?</span>
            <div role="radiogroup" aria-label="Sector" class="flex flex-wrap border border-ink">
              <button
                v-for="s in cat.sectors"
                :key="s.id"
                type="button"
                role="radio"
                :aria-checked="s.id === sectorId"
                class="cursor-pointer border-0 border-r border-ink px-[18px] py-2.5 text-[15px] font-bold last:border-r-0"
                :class="optClass(s.id === sectorId)"
                @click="s.id !== sectorId && setProfile(s.default_profile)"
              >{{ s.label }}</button>
            </div>
          </div>
          <div class="flex flex-[1_1_320px] flex-col gap-2">
            <span class="font-mono text-[11px] font-bold tracking-[0.08em]">{{ TYPE_TITLE[sectorId] }}</span>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="p in types"
                :key="p.id"
                type="button"
                role="radio"
                :aria-checked="p.id === c.profile"
                class="cursor-pointer border border-ink px-3 py-2 text-sm font-semibold"
                :class="optClass(p.id === c.profile)"
                @click="setProfile(p.id)"
              >{{ p.label }}</button>
            </div>
          </div>
        </section>

        <section class="flex flex-col gap-2.5 border border-ink bg-white p-5">
          <span class="font-mono text-[11px] font-bold tracking-[0.08em]">C · GOVERNING STANDARD</span>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="gv in govs"
              :key="gv.id"
              type="button"
              role="radio"
              :aria-checked="gv.id === c.governing"
              class="cursor-pointer border border-ink px-3 py-2 font-mono text-[12.5px] font-bold whitespace-nowrap"
              :class="optClass(gv.id === c.governing)"
              @click="setCond({ governing: gv.id })"
            >{{ gv.id }}</button>
          </div>
          <span v-if="g" class="text-sm leading-[1.45] text-muted">
            Welding qualification: {{ g.qual }} · NDE: {{ g.nde }} · PWHT rule: {{ g.rule }}
          </span>
          <div class="flex flex-wrap items-center gap-2.5 pt-1">
            <span class="font-mono text-[11px] font-bold tracking-[0.08em]">C-1 · CODE EDITION</span>
            <div role="radiogroup" aria-label="Code edition" class="flex border border-ink">
              <button
                v-for="ed in cat.editions"
                :key="ed"
                type="button"
                role="radio"
                :aria-checked="ed === c.edition"
                class="cursor-pointer border-0 border-r border-ink px-3 py-1.5 font-mono text-xs font-bold last:border-r-0"
                :class="optClass(ed === c.edition)"
                @click="setCond({ edition: ed })"
              >{{ ed }}</button>
            </div>
            <span class="text-[13px] text-muted">Clause numbers in findings cite this edition.</span>
          </div>
        </section>

        <section class="flex flex-col gap-2.5 border border-ink bg-white p-5">
          <span class="font-mono text-[11px] font-bold tracking-[0.08em]">
            D · SUPPLEMENTARY REQUIREMENTS <span class="font-normal text-faint">· OPTIONAL, PICK ANY</span>
          </span>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="s in supps"
              :key="s.id"
              type="button"
              role="checkbox"
              :aria-checked="c.supplementary.includes(s.id)"
              class="flex cursor-pointer items-start gap-2.5 border border-ink px-3 py-2.5 text-left"
              :class="optClass(c.supplementary.includes(s.id))"
              @click="toggleSupp(s.id)"
            >
              <span
                aria-hidden="true"
                class="mt-[3px] size-3 flex-none border"
                :class="c.supplementary.includes(s.id) ? 'border-signal bg-signal' : 'border-ink'"
              ></span>
              <span class="flex flex-col gap-0.5">
                <span class="text-sm font-bold whitespace-nowrap">{{ s.label }}</span>
                <span class="text-[12.5px] opacity-80">{{ s.desc }}</span>
              </span>
            </button>
          </div>
        </section>

        <section class="flex flex-col gap-3 border border-ink bg-white p-5">
          <span class="font-mono text-[11px] font-bold tracking-[0.08em]">E · WHAT IS THIS ASSESSMENT FOR?</span>
          <div role="radiogroup" aria-label="Purpose" class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,260px),1fr))] gap-2.5">
            <button
              v-for="m in cat.purposes"
              :key="m.id"
              type="button"
              role="radio"
              :aria-checked="m.id === purpose"
              class="flex cursor-pointer items-start gap-3 border border-ink px-4 py-3.5 text-left"
              :class="optClass(m.id === purpose)"
              @click="setCond({ purpose: m.id })"
            >
              <span
                aria-hidden="true"
                class="mt-[3px] size-3.5 flex-none rounded-full border"
                :class="m.id === purpose ? 'border-signal bg-signal' : 'border-ink'"
              ></span>
              <span class="flex flex-col gap-1">
                <span class="text-base font-extrabold">{{ m.label }}</span>
                <span class="text-[13px] leading-[1.4] opacity-85">{{ m.desc }}</span>
              </span>
            </button>
          </div>
        </section>

        <section class="flex flex-col gap-3 border border-ink bg-white p-5">
          <span class="font-mono text-[11px] font-bold tracking-[0.08em]">F · HOW WILL YOU SUBMIT THE DOCUMENTS?</span>
          <div role="radiogroup" aria-label="Upload mode" class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,260px),1fr))] gap-2.5">
            <button
              v-for="m in uploadModes"
              :key="m.id"
              type="button"
              role="radio"
              :aria-checked="m.id === uploadMode"
              class="flex cursor-pointer items-start gap-3 border border-ink px-4 py-3.5 text-left"
              :class="optClass(m.id === uploadMode)"
              @click="setCond({ upload_mode: m.id })"
            >
              <span
                aria-hidden="true"
                class="mt-[3px] size-3.5 flex-none rounded-full border"
                :class="m.id === uploadMode ? 'border-signal bg-signal' : 'border-ink'"
              ></span>
              <span class="flex flex-col gap-1">
                <span class="text-base font-extrabold">{{ m.label }}</span>
                <span class="text-[13px] leading-[1.4] opacity-85">{{ m.desc }}</span>
              </span>
            </button>
          </div>
        </section>
      </div>

      <!-- 2 · DOCUMENTS -->
      <div v-else-if="step === 1" class="flex flex-col gap-4">
        <div class="flex flex-wrap items-center justify-between gap-3 border border-ink px-[18px] py-3.5" :class="mode === 'PLAN' ? 'bg-white' : 'bg-panel'">
          <span class="flex items-center gap-3">
            <span class="border-2 border-ink px-[9px] py-[3px] font-mono text-xs font-bold tracking-[0.1em]">{{ mode }}</span>
            <span class="text-[14.5px]">
              {{ c.complete_set
                ? 'Final record. The report checks the finished work, and anything missing is assessed as missing.'
                : mode === 'PLAN'
                  ? 'No as-built document yet. The report will be a plan review, before fabrication.'
                  : 'As-built document added. The report will verify the finished work against the plan.' }}
            </span>
          </span>
          <button v-if="!uploaded" type="button" class="btn-hard bg-white px-3 py-2 text-[11.5px] whitespace-nowrap" @click="loadSample()">Load all samples</button>
        </div>
        <label
          class="flex cursor-pointer items-start gap-3 border bg-white px-[18px] py-3.5"
          :class="c.complete_set ? 'border-2 border-ink' : 'border-ink/40'"
        >
          <input
            type="checkbox"
            class="mt-0.5 size-[18px] flex-none cursor-pointer accent-[var(--color-ink)]"
            :checked="!!c.complete_set"
            @change="setCond({ complete_set: $event.target.checked })"
          />
          <span class="flex flex-col gap-1">
            <span class="text-[15px] font-bold">This is all the documents I have</span>
            <span class="text-[13px] leading-[1.45] text-muted">
              Assess the documents as the final record before release. Evidence the governing standard requires but
              that isn't here fails, for example a PWHT record when PWHT is required. A missing document is a finding
              ranked by its risk: a missing mill certificate is a note, a missing WPS fails. Leave it unticked to keep
              checks pending while documents are still coming.
            </span>
          </span>
        </label>
        <p v-if="st.unresolved.length" role="status" class="m-0 border border-reject bg-white px-[18px] py-3 text-[14px] text-reject">
          {{ st.unresolved.length }} rejected {{ st.unresolved.length > 1 ? 'files need' : 'file needs' }} a decision before the
          assessment can run: assign {{ st.unresolved.length > 1 ? 'each' : 'it' }} to a slot or remove it.
        </p>

        <section v-if="uploadMode === 'batch'" aria-label="Batch upload" class="flex flex-col border border-ink bg-white">
          <label
            class="relative flex cursor-pointer flex-wrap items-center gap-x-5 gap-y-3.5 border-b border-ink px-5 py-[22px] hover:bg-panel"
            :class="drag ? 'bg-panel' : 'bg-white'"
            @dragover.prevent="drag = true"
            @dragleave="drag = false"
            @drop.prevent="onDrop"
          >
            <span aria-hidden="true" class="flex size-11 flex-none items-center justify-center border border-ink bg-signal font-mono text-[22px]">+</span>
            <span class="flex flex-[1_1_300px] flex-col gap-1">
              <span class="text-[19px] font-extrabold tracking-[-0.01em]">Batch upload: drop all documents at once</span>
              <span class="text-[13.5px] leading-[1.4] text-muted">
                Each file is identified and sent to the right slot below. Files that aren't a standard document are flagged with the reason.
              </span>
            </span>
            <span class="font-mono text-[10.5px] tracking-[0.05em] text-faint">PDF · JPG · PNG · XLSX</span>
            <input type="file" multiple class="absolute size-px opacity-0" @change="onBatch" />
          </label>
          <template v-if="st.files.length">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-ink/15 px-4 py-2.5 font-mono text-[11px] font-bold tracking-[0.05em]">
              <span>{{ st.reading.length ? `READING ${st.reading.length} OF ${st.files.length}…` : `${st.files.length - rejected.length} OF ${st.files.length} IDENTIFIED` }}</span>
              <span class="flex gap-3.5">
                <span v-if="rejected.length" class="text-reject">{{ rejected.length }} {{ rejected.length > 1 ? 'ERRORS' : 'ERROR' }}</span>
                <button
                  v-if="rejected.length"
                  type="button"
                  class="cursor-pointer border-0 bg-transparent p-0 text-muted underline"
                  @click="clearRejected"
                >CLEAR ERRORS</button>
              </span>
            </div>
            <ul class="m-0 max-h-[340px] list-none overflow-auto p-0">
              <li
                v-for="(b, i) in st.files"
                :key="`${b.name}:${b.slot}`"
                class="animate-row-in flex flex-wrap items-center gap-x-3.5 gap-y-2 border-b border-ink/15 px-4 py-2.5"
                :class="b.status === 'reading' ? 'bg-white' : !b.slot ? 'row-err shadow-[inset_3px_0_0_var(--color-reject)]' : b.needs_confirm ? 'bg-white shadow-[inset_3px_0_0_var(--color-signal)]' : 'bg-white'"
                :style="{ animationDelay: `${Math.min(i, 12) * 40}ms` }"
              >
                <span
                  aria-hidden="true"
                  class="size-[9px] flex-none border border-ink"
                  :class="b.status === 'reading' ? 'animate-pulse bg-pending' : !b.slot ? 'bg-reject' : b.needs_confirm ? 'bg-signal' : 'bg-pass'"
                ></span>
                <span class="flex min-w-0 flex-[1_1_200px] flex-col gap-[3px]">
                  <span class="truncate font-mono text-[12.5px]">{{ b.name }}</span>
                  <span class="text-[12.5px] leading-[1.35]" :class="b.slot || b.status === 'reading' ? 'text-muted' : 'text-reject'">
                    {{ b.reason }}<template v-if="b.confidence != null && b.status !== 'reading' && !b.manual"> · {{ Math.round(b.confidence * 100) }}% sure</template>
                  </span>
                </span>
                <button
                  v-if="b.needs_confirm"
                  type="button"
                  class="btn-hard flex-none bg-white px-2.5 py-1 text-[11px] uppercase"
                  @click="addFiles([b.name], b.slot)"
                >Confirm</button>
                <select
                  v-if="(!b.slot || b.needs_confirm) && b.status !== 'reading'"
                  :aria-label="`Assign ${b.name} to a slot`"
                  value=""
                  class="flex-none cursor-pointer rounded-none border border-ink bg-white px-2 py-1.5 text-[13px]"
                  @change="$event.target.value && addFiles([b.name], $event.target.value)"
                >
                  <option value="">{{ b.slot ? 'Change slot…' : 'Assign manually…' }}</option>
                  <option v-for="s in st.slots" :key="s.id" :value="s.id">{{ s.label }}</option>
                </select>
                <span
                  class="flex-none font-mono text-[10.5px] font-bold tracking-[0.06em]"
                  :class="b.status === 'reading' ? 'text-faint' : !b.slot ? 'text-reject' : b.needs_confirm ? 'text-signal' : 'text-pass'"
                >{{ b.status === 'reading' ? 'READING' : b.slot ? `→ ${slotLabel(b.slot).toUpperCase()}` : 'ERROR' }}</span>
                <button
                  v-if="b.document_id"
                  type="button"
                  :aria-label="`Open ${b.name}`"
                  title="Open document"
                  class="size-[26px] flex-none cursor-pointer border border-pending bg-white text-[12px] hover:border-ink"
                  @click="openDoc(b.name)"
                >↗</button>
                <button
                  type="button"
                  :aria-label="`Remove ${b.name}`"
                  class="size-[26px] flex-none cursor-pointer border border-pending bg-white text-[11px] hover:border-ink"
                  @click="removeFiles({ name: b.name, slot: b.slot })"
                >✕</button>
              </li>
            </ul>
          </template>
          <button
            v-else
            type="button"
            class="mx-4 my-3 cursor-pointer self-start border-0 bg-transparent p-0 text-[13.5px] underline underline-offset-[3px]"
            @click="addFiles(SAMPLE_BATCH)"
          >Try a sample batch (12 file names, 4 with errors; no real reading)</button>
        </section>

        <ul
          v-if="uploadMode !== 'batch' && unplaced.length"
          aria-label="Files not in a slot"
          class="m-0 flex list-none flex-col border border-ink bg-white p-0"
        >
          <li v-for="f in unplaced" :key="f.name" class="flex flex-wrap items-center gap-x-3.5 gap-y-2 border-b border-ink/15 px-4 py-2.5 last:border-b-0">
            <span aria-hidden="true" class="size-[9px] flex-none border border-ink" :class="f.status === 'reading' ? 'animate-pulse bg-pending' : 'bg-reject'"></span>
            <span class="flex min-w-0 flex-[1_1_200px] flex-col gap-[3px]">
              <span class="truncate font-mono text-[12.5px]">{{ f.name }}</span>
              <span class="text-[12.5px] leading-[1.35]" :class="f.status === 'reading' ? 'text-muted' : 'text-reject'">{{ f.status === 'reading' ? 'Reading…' : f.reason }}</span>
            </span>
            <button
              v-if="f.document_id"
              type="button"
              :aria-label="`Open ${f.name}`"
              title="Open document"
              class="size-[26px] flex-none cursor-pointer border border-pending bg-white text-[12px] hover:border-ink"
              @click="openDoc(f.name)"
            >↗</button>
            <button
              v-if="f.status !== 'reading'"
              type="button"
              :aria-label="`Remove ${f.name}`"
              class="size-[26px] flex-none cursor-pointer border border-pending bg-white text-[11px] hover:border-ink"
              @click="removeFiles({ name: f.name })"
            >✕</button>
          </li>
        </ul>

        <div class="grid grid-cols-[repeat(auto-fill,minmax(min(100%,300px),1fr))] gap-4">
          <section
            v-for="s in st.slots"
            :key="s.id"
            class="flex flex-col bg-white"
            :class="s.files.length || slotPending(s.id).length ? 'border border-ink' : s.required ? 'border-[1.5px] border-dashed border-ink' : 'border border-dashed border-faint'"
          >
            <div class="flex items-baseline justify-between gap-2.5 px-4 pt-3.5 pb-2.5">
              <span class="text-lg font-extrabold tracking-[-0.01em]">{{ s.label }}</span>
              <span
                class="font-mono text-[10px] font-bold tracking-[0.08em]"
                :class="s.files.length ? 'text-pass' : slotPending(s.id).length ? 'text-muted' : s.required ? 'text-signal' : 'text-faint'"
              >{{ s.files.length ? 'IDENTIFIED' : slotPending(s.id).some((p) => p.state !== 'error') ? 'IN PROGRESS' : s.required ? 'REQUIRED' : 'OPTIONAL' }}</span>
            </div>
            <span class="px-4 pb-3 text-[13px] leading-[1.4] text-muted">{{ s.desc }}</span>
            <div
              v-if="s.if_missing && !s.files.length && !slotPending(s.id).length"
              class="mx-4 mb-3 flex flex-col gap-1 border-l-[3px] py-0.5 pl-2.5"
              :class="{ FAIL: 'border-reject', WARN: 'border-signal', INFO: 'border-faint' }[s.if_missing.severity]"
            >
              <span
                class="font-mono text-[10px] font-bold tracking-[0.08em]"
                :class="{ FAIL: 'text-reject', WARN: 'text-signal', INFO: 'text-faint' }[s.if_missing.severity]"
              >
                IF MISSING · {{ s.if_missing.risk }} RISK · {{ { FAIL: s.required ? 'DEEMED REJECTED' : 'FAILS', WARN: 'NOTE', INFO: 'NOT ASSESSED' }[s.if_missing.severity] }}{{ c.complete_set || s.required || s.if_missing.severity === 'INFO' ? '' : ' (WHEN FINAL)' }}
              </span>
              <span class="text-[12px] leading-[1.4] text-muted">{{ s.if_missing.statement }} <span class="font-mono text-[11px]">{{ s.if_missing.clause }}</span></span>
            </div>
            <ul v-if="slotPending(s.id).length" role="status" class="m-0 flex list-none flex-col border-t border-ink/15 p-0">
              <li
                v-for="p in slotPending(s.id)"
                :key="`${p.state}:${p.name}`"
                class="animate-row-in flex items-center gap-2.5 border-b border-ink/10 px-4 py-2.5 last:border-b-0"
                :class="p.state === 'error' ? 'shadow-[inset_3px_0_0_var(--color-reject)]' : ''"
              >
                <span v-if="p.state === 'error'" aria-hidden="true" class="size-[9px] flex-none border border-ink bg-reject"></span>
                <span v-else aria-hidden="true" class="spinner size-3.5 flex-none rounded-full border-2 border-ink/20"></span>
                <span class="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span class="truncate font-mono text-[11.5px]">{{ p.name }}</span>
                  <span class="text-[12px] leading-[1.35]" :class="p.state === 'error' ? 'text-reject' : 'text-muted'">{{ p.text }}</span>
                </span>
                <button
                  v-if="p.state === 'error'"
                  type="button"
                  :aria-label="`Remove ${p.name}`"
                  class="size-[24px] flex-none cursor-pointer border border-pending bg-white text-[11px] hover:border-ink"
                  @click="removeFiles({ name: p.name })"
                >✕</button>
              </li>
            </ul>
            <template v-if="s.files.length">
              <ul class="m-0 flex animate-row-in list-none flex-col gap-1.5 border-t border-ink/15 px-4 py-2.5">
                <li v-for="f in s.files" :key="f" class="flex items-center gap-2 font-mono text-[11.5px]">
                  <span class="min-w-0 flex-1 truncate">▪ {{ f }}</span>
                  <button
                    v-if="docId(f)"
                    type="button"
                    :aria-label="`Open ${f}`"
                    title="Open document"
                    class="size-[22px] flex-none cursor-pointer border border-pending bg-white text-[11px] hover:border-ink"
                    @click="openDoc(f)"
                  >↗</button>
                </li>
              </ul>
              <div class="flex flex-col gap-1 border-t border-ink/15 bg-panel px-4 py-2.5">
                <span class="font-mono text-[10px] tracking-[0.08em] text-faint">IDENTIFIED</span>
                <span v-for="ft in s.facts" :key="ft" class="font-mono text-[11.5px] leading-[1.45]">{{ ft }}</span>
              </div>
            </template>
            <div class="mt-auto flex flex-wrap items-center gap-2.5 border-t border-ink/15 px-4 py-3">
              <label class="btn-hard relative bg-white px-3 py-[7px] text-[11.5px]">
                Upload<input type="file" multiple class="absolute size-px opacity-0" @change="onSlotFile(s.id, $event)" />
              </label>
              <button
                v-if="!s.files.length && !uploaded && s.id !== 'other'"
                type="button"
                class="cursor-pointer border-0 bg-transparent p-0 text-[13.5px] underline underline-offset-[3px]"
                @click="loadSample(s.id)"
              >Use sample</button>
              <button
                v-else-if="s.files.length"
                type="button"
                class="cursor-pointer border-0 bg-transparent p-0 text-[13.5px] text-muted underline underline-offset-[3px]"
                @click="removeFiles({ slot: s.id })"
              >Remove</button>
            </div>
          </section>
        </div>
      </div>

      <!-- 3 · REVIEW -->
      <div v-else-if="!run" class="flex flex-col items-start gap-3 border border-ink bg-white p-6">
        <span class="text-lg font-extrabold">The assessment has not run yet.</span>
        <span class="text-sm text-muted">Every required document is in. Run the rules to see the findings.</span>
        <button type="button" :disabled="running" class="btn-hard bg-signal px-4 py-[11px] text-xs tracking-[0.06em] uppercase" @click="runAssessment">
          {{ running ? 'Running…' : 'Run assessment →' }}
        </button>
      </div>
      <div v-else class="flex flex-col gap-5">
        <div v-if="st.state === 'stale'" role="status" class="flex flex-wrap items-center justify-between gap-3 border-2 border-signal bg-white px-[18px] py-3">
          <span class="text-[14.5px]"><strong>{{ st.stale_reasons.join(' · ') }} — re-run.</strong> This review shows run #{{ run.number }}.</span>
          <button type="button" :disabled="!st.ready || running" class="btn-hard bg-signal px-3.5 py-2 text-xs tracking-[0.06em] uppercase" @click="runAssessment">
            {{ running ? 'Running…' : 'Re-run' }}
          </button>
        </div>

        <div
          v-for="a in r.alerts || []"
          :key="a"
          role="alert"
          class="flex flex-wrap items-center gap-3 border-2 border-reject bg-reject px-[18px] py-3 text-white"
        >
          <span class="border-2 border-white px-2 py-0.5 font-mono text-xs font-bold tracking-[0.1em]">HIGH ALERT</span>
          <span class="text-[15px] font-bold">{{ a }}</span>
        </div>

        <div class="flex flex-wrap gap-3">
          <div class="flex flex-[1_1_260px] flex-col gap-1.5 border-2 bg-white px-[18px] py-4" :class="BORDER[r.verdict_tone]">
            <span class="font-mono text-[10.5px] tracking-[0.08em] text-faint">ASSESSMENT CONCLUSION</span>
            <span class="font-mono text-[22px] font-bold tracking-[0.06em]" :class="TONE[r.verdict_tone]">{{ r.verdict }}</span>
            <span class="text-[13px] leading-[1.4] text-muted">{{ r.verdict_note }}</span>
            <span class="flex flex-wrap gap-x-3 pt-1 font-mono text-[11px] font-bold">
              <span class="text-reject">{{ r.counts.fail }} FAIL</span><span class="text-signal">{{ r.counts.warn }} WARN</span>
              <span class="text-faint">{{ r.counts.waived }} WAIVED</span>
            </span>
          </div>
          <div class="flex flex-[2_1_400px] flex-col gap-1.5 border border-ink bg-white px-[18px] py-4">
            <span class="font-mono text-[10.5px] tracking-[0.08em] text-faint">BASIS</span>
            <span class="text-[15px] leading-[1.45]">{{ r.basis }}</span>
            <span class="pt-1 font-mono text-[10.5px] leading-relaxed text-faint">
              RUN #{{ run.number }} · {{ fmtTime(run.created_at) }} · {{ run.rule_pack }} · CONDITIONS {{ run.condition_hash }} · {{ run.run_by }}
            </span>
          </div>
        </div>

        <section aria-labelledby="notes-h" class="flex flex-col gap-2.5 border border-ink bg-white px-4 py-3.5">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <span id="notes-h" class="font-mono text-[11px] font-bold tracking-[0.08em]">REVIEWER NOTES</span>
            <span class="font-mono text-[10.5px] text-faint">
              {{ run.notes ? `Saved · ${run.notes.by} · ${fmtTime(run.notes.at)}` : 'Printed on the report with the conclusion' }}
            </span>
          </div>
          <textarea
            v-model="notesDraft"
            rows="3"
            aria-labelledby="notes-h"
            @blur="notesDirty && saveNotes()"
            :placeholder="r.verdict === 'ACCEPTABLE WITH NOTES'
              ? 'Your decision on the warnings and gaps, e.g. which records were requested, or why they are accepted…'
              : 'Notes on this conclusion for the report…'"
            class="w-full resize-y border border-ink/40 bg-white px-3 py-2 text-[14px] leading-[1.45] focus:border-ink"
          ></textarea>
          <div class="flex items-center gap-3">
            <button
              type="button"
              :disabled="savingNotes || !notesDirty"
              class="btn-hard bg-white px-3 py-1.5 text-[11px] uppercase"
              @click="saveNotes"
            >{{ savingNotes ? 'Saving…' : 'Save notes' }}</button>
            <span v-if="notesDirty" class="text-[12.5px] text-muted">Unsaved changes · saved when you leave the box</span>
          </div>
        </section>

        <section v-for="g in findingGroups" :key="g.title" class="border border-ink bg-white">
          <span class="flex flex-wrap items-baseline justify-between gap-2 border-b border-ink px-4 py-3 font-mono text-[11px] font-bold tracking-[0.08em]">
            <span>{{ g.title }}</span><span class="font-normal text-faint">{{ g.note }}</span>
          </span>
          <ol class="m-0 list-none p-0">
            <li
              v-for="f in g.items"
              :key="f.key"
              class="flex flex-col gap-1.5 border-b border-ink/15 px-4 py-3.5 last:border-b-0"
              :class="f.status === 'waived' ? 'opacity-70' : ''"
            >
              <div class="flex flex-wrap items-center gap-x-2.5 gap-y-1 font-mono text-[11px] font-bold tracking-[0.04em]">
                <span class="px-1.5 py-0.5" :class="f.status === 'waived' ? 'bg-panel text-faint line-through' : SEVERITY[f.severity]">{{ f.severity }}</span>
                <span>{{ f.rule_id }}</span><span class="text-faint">{{ f.id }}</span><span>{{ f.item }}</span>
                <span v-if="f.kind === 'gap'" class="border border-ink/40 px-1.5 py-px text-muted">EVIDENCE GAP</span>
                <span v-if="f.status === 'waived'" class="border border-ink px-1.5 py-px">WAIVED</span>
              </div>
              <p class="m-0 text-[14.5px] leading-[1.45]">{{ f.statement }}</p>
              <dl class="m-0 grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-0.5 text-[12.5px] leading-[1.4]">
                <dt class="font-mono text-[10.5px] text-faint">CLAUSE</dt><dd class="m-0">{{ f.clause }}</dd>
                <dt class="font-mono text-[10.5px] text-faint">DOCUMENTS</dt><dd class="m-0 font-mono text-[11.5px]">{{ f.documents.join(' · ') || '—' }}</dd>
                <dt class="font-mono text-[10.5px] text-faint">FIX</dt><dd class="m-0">{{ f.fix }}</dd>
                <template v-if="f.waiver">
                  <dt class="font-mono text-[10.5px] text-faint">WAIVER</dt>
                  <dd class="m-0">{{ f.waiver.reason }} — {{ f.waiver.by }}, {{ fmtTime(f.waiver.at) }}</dd>
                </template>
              </dl>
              <div v-if="f.evidence?.length && !st.sample_data" class="grid grid-cols-[repeat(auto-fill,minmax(min(100%,260px),1fr))] gap-3 pt-1.5">
                <EvidenceSnap v-for="(e, i) in f.evidence" :key="i" :project-no="projectNo" :evidence="e" />
              </div>
              <div class="flex flex-wrap items-center gap-2 pt-1">
                <template v-if="waiving === f.key">
                  <input
                    v-model="waiveReason"
                    type="text"
                    :aria-label="`Reason for waiving ${f.id}`"
                    placeholder="Reason for the waiver"
                    class="min-w-[240px] flex-1 border border-ink bg-white px-2.5 py-1.5 text-[13px]"
                    @keyup.enter="waiveReason.trim() && setWaiver(f.key, 'waived')"
                  />
                  <button type="button" :disabled="!waiveReason.trim()" class="btn-hard bg-white px-3 py-1.5 text-[11px] uppercase" @click="setWaiver(f.key, 'waived')">Waive</button>
                  <button type="button" class="cursor-pointer border-0 bg-transparent p-0 text-[13px] text-muted underline" @click="waiving = null">Cancel</button>
                </template>
                <button v-else-if="f.status === 'waived'" type="button" class="cursor-pointer border-0 bg-transparent p-0 text-[13px] underline" @click="setWaiver(f.key, 'open')">Re-open</button>
                <button v-else type="button" class="cursor-pointer border-0 bg-transparent p-0 text-[13px] underline" @click="openWaive(f.key)">Waive with reason…</button>
              </div>
            </li>
          </ol>
        </section>

        <section v-for="sec in r.sections" :key="sec.id" class="border border-ink bg-white">
          <div class="flex flex-col gap-1 border-b border-ink px-4 py-3">
            <span class="text-[17px] font-extrabold">{{ sec.title }}</span>
            <span class="text-[13px] leading-[1.4] text-muted">{{ sec.note }}</span>
          </div>
          <div v-if="sec.rows" class="overflow-x-auto">
            <table class="w-full min-w-[720px] border-collapse text-[13px]">
              <thead>
                <tr class="bg-ink text-left text-paper">
                  <th v-for="h in sec.headers" :key="h" scope="col" class="px-3 py-2 font-mono text-[10.5px] font-bold tracking-[0.06em] whitespace-nowrap">{{ h }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in sec.rows" :key="i" class="border-b border-ink/15">
                  <td
                    v-for="(cl, j) in row"
                    :key="j"
                    class="px-3 py-[9px] font-mono text-xs"
                    :class="[TONE[cl.tone], cl.bold ? 'font-bold' : 'font-normal']"
                  >{{ cl.v }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="m-0 px-4 py-3.5 font-mono text-[11.5px] text-faint">PENDING · {{ sec.missing }}</p>
        </section>

        <section class="border border-ink bg-white">
          <span class="block border-b border-ink px-4 py-3 text-[17px] font-extrabold">Assessment Criteria</span>
          <div v-for="cr in r.criteria" :key="cr.label" class="flex justify-between gap-4 border-b border-ink/15 px-4 py-2.5 last:border-b-0">
            <span class="text-sm">{{ cr.label }}</span>
            <span class="font-mono text-xs font-bold whitespace-nowrap" :class="TONE[cr.tone]">{{ cr.status }}</span>
          </div>
        </section>
        <p v-if="st.sample_data" class="m-0 font-mono text-[11px] leading-relaxed text-faint">
          SAMPLE DATA · Results come from the sample documents until document extraction feeds the assessment. Clause numbers and
          limits must be confirmed by an engineer against the contract editions.
        </p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.row-err {
  background: color-mix(in srgb, var(--color-reject) 5%, var(--color-white));
}
.spinner {
  border-top-color: var(--color-signal);
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation-duration: 2.4s;
  }
}
</style>
