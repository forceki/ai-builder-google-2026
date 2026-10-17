// Tailwind classes for rule results (PASS / HOLD / REJECT) on the app screens.
export const STAMP = {
  PASS: 'border-pass text-pass',
  HOLD: 'border-ink bg-signal text-ink',
  REJECT: 'border-reject text-reject',
}

export const LED = {
  PASS: 'bg-pass',
  HOLD: 'bg-signal',
  REJECT: 'bg-reject',
}

const pad = (n) => String(n).padStart(2, '0')

export const clockTime = (d = new Date()) => `${pad(d.getHours())}:${pad(d.getMinutes())}`
export const isoDate = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

const SEVERITY = { PASS: 0, HOLD: 1, REJECT: 2 }

export const worst = (statuses) =>
  statuses.reduce((w, s) => (SEVERITY[s] > SEVERITY[w] ? s : w), 'PASS')

// "TODAY 16:21", "YESTERDAY 11:05", or "2026-10-15".
export function formatUpdated(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const now = new Date()
  const days = Math.round((new Date(now.toDateString()) - new Date(d.toDateString())) / 86400000)
  if (days === 0) return `TODAY ${clockTime(d)}`
  if (days === 1) return `YESTERDAY ${clockTime(d)}`
  return isoDate(d)
}
