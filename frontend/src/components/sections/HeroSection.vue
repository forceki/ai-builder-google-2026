<script setup>
import SectionLabel from '../ui/SectionLabel.vue'
import StatusDot from '../ui/StatusDot.vue'
import PanelBolts from '../ui/PanelBolts.vue'
import TraceDrawing from './TraceDrawing.vue'
</script>

<template>
  <section
    id="top"
    aria-labelledby="hero-h"
    class="wrap flex flex-wrap items-center gap-[clamp(40px,5vw,72px)] pt-[clamp(40px,7vw,96px)] pb-[clamp(64px,10vw,140px)]"
  >
    <div class="flex min-w-0 flex-[1_1_420px] flex-col gap-7">
      <SectionLabel num="02" label="OVERVIEW" />
      <h1 id="hero-h" class="m-0 text-[clamp(48px,7vw,104px)] leading-[0.92] font-extrabold tracking-[-0.045em] text-balance">
        Every weld, every cert, one thread.
      </h1>
      <p data-reveal class="m-0 max-w-[480px] text-[clamp(17px,1.5vw,20px)] leading-[1.45] text-pretty">
        Heatmark uses AI to read your material certificates, weld records and inspection reports, connects them into one
        traceable thread, and shows exactly what's missing before you release.
      </p>
      <div class="flex flex-wrap items-center gap-6 pt-2">
        <a href="#contact" class="btn-primary">
          <span aria-hidden="true" class="size-[9px] rounded-full bg-ink"></span>Request demo
        </a>
        <a href="#process" class="font-mono text-sm underline-offset-4">See the process →</a>
      </div>
      <span class="font-mono text-[11px] tracking-[0.08em] text-muted">
        AI EXTRACTION · RULE-BASED VERIFICATION · ENGINEER SIGN-OFF
      </span>
    </div>

    <figure
      class="relative m-0 min-w-0 flex-[1.25_1_520px] rounded border border-ink/18 bg-panel px-7 pt-7 pb-5 shadow-[inset_0_-3px_0_rgb(var(--shade)/0.1)]"
    >
      <PanelBolts />

      <div class="rounded-[3px] border border-ink/22 bg-white shadow-[inset_0_2px_0_rgb(var(--shade)/0.06)]">
        <TraceDrawing />
      </div>

      <div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-4 px-1.5 pt-[18px] pb-1 font-mono text-[11px] tracking-[0.06em]">
        <div class="flex items-center gap-[18px]">
          <span class="flex flex-col items-center gap-1.5"><StatusDot status="PASS" size="size-2.5" />PASS</span>
          <span class="flex flex-col items-center gap-1.5"><StatusDot status="HOLD" size="size-2.5" /><strong>HOLD</strong></span>
          <span class="flex flex-col items-center gap-1.5"><StatusDot status="PASS" size="size-2.5" />REJECT</span>
        </div>
        <figcaption class="flex-[1_1_200px] leading-normal text-muted">
          DWG HM-A-0021 · PIPE SUPPORT ASSY · 1:5<br />One part, traced from material heat to weld to inspection record.
        </figcaption>
        <span aria-hidden="true" class="flex items-center gap-2.5">
          <span class="relative block size-[38px] rounded-full border-[3px] border-pending bg-graphite">
            <span class="absolute top-1 left-[18px] h-[11px] w-0.5 origin-[1px_15px] rotate-40 rounded-[1px] bg-signal"></span>
          </span>
          TRACE
        </span>
      </div>
    </figure>
  </section>
</template>
