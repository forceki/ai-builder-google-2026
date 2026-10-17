<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  confirmLabel: { type: String, default: 'Delete' },
  action: { type: Function, required: true },
})
const emit = defineEmits(['close'])

const busy = ref(false)
const error = ref('')
const cancelBtn = ref(null)

const confirm = async () => {
  busy.value = true
  error.value = ''
  try {
    await props.action()
    emit('close')
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

const onKey = (e) => e.key === 'Escape' && !busy.value && emit('close')
onMounted(() => {
  window.addEventListener('keydown', onKey)
  cancelBtn.value?.focus()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div
    role="alertdialog"
    aria-modal="true"
    aria-labelledby="hm-confirm-h"
    aria-describedby="hm-confirm-body"
    class="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 p-5"
    @click.self="!busy && emit('close')"
  >
    <div class="flex w-full max-w-[460px] flex-col border border-ink bg-white">
      <div class="flex items-center gap-2 border-b border-ink bg-reject px-4 py-2.5 font-mono text-[11px] font-bold tracking-[0.08em] text-[#fff]">
        <span aria-hidden="true">!</span><span id="hm-confirm-h">{{ title }}</span>
      </div>
      <div id="hm-confirm-body" class="flex flex-col gap-3 p-5 text-[14.5px] leading-[1.45]">
        <slot />
        <p v-if="error" role="alert" class="m-0 border border-reject px-3 py-2 font-mono text-xs text-reject">{{ error }}</p>
      </div>
      <div class="flex justify-end gap-2 border-t border-ink px-4 py-3">
        <button ref="cancelBtn" type="button" :disabled="busy" class="btn-hard bg-white px-3 py-[7px] text-[11.5px] tracking-[0.04em]" @click="emit('close')">
          Cancel
        </button>
        <button type="button" :disabled="busy" class="btn-hard bg-reject px-3 py-[7px] text-[11.5px] tracking-[0.04em] text-[#fff]" @click="confirm">
          {{ busy ? 'Deleting…' : confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>
