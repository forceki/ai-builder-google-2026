"""C-03 NDT evidence: does every required weld have inspection results?"""

from app.rules.types import RuleFinding, Status, TraceGraph

CHECK = "C-03"
NAME = "NDT evidence"
QUESTION = "Does every required weld have inspection results?"


def run(graph: TraceGraph) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    for weld in graph.welds.values():
        required, req_sources = graph.required_methods(weld.weld_id)
        reports = graph.reports_for(weld.weld_id)
        covered = {r.method for r in reports}

        for method in sorted(required - covered):
            findings.append(RuleFinding(
                CHECK, "R-NDT-03", weld.weld_id, Status.HOLD,
                f"No {method} report references weld {weld.weld_id}; {method} is required by the inspection plan.",
                [weld.source, *req_sources],
            ))

        for r in reports:
            if r.result == "reject":
                findings.append(RuleFinding(
                    CHECK, "R-NDT-04", weld.weld_id, Status.REJECT,
                    f"{r.report_no} ({r.method}) rejects weld {weld.weld_id}.",
                    [r.source],
                ))
    return findings
