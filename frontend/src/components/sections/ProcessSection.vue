<script setup>
import SectionLabel from '../ui/SectionLabel.vue'

const steps = [
  { title: 'Upload', role: 'ENGINEER', text: 'Certificates, weld logs, NDT reports and production records. PDF or scan.' },
  { title: 'Extract', role: 'AI', text: 'Reads scanned and digital documents and pulls out heat numbers, weld IDs, procedures and inspection results, each linked to its source page.' },
  { title: 'Map', role: 'RULES', text: 'Material → part → weld → inspection, linked into one traceability map.' },
  { title: 'Verify', role: 'RULES', text: 'Deterministic rules check every link against your project requirements.' },
  { title: 'Explain', role: 'AI', text: 'Describes each issue in plain language and suggests the next verification step.' },
  { title: 'Report', role: 'ENGINEER', text: 'A ranked release-readiness report, ready for engineer sign-off.' },
]
</script>

<template>
  <section id="process" aria-labelledby="proc-h" class="bg-panel">
    <div class="wrap flex flex-col gap-[clamp(40px,5vw,64px)] py-[clamp(64px,9vw,120px)]">
      <div class="flex flex-wrap items-end justify-between gap-5">
        <div class="flex flex-col gap-6">
          <SectionLabel num="04" label="PROCESS" />
          <h2 id="proc-h" class="h-section">Six steps to release.</h2>
        </div>
        <span class="font-mono text-xs text-muted">FLOW: LEFT → RIGHT</span>
      </div>

      <ol class="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-y-10 p-0">
        <li
          v-for="(step, i) in steps"
          :key="step.title"
          data-reveal
          class="flex flex-col gap-3.5"
          :class="{ 'pr-5': i < steps.length - 1 }"
        >
          <div aria-hidden="true" class="flex items-center">
            <span
              class="flex size-14 flex-none items-center justify-center rounded font-mono text-base font-bold"
              :class="
                i === steps.length - 1
                  ? 'border border-ink bg-signal shadow-[inset_0_-4px_0_rgb(var(--shade)/0.3)]'
                  : 'border border-ink/30 bg-white shadow-[inset_0_-4px_0_rgb(var(--shade)/0.14)]'
              "
            >{{ String(i + 1).padStart(2, '0') }}</span>
            <span v-if="i < steps.length - 1" class="h-px flex-1 bg-ink"></span>
          </div>
          <div class="flex flex-wrap items-center gap-2.5">
            <h3 class="m-0 text-[22px] font-extrabold tracking-[-0.02em]">{{ step.title }}</h3>
            <span
              class="border border-ink px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-[0.08em]"
              :class="{ 'bg-ink text-paper': step.role === 'AI' }"
            >{{ step.role }}</span>
          </div>
          <p class="m-0 text-[15px] leading-[1.45]">{{ step.text }}</p>
        </li>
      </ol>
    </div>
  </section>
</template>
