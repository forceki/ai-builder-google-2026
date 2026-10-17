<script setup>
import SectionLabel from '../ui/SectionLabel.vue'

const columns = [
  { head: 'AI DOES', dark: true, items: ['Reads documents', 'Extracts data', 'Explains findings', 'Suggests next steps'] },
  { head: 'RULES DO', items: ['Decide PASS / HOLD / REJECT based on your procedures and requirements'] },
  { head: 'ENGINEERS DO', items: ['Review evidence', 'Resolve issues', 'Sign off the release'] },
]
</script>

<template>
  <section id="ai" aria-labelledby="ai-h" class="wrap flex flex-col gap-[clamp(32px,4vw,48px)] pb-[clamp(64px,10vw,140px)]">
    <div class="flex max-w-[640px] flex-col gap-6">
      <SectionLabel num="06" label="WHERE AI FITS" />
      <h2 id="ai-h" class="h-section">Where AI fits.</h2>
    </div>
    <div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,220px),1fr))] overflow-hidden rounded border border-ink/25 bg-white">
      <div
        v-for="col in columns"
        :key="col.head"
        data-reveal
        class="-mr-px -mb-px flex flex-col border-r border-b border-ink/25"
      >
        <div
          class="flex items-center gap-2.5 px-5 py-3 font-mono text-xs font-bold tracking-[0.08em]"
          :class="col.dark ? 'bg-ink text-paper' : 'bg-panel text-ink'"
        >
          <span aria-hidden="true" class="size-2 rounded-full" :class="col.dark ? 'bg-paper' : 'bg-ink'"></span>{{ col.head }}
        </div>
        <ul class="m-0 flex list-none flex-col px-5 pt-2 pb-5">
          <li v-for="item in col.items" :key="item" class="border-b border-dashed border-ink/30 py-3 text-[17px] leading-[1.4]">
            {{ item }}
          </li>
        </ul>
      </div>
    </div>
    <p class="m-0 font-mono text-xs leading-relaxed">AI never approves a release. It does the reading so engineers can do the deciding.</p>
  </section>
</template>
