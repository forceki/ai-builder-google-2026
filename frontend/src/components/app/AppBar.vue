<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import BrandStamp from '../ui/BrandStamp.vue'
import ThemeToggle from '../ui/ThemeToggle.vue'

defineProps({
  title: { type: String, default: '' },
  avatar: { type: Boolean, default: true },
})

const store = useStore()
const router = useRouter()
const user = computed(() => store.state.auth.user)
const initials = computed(() => store.getters['auth/initials'] || '··')

const signOut = () => {
  store.dispatch('auth/signOut')
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="flex flex-wrap items-center gap-x-5 gap-y-2.5 border-b border-ink bg-paper px-4 py-2">
    <RouterLink to="/" class="flex flex-none items-center gap-2 no-underline" aria-label="Hibanako home">
      <BrandStamp class="size-8" />
      <span class="text-xl leading-none font-black tracking-[0.06em] [font-stretch:115%]">HIBANAKO</span>
    </RouterLink>
    <span aria-hidden="true" class="-mx-2 font-mono text-[11px] text-faint">/</span>
    <slot name="title">
      <span class="flex-[1_1_160px] font-mono text-[11px] font-bold tracking-[0.06em]">{{ title }}</span>
    </slot>
    <div class="flex flex-none flex-wrap items-center gap-2">
      <slot name="status" />
      <ThemeToggle />
      <slot name="actions" />
      <template v-if="avatar">
        <span
          :title="user ? `${user.name}, ${user.role} (${user.email})` : ''"
          class="flex size-8 items-center justify-center bg-ink font-mono text-xs font-bold text-paper"
        >{{ initials }}</span>
        <button
          type="button"
          class="btn-hard bg-white px-2.5 py-1.5 text-[11px] tracking-[0.06em] uppercase"
          @click="signOut"
        >Sign out</button>
      </template>
    </div>
  </header>
</template>
