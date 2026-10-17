<script setup>
import { inject } from 'vue'

const openUpload = inject('openUpload')
const draw = (delay) => ({ strokeDasharray: 1, animation: `hm-draw 1.4s ${delay}s ease-out both` })
</script>

<template>
  <div class="bg-grid flex min-h-0 flex-1 flex-col items-center justify-center gap-6 overflow-auto px-6 py-10 text-center">
    <svg aria-hidden="true" viewBox="20 90 420 330" class="h-auto w-full max-w-[480px]">
      <g fill="none" stroke-width="1.5" class="stroke-ink">
        <rect x="60" y="330" width="360" height="26" pathLength="1" :style="draw(0)" />
        <rect x="100" y="110" width="24" height="220" pathLength="1" :style="draw(0.1)" />
        <polygon points="124,330 124,196 270,330" pathLength="1" :style="draw(0.2)" />
        <rect x="124" y="132" width="196" height="36" pathLength="1" :style="draw(0.3)" />
        <rect x="320" y="112" width="18" height="76" pathLength="1" :style="draw(0.4)" />
        <circle cx="112" cy="250" r="5" /><circle cx="112" cy="290" r="5" />
      </g>
      <g class="fill-ink">
        <polygon points="124,132 124,122 134,132" /><polygon points="124,168 124,178 134,168" />
        <polygon points="124,330 124,320 134,330" /><polygon points="100,330 100,320 90,330" />
      </g>
      <g stroke-width="0.8" fill="none" class="stroke-ink">
        <line x1="84" y1="150" x2="356" y2="150" stroke-dasharray="14 3 2 3" />
        <line x1="60" y1="362" x2="60" y2="402" /><line x1="420" y1="362" x2="420" y2="402" />
        <line x1="60" y1="396" x2="420" y2="396" />
      </g>
      <text x="240" y="390" text-anchor="middle" font-size="12" font-family="JetBrains Mono, monospace" class="fill-ink">360</text>
    </svg>
    <h2 class="m-0 max-w-[480px] text-[30px] leading-[1.05] font-extrabold tracking-[-0.03em] text-balance">
      Start by uploading your certificates and weld records.
    </h2>
    <p class="m-0 font-mono text-[11px] tracking-[0.06em] text-faint">MTC · WPS / PQR · WELD LOGS · NDT · ITP · TRAVELERS</p>
    <button
      type="button"
      class="btn-hard flex items-center gap-2.5 border-b-4 bg-signal px-5 py-3 text-[13px] tracking-[0.06em] uppercase"
      @click="openUpload()"
    >
      <span aria-hidden="true" class="size-2 bg-ink"></span>Browse files
    </button>
  </div>
</template>
