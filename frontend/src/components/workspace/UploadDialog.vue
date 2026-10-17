<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useStore } from 'vuex'
import { GROUP_INFO, guess } from '../../data/workspace'

// v-model: { file: File | null, group, detected, link }
const upload = defineModel({ type: Object, required: true })
const emit = defineEmits(['close'])

const store = useStore()
const openKeys = computed(() => store.getters['workspace/openKeys'])
const sending = ref(false)
const error = ref('')
const canAdd = computed(() => upload.value.file && upload.value.group && !sending.value)

const detectText = computed(() =>
  !upload.value.file
    ? 'Choose a file first. We suggest a type from the file name.'
    : upload.value.detected
      ? 'We suggest this type from the file name. Change it if it is wrong.'
      : "We couldn't tell the type from the file name. Pick one.",
)

const onFile = (e) => {
  const f = e.target.files?.[0]
  if (!f) return
  const g = guess(f.name)
  upload.value = { ...upload.value, file: f, detected: g, group: g || upload.value.group }
}

const submit = async () => {
  if (!canAdd.value) return
  sending.value = true
  error.value = ''
  try {
    const { file, group, link } = upload.value
    await store.dispatch('workspace/upload', { file, docType: group, evidenceFor: link || undefined })
    emit('close')
  } catch (e) {
    error.value = e.message
  } finally {
    sending.value = false
  }
}

const onKey = (e) => e.key === 'Escape' && emit('close')
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div
    role="dialog"
    aria-modal="true"
    aria-labelledby="hm-up-h"
    class="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 p-5"
    @click.self="emit('close')"
  >
    <form
      class="flex max-h-[calc(100vh-40px)] w-full max-w-[580px] flex-col overflow-auto border border-ink bg-white"
      @submit.prevent="submit"
    >
      <div class="flex items-center justify-between gap-3 border-b border-ink px-4 py-2.5 font-mono text-[11px] tracking-[0.08em]">
        <span id="hm-up-h" class="font-bold">ADD DOCUMENT</span>
        <button type="button" aria-label="Close" class="size-[26px] cursor-pointer border border-ink bg-white" @click="emit('close')">✕</button>
      </div>

      <div class="flex flex-col gap-[22px] p-5">
        <div class="flex flex-col gap-2">
          <span class="font-mono text-[11px] font-bold tracking-[0.08em]">1 · FILE</span>
          <div class="flex flex-wrap items-center gap-2">
            <span class="flex-[1_1_220px] border border-dashed border-ink px-3 py-2.5 font-mono text-[13px]" :class="upload.file ? 'text-ink' : 'text-faint'">
              {{ upload.file?.name || 'No file chosen' }}
            </span>
            <label class="btn-hard relative inline-block bg-white px-3 py-[7px] text-[11.5px] tracking-[0.04em]">
              Choose file<input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp,.xlsx,.xlsm,.csv,.txt"
                class="absolute size-px opacity-0"
                @change="onFile"
              />
            </label>
          </div>
        </div>

        <fieldset class="m-0 flex flex-col gap-2 border-0 p-0">
          <legend class="pb-2 font-mono text-[11px] font-bold tracking-[0.08em]">2 · DOCUMENT TYPE</legend>
          <p class="m-0 mb-1 text-sm leading-[1.4]">{{ detectText }}</p>
          <label
            v-for="[key, label, desc] in GROUP_INFO"
            :key="key"
            class="flex cursor-pointer items-start gap-3 border px-3 py-2.5"
            :class="upload.group === key ? 'border-ink bg-paper' : 'border-pending bg-white'"
          >
            <input v-model="upload.group" type="radio" name="hm-doctype" :value="key" class="mt-[3px] accent-ink" />
            <span class="flex flex-1 flex-col gap-0.5">
              <span class="text-[14.5px] font-bold">{{ label }}</span>
              <span class="text-[13px] leading-[1.35] text-muted">{{ desc }}</span>
            </span>
            <span v-if="upload.detected === key" class="flex-none border border-ink px-1.5 py-px font-mono text-[10px] font-bold">DETECTED</span>
          </label>
        </fieldset>

        <div class="flex flex-col gap-2">
          <span class="font-mono text-[11px] font-bold tracking-[0.08em]">3 · EVIDENCE FOR (OPTIONAL)</span>
          <p class="m-0 text-[13.5px] leading-[1.4] text-muted">Linking tells the rule check which open item this file should clear.</p>
          <div role="radiogroup" aria-label="Evidence for" class="flex flex-wrap gap-1.5">
            <button
              v-for="id in ['', ...openKeys]"
              :key="id"
              type="button"
              role="radio"
              :aria-checked="upload.link === id"
              class="cursor-pointer border border-ink px-2.5 py-1.5 font-mono text-xs font-bold"
              :class="upload.link === id ? 'bg-ink text-paper' : 'bg-white'"
              @click="upload.link = id"
            >{{ id || 'None' }}</button>
          </div>
        </div>

        <p v-if="error" role="alert" class="m-0 border border-reject px-3 py-2 font-mono text-xs text-reject">{{ error }}</p>
      </div>

      <div class="flex justify-end gap-2 border-t border-ink px-4 py-3">
        <button type="button" class="btn-hard bg-white px-3 py-[7px] text-[11.5px] tracking-[0.04em]" @click="emit('close')">Cancel</button>
        <button type="submit" :disabled="!canAdd" class="btn-hard bg-signal px-3 py-[7px] text-[11.5px] tracking-[0.04em]">
          {{ sending ? 'Uploading…' : 'Add document' }}
        </button>
      </div>
    </form>
  </div>
</template>
