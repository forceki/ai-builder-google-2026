<script setup>
import { computed, ref } from 'vue'
import { useStore } from 'vuex'
import SectionLabel from '../ui/SectionLabel.vue'

const store = useStore()
const submitted = computed(() => store.state.demo.submitted)
const email = ref('')

const onSubmit = () => store.dispatch('demo/request', email.value)
</script>

<template>
  <section id="contact" aria-labelledby="con-h" class="wrap flex flex-col gap-[clamp(32px,5vw,56px)] py-[clamp(64px,10vw,140px)]">
    <SectionLabel num="09" label="CONTACT" />
    <h2 id="con-h" class="m-0 text-[clamp(56px,11vw,168px)] leading-[0.88] font-extrabold tracking-[-0.05em]">Ship with evidence.</h2>

    <form
      class="relative flex w-full max-w-[680px] flex-col gap-[18px] self-end rounded border border-ink/15 bg-panel px-[clamp(18px,3vw,32px)] py-7 shadow-[inset_0_-3px_0_rgb(var(--shade)/0.08)]"
      @submit.prevent="onSubmit"
    >
      <div class="flex justify-between gap-3 font-mono text-[11px] tracking-[0.08em] text-muted">
        <span>DEMO REQUEST</span><span>FORM HBK-DR-01</span>
      </div>
      <div class="flex flex-wrap items-end gap-3.5">
        <label class="flex flex-[1_1_280px] flex-col gap-2">
          <span class="font-mono text-[11px] text-muted">WORK EMAIL</span>
          <input
            v-model="email"
            type="email"
            name="email"
            required
            placeholder="name@company.com"
            class="field py-[15px]"
          />
        </label>
        <button type="submit" class="btn-primary">
          <span aria-hidden="true" class="size-[9px] rounded-full bg-ink"></span>Request demo
        </button>
      </div>
      <p class="m-0 font-mono text-[11px] leading-relaxed text-muted">
        We use your email only to arrange the demo. See the
        <RouterLink to="/privacy" class="text-ink underline-offset-[3px]">Privacy policy</RouterLink>.
      </p>
      <div v-if="submitted" role="status" class="flex items-center gap-3.5 font-mono text-xs">
        <span class="inline-block -rotate-3 rounded-[3px] border-2 border-ink px-2.5 py-1 font-bold tracking-[0.12em]">RECEIVED</span>
        <span>We'll reply within one working day.</span>
      </div>
    </form>
  </section>
</template>
