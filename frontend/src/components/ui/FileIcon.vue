<script setup>
import { computed } from 'vue'

const props = defineProps({
  filename: { type: String, required: true },
})

const KINDS = {
  pdf: 'pdf',
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  webp: 'image',
  gif: 'image',
  xlsx: 'sheet',
  xlsm: 'sheet',
  xls: 'sheet',
  csv: 'sheet',
}
const ext = computed(() => (props.filename.includes('.') ? props.filename.split('.').pop().toLowerCase() : ''))
const kind = computed(() => KINDS[ext.value] ?? 'doc')
const label = computed(() => `${ext.value ? ext.value.toUpperCase() : 'Unknown'} file`)
</script>

<template>
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.6"
    stroke-linecap="round"
    stroke-linejoin="round"
    role="img"
    :aria-label="label"
  >
    <title>{{ label }}</title>
    <template v-if="kind === 'image'">
      <rect x="3" y="4.5" width="18" height="15" rx="1.5" />
      <circle cx="8.5" cy="9.5" r="1.7" />
      <path d="M3.5 17.5l5-5 3.5 3.5 2.5-2.5 6 5" />
    </template>
    <template v-else>
      <path d="M6 2.5h8.5l4.5 4.5v13.5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-17a1 1 0 0 1 1-1z" />
      <path d="M14.5 2.5V7H19" />
      <template v-if="kind === 'pdf'">
        <rect x="2.5" y="11.5" width="14" height="7.5" rx="1" fill="currentColor" stroke="none" />
        <text
          x="9.5"
          y="17.3"
          text-anchor="middle"
          font-size="5.4"
          font-weight="700"
          font-family="JetBrains Mono, monospace"
          stroke="none"
          class="fill-white"
        >PDF</text>
      </template>
      <template v-else-if="kind === 'sheet'">
        <rect x="7.5" y="10.5" width="9" height="8" fill="currentColor" fill-opacity="0.15" />
        <path d="M7.5 13.2h9M7.5 15.8h9M10.5 10.5v8M13.5 10.5v8" stroke-width="1.2" />
      </template>
      <path v-else d="M8 11.5h8M8 14.5h8M8 17.5h5" />
    </template>
  </svg>
</template>
