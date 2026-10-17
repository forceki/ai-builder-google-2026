<script setup>
import { computed, inject, nextTick, ref, watch } from 'vue'
import { useStore } from 'vuex'
import { EVIDENCE_GROUP, KIND_LABEL, itemSub } from '../../data/workspace'
import { clockTime } from '../../lib/status'
import PanelHeader from './PanelHeader.vue'
import RuleStamp from '../ui/RuleStamp.vue'

const store = useStore()
const openUpload = inject('openUpload')

const ws = computed(() => store.state.workspace)
const phase = computed(() => store.getters['workspace/phase'])
const item = computed(() => (phase.value === 'review' && ws.value.sel ? store.getters['workspace/itemByKey'][ws.value.sel] : null))
const status = computed(() => item.value && store.getters['workspace/statusOf'](item.value.key))
const findings = computed(() => (item.value ? store.getters['workspace/findingsFor'](item.value.key) : []))

const previewIdx = ref(0)
const noting = ref(false)
const noteVal = ref('')
const title = ref(null)
const noteBox = ref(null)

watch(
  () => ws.value.sel,
  () => {
    previewIdx.value = 0
    noting.value = false
  },
)

const show = (v) =>
  v == null || v === '' ? '—' : Array.isArray(v) ? v.join(', ') || '—' : typeof v === 'boolean' ? (v ? 'YES' : 'NO') : String(v).toUpperCase()

const fields = computed(() =>
  Object.entries(item.value.attributes).map(([k, v]) => ({ label: k.replaceAll('_', ' ').toUpperCase(), value: show(v) })),
)
const sources = computed(() => item.value.sources)
const preview = computed(() => {
  const i = Math.min(previewIdx.value, Math.max(0, sources.value.length - 1))
  const src = sources.value[i] ?? { document: '—', page: null }
  return { ...src, field: fields.value[i] ?? fields.value[0], top: 56 + (i % 5) * 22 }
})

const attach = () => {
  const f = findings.value[0]
  openUpload({ group: f ? EVIDENCE_GROUP[f.rule_id] : '', id: item.value.key })
}

const startNote = () => {
  noting.value = true
  noteVal.value = ''
  nextTick(() => noteBox.value?.focus())
}
const saveNote = () => {
  const text = noteVal.value.trim()
  if (!text) return
  store.commit('workspace/addNote', { key: item.value.key, text, time: clockTime() })
  noting.value = false
}

const emptyText = computed(() =>
  phase.value === 'empty'
    ? 'Nothing to inspect yet. Upload documents to build the traceability map.'
    : phase.value === 'processing'
      ? 'The inspector opens once extraction finishes.'
      : 'Select an item on the map to inspect it.',
)

const actionBtn = 'btn-hard px-2.5 py-2 text-[11px] tracking-[0.04em]'
defineExpose({ focusTitle: () => title.value?.focus() })
</script>

<template>
  <aside aria-label="Inspector" class="flex min-h-0 flex-col bg-white">
    <PanelHeader title="C / INSPECTOR" :meta="item ? KIND_LABEL[item.kind] : '—'" />

    <div v-if="item" class="min-h-0 flex-1 overflow-auto">
      <div class="flex flex-col gap-2.5 border-b border-ink px-[18px] pt-[18px] pb-4">
        <div class="flex items-center justify-between gap-3">
          <h2 ref="title" tabindex="-1" class="m-0 font-mono text-[26px] font-bold tracking-[-0.01em] outline-none">{{ item.label }}</h2>
          <RuleStamp
            :key="status"
            :status="status"
            class="flex-none -rotate-5 px-[11px] py-1 text-sm tracking-[0.14em] outline outline-offset-2 [animation:hm-stamp_.25s_ease-out_both]"
          />
        </div>
        <span class="font-mono text-[11px] text-faint">{{ itemSub(item) }}</span>
        <span class="font-mono text-[10.5px] tracking-[0.04em]">
          STATUS FROM {{ findings.length ? `RULE ${findings.map((f) => f.rule_id).join(', ')}` : 'RULE SET ' + (ws.result?.rule_set ?? '—') }}
          · LAST RUN {{ store.getters['workspace/lastRun'] }}
        </span>
        <span v-if="ws.resolved[item.key]" class="self-start border border-ink px-2 py-[3px] font-mono text-[10.5px] font-bold">
          MARKED RESOLVED · RE-RUN CHECKS TO CLEAR
        </span>
      </div>

      <div class="px-[18px] pt-2.5 pb-1 font-mono text-[10.5px] tracking-[0.08em] text-faint">EXTRACTED FIELDS</div>
      <dl class="m-0">
        <div v-for="f in fields" :key="f.label" class="grid grid-cols-[108px_minmax(0,1fr)] gap-x-3 gap-y-1 border-b border-ink/15 px-[18px] py-[9px]">
          <dt class="pt-0.5 font-mono text-[10.5px] tracking-[0.05em] text-faint">{{ f.label }}</dt>
          <dd class="m-0 font-mono text-[13px] font-bold break-words">{{ f.value }}</dd>
        </div>
        <div class="grid grid-cols-[108px_minmax(0,1fr)] gap-x-3 px-[18px] py-[9px]">
          <dt class="pt-0.5 font-mono text-[10.5px] tracking-[0.05em] text-faint">SOURCES</dt>
          <dd class="m-0 flex flex-col items-start gap-1">
            <button
              v-for="(s, i) in sources"
              :key="`${s.document}-${s.page}-${i}`"
              type="button"
              class="cursor-pointer border-0 bg-transparent p-0 text-left font-mono text-[10.5px] underline underline-offset-2"
              :class="{ 'font-bold': i === previewIdx }"
              @click="previewIdx = i"
            >↳ {{ s.document }}{{ s.page ? ` · p.${s.page}` : '' }}</button>
          </dd>
        </div>
      </dl>

      <div class="flex justify-between px-[18px] pt-3.5 pb-1.5 font-mono text-[10.5px] tracking-[0.08em] text-faint">
        <span>SOURCE PREVIEW</span><span>{{ preview.document }}{{ preview.page ? ` · p.${preview.page}` : '' }}</span>
      </div>
      <div
        role="img"
        :aria-label="`Page ${preview.page ?? ''} of ${preview.document}`"
        class="relative mx-[18px] h-[200px] overflow-hidden border border-ink bg-white"
      >
        <span class="absolute top-3.5 left-3.5 h-[7px] w-[38%] bg-ink"></span>
        <span class="absolute top-3.5 right-3.5 h-[7px] w-[16%] bg-pending"></span>
        <span class="absolute top-8 left-3.5 h-1 w-[60%] bg-[#E0E0E0]"></span>
        <span class="absolute inset-x-3.5 top-[50px] h-px bg-ink"></span>
        <template v-for="(row, r) in [[28, 34], [24, 30], [30, 26], [22, 36], [26, 22]]" :key="r">
          <span class="absolute left-3.5 h-1 bg-[#E0E0E0]" :style="{ top: `${62 + r * 22}px`, width: `${row[0]}%` }"></span>
          <span class="absolute left-[46%] h-1 bg-[#E0E0E0]" :style="{ top: `${62 + r * 22}px`, width: `${row[1]}%` }"></span>
        </template>
        <span class="absolute inset-x-3.5 bottom-[18px] h-px bg-pending"></span>
        <span
          v-if="preview.field"
          class="absolute inset-x-2.5 box-border flex h-[22px] items-center gap-2 border-2 border-signal bg-white px-1.5 font-mono text-[10.5px] transition-[top] duration-200"
          :style="{ top: `${preview.top}px` }"
        >
          <span class="text-faint">{{ preview.field.label }}</span><span class="truncate font-bold">{{ preview.field.value }}</span>
        </span>
      </div>
      <p class="m-0 px-[18px] pt-1.5 font-mono text-[9.5px] text-faint">Layout preview. Page images are not stored yet.</p>

      <div class="mt-4 flex flex-col gap-2.5 border-t border-ink px-[18px] py-3.5">
        <div class="flex items-center justify-between gap-2 font-mono text-[10.5px] tracking-[0.08em]">
          <span class="font-bold">FINDING — EXPLANATION</span><span class="text-faint">GENERATED · FOR REVIEW</span>
        </div>
        <template v-if="findings.length">
          <div v-for="f in findings" :key="f.id" class="flex flex-col gap-2.5">
            <p class="m-0 text-[14.5px] leading-[1.45]">{{ f.explanation || f.message }}</p>
            <div v-if="f.next_step" class="flex flex-col gap-1 border border-ink bg-white px-3 py-2.5">
              <span class="font-mono text-[10px] tracking-[0.08em] text-faint">SUGGESTED NEXT STEP</span>
              <span class="text-sm leading-[1.4]">{{ f.next_step }}</span>
            </div>
            <span class="font-mono text-[10px] text-faint">
              {{ f.rule_id }} · SRC: {{ f.sources.map((s) => `${s.document}${s.page ? ` p.${s.page}` : ''}`).join(' / ') }}
            </span>
          </div>
        </template>
        <p v-else class="m-0 text-[14.5px] leading-[1.45]">No findings for this item on the last run.</p>

        <div class="flex flex-wrap gap-1.5 pt-1">
          <button type="button" :class="actionBtn" class="border-b-black bg-ink text-paper" @click="attach">ATTACH EVIDENCE</button>
          <button
            type="button"
            :aria-pressed="!!ws.resolved[item.key]"
            :class="actionBtn"
            class="bg-white"
            @click="store.commit('workspace/toggleResolved', item.key)"
          >{{ ws.resolved[item.key] ? 'UNMARK RESOLVED' : 'MARK AS RESOLVED' }}</button>
          <button type="button" :class="actionBtn" class="bg-white" @click="startNote">ADD NOTE</button>
        </div>
        <form v-if="noting" class="flex flex-col gap-1.5" @submit.prevent="saveNote">
          <label for="hm-note" class="font-mono text-[10px] tracking-[0.08em] text-faint">NOTE</label>
          <textarea
            id="hm-note"
            ref="noteBox"
            v-model="noteVal"
            rows="3"
            class="resize-y border border-ink bg-white p-2 text-[13px] outline-none focus:outline-2 focus:outline-signal"
          ></textarea>
          <span class="flex gap-1.5">
            <button type="submit" class="cursor-pointer border border-ink bg-ink px-2.5 py-1.5 font-mono text-[11px] font-bold text-paper">SAVE NOTE</button>
            <button type="button" class="cursor-pointer border border-ink bg-white px-2.5 py-1.5 font-mono text-[11px]" @click="noting = false">CANCEL</button>
          </span>
        </form>
        <div v-for="(n, i) in ws.notes[item.key] || []" :key="i" class="flex flex-col gap-[3px] border border-dashed border-ink px-2.5 py-2">
          <span class="font-mono text-[10px] text-faint">{{ n.meta }}</span>
          <span class="text-[13px] leading-[1.4]">{{ n.text }}</span>
        </div>
      </div>
      <p class="m-0 border-t border-ink px-[18px] pt-3 pb-[18px] font-mono text-[10.5px] leading-normal text-faint">
        PASS / HOLD / REJECT comes from the rule check. The explanation is generated for review. Final release sign-off:
        quality engineer.
      </p>
    </div>

    <div v-else class="flex flex-1 flex-col justify-center gap-2.5 p-6">
      <span aria-hidden="true" class="size-2.5 border border-ink bg-pending"></span>
      <p class="m-0 max-w-[260px] text-[15px] leading-[1.45]">{{ emptyText }}</p>
    </div>
  </aside>
</template>
