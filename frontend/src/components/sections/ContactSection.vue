<script setup>
import { computed, ref } from 'vue'
import { useStore } from 'vuex'
import SectionLabel from '../ui/SectionLabel.vue'

const store = useStore()
const submitted = computed(() => store.state.demo.submitted)
const sending = computed(() => store.state.demo.sending)
const error = computed(() => store.state.demo.error)
const email = ref('')
const website = ref('') // honeypot: hidden from people, filled by bots

const onSubmit = () => store.dispatch('demo/request', { email: email.value, website: website.value })
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

      <form v-if="!submitted" class="flex w-full max-w-[520px] flex-wrap gap-3 pt-2" @submit.prevent="onSubmit">
        <label class="sr-only" for="demo-email">Work email</label>
        <input
          id="demo-email"
          v-model="email"
          type="email"
          name="email"
          autocomplete="email"
          required
          maxlength="320"
          placeholder="Work email"
          :disabled="sending"
          :aria-invalid="!!error"
          :aria-describedby="error ? 'demo-error' : undefined"
          class="min-w-0 flex-[1_1_240px] rounded-lg border border-paper/20 bg-paper/10 px-4 py-3.5 text-[15px] text-paper outline-none placeholder:text-paper/50 focus:border-signal disabled:opacity-60"
        />
        <!-- Honeypot: off-screen and skipped by keyboard and screen readers; only bots fill it. -->
        <input v-model="website" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true" class="absolute -left-[9999px] size-px opacity-0" />
        <button type="submit" :disabled="sending" class="btn-cta flex-[1_0_auto] disabled:opacity-70">
          {{ sending ? 'Sending…' : 'Request a demo' }}
        </button>
      </form>

      <p v-if="error" id="demo-error" role="alert" class="m-0 text-sm font-semibold text-signal">{{ error }}</p>
      <div v-if="submitted" role="status" class="flex flex-col items-center gap-1.5 pt-2">
        <span class="text-[17px] font-semibold text-paper">Thanks, we've received your request.</span>
        <span class="text-sm text-paper/70">We'll reply to {{ store.state.demo.email }} within one working day to set up the session.</span>
      </div>
      <p v-else class="m-0 text-[13px] text-paper/55">
        We use your email only to arrange the demo. See our
        <RouterLink to="/privacy" class="text-paper/80 underline-offset-[3px]">Privacy policy</RouterLink>.
      </p>
    </div>
  </section>
</template>
