<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { useMotion } from '../composables/useMotion'
import SiteHeader from '../components/sections/SiteHeader.vue'
import HeroSection from '../components/sections/HeroSection.vue'
import ProblemSection from '../components/sections/ProblemSection.vue'
import ProcessSection from '../components/sections/ProcessSection.vue'
import ChecksSection from '../components/sections/ChecksSection.vue'
import CoverageSection from '../components/sections/CoverageSection.vue'
import ReportSection from '../components/sections/ReportSection.vue'
import PrinciplesSection from '../components/sections/PrinciplesSection.vue'
import ContactSection from '../components/sections/ContactSection.vue'
import SiteFooter from '../components/sections/SiteFooter.vue'
import TraceBackground from '../components/sections/TraceBackground.vue'

useMotion()

// The landing page sits on a neutral near-white; app pages keep the warm paper.
onMounted(() => document.documentElement.setAttribute('data-page', 'landing'))
onBeforeUnmount(() => document.documentElement.removeAttribute('data-page'))
</script>

<template>
  <TraceBackground />
  <div class="relative z-[1] min-h-screen font-sans text-ink">
    <SiteHeader />
    <main>
      <HeroSection />
      <ProblemSection />
      <ProcessSection />
      <ChecksSection />
      <CoverageSection />
      <ReportSection />
      <PrinciplesSection />
      <ContactSection />
    </main>
    <SiteFooter />
  </div>
</template>
