<script setup>
import { computed } from 'vue'
import BrandMark from '../components/ui/BrandMark.vue'
import ThemeToggle from '../components/ui/ThemeToggle.vue'
import PoweredBy from '../components/ui/PoweredBy.vue'
import { EFFECTIVE_DATE, PRIVACY, TERMS } from '../data/legal'

const props = defineProps({
  doc: { type: String, required: true }, // terms | privacy
})

const page = computed(() => (props.doc === 'privacy' ? PRIVACY : TERMS))
const other = computed(() =>
  props.doc === 'privacy' ? { to: '/terms', label: 'Terms and conditions' } : { to: '/privacy', label: 'Privacy policy' },
)
const anchor = (i) => `s-${String(i + 1).padStart(2, '0')}`
</script>

<template>
  <div class="flex min-h-screen flex-col bg-paper font-sans text-ink">
    <header data-noprint class="wrap box-border flex w-full flex-wrap items-center justify-between gap-4 py-5">
      <BrandMark />
      <div class="flex items-center gap-4">
        <ThemeToggle />
        <RouterLink to="/" class="font-mono text-[13px] underline-offset-4">← Back to site</RouterLink>
      </div>
    </header>

    <main class="flex-1 px-[clamp(12px,3vw,32px)] pb-[clamp(32px,6vw,80px)]">
      <article :aria-labelledby="`${doc}-h`" class="mx-auto max-w-[920px] border border-ink bg-white">
        <div class="flex flex-wrap items-end justify-between gap-5 border-b-2 border-ink px-[clamp(20px,4vw,40px)] pt-7 pb-6">
          <div class="flex max-w-[620px] flex-col gap-3">
            <span class="font-mono text-[11px] tracking-[0.08em] text-faint">HIBANAKO · FORM {{ page.form }} · REV. A</span>
            <h1 :id="`${doc}-h`" class="m-0 text-[clamp(32px,4.5vw,52px)] leading-[0.95] font-extrabold tracking-[-0.035em]">
              {{ page.title }}
            </h1>
            <p class="m-0 text-base leading-normal">{{ page.lead }}</p>
          </div>
          <dl class="m-0 flex flex-col gap-1 font-mono">
            <dt class="text-[10px] tracking-[0.08em] text-faint">EFFECTIVE</dt>
            <dd class="m-0 text-[13px] font-bold">{{ EFFECTIVE_DATE }}</dd>
          </dl>
        </div>

        <p class="m-0 flex items-center gap-2.5 border-b border-ink bg-signal px-[clamp(20px,4vw,40px)] py-2.5 font-mono text-[11px] font-bold tracking-[0.06em]">
          <span aria-hidden="true" class="size-2 flex-none bg-ink"></span>
          DRAFT · ITEMS IN [BRACKETS] ARE TO BE COMPLETED · REVIEW WITH COUNSEL BEFORE PUBLISHING
        </p>

        <nav aria-label="Sections" class="border-b border-ink px-[clamp(20px,4vw,40px)] py-5">
          <h2 class="m-0 mb-3 font-mono text-xs tracking-[0.08em]">CONTENTS</h2>
          <ol class="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-x-6 gap-y-1.5 p-0 font-mono text-[12.5px]">
            <li v-for="(s, i) in page.sections" :key="s.title" class="flex gap-2.5">
              <span class="text-faint">{{ String(i + 1).padStart(2, '0') }}</span>
              <a :href="`#${anchor(i)}`" class="underline-offset-[3px]">{{ s.title }}</a>
            </li>
          </ol>
        </nav>

        <section
          v-for="(s, i) in page.sections"
          :id="anchor(i)"
          :key="s.title"
          class="grid scroll-mt-4 grid-cols-[48px_minmax(0,1fr)] gap-x-4 border-b border-ink px-[clamp(20px,4vw,40px)] py-6 break-inside-avoid last:border-b-0"
        >
          <span class="pt-1 font-mono text-[13px] font-bold">{{ String(i + 1).padStart(2, '0') }}</span>
          <div class="flex max-w-[680px] flex-col gap-3">
            <h2 class="m-0 text-[22px] font-extrabold tracking-[-0.02em]">{{ s.title }}</h2>
            <ul v-if="s.list" class="m-0 flex list-none flex-col gap-2 p-0">
              <li v-for="item in s.list" :key="item" class="flex gap-3 text-[15px] leading-normal">
                <span aria-hidden="true" class="mt-[9px] size-1.5 flex-none bg-ink"></span>{{ item }}
              </li>
            </ul>
            <p v-for="para in s.body || []" :key="para" class="m-0 text-[15px] leading-[1.55]">{{ para }}</p>
          </div>
        </section>

        <div class="flex flex-wrap justify-between gap-2 border-t-2 border-ink px-[clamp(20px,4vw,40px)] py-2.5 font-mono text-[10.5px] tracking-[0.06em] text-muted">
          <span>HIBANAKO · {{ page.form }} · REV. A</span>
          <RouterLink :to="other.to" class="text-muted underline-offset-[3px]">{{ other.label }} →</RouterLink>
        </div>
      </article>
    </main>

    <footer class="border-t border-ink font-mono text-xs">
      <div class="wrap flex flex-wrap items-center justify-between gap-4 py-[18px] text-muted">
        <span>© 2026 HIBANAKO</span>
        <PoweredBy />
      </div>
    </footer>
  </div>
</template>
