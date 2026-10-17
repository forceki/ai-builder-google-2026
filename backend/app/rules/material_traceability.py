"""C-01 Material traceability: is each certificate matched to the right part and register?"""

from app.rules.types import RuleFinding, Status, TraceGraph

CHECK = "C-01"
NAME = "Material traceability"
QUESTION = "Is each certificate matched to the right part and register?"


def run(graph: TraceGraph) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    for part in graph.parts.values():
        heats = part.heat_nos
        if not heats:
            findings.append(RuleFinding(
                CHECK, "R-MAT-01", part.part_no, Status.HOLD,
                f"No heat number is recorded for part {part.part_no}.",
                list(part.sources),
            ))
            continue

        # R-MAT-02: documents disagree on the part's heat number.
        if len(heats) > 1:
            refs = sorted(part.heat_refs, key=lambda r: r.heat_no)
            listed = "; ".join(f"{r.source.document} lists {r.heat_no}" for r in refs)
            findings.append(RuleFinding(
                CHECK, "R-MAT-02", part.part_no, Status.REJECT,
                f"Heat number conflict for part {part.part_no}: {listed}.",
                [r.source for r in refs],
            ))
            continue

        # R-MAT-01: the part's heat has no certificate.
        (heat,) = heats
        if heat not in graph.heats:
            findings.append(RuleFinding(
                CHECK, "R-MAT-01", part.part_no, Status.HOLD,
                f"No material certificate found for heat {heat} used in part {part.part_no}.",
                [r.source for r in part.heat_refs],
            ))
    return findings
