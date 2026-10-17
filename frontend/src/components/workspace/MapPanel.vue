<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useStore } from 'vuex'
import PanelHeader from './PanelHeader.vue'
import TraceMap from './TraceMap.vue'
import TraceTable from './TraceTable.vue'
import ExtractionProgress from './ExtractionProgress.vue'
import EmptyState from './EmptyState.vue'
import ChecksDrawer from './ChecksDrawer.vue'

const props = defineProps({
  projectNo: { type: String, required: true },
  visible: { type: Boolean, default: true },
})
const emit = defineEmits(['open-inspector'])

const store = useStore()
const ws = computed(() => store.state.workspace)
const isReview = computed(() => store.getters['workspace/isReview'])
const phase = computed(() => store.getters['workspace/phase'])

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

      <TraceMap v-if="mode === 'map'" ref="map" v-model:zoom="zoom" :q="q" @open-inspector="emit('open-inspector')" />
      <TraceTable v-else :q="q" @open-inspector="emit('open-inspector')" />
    </template>

    <ExtractionProgress v-else-if="phase === 'processing'" />
    <EmptyState v-else />

    <ChecksDrawer v-if="ws.drawer && isReview" @show-item="showItem" />
  </section>
</template>
