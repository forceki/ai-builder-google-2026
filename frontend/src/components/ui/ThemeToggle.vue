<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()
const dark = computed(() => store.state.theme.dark)
const label = computed(() => store.getters['theme/label'])
const toggle = () => store.dispatch('theme/toggle')
</script>

<template>
  <button
    type="button"
    :aria-pressed="dark"
    aria-label="Toggle dark mode"
    class="flex cursor-pointer items-center gap-1.5 rounded-[3px] border border-ink bg-transparent px-2.5 py-[7px] font-mono text-[11px] font-bold tracking-[0.06em]"
    @click="toggle"
  >
    <span aria-hidden="true" class="size-2.5 rounded-full border border-ink bg-[linear-gradient(90deg,#111111_50%,transparent_50%)]"></span>
    {{ label }}
  </button>
</template>
