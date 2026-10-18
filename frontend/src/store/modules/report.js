// Specimen data shown on the landing page (placeholder, not real records).
export default {
  namespaced: true,
  state: () => ({
    checks: [
      { id: 'C-01', title: 'Materials', question: 'Does each mill certificate meet EN 10204 3.1, and the CE and impact limits for the service?', status: 'PASS', rot: -3, note: '3/3 heats compliant' },
      { id: 'C-02', title: 'PWHT', question: 'Does each joint need post-weld heat treatment, and is its WPS qualified with it?', status: 'PENDING', rot: 2, note: 'W-11 PWHT chart not submitted' },
      { id: 'C-03', title: 'Welding procedure', question: 'Is every joint inside its WPS range for material, thickness, process and PWHT?', status: 'PASS', rot: -4, note: '12/12 joints in range' },
      { id: 'C-04', title: 'Welder qualification', question: 'Is each welder qualified for the position and thickness, and still within continuity?', status: 'FAIL', rot: 3, note: 'W-22 overhead · welder 204 F, H only' },
    ],
  }),
}
