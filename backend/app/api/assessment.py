import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from litestar import Controller, delete, get, patch, post, put
from litestar.exceptions import ClientException, NotFoundException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_project
from app.assessment.catalog import (
    EDITIONS,
    GOVERNING,
    PROFILES,
    RULE_PACK_VERSION,
    SLOT_IDS,
    SLOTS,
    SUPP_BY_ID,
    catalog,
    condition_hash,
    default_conditions,
)
from app.assessment.dossier import SAMPLE_DOSSIER, facts
from app.assessment.engine import VERDICT_TONE, assess, conclude, missing_required
from app.assessment.report import build_report
from app.assessment.sorting import sort_file
from app.models import Assessment, AssessmentRun, Project, User
from app.models._common import utcnow

SlotId = Literal["mtc", "wps", "wpq", "drawing", "asbuilt"]
State = Literal["draft", "ready", "complete", "stale"]


class ConditionsIn(BaseModel):
    profile: str
    governing: str
    edition: str = EDITIONS[0]
    supplementary: list[str] = []
    design_pressure_mpa: float = 1.6
    design_temp_c: float = 210
    mdmt_c: float = -20
    upload_mode: Literal["single", "batch"] = "batch"
    confirmed: bool = Field(default=False, description="Set when the user finishes step 1; unlocks the documents step")

    @model_validator(mode="after")
    def _consistent(self) -> "ConditionsIn":
        profile = PROFILES.get(self.profile)
        if profile is None:
            raise ValueError(f"unknown equipment type {self.profile!r}")
        gov = GOVERNING.get(self.governing)
        if gov is None or gov.sector != profile.sector:
            raise ValueError(f"{self.governing!r} is not a governing standard for this sector")
        if self.edition not in EDITIONS:
            raise ValueError(f"edition {self.edition!r} is not supported; choose one of {', '.join(EDITIONS)}")
        for s in self.supplementary:
            if s not in SUPP_BY_ID or profile.sector not in SUPP_BY_ID[s].sectors:
                raise ValueError(f"supplementary requirement {s!r} does not apply to this sector")
        return self


class FilesIn(BaseModel):
    names: list[str] = Field(min_length=1, max_length=200)
    slot: SlotId | None = Field(default=None, description="Put the files in this slot; omit to sort them by name")


class SamplesIn(BaseModel):
    slot: SlotId | None = Field(default=None, description="Load the sample for one slot; omit for every slot")


class WaiverIn(BaseModel):
    status: Literal["waived", "open"]
    reason: str = Field(default="", max_length=1000)


class SortedFileOut(BaseModel):
    name: str
    slot: str | None
    reason: str
    manual: bool = False


class SlotOut(BaseModel):
    id: str
    label: str
    desc: str
    required: bool
    files: list[str]
    facts: list[str]


class RunOut(BaseModel):
    number: int
    condition_hash: str
    documents_hash: str
    rule_pack: str
    mode: str
    conclusion: str
    conditions: dict[str, Any]
    documents: dict[str, Any]
    result: dict[str, Any]
    run_by: str
    created_at: datetime


class AssessmentOut(BaseModel):
    project_no: str
    conditions: dict[str, Any]
    condition_hash: str
    documents_hash: str
    files: list[SortedFileOut]
    slots: list[SlotOut]
    mode: Literal["PLAN", "AS-BUILT"]
    missing: list[str] = Field(description="Required document slots still empty")
    unresolved: list[str] = Field(description="Rejected files that must be assigned or removed before a run")
    ready: bool = Field(description="Every required slot is filled and no file is unresolved, so the rules can run")
    state: State = Field(description="draft → ready → complete; stale when conditions or documents changed after the run")
    stale_reasons: list[str]
    run: RunOut | None = Field(description="Latest run")
    sample_data: bool = Field(description="True while results come from the sample dossier rather than extracted documents")


def _by_slot(files: list[dict]) -> dict[str, list[str]]:
    return {s: [f["name"] for f in files if f.get("slot") == s] for s in SLOT_IDS}


def _documents_hash(files: list[dict]) -> str:
    key = sorted((f.get("slot") or "", f["name"]) for f in files)
    return hashlib.sha256(json.dumps(key).encode()).hexdigest()[:12]


async def _latest_run(db: AsyncSession, a: Assessment) -> AssessmentRun | None:
    return await db.scalar(select(AssessmentRun).where(AssessmentRun.assessment_id == a.id)
                           .order_by(AssessmentRun.number.desc()).limit(1))


def _out(project: Project, a: Assessment, run: AssessmentRun | None) -> AssessmentOut:
    by_slot = _by_slot(a.files)
    present = {s for s, names in by_slot.items() if names}
    missing = missing_required(present)
    unresolved = [f["name"] for f in a.files if not f.get("slot")]
    c_hash, d_hash = condition_hash(a.conditions), _documents_hash(a.files)
    stale = []
    if run:
        if run.condition_hash != c_hash:
            stale.append("Conditions changed")
        if run.documents_hash != d_hash:
            stale.append("Documents changed")
        if run.rule_pack != RULE_PACK_VERSION:
            stale.append(f"Rules updated to {RULE_PACK_VERSION}")
    ready = not missing and not unresolved
    state: State = ("stale" if stale else "complete") if run else ("ready" if ready else "draft")
    return AssessmentOut(
        project_no=project.no, conditions=a.conditions, condition_hash=c_hash, documents_hash=d_hash,
        files=[SortedFileOut(**f) for f in a.files],
        slots=[SlotOut(id=s.id, label=s.label, desc=s.desc, required=s.required, files=by_slot[s.id],
                       facts=facts(SAMPLE_DOSSIER, s.id) if s.id in present else []) for s in SLOTS],
        mode="AS-BUILT" if "asbuilt" in present else "PLAN", missing=missing, unresolved=unresolved, ready=ready,
        state=state, stale_reasons=stale, run=RunOut.model_validate(run, from_attributes=True) if run else None,
        sample_data=True,
    )


async def _load(db: AsyncSession, project: Project) -> Assessment:
    a = await db.scalar(select(Assessment).where(Assessment.project_id == project.id))
    if a is None:
        a = Assessment(project_id=project.id, conditions=default_conditions(), files=[], waivers={})
        db.add(a)
        await db.flush()
    return a


async def _state(db: AsyncSession, project: Project, a: Assessment) -> AssessmentOut:
    return _out(project, a, await _latest_run(db, a))


def _add(files: list[dict], entries: list[dict]) -> list[dict]:
    """Add or replace by (name, slot); a manual assignment also clears the rejected entry of the same name."""
    out = list(files)
    for e in entries:
        out = [f for f in out if not (f["name"] == e["name"] and (f.get("slot") in (e["slot"], None)))]
        out.append(e)
    return out


def _apply_waivers(result: dict, waivers: dict) -> dict:
    """Re-apply waivers to a stored run's findings and recompute its conclusion and counts."""
    findings = [{**f, "status": "waived" if f["key"] in waivers else "open", "waiver": waivers.get(f["key"])}
                for f in result["findings"]]

    class _F:  # conclude() reads .status and .severity
        def __init__(self, d: dict) -> None:
            self.status, self.severity = d["status"], d["severity"]

    verdict = conclude([_F(f) for f in findings], pending=result["verdict"] == "INCOMPLETE")
    open_ = [f for f in findings if f["status"] == "open"]
    counts = {"fail": sum(f["severity"] == "FAIL" for f in open_), "warn": sum(f["severity"] == "WARN" for f in open_),
              "info": sum(f["severity"] == "INFO" for f in open_), "waived": len(findings) - len(open_)}
    return {**result, "findings": findings, "verdict": verdict, "verdict_tone": VERDICT_TONE[verdict], "counts": counts}


class AssessmentController(Controller):
    path = "/api"

    @get("/assessment/catalog")
    async def get_catalog(self) -> dict[str, Any]:
        """Sectors, equipment types, governing standards, editions, supplementary requirements and document slots."""
        return catalog()

    @get("/projects/{project_no:str}/assessment")
    async def get_assessment(self, db: AsyncSession, user: User, project_no: str) -> AssessmentOut:
        project = await get_project(db, project_no, user)
        return await _state(db, project, await _load(db, project))

    @put("/projects/{project_no:str}/assessment/conditions")
    async def set_conditions(self, db: AsyncSession, user: User, project_no: str, data: ConditionsIn) -> AssessmentOut:
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        a.conditions = data.model_dump()
        return await _state(db, project, a)

    @post("/projects/{project_no:str}/assessment/files")
    async def add_files(self, db: AsyncSession, user: User, project_no: str, data: FilesIn) -> AssessmentOut:
        """Sort files into slots by name, or put them in the given slot (manual assignment)."""
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        if data.slot:
            entries = [{"name": n, "slot": data.slot, "reason": "Assigned by you", "manual": True} for n in data.names]
        else:
            entries = [{"name": s.name, "slot": s.slot, "reason": s.reason, "manual": False} for s in map(sort_file, data.names)]
        a.files = _add(a.files, entries)
        return await _state(db, project, a)

    @delete("/projects/{project_no:str}/assessment/files", status_code=200)
    async def remove_files(
        self, db: AsyncSession, user: User, project_no: str, name: str | None = None, slot: str | None = None
    ) -> AssessmentOut:
        """Remove one file (by name, optionally within a slot), every file in a slot, or everything when neither is given."""
        if slot and slot not in SLOT_IDS:
            raise ClientException(f"unknown slot {slot!r}")
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        a.files = [f for f in a.files
                   if not ((name is None or f["name"] == name) and (slot is None or f.get("slot") == slot))]
        return await _state(db, project, a)

    @post("/projects/{project_no:str}/assessment/samples")
    async def load_samples(self, db: AsyncSession, user: User, project_no: str, data: SamplesIn) -> AssessmentOut:
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        slots = [s for s in SLOTS if data.slot in (None, s.id)]
        a.files = _add([f for f in a.files if f.get("slot") not in {s.id for s in slots}],
                       [{"name": n, "slot": s.id, "reason": "Sample document", "manual": False} for s in slots for n in s.sample])
        return await _state(db, project, a)

    @post("/projects/{project_no:str}/assessment/runs")
    async def run(self, db: AsyncSession, user: User, project_no: str) -> AssessmentOut:
        """Run the rules on the current conditions and documents and store the result."""
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        state = await _state(db, project, a)
        if state.missing:
            raise ClientException(f"submit the required documents first: {', '.join(state.missing)}")
        if state.unresolved:
            raise ClientException(f"assign or remove the rejected files first: {', '.join(state.unresolved)}")
        files = _by_slot(a.files)
        result = assess(a.conditions, files, SAMPLE_DOSSIER, waivers=a.waivers)
        number = (await db.scalar(select(func.max(AssessmentRun.number)).where(AssessmentRun.assessment_id == a.id))) or 0
        run = AssessmentRun(
            assessment_id=a.id, number=number + 1, condition_hash=state.condition_hash, documents_hash=state.documents_hash,
            rule_pack=RULE_PACK_VERSION, mode=result.mode, conclusion=result.verdict, conditions=dict(a.conditions),
            documents=files, result=result.as_dict(), run_by=f"{user.name}, {user.role}",
        )
        db.add(run)
        await db.flush()
        return _out(project, a, run)

    @patch("/projects/{project_no:str}/assessment/findings/{key:str}")
    async def set_waiver(self, db: AsyncSession, user: User, project_no: str, key: str, data: WaiverIn) -> AssessmentOut:
        """Waive a finding with a reason, or re-open it. The waiver follows the finding (rule + item) across re-runs."""
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        run = await _latest_run(db, a)
        if run is None or not any(f["key"] == key for f in run.result["findings"]):
            raise NotFoundException(f"finding {key} is not in the latest run")
        waivers = dict(a.waivers)
        if data.status == "waived":
            if not data.reason.strip():
                raise ClientException("give a reason for the waiver")
            waivers[key] = {"by": f"{user.name}, {user.role}", "reason": data.reason.strip(), "at": utcnow().isoformat()}
        else:
            waivers.pop(key, None)
        a.waivers = waivers
        run.result = _apply_waivers(run.result, waivers)
        run.conclusion = run.result["verdict"]
        return _out(project, a, run)

    @get("/projects/{project_no:str}/assessment/report")
    async def get_report(self, db: AsyncSession, user: User, project_no: str) -> dict[str, Any]:
        """The formal report of the latest run, for printing."""
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        state = await _state(db, project, a)
        if state.run is None:
            raise ClientException("run the assessment before generating the report")
        r = state.run
        return build_report(
            project_no=project.no, project_name=project.name, prepared_by=r.run_by, conditions=r.conditions,
            documents=r.documents, result=r.result, run_number=r.number, run_at=r.created_at,
            condition_hash=r.condition_hash, rule_pack=r.rule_pack,
        ) | {"sample_data": True, "stale": state.state == "stale", "stale_reasons": state.stale_reasons}
