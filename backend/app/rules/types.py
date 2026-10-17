"""The traceability graph the rules run on, and what they return."""

from dataclasses import dataclass, field
from enum import StrEnum


class Status(StrEnum):
    PASS = "PASS"
    HOLD = "HOLD"
    REJECT = "REJECT"


SEVERITY = {Status.PASS: 0, Status.HOLD: 1, Status.REJECT: 2}


def worst(statuses) -> Status:
    return max(statuses, key=SEVERITY.__getitem__, default=Status.PASS)


@dataclass(frozen=True)
class Source:
    document: str
    page: int | None = None

    def __str__(self) -> str:
        return f"{self.document} p.{self.page}" if self.page else self.document


@dataclass(frozen=True)
class HeatRef:
    """A heat number as recorded for a part by one document."""

    heat_no: str
    source: Source


@dataclass
class Heat:
    heat_no: str
    grade: str | None
    source: Source


@dataclass
class Part:
    part_no: str
    description: str | None
    heat_refs: list[HeatRef] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)

    @property
    def heat_nos(self) -> set[str]:
        return {r.heat_no for r in self.heat_refs}


@dataclass
class Weld:
    weld_id: str
    wps: str | None
    welder_id: str | None
    parts: list[str]
    source: Source


@dataclass
class Procedure:
    wps_id: str
    pwht_required: bool
    source: Source


@dataclass
class NdtReport:
    report_no: str
    method: str
    welds: list[str]
    result: str  # accept | reject | unknown
    signed: bool
    source: Source


@dataclass
class TraceGraph:
    heats: dict[str, Heat] = field(default_factory=dict)
    parts: dict[str, Part] = field(default_factory=dict)
    welds: dict[str, Weld] = field(default_factory=dict)
    procedures: dict[str, Procedure] = field(default_factory=dict)
    qualified_welders: set[str] = field(default_factory=set)
    # weld id -> required methods ("ALL" key applies to every weld), with the ITP source
    ndt_required: dict[str, tuple[set[str], Source]] = field(default_factory=dict)
    ndt_reports: dict[str, NdtReport] = field(default_factory=dict)
    pwht_done: dict[str, Source] = field(default_factory=dict)

    def required_methods(self, weld_id: str) -> tuple[set[str], list[Source]]:
        methods: set[str] = set()
        sources: list[Source] = []
        for key in (weld_id, "ALL"):
            if key in self.ndt_required:
                m, src = self.ndt_required[key]
                methods |= m
                sources.append(src)
        return methods, sources

    def reports_for(self, weld_id: str) -> list[NdtReport]:
        return [r for r in self.ndt_reports.values() if weld_id in r.welds]


@dataclass
class RuleFinding:
    check: str  # C-01 … C-04
    rule: str  # e.g. R-NDT-03
    item: str  # item key the finding is about, e.g. W-14
    status: Status
    message: str
    sources: list[Source] = field(default_factory=list)


@dataclass
class CheckResult:
    check: str
    name: str
    question: str
    findings: list[RuleFinding]

    @property
    def status(self) -> Status:
        return worst(f.status for f in self.findings)
