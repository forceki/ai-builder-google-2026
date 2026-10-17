<script setup>
import { nextTick, onBeforeUnmount, ref } from 'vue'

defineProps({
  label: { type: String, required: true },
  items: { type: Array, required: true },
})

const ICONS = {
  open: ['M14 4h6v6', 'M20 4l-9 9', 'M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5'],
  trash: ['M4 7h16', 'M10 11v6', 'M14 11v6', 'M6 7l1 13h10l1-13', 'M9 7V4h6v3'],
}

const open = ref(false)
const root = ref(null)
const menu = ref(null)

const onOutside = (e) => {
  if (!root.value?.contains(e.target)) close()
}
const onKey = (e) => {
  if (e.key === 'Escape') {
    close()
    root.value?.querySelector('button')?.focus()
  }
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    const els = [...(menu.value?.querySelectorAll('[role="menuitem"]:not(:disabled)') ?? [])]
    const i = els.indexOf(document.activeElement) + (e.key === 'ArrowDown' ? 1 : -1)
    els[(i + els.length) % els.length]?.focus()
  }
}

function close() {
  open.value = false
  document.removeEventListener('pointerdown', onOutside)
  document.removeEventListener('keydown', onKey)
}

function toggle() {
  if (open.value) return close()
  open.value = true
  document.addEventListener('pointerdown', onOutside)
  document.addEventListener('keydown', onKey)
  nextTick(() => menu.value?.querySelector('[role="menuitem"]:not(:disabled)')?.focus())
}

function choose(item) {
  close()
  item.action()
}

onBeforeUnmount(close)
</script>

<template>
  <span ref="root" class="relative inline-flex">
    <button
      type="button"
      :aria-label="label"
      aria-haspopup="menu"
      :aria-expanded="open"
      class="flex size-6 cursor-pointer items-center justify-center border bg-white font-mono text-sm leading-none"
      :class="open ? 'border-ink text-ink' : 'border-transparent text-muted hover:border-ink/30 hover:text-ink'"
      @click.stop="toggle"
    >⋮</button>
    <span
      v-if="open"
      ref="menu"
      role="menu"
      :aria-label="label"
      class="absolute top-full right-0 z-30 mt-1 flex min-w-[150px] flex-col border border-ink bg-white py-1 shadow-[3px_3px_0_rgb(var(--shade)/0.15)]"
    >
      <button
        v-for="item in items"
        :key="item.label"
        type="button"
        role="menuitem"
        :disabled="item.disabled"
        :title="item.title"
        class="flex cursor-pointer items-center gap-2.5 px-3 py-[7px] text-left font-mono text-[11.5px] outline-none hover:bg-paper focus-visible:bg-paper disabled:cursor-not-allowed disabled:opacity-40"
        :class="item.danger ? 'text-reject' : 'text-ink'"
        @click.stop="choose(item)"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path v-for="d in ICONS[item.icon]" :key="d" :d="d" />
        </svg>
        {{ item.label }}
      </button>
    </span>
  </span>
</template>
