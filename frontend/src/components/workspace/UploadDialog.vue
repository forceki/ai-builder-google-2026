<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useStore } from 'vuex'
import { GROUP_INFO, guess } from '../../data/workspace'

const upload = defineModel({ type: Object, required: true })
const emit = defineEmits(['close'])

const CONCURRENCY = 3

const store = useStore()
const openKeys = computed(() => store.getters['workspace/openKeys'])
const signed = computed(() => !!store.state.workspace.project?.signoff?.current)
const sending = ref(false)

let nextId = 0
const toRow = (file) => {
  const detected = guess(file.name)
  return { id: nextId++, file, group: detected || upload.value.group || '', detected, state: 'ready', error: '' }
}
const rows = ref((upload.value.files ?? []).map(toRow))

const pending = computed(() => rows.value.filter((r) => r.state !== 'done'))
const canAdd = computed(() => pending.value.length && pending.value.every((r) => r.group) && !sending.value)
const untyped = computed(() => pending.value.filter((r) => !r.group).length)

const helpText = computed(() =>
  !rows.value.length
    ? 'Choose one or more files. We suggest a type from each file name.'
    : untyped.value
      ? `Pick a type for ${untyped.value} ${untyped.value === 1 ? 'file' : 'files'} we couldn't recognise.`
      : 'Check the suggested types and change any that are wrong.',
)

const onFiles = (e) => {
  rows.value.push(...[...(e.target.files ?? [])].map(toRow))
  e.target.value = ''
}
const remove = (row) => (rows.value = rows.value.filter((r) => r !== row))

const send = async (row) => {
  row.state = 'sending'
  row.error = ''
  try {
    await store.dispatch('workspace/upload', {
      file: row.file,
      docType: row.group,
      evidenceFor: upload.value.link || undefined,
    })
    row.state = 'done'
  } catch (e) {
    row.state = 'failed'
    row.error = e.message
  }
}

const submit = async () => {
  if (!canAdd.value) return
  sending.value = true
  const queue = [...pending.value]
  const worker = async () => {
    while (queue.length) await send(queue.shift())
  }
  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, queue.length) }, worker))
  sending.value = false
  if (rows.value.every((r) => r.state === 'done')) emit('close')
  else rows.value = rows.value.filter((r) => r.state !== 'done')
}

const STATE_LABEL = { ready: '', sending: 'UPLOADING…', done: 'ADDED', failed: 'FAILED' }
const submitLabel = computed(() => {
  if (sending.value) return 'Uploading…'
  const n = pending.value.length
  return n > 1 ? `Add ${n} documents` : 'Add document'
})

const onKey = (e) => e.key === 'Escape' && !sending.value && emit('close')
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div
    role="dialog"
    aria-modal="true"
    aria-labelledby="hm-up-h"
    class="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 p-5"
    @click.self="!sending && emit('close')"
  >
    <form
      class="flex max-h-[calc(100vh-40px)] w-full max-w-[640px] flex-col overflow-auto border border-ink bg-white"
      @submit.prevent="submit"
    >
      <div class="flex items-center justify-between gap-3 border-b border-ink px-4 py-2.5 font-mono text-[11px] tracking-[0.08em]">
        <span id="hm-up-h" class="font-bold">ADD DOCUMENTS</span>
        <button type="button" aria-label="Close" :disabled="sending" class="size-[26px] cursor-pointer border border-ink bg-white" @click="emit('close')">✕</button>
      </div>

      <div class="flex flex-col gap-[22px] p-5">
        <div class="flex flex-col gap-2">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="font-mono text-[11px] font-bold tracking-[0.08em]">1 · FILES AND TYPES</span>
            <label class="btn-hard relative inline-block bg-white px-3 py-[7px] text-[11.5px] tracking-[0.04em]">
              {{ rows.length ? 'Add more files' : 'Choose files' }}<input
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png,.webp,.xlsx,.xlsm,.csv,.txt"
                class="absolute size-px opacity-0"
                :disabled="sending"
                @change="onFiles"
              />
            </label>
          </div>
          <p class="m-0 text-sm leading-[1.4]">{{ helpText }}</p>

          <ul v-if="rows.length" class="m-0 flex list-none flex-col border border-ink p-0">
            <li
              v-for="r in rows"
              :key="r.id"
              class="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-ink/15 px-3 py-2 last:border-b-0"
            >
              <span class="min-w-0 flex-[1_1_200px] truncate font-mono text-[12.5px]" :title="r.file.name">{{ r.file.name }}</span>
              <select
                v-model="r.group"
                :aria-label="`Document type for ${r.file.name}`"
                :disabled="sending || r.state === 'done'"
                class="flex-[0_1_230px] border bg-white px-2 py-1.5 font-mono text-[11.5px]"
                :class="r.group ? 'border-ink' : 'border-reject text-reject'"
              >
                <option value="" disabled>Pick a type…</option>
                <option v-for="[key, label] in GROUP_INFO" :key="key" :value="key">
                  {{ label }}{{ r.detected === key ? ' (detected)' : '' }}
                </option>
              </select>
              <span
                v-if="STATE_LABEL[r.state]"
                class="font-mono text-[10px] font-bold"
                :class="r.state === 'failed' ? 'text-reject' : r.state === 'done' ? 'text-pass' : 'text-ink'"
              >{{ STATE_LABEL[r.state] }}</span>
              <button
                v-if="r.state !== 'done'"
                type="button"
                :aria-label="`Remove ${r.file.name}`"
                :disabled="sending"
                class="size-6 flex-none cursor-pointer border border-ink/30 bg-white font-mono text-[11px]"
                @click="remove(r)"
              >✕</button>
              <span v-if="r.error" class="basis-full font-mono text-[10.5px] text-reject">{{ r.error }}</span>
            </li>
          </ul>
          <span v-else class="border border-dashed border-ink px-3 py-2.5 font-mono text-[13px] text-faint">No files chosen</span>
        </div>

        <details class="flex flex-col gap-2">
          <summary class="cursor-pointer font-mono text-[11px] font-bold tracking-[0.08em]">2 · TYPE GUIDE</summary>
          <dl class="m-0 mt-2 flex flex-col gap-1.5">
            <div v-for="[key, label, desc] in GROUP_INFO" :key="key" class="flex flex-col">
              <dt class="text-[13.5px] font-bold">{{ label }}</dt>
              <dd class="m-0 text-[13px] leading-[1.35] text-muted">{{ desc }}</dd>
            </div>
          </dl>
        </details>

        <div class="flex flex-col gap-2">
          <span class="font-mono text-[11px] font-bold tracking-[0.08em]">3 · EVIDENCE FOR (OPTIONAL)</span>
          <p class="m-0 text-[13.5px] leading-[1.4] text-muted">Linking tells the rule check which open item these files should clear.</p>
          <div role="radiogroup" aria-label="Evidence for" class="flex flex-wrap gap-1.5">
            <button
              v-for="id in ['', ...openKeys]"
              :key="id"
              type="button"
              role="radio"
              :aria-checked="upload.link === id"
              :disabled="sending"
              class="cursor-pointer border border-ink px-2.5 py-1.5 font-mono text-xs font-bold"
              :class="upload.link === id ? 'bg-ink text-paper' : 'bg-white'"
              @click="upload.link = id"
            >{{ id || 'None' }}</button>
          </div>
        </div>
      </div>

      <p v-if="signed" role="note" class="m-0 border-t border-ink bg-signal/15 px-4 py-2.5 font-read text-[13.5px] leading-snug">
        <b>This project is signed.</b> Adding documents makes the current signature outdated; it stays on record and
        the report has to be signed again.
      </p>
      <div class="flex justify-end gap-2 border-t border-ink px-4 py-3">
        <button type="button" :disabled="sending" class="btn-hard bg-white px-3 py-[7px] text-[11.5px] tracking-[0.04em]" @click="emit('close')">Cancel</button>
        <button type="submit" :disabled="!canAdd" class="btn-hard bg-signal px-3 py-[7px] text-[11.5px] tracking-[0.04em]">
          {{ submitLabel }}
        </button>
      </div>
    </form>
  </div>
</template>
