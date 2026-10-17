"""C-04 Dossier completeness: are records missing, contradictory or unsigned?"""

from app.rules.types import RuleFinding, Status, TraceGraph

CHECK = "C-04"
NAME = "Dossier completeness"
QUESTION = "Are records missing, contradictory or unsigned?"


def run(graph: TraceGraph) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    # R-DOS-02: PWHT required by the weld's procedure but not recorded.
    for weld in graph.welds.values():
        proc = graph.procedures.get(weld.wps or "")
        if proc and proc.requires_pwht(weld.weld_id) and weld.weld_id not in graph.pwht_done:
            findings.append(RuleFinding(
                CHECK, "R-DOS-02", weld.weld_id, Status.HOLD,
                f"{proc.wps_id} requires post-weld heat treatment for {weld.weld_id}; no PWHT record found.",
                [proc.source, weld.source],
            ))

    # R-DOS-04: NDT report without the responsible signature.
    for r in graph.ndt_reports.values():
        if not r.signed:
            findings.append(RuleFinding(
                CHECK, "R-DOS-04", r.report_no, Status.HOLD,
                f"{r.report_no} is not signed by the responsible NDT level.",
                [r.source],
            ))
    return findings
