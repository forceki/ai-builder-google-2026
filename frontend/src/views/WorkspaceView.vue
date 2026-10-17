<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useStore } from 'vuex'
import AppBar from '../components/app/AppBar.vue'
import Breadcrumb from '../components/app/Breadcrumb.vue'
import DocumentsPanel from '../components/workspace/DocumentsPanel.vue'
import MapPanel from '../components/workspace/MapPanel.vue'
import InspectorPanel from '../components/workspace/InspectorPanel.vue'
import StatusStrip from '../components/workspace/StatusStrip.vue'
import UploadDialog from '../components/workspace/UploadDialog.vue'
import { STAGE_LABELS, guess } from '../data/workspace'

const route = useRoute()
const store = useStore()

const projectNo = computed(() => route.params.no)
const project = computed(() => store.state.workspace.project)
const crumbs = computed(() => [
  { label: 'PROJECTS', to: '/projects' },
  { label: projectNo.value, to: route.path },
  { label: (project.value?.name ?? '…').toUpperCase() },
])

const isReview = computed(() => store.getters['workspace/isReview'])
const running = computed(() => store.getters['workspace/running'])
const stage = computed(() => store.getters['workspace/stage'])

watch(projectNo, (no) => no && store.dispatch('workspace/load', no), { immediate: true })
onBeforeUnmount(() => store.dispatch('workspace/teardown'))

// Below 1100px the three panels become tabs.
const narrow = ref(false)
const tab = ref('B')
const onResize = () => (narrow.value = window.innerWidth < 1100)
onMounted(() => {
  onResize()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
const shows = (k) => !narrow.value || tab.value === k

const inspector = ref(null)
function openInspector() {
  if (narrow.value) tab.value = 'C'
  nextTick(() => setTimeout(() => inspector.value?.focusTitle(), 40))
}

const upload = ref(null)
// p: { file?: File, group?, id? (open item the file is evidence for) }
function openUpload(p = {}) {
  upload.value = {
    file: p.file ?? null,
    group: p.group || (p.file ? guess(p.file.name) : ''),
    detected: p.file ? guess(p.file.name) : '',
    link: p.id || '',
  }
}

provide('openUpload', openUpload)

const tabs = [
  { key: 'A', label: 'A / DOCUMENTS' },
  { key: 'B', label: 'B / MAP' },
  { key: 'C', label: 'C / INSPECTOR' },
]
</script>

<template>
  <div class="grid h-screen grid-rows-[auto_auto_minmax(0,1fr)_auto] overflow-hidden bg-paper font-sans text-ink">
    <AppBar class="min-h-10">
      <template #title>
        <Breadcrumb :items="crumbs" />
        <ol aria-label="Job stage" class="m-0 flex flex-none list-none border border-ink p-0 font-mono text-[11px] tracking-[0.06em]">
          <li
            v-for="(label, i) in STAGE_LABELS"
            :key="label"
            :aria-current="i === stage ? 'step' : undefined"
            class="flex items-center gap-1.5 px-3 py-[7px]"
            :class="[
              i === stage ? 'bg-signal font-bold' : '',
              i > stage ? 'text-faint' : 'text-ink',
              { 'border-l border-ink': i },
            ]"
          >
            <span>{{ String(i + 1).padStart(2, '0') }}</span><span>{{ label }}</span>
            <span v-if="i < 3" aria-hidden="true">→</span>
          </li>
        </ol>
      </template>
      <template #actions>
        <button
          type="button"
          :disabled="!isReview || running"
          class="btn-hard flex items-center gap-2 bg-signal px-3.5 py-2 text-xs tracking-[0.06em] uppercase"
          @click="store.dispatch('workspace/runChecks')"
        >
          <span aria-hidden="true" class="size-[7px] bg-ink"></span>Run checks
        </button>
        <RouterLink
          v-if="isReview"
          :to="`/projects/${projectNo}/report`"
          class="btn-hard bg-white px-3.5 py-2 text-xs tracking-[0.06em] uppercase no-underline"
        >Export report</RouterLink>
        <button v-else type="button" disabled class="btn-hard bg-white px-3.5 py-2 text-xs tracking-[0.06em] uppercase">
          Export report
        </button>
      </template>
    </AppBar>

    <div v-if="narrow" role="tablist" aria-label="Panels" class="flex border-b border-ink font-mono text-xs tracking-[0.06em]">
      <button
        v-for="t in tabs"
        :key="t.key"
        type="button"
        role="tab"
        :aria-selected="tab === t.key"
        class="flex-1 cursor-pointer border-r border-ink px-3 py-2.5 text-left font-bold"
        :class="tab === t.key ? 'bg-ink text-paper' : 'bg-white'"
        @click="tab = t.key"
      >{{ t.label }}</button>
    </div>
    <div v-else></div>

    <div class="grid min-h-0" :class="narrow ? 'grid-cols-[minmax(0,1fr)]' : 'grid-cols-[300px_minmax(0,1fr)_360px]'">
      <DocumentsPanel v-show="shows('A')" />
      <MapPanel v-show="shows('B')" :project-no="projectNo" :visible="shows('B')" @open-inspector="openInspector" />
      <InspectorPanel v-show="shows('C')" ref="inspector" />
    </div>

    <StatusStrip />

    <UploadDialog v-if="upload" v-model="upload" @close="upload = null" />
  </div>
</template>
