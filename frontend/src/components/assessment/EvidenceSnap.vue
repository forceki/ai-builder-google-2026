<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { api } from '../../api/client'

// One evidence crop: the part of the source page a finding points at. Spreadsheets have no page image, so they
// show the label only. `paper` keeps print colours for the formal report.
const props = defineProps({
  projectNo: { type: String, required: true },
  evidence: { type: Object, required: true }, // { file, page, box, label }
  paper: { type: Boolean, default: false },
})

const url = ref(null)
const failed = ref('')
const isSheet = (name) => /\.(xlsx|xlsm|csv)$/i.test(name)

watch(
  () => [props.projectNo, props.evidence.file, props.evidence.page, String(props.evidence.box)],
  async () => {
    if (url.value) URL.revokeObjectURL(url.value)
    url.value = null
    failed.value = ''
    if (isSheet(props.evidence.file)) return
    try {
      url.value = await api.assessment.snapshot(props.projectNo, props.evidence)
    } catch (e) {
      failed.value = e.message || 'Request failed'
    }
  },
  { immediate: true },
)
onBeforeUnmount(() => url.value && URL.revokeObjectURL(url.value))
</script>

<template>
  <figure class="m-0 flex min-w-0 flex-col gap-1">
    <a v-if="url" :href="url" target="_blank" rel="noopener" class="block" :title="`Open ${evidence.file} p.${evidence.page}`">
      <img
        :src="url"
        :alt="`${evidence.label || evidence.file}, page ${evidence.page}`"
        class="block max-h-40 max-w-full border object-contain object-left-top"
        :class="paper ? 'border-(--r-line) bg-white' : 'border-ink/25 bg-white'"
      />
    </a>
    <div
      v-else
      class="flex min-h-10 items-center border border-dashed px-2.5 py-1 font-mono text-[10.5px]"
      :class="[paper ? 'border-(--r-line) text-(--r-muted)' : 'border-ink/25 text-faint', failed ? 'text-reject' : '']"
    >{{ isSheet(evidence.file) ? 'Spreadsheet: no page image' : failed ? `Preview failed: ${failed}` : 'Loading…' }}</div>
    <figcaption class="font-mono text-[10px] leading-snug" :class="paper ? 'text-(--r-sub)' : 'text-faint'">
      {{ evidence.label ? `${evidence.label} · ` : '' }}{{ evidence.file }} p.{{ evidence.page }}
    </figcaption>
  </figure>
</template>
