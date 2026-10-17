<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'
import { heatText } from '../../data/workspace'
import { worst } from '../../lib/status'
import RuleStamp from '../ui/RuleStamp.vue'

const props = defineProps({
  q: { type: String, default: '' },
})
const emit = defineEmits(['open-inspector'])

const store = useStore()
const ws = computed(() => store.state.workspace)
const sel = computed(() => ws.value.sel)
const statusOf = (key) => store.getters['workspace/statusOf'](key)
const itemByKey = computed(() => store.getters['workspace/itemByKey'])

// One row per weld, with the parts and heats it joins and the NDT reports covering it.
const rows = computed(() => {
  const q = props.q.trim().toLowerCase()
  const welds = ws.value.items.filter((i) => i.kind === 'weld').sort((a, b) => a.key.localeCompare(b.key, undefined, { numeric: true }))
  const ndts = ws.value.items.filter((i) => i.kind === 'ndt')
  return welds.map((w) => {
    const parts = w.attributes.parts ?? []
    const heats = [...new Set(parts.flatMap((p) => itemByKey.value[p]?.attributes.heat_nos ?? []))]
    const reports = ndts.filter((n) => n.attributes.welds?.includes(w.key)).map((n) => n.key)
    const ids = [w.key, ...parts, ...heats, ...reports]
    const r = {
      weld: w.key,
      part: parts.join(' / ') || '—',
      heat: heatText(parts, itemByKey.value),
      wps: w.attributes.wps ?? '—',
      welder: w.attributes.welder ?? '—',
      ndt: reports.join(' · ') || '— MISSING',
      status: worst(ids.map(statusOf)),
      ids,
    }
    r.match = !q || Object.values(r).join(' ').toLowerCase().includes(q)
    return r
  })
})

const select = (key) => store.commit('workspace/select', key)
const openRow = (r) => {
  select(r.weld)
  emit('open-inspector')
}
</script>

<template>
  <div class="min-h-0 flex-1 overflow-auto bg-white">
    <table class="w-full border-collapse font-mono text-xs">
      <thead>
        <tr class="bg-ink text-left text-[10.5px] tracking-[0.08em] text-paper">
          <th scope="col" class="px-3.5 py-[9px] font-bold">PART</th>
          <th scope="col" class="px-2.5 py-[9px] font-bold">HEAT NO.</th>
          <th scope="col" class="px-2.5 py-[9px] font-bold">WELD ID</th>
          <th scope="col" class="px-2.5 py-[9px] font-bold">WPS</th>
          <th scope="col" class="px-2.5 py-[9px] font-bold">WELDER</th>
          <th scope="col" class="px-2.5 py-[9px] font-bold">NDT</th>
          <th scope="col" class="px-3.5 py-[9px] font-bold">STATUS</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="r in rows"
          :key="r.weld"
          tabindex="0"
          :aria-selected="r.ids.includes(sel)"
          class="cursor-pointer border-b border-ink -outline-offset-2 hover:bg-white"
          :class="[r.weld === sel ? 'outline-2 outline-signal' : '', r.match ? 'opacity-100' : 'opacity-30']"
          @click="select(r.weld)"
          @keydown.enter.prevent="openRow(r)"
          @keydown.space.prevent="openRow(r)"
        >
          <td class="px-3.5 py-[11px]">{{ r.part }}</td>
          <td class="px-2.5 py-[11px]">{{ r.heat }}</td>
          <td class="px-2.5 py-[11px] font-bold">{{ r.weld }}</td>
          <td class="px-2.5 py-[11px]">{{ r.wps }}</td>
          <td class="px-2.5 py-[11px]">{{ r.welder }}</td>
          <td class="px-2.5 py-[11px]">{{ r.ndt }}</td>
          <td class="px-3.5 py-2"><RuleStamp :status="r.status" class="px-2 py-0.5 text-[11px] tracking-[0.1em]" /></td>
        </tr>
      </tbody>
    </table>
    <p class="m-0 px-3.5 py-2.5 font-mono text-[10.5px] text-faint">{{ rows.length }} WELDS — WITH LINKED PARTS, HEATS AND NDT REPORTS</p>
  </div>
</template>
