import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from arq.connections import ArqRedis
from litestar import Controller, delete, get, patch, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException, NotFoundException
from litestar.params import Body
from litestar.status_codes import HTTP_200_OK
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import storage
from app.ai.classify import guess_from_filename
from app.ai.inputs import UnreadableFile, page_count
from app.api.deps import get_project
from app.config import get_settings
from app.events import publish
from app.models import CheckRun, Document, User
from app.models._common import utcnow
from app.models.document import DocStatus, DocType
from app.queue import PROCESS_DOCUMENT, RUN_CHECKS
from app.schemas.api import CheckRunOut, DocumentDetail, DocumentLinkOut, DocumentOut, DocumentTypeUpdate

ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".xlsx", ".xlsm", ".csv", ".txt"}


@dataclass
class UploadForm:
    file: UploadFile
    doc_type: DocType | None = None  # confirmed type; omitted -> classified by the worker
    evidence_for: str | None = None  # open item this file should clear, e.g. W-14


class DocumentController(Controller):
    path = "/api/projects/{project_no:str}/documents"

    @get("/")
    async def list_documents(self, db: AsyncSession, user: User, project_no: str) -> list[DocumentOut]:
        project = await get_project(db, project_no, user)
        docs = await db.scalars(
            select(Document).where(Document.project_id == project.id).order_by(Document.created_at)
        )
        return [DocumentOut.model_validate(d) for d in docs]

    @post("/")
    async def upload(
        self,
        db: AsyncSession, user: User,
        queue: ArqRedis,
        project_no: str,
        data: Annotated[UploadForm, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> DocumentOut:
        settings = get_settings()
        project = await get_project(db, project_no, user)
        filename = data.file.filename or "upload"
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in ALLOWED:
            raise ClientException(f"unsupported file type {suffix or '(none)'}")
        content = await data.file.read()
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise ClientException(f"file exceeds {settings.max_upload_mb} MB")

        try:
            pages = page_count(filename, content)
        except UnreadableFile as e:
            raise ClientException(str(e)) from e

        key = storage.new_key(project.no, filename)
        content_type = data.file.content_type or "application/octet-stream"
        await storage.put(settings.documents_bucket, key, content, content_type)
        doc = Document(
            project_id=project.id,
            filename=filename,
            content_type=content_type,
            size=len(content),
            pages=pages,
            storage_key=key,
            doc_type=data.doc_type,
            suggested_type=guess_from_filename(filename),
            evidence_for=data.evidence_for,
        )
        db.add(doc)
        await db.commit()  # the worker must see the row before it picks up the job
        await queue.enqueue_job(PROCESS_DOCUMENT, str(doc.id))
        await publish(queue, project.id, "document", id=doc.id, status=doc.status)
        return DocumentOut.model_validate(doc)

    @get("/{document_id:uuid}")
    async def get_document(self, db: AsyncSession, project_no: str, document_id: uuid.UUID) -> DocumentDetail:
        return DocumentDetail.model_validate(await self._get(db, project_no, document_id))

    @get("/{document_id:uuid}/link")
    async def file_link(self, db: AsyncSession, project_no: str, document_id: uuid.UUID) -> DocumentLinkOut:
        doc = await self._get(db, project_no, document_id)
        settings = get_settings()
        url = await storage.signed_url(
            settings.documents_bucket, doc.storage_key,
            filename=doc.filename, content_type=doc.content_type, minutes=settings.signed_url_minutes,
        )
        if url is None:
            raise ClientException("file links need Google Cloud Storage (HIBANAKO_STORAGE_BACKEND=gcs)")
        return DocumentLinkOut(url=url, expires_at=utcnow() + timedelta(minutes=settings.signed_url_minutes))

    @delete("/{document_id:uuid}", status_code=HTTP_200_OK)
    async def delete_document(
        self, db: AsyncSession, queue: ArqRedis, project_no: str, document_id: uuid.UUID
    ) -> CheckRunOut:
        doc = await self._get(db, project_no, document_id)
        if doc.status in (DocStatus.QUEUED, DocStatus.READING):
            raise ClientException(f"{doc.filename} is still being read; delete it once it has finished")
        project_id = doc.project_id
        await db.delete(doc)
        run = CheckRun(project_id=project_id, rule_set=get_settings().rule_set, findings=[])
        db.add(run)
        await db.commit()
        await queue.enqueue_job(RUN_CHECKS, str(run.id))
        await publish(queue, project_id, "run", id=run.id, status=run.status)
        return CheckRunOut.model_validate(run)

    @patch("/{document_id:uuid}")
    async def set_type(
        self, db: AsyncSession, user: User, queue: ArqRedis, project_no: str, document_id: uuid.UUID, data: DocumentTypeUpdate
    ) -> DocumentOut:
        """Correct the document type and read the document again with the right schema."""
        doc = await self._get(db, project_no, document_id)
        doc.doc_type = DocType(data.doc_type)
        doc.status = DocStatus.QUEUED
        doc.extraction = None
        await db.commit()
        await queue.enqueue_job(PROCESS_DOCUMENT, str(doc.id))
        await publish(queue, doc.project_id, "document", id=doc.id, status=doc.status)
        return DocumentOut.model_validate(doc)

    async def _get(self, db: AsyncSession, project_no: str, document_id: uuid.UUID) -> Document:
        project = await get_project(db, project_no, user)
        doc = await db.get(Document, document_id)
        if doc is None or doc.project_id != project.id:
            raise NotFoundException("document not found")
        return doc
