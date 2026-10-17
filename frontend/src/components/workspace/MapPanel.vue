<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useStore } from 'vuex'
import PanelHeader from './PanelHeader.vue'
import TraceMap from './TraceMap.vue'
import TraceTable from './TraceTable.vue'
import ExtractionProgress from './ExtractionProgress.vue'
import EmptyState from './EmptyState.vue'
import ChecksDrawer from './ChecksDrawer.vue'
import { GROUPS } from '../../data/workspace'

const props = defineProps({
  projectNo: { type: String, required: true },
  visible: { type: Boolean, default: true },
})
const emit = defineEmits(['open-inspector'])

const store = useStore()
const ws = computed(() => store.state.workspace)
const isReview = computed(() => store.getters['workspace/isReview'])
const phase = computed(() => store.getters['workspace/phase'])
const types = computed(() => store.getters['workspace/docTypes'])
const SHORT = { mtc: 'MTC', weld: 'WELD', ndt: 'NDT', insp: 'INSP', prod: 'PROD' }
const missingTypes = computed(() => GROUPS.filter(([key]) => !types.value.has(key)).map(([, label]) => label))

const update = computed(() => {
  const g = store.getters
  const pending = g['workspace/pendingDocs']
  if (pending.length) {
    const reading = pending.filter((d) => d.status === 'reading').map((d) => d.filename)
    const lastRun = ws.value.result?.created_at ? Date.parse(ws.value.result.created_at) : 0
    const batch = ws.value.docs.filter((d) => pending.includes(d) || Date.parse(d.updated_at ?? d.created_at) > lastRun)
    const done = batch.length - pending.length
    return {
      stage: 'STEP 1 / 3 · READ',
      title: `Reading ${pending.length} new ${pending.length === 1 ? 'document' : 'documents'}`,
      progress: batch.length ? done / batch.length : null,
      detail: reading.length ? `Now reading: ${reading.slice(0, 2).join(', ')}${reading.length > 2 ? ` +${reading.length - 2}` : ''}` : 'Queued for reading…',
    }
  }
  if (g['workspace/awaitingRun'])
    return {
      stage: 'STEP 2 / 3 · WAIT',
      title: 'Waiting in case more files are added',
      progress: null,
      detail: 'Checks start about 15 s after the last file is read. The map below is from the last run.',
      runNow: true,
    }
  if (g['workspace/checking'])
    return {
      stage: 'STEP 3 / 3 · CHECK',
      title: 'Rebuilding the map and running checks',
      progress: null,
      detail: 'Usually under a second. The new map replaces this one when it is ready.',
    }
  return null
})

const mode = ref('map')
const zoom = ref(1)
const q = ref('')
const map = ref(null)

const step = (d) => (zoom.value = Math.max(0.4, Math.min(1.6, Math.round((zoom.value + d) * 100) / 100)))
const refit = () => nextTick(() => setTimeout(() => map.value?.fit(), 40))

// Refit when the map tab becomes visible again on narrow screens.
watch(() => props.visible, (v) => v && refit())

const showItem = (id) => {
  store.commit('workspace/select', id)
  if (mode.value === 'map') map.value?.focusNode(id)
  emit('open-inspector')
}

const toolBtn = 'h-[30px] cursor-pointer border border-ink bg-white font-mono'
</script>

<template>
  <section aria-label="Traceability map" class="relative flex min-h-0 flex-col overflow-hidden border-r border-ink">
    <PanelHeader title="B / TRACEABILITY MAP" :meta="`${projectNo} · REV. A`" />

    <p v-if="ws.error" role="alert" class="m-0 border-b border-ink bg-white px-3.5 py-2 font-mono text-[11px] text-reject">{{ ws.error }}</p>

    <template v-if="isReview">
      <div
        v-if="missingTypes.length"
        role="status"
        class="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-ink bg-paper px-3.5 py-2 font-mono text-[10.5px]"
      >
        <span class="border border-ink bg-signal px-1.5 py-px font-bold tracking-[0.06em]">INCOMPLETE DOSSIER</span>
        <span class="flex flex-wrap gap-1.5" aria-label="Document types">
          <span
            v-for="[key, label] in GROUPS"
            :key="key"
            class="flex items-center gap-1 border px-1.5 py-px"
            :class="types.has(key) ? 'border-ink text-ink' : 'border-dashed border-ink/40 text-faint'"
            :title="types.has(key) ? `${label}: uploaded` : `${label}: none yet`"
          >
            <span aria-hidden="true">{{ types.has(key) ? '■' : '□' }}</span>{{ SHORT[key] }}
          </span>
        </span>
        <span class="text-muted">No {{ missingTypes.join(', ').toLowerCase() }} yet. Findings may change as you add them.</span>
      </div>
      <div class="flex flex-wrap items-center gap-2 border-b border-ink bg-white px-3.5 py-2">
        <div class="flex">
          <button type="button" aria-label="Zoom out" :class="toolBtn" class="w-[30px] text-[15px]" @click="step(-0.1)">−</button>
          <button type="button" aria-label="Zoom in" :class="toolBtn" class="-ml-px w-[30px] text-[15px]" @click="step(0.1)">+</button>
          <button type="button" :class="toolBtn" class="-ml-px px-2.5 text-[11px] font-bold" @click="map?.fit()">FIT</button>
        </div>
        <span class="w-11 font-mono text-[11px]">{{ Math.round(zoom * 100) }}%</span>
        <label class="flex h-[30px] max-w-[340px] flex-[1_1_220px] items-center gap-2 border border-ink bg-white px-2.5">
          <span aria-hidden="true" class="font-mono text-[11px] text-faint">FIND</span>
          <input
            v-model="q"
            type="search"
            aria-label="Find heat no., weld ID, part"
            placeholder="Find heat no., weld ID, part..."
            class="min-w-0 flex-1 border-0 bg-transparent font-mono text-xs outline-none"
            @keydown.enter="map?.findFirst()"
          />
        </label>
        <div role="radiogroup" aria-label="View" class="ml-auto flex">
          <button
            v-for="(m, i) in ['map', 'table']"
            :key="m"
            type="button"
            role="radio"
            :aria-checked="mode === m"
            class="h-[30px] cursor-pointer border border-ink px-3 font-mono text-[11px] font-bold uppercase"
            :class="[mode === m ? 'bg-ink text-paper' : 'bg-white', { '-ml-px': i }]"
            @click="mode = m"
          >{{ m }}</button>
        </div>
      </div>

      <div class="relative flex min-h-0 flex-1 flex-col">
        <TraceMap v-if="mode === 'map'" ref="map" v-model:zoom="zoom" :q="q" @open-inspector="emit('open-inspector')" />
        <TraceTable v-else :q="q" @open-inspector="emit('open-inspector')" />

        <div v-if="update" class="pointer-events-none absolute inset-0 z-20 flex justify-center bg-paper/55 px-4 pt-10">
          <div
            role="status"
            aria-live="polite"
            class="pointer-events-auto flex h-fit w-full max-w-[420px] flex-col gap-3 border border-ink bg-white p-4 shadow-[4px_4px_0_rgb(var(--shade)/0.15)]"
          >
            <div class="flex items-center justify-between gap-3 font-mono text-[10.5px] tracking-[0.08em]">
              <span class="font-bold">UPDATING THE MAP</span>
              <span class="text-faint">{{ update.stage }}</span>
            </div>
            <span class="text-[17px] leading-tight font-extrabold tracking-[-0.01em]">{{ update.title }}</span>
            <span aria-hidden="true" class="relative block h-[5px] w-full overflow-hidden border border-ink bg-white">
              <span
                v-if="update.progress != null"
                class="absolute inset-y-0 left-0 bg-ink transition-[width] duration-300"
                :style="{ width: `${update.progress * 100}%` }"
              ></span>
              <span v-else class="absolute inset-y-0 w-[30%] bg-ink [animation:hm-bar_1s_linear_infinite]"></span>
            </span>
            <span class="font-mono text-[11px] leading-relaxed text-muted">{{ update.detail }}</span>
            <button
              v-if="update.runNow"
              type="button"
              class="btn-hard self-start bg-signal px-3 py-1.5 text-[11px] tracking-[0.04em]"
              @click="store.dispatch('workspace/runChecks')"
            >Run checks now</button>
          </div>
        </div>
      </div>
    </template>

    <ExtractionProgress v-else-if="phase === 'processing'" />
    <EmptyState v-else />

    <ChecksDrawer v-if="ws.drawer && isReview" @show-item="showItem" />
  </section>
</template>
