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
  <section id="contact" aria-labelledby="con-h" class="wrap py-[clamp(64px,10vw,140px)]">
    <div class="flex flex-col items-center gap-6 rounded-2xl bg-graphite px-[clamp(20px,5vw,64px)] py-[clamp(48px,7vw,88px)] text-center text-paper">
      <SectionLabel label="Get started" />
      <h2 id="con-h" class="h-section max-w-[680px] text-balance">See Hibanako on one of your own documents.</h2>
      <p class="m-0 max-w-[520px] text-[17px] leading-[1.55] text-paper/75">
        Send us a recent document package and we'll walk your quality team through the verdict, the gaps and the evidence in a
        30-minute session.
      </p>

      <form class="flex w-full max-w-[520px] flex-wrap gap-3 pt-2" @submit.prevent="onSubmit">
        <label class="sr-only" for="demo-email">Work email</label>
        <input
          id="demo-email"
          v-model="email"
          type="email"
          name="email"
          required
          placeholder="Work email"
          class="min-w-0 flex-[1_1_240px] rounded-lg border border-paper/20 bg-paper/10 px-4 py-3.5 text-[15px] text-paper outline-none placeholder:text-paper/50 focus:border-signal"
        />
        <button type="submit" class="btn-cta flex-[1_0_auto]">Request a demo</button>
      </form>

      <p v-if="submitted" role="status" class="m-0 text-sm font-semibold text-paper">
        Thanks, we've received your request and will reply within one working day.
      </p>
      <p v-else class="m-0 text-[13px] text-paper/55">
        We use your email only to arrange the demo. See our
        <RouterLink to="/privacy" class="text-paper/80 underline-offset-[3px]">Privacy policy</RouterLink>.
      </p>
    </div>
  </section>
</template>
