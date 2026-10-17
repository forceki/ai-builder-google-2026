// Static vocabulary for the workspace screens.

export const STAGE_LABELS = ['UPLOAD', 'EXTRACT', 'MAP', 'VERIFY']

export const GROUP_INFO = [
  ['mtc', 'Material certificates', 'Mill test certificates (MTC) with heat numbers'],
  ['weld', 'Welding records / WPS / PQR', 'Weld logs, procedures, procedure and welder qualifications'],
  ['ndt', 'NDT reports', 'UT, RT, MT, PT and VT test reports'],
  ['insp', 'Inspection reports', 'Inspection plan (ITP), dimensional, hydro test, visual'],
  ['prod', 'Production / traveler', 'Travelers, fabrication records, PWHT records'],
]

export const GROUPS = [
  ['mtc', 'MATERIAL CERTIFICATES'],
  ['weld', 'WELDING RECORDS / WPS / PQR'],
  ['ndt', 'NDT REPORTS'],
  ['insp', 'INSPECTION REPORTS'],
  ['prod', 'PRODUCTION / TRAVELER'],
]

// Suggest a document type from the file name (same heuristic as the backend).
export const guess = (n) => {
  const u = (n || '').toUpperCase()
  if (/MTC|CERT/.test(u)) return 'mtc'
  if (/NDT|^UT|^RT|^MT|^PT|^VT-/.test(u)) return 'ndt'
  if (/WPS|PQR|^WR_|WELD|^WQ/.test(u)) return 'weld'
  if (/ITP|DIM|HYDRO|INSP/.test(u)) return 'insp'
  if (/TRAVEL|FAB|PWHT/.test(u)) return 'prod'
  return ''
}

// Which kind of document usually clears a finding of a given rule.
export const EVIDENCE_GROUP = {
  'R-MAT-01': 'mtc',
  'R-MAT-02': 'prod',
  'R-WLD-01': 'weld',
  'R-WLD-02': 'weld',
  'R-WLD-03': 'prod',
  'R-NDT-03': 'ndt',
  'R-NDT-04': 'ndt',
  'R-DOS-02': 'prod',
  'R-DOS-04': 'ndt',
}

export const KIND_LABEL = { material: 'MATERIAL', part: 'PART', weld: 'WELD', ndt: 'NDT' }
export const COLUMN_KINDS = ['material', 'part', 'weld', 'ndt']

export const docStatusLabel = (s) => (s || '').replace('_', ' ').toUpperCase()

// One-line summary of an item's attributes for the map and inspector.
export function itemSub(item) {
  const a = item.attributes || {}
  switch (item.kind) {
    case 'material':
      return a.grade || 'CERTIFICATE'
    case 'part':
      return [a.description, a.heat_nos?.length ? `HEAT ${a.heat_nos.join(' / ')}` : null].filter(Boolean).join(' · ') || 'PART'
    case 'weld':
      return [a.wps, a.welder ? `WELDER ${a.welder}` : null].filter(Boolean).join(' · ') || 'WELD'
    case 'ndt':
      return [a.method, a.welds?.join(', ')].filter(Boolean).join(' · ')
    default:
      return ''
  }
}

// Heat numbers for the parts a weld joins: "/" between parts, "≠" between conflicting heats of one part.
export function heatText(parts, itemByKey) {
  const perPart = parts.map((p) => (itemByKey[p]?.attributes.heat_nos ?? []).join(' ≠ ')).filter(Boolean)
  return [...new Set(perPart)].join(' / ') || '—'
}
