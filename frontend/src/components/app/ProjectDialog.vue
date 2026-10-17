<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useStore } from 'vuex'

const props = defineProps({
  project: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved'])

const store = useStore()
const editing = computed(() => !!props.project)
const name = ref(props.project?.name ?? '')
const scope = ref(props.project?.scope === 'NOT SCOPED' ? '' : (props.project?.scope ?? ''))
const sending = ref(false)
const error = ref('')
const canSave = computed(() => name.value.trim() && !sending.value)

const submit = async () => {
  if (!canSave.value) return
  sending.value = true
  error.value = ''
  try {
    const data = { name: name.value.trim(), scope: scope.value.trim() || 'NOT SCOPED' }
    const row = editing.value
      ? await store.dispatch('projects/update', { no: props.project.no, ...data })
      : await store.dispatch('projects/create', data)
    emit('saved', row)
    emit('close')
  } catch (e) {
    error.value = e.message
  } finally {
    sending.value = false
  }
}

const nameInput = ref(null)
const onKey = (e) => e.key === 'Escape' && emit('close')
onMounted(() => {
  window.addEventListener('keydown', onKey)
  nameInput.value?.focus()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div
    role="dialog"
    aria-modal="true"
    aria-labelledby="hm-prj-h"
    class="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 p-5"
    @click.self="emit('close')"
  >
    <form
      class="flex max-h-[calc(100vh-40px)] w-full max-w-[480px] flex-col overflow-auto border border-ink bg-white"
      @submit.prevent="submit"
    >
      <div class="flex items-center justify-between gap-3 border-b border-ink px-4 py-2.5 font-mono text-[11px] tracking-[0.08em]">
        <span id="hm-prj-h" class="font-bold">{{ editing ? `RENAME ${project.no}` : 'NEW PROJECT' }}</span>
        <button type="button" aria-label="Close" class="size-[26px] cursor-pointer border border-ink bg-white" @click="emit('close')">✕</button>
      </div>

      <div class="flex flex-col gap-[18px] p-5">
        <label class="flex flex-col gap-2">
          <span class="font-mono text-[11px] font-bold tracking-[0.08em]">PROJECT NAME</span>
          <input
            ref="nameInput"
            v-model="name"
            type="text"
            required
            maxlength="200"
            placeholder="e.g. Crude unit spool 04"
            class="field"
          />
        </label>
        <label class="flex flex-col gap-2">
          <span class="font-mono text-[11px] font-bold tracking-[0.08em]">SCOPE (OPTIONAL)</span>
          <input v-model="scope" type="text" maxlength="200" placeholder="e.g. LOT 24-117 · 4 WELDS" class="field" />
          <span class="text-[13px] leading-[1.35] text-muted">Shown under the name in the project list.</span>
        </label>
        <p v-if="!editing" class="m-0 font-mono text-[11px] text-muted">The project number (HBK-…) is assigned automatically.</p>
        <p v-if="error" role="alert" class="m-0 border border-reject px-3 py-2 font-mono text-xs text-reject">{{ error }}</p>
      </div>

      <div class="flex justify-end gap-2 border-t border-ink px-4 py-3">
        <button type="button" class="btn-hard bg-white px-3 py-[7px] text-[11.5px] tracking-[0.04em]" @click="emit('close')">Cancel</button>
        <button type="submit" :disabled="!canSave" class="btn-hard bg-signal px-3 py-[7px] text-[11.5px] tracking-[0.04em]">
          {{ sending ? 'Saving…' : editing ? 'Save' : 'Create project' }}
        </button>
      </div>
    </form>
  </div>
</template>
