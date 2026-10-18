import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Literal

from litestar import Controller, Response, delete, get, patch, post, put
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException, NotFoundException
from litestar.params import Body
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import storage
from app.ai.inputs import UnreadableFile, page_count
from app.api.deps import get_project
from app.assessment.adapter import ExtractedDoc, build_dossier
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
from app.assessment.dossier import SAMPLE_DOSSIER, Dossier, facts
from app.assessment.engine import VERDICT_TONE, assess, conclude, missing_required
from app.assessment.intake import AUTO
from app.assessment.report import build_report
from app.assessment.snapshot import NoPreview, snapshot
from app.assessment.sorting import sort_file
from app.config import get_settings
from app.models import Assessment, AssessmentRun, Document, Project, User
from app.models._common import utcnow
from app.models.document import DocStatus
from app.queue import ASSESS_DOCUMENT, Queue

SlotId = Literal["mtc", "wps", "wpq", "drawing", "asbuilt", "other"]
State = Literal["draft", "ready", "complete", "stale"]
UPLOAD_TYPES = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".xlsx", ".xlsm"}
READING = (DocStatus.QUEUED, DocStatus.READING)


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


@dataclass
class DocumentUpload:
    file: UploadFile
    slot: SlotId | None = None  # put the file in this slot; omitted → sorted by content


class SortedFileOut(BaseModel):
    name: str
    slot: str | None
    reason: str
    manual: bool = False
    status: Literal["reading", "ready", "failed"] = "ready"
    confidence: float | None = None
    needs_confirm: bool = Field(default=False, description="Sorted with 0.5–0.85 confidence; the user should confirm")
    document_id: str | None = Field(default=None, description="Uploaded file; null for a sample file name")


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
    reading: list[str] = Field(description="Files still being read")
    ready: bool = Field(description="Every required slot is filled, nothing is being read and no file is unresolved")
    state: State = Field(description="draft → ready → complete; stale when conditions or documents changed after the run")
    stale_reasons: list[str]
    run: RunOut | None = Field(description="Latest run")
    sample_data: bool = Field(description="True while results come from the sample documents rather than uploaded files")


@dataclass
class View:
    """The assessment's files resolved against their uploaded documents, and the dossier read from them."""

    files: list[SortedFileOut]
    dossier: Dossier
    sample: bool

    def by_slot(self) -> dict[str, list[str]]:
        return {s: [f.name for f in self.files if f.slot == s and f.status == "ready"] for s in SLOT_IDS}

    def documents_hash(self) -> str:
        key = sorted((f.slot or "", f.name, f.document_id or "", f.status) for f in self.files)
        return hashlib.sha256(json.dumps(key).encode()).hexdigest()[:12]


async def _view(db: AsyncSession, a: Assessment) -> View:
    ids = [uuid.UUID(f["document_id"]) for f in a.files if f.get("document_id")]
    docs = {d.id: d for d in (await db.scalars(select(Document).where(Document.id.in_(ids)))).all()} if ids else {}
    files: list[SortedFileOut] = []
    extracted: list[ExtractedDoc] = []
    for f in a.files:
        if not f.get("document_id"):
            files.append(SortedFileOut(**f))
            continue
        d = docs.get(uuid.UUID(f["document_id"]))
        if d is None:
            continue
        reading = d.status in READING
        files.append(SortedFileOut(
            name=d.filename, slot=None if reading else d.slot, reason="Reading…" if reading else (d.slot_reason or ""),
            manual=d.slot_manual, status="reading" if reading else "failed" if d.status == DocStatus.FAILED else "ready",
            confidence=d.slot_confidence, document_id=str(d.id),
            needs_confirm=bool(not reading and d.slot and not d.slot_manual and (d.slot_confidence or 1) < AUTO)))
        if not reading and d.slot and d.extraction is not None:
            extracted.append(ExtractedDoc(d.slot, d.filename, d.extraction))
    sample = not ids
    return View(files, SAMPLE_DOSSIER if sample else build_dossier(extracted), sample)


async def _latest_run(db: AsyncSession, a: Assessment) -> AssessmentRun | None:
    return await db.scalar(select(AssessmentRun).where(AssessmentRun.assessment_id == a.id)
                           .order_by(AssessmentRun.number.desc()).limit(1))


def _out(project: Project, a: Assessment, run: AssessmentRun | None, view: View) -> AssessmentOut:
    by_slot = view.by_slot()
    present = {s for s, names in by_slot.items() if names}
    missing = missing_required(present)
    unresolved = [f.name for f in view.files if not f.slot and f.status != "reading"]
    reading = [f.name for f in view.files if f.status == "reading"]
    c_hash, d_hash = condition_hash(a.conditions), view.documents_hash()
    stale = []
    if run:
        if run.condition_hash != c_hash:
            stale.append("Conditions changed")
        if run.documents_hash != d_hash:
            stale.append("Documents changed")
        if run.rule_pack != RULE_PACK_VERSION:
            stale.append(f"Rules updated to {RULE_PACK_VERSION}")
    ready = not missing and not unresolved and not reading
    state: State = ("stale" if stale else "complete") if run else ("ready" if ready else "draft")
    return AssessmentOut(
        project_no=project.no, conditions=a.conditions, condition_hash=c_hash, documents_hash=d_hash, files=view.files,
        slots=[SlotOut(id=s.id, label=s.label, desc=s.desc, required=s.required, files=by_slot[s.id],
                       facts=facts(view.dossier, s.id) if s.id in present and s.id != "other" else []) for s in SLOTS],
        mode="AS-BUILT" if "asbuilt" in present else "PLAN", missing=missing, unresolved=unresolved, reading=reading,
        ready=ready, state=state, stale_reasons=stale,
        run=RunOut.model_validate(run, from_attributes=True) if run else None, sample_data=view.sample,
    )


async def _load(db: AsyncSession, project: Project) -> Assessment:
    a = await db.scalar(select(Assessment).where(Assessment.project_id == project.id))
    if a is None:
        a = Assessment(project_id=project.id, conditions=default_conditions(), files=[], waivers={})
        db.add(a)
        await db.flush()
    return a


async def _state(db: AsyncSession, project: Project, a: Assessment) -> AssessmentOut:
    return _out(project, a, await _latest_run(db, a), await _view(db, a))


def _add(files: list[dict], entries: list[dict]) -> list[dict]:
    """Add or replace by (name, slot); a manual assignment also clears the rejected entry of the same name."""
    out = list(files)
    for e in entries:
        out = [f for f in out if not (f["name"] == e["name"] and (f.get("slot") in (e["slot"], None)))]
        out.append(e)
    return out


async def _drop_documents(db: AsyncSession, entries: list[dict]) -> None:
    """Delete the document rows of removed entries; stored objects are kept, as for project documents."""
    for f in entries:
        if f.get("document_id"):
            doc = await db.get(Document, uuid.UUID(f["document_id"]))
            if doc is not None:
                await db.delete(doc)


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

    @post("/projects/{project_no:str}/assessment/documents")
    async def upload_document(
        self, db: AsyncSession, user: User, queue: Queue, project_no: str,
        data: Annotated[DocumentUpload, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> AssessmentOut:
        """Upload one document. It is sorted into a slot by content (unless a slot is given) and read in the background."""
        settings = get_settings()
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        filename = data.file.filename or "upload"
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        # Sample file names give way to real documents; an upload with the same name replaces the earlier one.
        keep = [f for f in a.files if (f.get("document_id") or f.get("uploaded")) and f["name"] != filename]
        await _drop_documents(db, [f for f in a.files if f.get("document_id") and f["name"] == filename])
        if suffix not in UPLOAD_TYPES:
            a.files = [*keep, {"name": filename, "slot": None, "manual": False, "uploaded": True,
                               "reason": f"FMT-01 Unsupported format ({suffix or 'no extension'}). Upload PDF, JPG, PNG or XLSX."}]
            return await _state(db, project, a)
        content = await data.file.read()
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise ClientException(f"{filename} exceeds {settings.max_upload_mb} MB")
        try:
            pages = page_count(filename, content)
        except UnreadableFile:
            a.files = [*keep, {"name": filename, "slot": None, "manual": False, "uploaded": True,
                               "reason": "OCR-01 Can't read: the file is not a readable PDF. Upload a clear scan or PDF."}]
            return await _state(db, project, a)
        key = storage.new_key(project.no, filename)
        content_type = data.file.content_type or "application/octet-stream"
        await storage.put(settings.documents_bucket, key, content, content_type)
        doc = Document(project_id=project.id, filename=filename, content_type=content_type, size=len(content), pages=pages,
                       storage_key=key, for_assessment=True, slot=data.slot, slot_manual=bool(data.slot),
                       slot_reason="Assigned by you" if data.slot else None)
        db.add(doc)
        await db.flush()
        a.files = [*keep, {"name": filename, "document_id": str(doc.id)}]
        await db.commit()  # the reader must see the row before it picks up the job
        await queue.enqueue(ASSESS_DOCUMENT, str(doc.id))
        return await _state(db, project, a)

    @post("/projects/{project_no:str}/assessment/files")
    async def add_files(self, db: AsyncSession, user: User, queue: Queue, project_no: str, data: FilesIn) -> AssessmentOut:
        """Sort sample file names by name, or put files in the given slot (manual assignment or confirmation).

        For an uploaded document, assigning a different slot reads it again with that slot's schema."""
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        uploaded = {f["name"]: f for f in a.files if f.get("document_id")}
        reread: list[str] = []
        names = [n for n in data.names if n not in uploaded]
        for name in (n for n in data.names if n in uploaded):
            if not data.slot:
                continue
            doc = await db.get(Document, uuid.UUID(uploaded[name]["document_id"]))
            if doc is None:
                continue
            same = doc.slot == data.slot and doc.extraction is not None
            doc.slot, doc.slot_manual, doc.slot_reason = data.slot, True, "Assigned by you"
            if not same:
                doc.status, doc.extraction = DocStatus.QUEUED, None
                reread.append(str(doc.id))
        if names:
            if data.slot:
                entries = [{"name": n, "slot": data.slot, "reason": "Assigned by you", "manual": True} for n in names]
            else:
                entries = [{"name": s.name, "slot": s.slot, "reason": s.reason, "manual": False} for s in map(sort_file, names)]
            a.files = _add(a.files, entries)
        if reread:
            await db.commit()
            for doc_id in reread:
                await queue.enqueue(ASSESS_DOCUMENT, doc_id)
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
        view = await _view(db, a)
        slot_of = {(f.name, f.document_id): f.slot for f in view.files}
        gone = [f for f in a.files if (name is None or f["name"] == name)
                and (slot is None or slot_of.get((f["name"], f.get("document_id"))) == slot)]
        await _drop_documents(db, gone)
        a.files = [f for f in a.files if f not in gone]
        return await _state(db, project, a)

    @post("/projects/{project_no:str}/assessment/samples")
    async def load_samples(self, db: AsyncSession, user: User, project_no: str, data: SamplesIn) -> AssessmentOut:
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        if any(f.get("document_id") or f.get("uploaded") for f in a.files):
            raise ClientException("this assessment has uploaded documents; remove them before loading the samples")
        slots = [s for s in SLOTS if data.slot in (None, s.id) and s.sample]
        a.files = _add([f for f in a.files if f.get("slot") not in {s.id for s in slots}],
                       [{"name": n, "slot": s.id, "reason": "Sample document", "manual": False} for s in slots for n in s.sample])
        return await _state(db, project, a)

    @post("/projects/{project_no:str}/assessment/runs")
    async def run(self, db: AsyncSession, user: User, project_no: str) -> AssessmentOut:
        """Run the rules on the current conditions and documents and store the result."""
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        view = await _view(db, a)
        state = _out(project, a, None, view)
        if state.reading:
            raise ClientException(f"wait until every document is read: {', '.join(state.reading)}")
        if state.missing:
            raise ClientException(f"submit the required documents first: {', '.join(state.missing)}")
        if state.unresolved:
            raise ClientException(f"assign or remove the rejected files first: {', '.join(state.unresolved)}")
        files = view.by_slot()
        result = assess(a.conditions, files, view.dossier, waivers=a.waivers)
        number = (await db.scalar(select(func.max(AssessmentRun.number)).where(AssessmentRun.assessment_id == a.id))) or 0
        run = AssessmentRun(
            assessment_id=a.id, number=number + 1, condition_hash=state.condition_hash, documents_hash=state.documents_hash,
            rule_pack=RULE_PACK_VERSION, mode=result.mode, conclusion=result.verdict, conditions=dict(a.conditions),
            documents=files, result=result.as_dict(), run_by=f"{user.name}, {user.role}",
        )
        db.add(run)
        await db.flush()
        return _out(project, a, run, view)

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
        return _out(project, a, run, await _view(db, a))

    @get("/projects/{project_no:str}/assessment/snapshot", cache=False)
    async def get_snapshot(
        self, db: AsyncSession, user: User, project_no: str, file: str, page: int = 1, box: str | None = None
    ) -> Response[bytes]:
        """PNG crop of an uploaded document around a finding's evidence box ("ymin,xmin,ymax,xmax", 0–1000)."""
        project = await get_project(db, project_no, user)
        a = await _load(db, project)
        entry = next((f for f in a.files if f.get("document_id") and f["name"] == file), None)
        doc = await db.get(Document, uuid.UUID(entry["document_id"])) if entry else None
        if doc is None or doc.project_id != project.id:
            raise NotFoundException(f"{file} is not an uploaded document of this assessment")
        coords = None
        if box:
            try:
                coords = tuple(int(float(v)) for v in box.split(","))
            except ValueError as e:
                raise ClientException("box must be ymin,xmin,ymax,xmax") from e
            if len(coords) != 4:
                raise ClientException("box must be ymin,xmin,ymax,xmax")
        data = await storage.get(get_settings().documents_bucket, doc.storage_key)
        try:
            png = snapshot(doc.filename, data, page, coords)
        except NoPreview as e:
            raise NotFoundException(str(e)) from e
        return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})

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
        ) | {"sample_data": state.sample_data, "stale": state.state == "stale", "stale_reasons": state.stale_reasons}
