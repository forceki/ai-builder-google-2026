"""Deterministic release rules. Pure functions of the traceability graph; no I/O, no AI."""

from app.rules import dossier_completeness, material_traceability, ndt_evidence, weld_linkage
from app.rules.types import CheckResult, TraceGraph

CHECKS = (material_traceability, weld_linkage, ndt_evidence, dossier_completeness)


def run_all(graph: TraceGraph) -> list[CheckResult]:
    return [CheckResult(c.CHECK, c.NAME, c.QUESTION, c.run(graph)) for c in CHECKS]
