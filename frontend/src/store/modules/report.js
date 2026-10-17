// Specimen data shown on the landing page (placeholder, not real records).
export default {
  namespaced: true,
  state: () => ({
    checks: [
      { id: 'C-01', title: 'Material traceability', question: 'Is each certificate matched to the right part and register?', status: 'PASS', rot: -3, note: '14/14 matched' },
      { id: 'C-02', title: 'Weld-record linkage', question: 'Is every weld tied to its record and procedure?', status: 'PASS', rot: 2, note: '42/42 linked' },
      { id: 'C-03', title: 'NDT evidence', question: 'Does every required weld have inspection results?', status: 'HOLD', rot: -4, note: 'W-14 no UT record' },
      { id: 'C-04', title: 'Dossier completeness', question: 'Are records missing, contradictory or unsigned?', status: 'REJECT', rot: 3, note: 'Heat no. conflict' },
    ],
    sample: {
      status: 'HOLD',
      meta: [
        { label: 'PROJECT NO.', value: 'HM-24-0193' },
        { label: 'ASSEMBLY', value: 'PS-3 PIPE SUPPORT' },
        { label: 'DATE', value: '2026-10-14' },
        { label: 'INSPECTOR', value: 'R. LINDQVIST' },
      ],
      totals: ['42 RECORDS', '38 PASS', '3 HOLD', '1 REJECT'],
      findings: [
        { title: 'Heat no. conflict in fabrication record', detail: 'Part P-112 lists 4A7712; MTC-0457 shows 4A7721.', source: 'SRC: FAB-REC-031 p.2 / MTC-0457 p.1', status: 'REJECT', rot: 2 },
        { title: 'Weld W-14: no matching NDT record', detail: 'UT required by ITP; no report references W-14.', source: 'SRC: WELD-LOG-07 row 14 / ITP-03 §4.2', status: 'HOLD', rot: -3 },
        { title: '1 PWHT record missing', detail: 'Heat treatment chart for W-22 not in dossier.', source: 'SRC: PWHT-REG p.1', status: 'HOLD', rot: 2 },
        { title: 'Inspection report unsigned', detail: 'NDT-RT-019 has no Level II signature.', source: 'SRC: NDT-RT-019 p.3', status: 'HOLD', rot: -2 },
        { title: 'Material certificates matched', detail: '14 of 14 certificates linked to parts and register.', source: 'SRC: MAT-REG rev. 4', status: 'PASS', rot: 3 },
      ],
    },
  }),
}
