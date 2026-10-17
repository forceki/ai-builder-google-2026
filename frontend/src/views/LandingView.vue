<script setup>
import { useMotion } from '../composables/useMotion'
import SiteHeader from '../components/sections/SiteHeader.vue'
import HeroSection from '../components/sections/HeroSection.vue'
import ProblemSection from '../components/sections/ProblemSection.vue'
import ProcessSection from '../components/sections/ProcessSection.vue'
import ChecksSection from '../components/sections/ChecksSection.vue'
import AiSection from '../components/sections/AiSection.vue'
import ReportSection from '../components/sections/ReportSection.vue'
import PrinciplesSection from '../components/sections/PrinciplesSection.vue'
import ContactSection from '../components/sections/ContactSection.vue'
import SiteFooter from '../components/sections/SiteFooter.vue'

useMotion()
</script>

<template>
  <div class="min-h-screen bg-paper font-sans text-ink">
    <SiteHeader />
    <main>
      <HeroSection />
      <ProblemSection />
      <ProcessSection />
      <ChecksSection />
      <AiSection />
      <ReportSection />
      <PrinciplesSection />
      <ContactSection />
    </main>
    <SiteFooter />
  </div>
</template>
