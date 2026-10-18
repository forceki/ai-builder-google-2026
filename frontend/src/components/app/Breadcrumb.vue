<script setup>
// items: [{ label, to? }] — the last item is the current page.
defineProps({
  items: { type: Array, required: true },
})
</script>

<template>
  <nav
    aria-label="Breadcrumb"
    class="min-w-0 flex-[1_1_200px] truncate font-mono text-[11px] tracking-[0.06em] text-faint"
  >
    <template v-for="(item, i) in items" :key="item.label">
      <template v-if="i > 0"> / </template>
      <RouterLink v-if="item.to" :to="item.to" class="text-ink underline underline-offset-[3px]">{{ item.label }}</RouterLink>
      <span v-else class="font-bold text-ink">{{ item.label }}</span>
    </template>
  </nav>
</template>
