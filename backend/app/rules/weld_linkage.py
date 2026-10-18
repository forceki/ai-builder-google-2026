"""C-02 Weld-record linkage: is every weld tied to its record and procedure?"""

from app.rules.types import RuleFinding, Status, TraceGraph

CHECK = "C-02"
NAME = "Weld-record linkage"
QUESTION = "Is every weld tied to its record and procedure?"


def run(graph: TraceGraph) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    for weld in graph.welds.values():
        src = [weld.source]
        if not weld.wps:
            findings.append(RuleFinding(CHECK, "R-WLD-01", weld.weld_id, Status.HOLD,
                                        f"Weld {weld.weld_id} has no WPS recorded.", src))
        elif weld.wps not in graph.procedures:
            findings.append(RuleFinding(CHECK, "R-WLD-01", weld.weld_id, Status.HOLD,
                                        f"Weld {weld.weld_id} references {weld.wps}, which is not in the documents.", src))

        if not weld.welder_id:
            findings.append(RuleFinding(CHECK, "R-WLD-02", weld.weld_id, Status.HOLD,
                                        f"Weld {weld.weld_id} has no welder recorded.", src))
        elif weld.welder_id not in graph.qualified_welders:
            findings.append(RuleFinding(CHECK, "R-WLD-02", weld.weld_id, Status.HOLD,
                                        f"No qualification on file for welder {weld.welder_id} (weld {weld.weld_id}).", src))

        unknown = [p for p in weld.parts if p not in graph.parts]
        if not weld.parts or unknown:
            what = ", ".join(unknown) if unknown else "any part"
            findings.append(RuleFinding(CHECK, "R-WLD-03", weld.weld_id, Status.HOLD,
                                        f"Weld {weld.weld_id} is not linked to {what} on the traveler.", src))
    return findings
