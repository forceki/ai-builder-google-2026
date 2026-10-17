<script setup>
import SectionLabel from '../ui/SectionLabel.vue'

const principles = [
  { title: 'Rules decide.', text: 'Pass, hold and reject come from deterministic rules you can read and audit; the AI only explains the result.' },
  { title: 'Every finding has a source.', text: 'Each finding links to the document and page it came from.' },
  { title: 'Engineers sign off.', text: 'Hibanako prepares the release decision. A qualified engineer makes it.' },
]
</script>

<template>
  <section id="principles" aria-labelledby="pri-h" class="bg-graphite text-paper">
    <div class="wrap flex flex-col gap-[clamp(40px,5vw,64px)] py-[clamp(64px,9vw,120px)]">
      <SectionLabel num="08" label="PRINCIPLES" label-id="pri-h" inverted />
      <div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,260px),1fr))] gap-x-[clamp(32px,4vw,64px)] gap-y-12">
        <div v-for="p in principles" :key="p.title" data-reveal class="flex flex-col gap-[18px]">
          <span aria-hidden="true" class="size-2.5 rounded-full bg-signal"></span>
          <h3 class="m-0 text-[clamp(28px,3vw,40px)] leading-none font-extrabold tracking-[-0.03em]">{{ p.title }}</h3>
          <p class="m-0 text-[17px] leading-[1.45] text-paper/85">{{ p.text }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
