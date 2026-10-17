import uuid
from dataclasses import dataclass
from typing import Annotated

from arq.connections import ArqRedis
from litestar import Controller, get, patch, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException, NotFoundException
from litestar.params import Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import storage
from app.ai.classify import guess_from_filename
from app.ai.inputs import UnreadableFile, page_count
from app.api.deps import get_project
from app.config import get_settings
from app.models import Document
from app.models.document import DocStatus, DocType
from app.queue import PROCESS_DOCUMENT
from app.schemas.api import DocumentDetail, DocumentOut, DocumentTypeUpdate

ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".xlsx", ".xlsm", ".csv", ".txt"}


@dataclass
class UploadForm:
    file: UploadFile
    doc_type: DocType | None = None  # confirmed type; omitted -> classified by the worker
    evidence_for: str | None = None  # open item this file should clear, e.g. W-14


class DocumentController(Controller):
    path = "/api/projects/{project_no:str}/documents"

    @get("/")
    async def list_documents(self, db: AsyncSession, project_no: str) -> list[DocumentOut]:
        project = await get_project(db, project_no)
        docs = await db.scalars(
            select(Document).where(Document.project_id == project.id).order_by(Document.created_at)
        )
        return [DocumentOut.model_validate(d) for d in docs]

    @post("/")
    async def upload(
        self,
        db: AsyncSession,
        queue: ArqRedis,
        project_no: str,
        data: Annotated[UploadForm, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> DocumentOut:
        settings = get_settings()
        project = await get_project(db, project_no)
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
        return DocumentOut.model_validate(doc)

    @get("/{document_id:uuid}")
    async def get_document(self, db: AsyncSession, project_no: str, document_id: uuid.UUID) -> DocumentDetail:
        return DocumentDetail.model_validate(await self._get(db, project_no, document_id))

    @patch("/{document_id:uuid}")
    async def set_type(
        self, db: AsyncSession, queue: ArqRedis, project_no: str, document_id: uuid.UUID, data: DocumentTypeUpdate
    ) -> DocumentOut:
        """Correct the document type and read the document again with the right schema."""
        doc = await self._get(db, project_no, document_id)
        doc.doc_type = DocType(data.doc_type)
        doc.status = DocStatus.QUEUED
        doc.extraction = None
        await db.commit()
        await queue.enqueue_job(PROCESS_DOCUMENT, str(doc.id))
        return DocumentOut.model_validate(doc)

    async def _get(self, db: AsyncSession, project_no: str, document_id: uuid.UUID) -> Document:
        project = await get_project(db, project_no)
        doc = await db.get(Document, document_id)
        if doc is None or doc.project_id != project.id:
            raise NotFoundException("document not found")
        return doc
