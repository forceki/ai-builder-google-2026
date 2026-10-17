<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from 'vuex'
import AppBar from '../components/app/AppBar.vue'
import AppFooter from '../components/app/AppFooter.vue'
import ConfirmDialog from '../components/app/ConfirmDialog.vue'
import ProjectDialog from '../components/app/ProjectDialog.vue'
import { RELEASE, STAGES, projectGroup } from '../store/modules/projects'

const store = useStore()
const router = useRouter()

const filter = ref('all')
const q = ref('')

const projects = computed(() => store.state.projects.list)
const loading = computed(() => store.state.projects.loading)
const error = computed(() => store.state.projects.error)
const dialog = ref(null)
const deleting = ref(null)

onMounted(() => store.dispatch('projects/fetchAll'))
const countBy = (k) => store.getters['projects/countBy'](k)

const filters = [
  { key: 'all', label: 'All' },
  { key: 'open', label: 'Open issues' },
  { key: 'ready', label: 'Ready' },
  { key: 'released', label: 'Released' },
]

const summary = computed(
  () =>
    `${countBy('all')} PROJECTS · ${countBy('open')} WITH OPEN ISSUES · ${countBy('ready')} READY FOR SIGN-OFF`,
)

const shown = computed(() => {
  const needle = q.value.trim().toLowerCase()
  return projects.value.filter(
    (p) =>
      (filter.value === 'all' || projectGroup(p) === filter.value) &&
      (!needle || `${p.no} ${p.name}`.toLowerCase().includes(needle)),
  )
})

const releaseStyle = {
  [RELEASE.NOT_READY]: { badge: 'border-reject bg-white text-reject', led: 'bg-reject' },
  [RELEASE.EXTRACTING]: { badge: 'border-ink bg-white text-ink', led: 'bg-signal' },
  [RELEASE.READY]: { badge: 'border-ink bg-signal text-ink', led: 'bg-ink' },
  [RELEASE.RELEASED]: { badge: 'border-pass bg-white text-pass', led: 'bg-pass' },
  [RELEASE.NO_DOCUMENTS]: { badge: 'border-pending bg-white text-muted', led: 'bg-pending' },
}

const released = (p) => p.release === RELEASE.RELEASED
const stageLabel = (p) => (released(p) ? 'DONE · RELEASED' : `${String(p.stage).padStart(2, '0')} ${STAGES[p.stage - 1]}`)
const segClass = (p, i) =>
  i + 1 < p.stage || released(p) ? 'bg-ink' : i + 1 === p.stage ? 'bg-signal' : 'bg-white'

const workspaceLink = (p) => `/projects/${p.no}`
const open = (p) => router.push(workspaceLink(p))
const onRowClick = (e, p) => {
  if (e.target.closest('a, button')) return
  open(p)
}

const newProject = () => (dialog.value = { project: null })
const renameProject = (p) => (dialog.value = { project: p })
const onSaved = () => {
  filter.value = 'all'
  q.value = ''
}
</script>

<template>
  <div class="flex min-h-screen flex-col bg-paper font-sans text-ink">
    <AppBar title="PROJECTS">
      <template #actions>
        <button
          type="button"
          class="btn-hard flex items-center gap-2 bg-signal px-3.5 py-2 text-xs tracking-[0.06em] uppercase"
          @click="newProject"
        >
          <span aria-hidden="true" class="size-[7px] bg-ink"></span>New project
        </button>
      </template>
    </AppBar>

    <main class="mx-auto box-border flex w-full max-w-[1320px] flex-1 flex-col gap-6 px-[clamp(16px,3vw,40px)] py-[clamp(24px,4vw,48px)]">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div class="flex flex-col gap-2.5">
          <span class="font-mono text-[11px] tracking-[0.08em] text-faint">SHEET 00 / PROJECT REGISTER</span>
          <h1 class="m-0 text-[clamp(36px,4.5vw,56px)] leading-[0.95] font-extrabold tracking-[-0.04em]">Projects</h1>
        </div>
        <span class="font-mono text-xs">{{ summary }}</span>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <div role="radiogroup" aria-label="Filter projects" class="flex border border-ink font-mono text-xs">
          <button
            v-for="(f, i) in filters"
            :key="f.key"
            type="button"
            role="radio"
            :aria-checked="filter === f.key"
            class="cursor-pointer px-3 py-2 whitespace-nowrap"
            :class="[filter === f.key ? 'bg-ink text-paper' : 'bg-white text-ink', { 'border-r border-ink': i < filters.length - 1 }]"
            @click="filter = f.key"
          >
            {{ f.label }} <span class="opacity-70">{{ countBy(f.key) }}</span>
          </button>
        </div>
        <label class="ml-auto flex h-[34px] max-w-[360px] flex-[1_1_240px] items-center gap-2 border border-ink bg-white px-2.5">
          <span aria-hidden="true" class="font-mono text-[11px] text-faint">FIND</span>
          <input
            v-model="q"
            type="search"
            aria-label="Find project"
            placeholder="Project no. or name"
            class="min-w-0 flex-1 border-0 bg-transparent font-mono text-[12.5px] outline-none"
          />
        </label>
      </div>

      <div class="overflow-x-auto border border-ink bg-white">
        <table class="w-full min-w-[880px] border-collapse">
          <thead>
            <tr class="bg-ink text-left font-mono text-[10.5px] tracking-[0.08em] text-paper">
              <th scope="col" class="px-4 py-2.5 font-bold">PROJECT</th>
              <th scope="col" class="px-3 py-2.5 font-bold">STAGE</th>
              <th scope="col" class="px-3 py-2.5 font-bold">DOCS</th>
              <th scope="col" class="px-3 py-2.5 font-bold">CHECKS</th>
              <th scope="col" class="px-3 py-2.5 font-bold">RELEASE</th>
              <th scope="col" class="px-4 py-2.5 font-bold">UPDATED</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in shown"
              :key="p.no"
              tabindex="0"
              class="cursor-pointer border-b border-ink hover:bg-paper"
              @click="onRowClick($event, p)"
              @keydown.enter="open(p)"
            >
              <td class="px-4 py-3.5">
                <span class="flex flex-col gap-1">
                  <span class="flex items-center gap-2">
                    <RouterLink :to="workspaceLink(p)" class="text-base font-bold no-underline hover:underline">{{ p.name }}</RouterLink>
                    <button
                      type="button"
                      :aria-label="`Rename ${p.no}`"
                      title="Rename"
                      class="cursor-pointer border border-ink/30 bg-white px-1.5 py-px font-mono text-[10px] tracking-[0.06em] text-muted hover:border-ink hover:text-ink"
                      @click="renameProject(p)"
                    >RENAME</button>
                    <button
                      type="button"
                      :aria-label="`Delete ${p.no}`"
                      title="Delete"
                      class="cursor-pointer border border-ink/30 bg-white px-1.5 py-px font-mono text-[10px] tracking-[0.06em] text-muted hover:border-reject hover:text-reject"
                      @click="deleting = p"
                    >DELETE</button>
                  </span>
                  <span class="font-mono text-[11.5px] text-muted">{{ p.no }} · {{ p.scope }}</span>
                </span>
              </td>
              <td class="px-3 py-3.5">
                <span class="flex flex-col gap-1.5">
                  <span aria-hidden="true" class="flex gap-[3px]">
                    <span v-for="(s, i) in STAGES" :key="s" class="h-2 w-[22px] border border-ink" :class="segClass(p, i)"></span>
                  </span>
                  <span class="font-mono text-[11px]">{{ stageLabel(p) }}</span>
                </span>
              </td>
              <td class="px-3 py-3.5 font-mono text-[13px]">{{ p.docs }}</td>
              <td class="px-3 py-3.5">
                <span v-if="p.pass != null" class="flex gap-1 font-mono text-[11px] font-bold">
                  <span class="border-[1.5px] border-pass px-1.5 py-0.5 text-pass">{{ p.pass }} PASS</span>
                  <span class="border-[1.5px] border-ink px-1.5 py-0.5" :class="p.hold ? 'bg-signal' : 'bg-white'">{{ p.hold }} HOLD</span>
                  <span class="border-[1.5px] border-reject px-1.5 py-0.5 text-reject">{{ p.reject }} REJ</span>
                </span>
                <span v-else class="font-mono text-[11px] text-faint">NOT RUN</span>
              </td>
              <td class="px-3 py-3.5">
                <span
                  class="inline-flex items-center gap-2 border-2 px-[9px] py-[3px] font-mono text-[11px] font-bold tracking-[0.06em] whitespace-nowrap"
                  :class="releaseStyle[p.release].badge"
                >
                  <span aria-hidden="true" class="size-2 rounded-full border border-ink" :class="releaseStyle[p.release].led"></span>
                  {{ p.release }}
                </span>
              </td>
              <td class="px-4 py-3.5 font-mono text-xs whitespace-nowrap text-muted">{{ p.updated }}</td>
            </tr>
            <tr v-if="error">
              <td colspan="6" class="px-4 py-6 font-mono text-xs text-reject">COULD NOT LOAD PROJECTS · {{ error }}</td>
            </tr>
            <tr v-else-if="loading && !projects.length">
              <td colspan="6" class="px-4 py-6 font-mono text-xs text-faint">LOADING…</td>
            </tr>
            <tr v-else-if="!shown.length">
              <td colspan="6" class="px-4 py-6 font-mono text-xs text-faint">NO PROJECTS MATCH</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="m-0 font-mono text-[11px] text-faint">Click a project to open its workspace. Status reflects the last rule check.</p>
    </main>

    <AppFooter />

    <ProjectDialog v-if="dialog" :project="dialog.project" @saved="onSaved" @close="dialog = null" />
    <ConfirmDialog
      v-if="deleting"
      :title="`DELETE ${deleting.no}`"
      confirm-label="Delete project"
      :action="() => store.dispatch('projects/remove', deleting.no)"
      @close="deleting = null"
    >
      <p class="m-0">Delete <b>{{ deleting.name }}</b> ({{ deleting.no }})?</p>
      <p class="m-0">
        This removes its {{ deleting.docs }} {{ deleting.docs === 1 ? 'document' : 'documents' }}, the map, all check results
        and sign-offs from Heatmark. This can't be undone. The original files stay in cloud storage.
      </p>
    </ConfirmDialog>
  </div>
</template>
