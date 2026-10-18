"""Read one uploaded assessment document: sort it into a slot by content, then extract the slot's fields.

PRD section 4: confidence ≥ 0.85 → assigned; 0.5–0.85 → assigned, the user confirms; below 0.5 → rejected with
"assign manually". Unreadable scans (OCR-01) and EN 10204 2.1 / 2.2 certificates (MTC-01) are rejected here.
"""

import asyncio
import logging
import uuid

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import storage
from app.ai.inputs import document_parts
from app.ai.usage import ai_context
from app.assessment.adapter import cert_type
from app.assessment.extraction import SCHEMAS, classify_slot, extract_slot
from app.config import get_settings
from app.models import Document
from app.models.document import DocStatus

log = logging.getLogger(__name__)

AUTO = 0.85
GUESS = 0.5
SLOT_NAMES = {"mtc": "mill certificate", "wps": "WPS", "wpq": "WPQ", "drawing": "welding drawing",
              "asbuilt": "as-built document", "other": "other document"}


def _low_confidence(value) -> bool:
    if isinstance(value, dict):
        return value.get("confidence") == "low" or any(_low_confidence(v) for v in value.values())
    if isinstance(value, list):
        return any(_low_confidence(v) for v in value)
    return False


def intake_rejection(slot: str, data: BaseModel) -> str | None:
    """A reason to refuse the document at intake, after extraction."""
    if slot == "mtc":
        types = {cert_type(h.cert_type) for h in data.heats}
        if types and types <= {"2.1", "2.2"}:
            return ("MTC-01 Not a usable mill certificate: EN 10204 type 2.1/2.2 has no specific test results. "
                    "Type 3.1 or 3.2 is required.")
        if not data.heats:
            return "MTC-02 Mill certificate has no heat number."
    if slot == "drawing" and not data.joints:
        return "DRW-01 Drawing has no weld table; upload the weld map sheet."
    return None


async def assess_document(sessions: async_sessionmaker[AsyncSession], document_id: str) -> None:
    async with sessions() as session:
        doc = await session.get(Document, uuid.UUID(document_id))
        if doc is None or not doc.for_assessment or doc.status not in (DocStatus.QUEUED, DocStatus.READING):
            return
        doc.status, doc.error = DocStatus.READING, None
        await session.commit()

        limit = get_settings().extract_timeout_seconds
        try:
            async with asyncio.timeout(limit):
                data = await storage.get(get_settings().documents_bucket, doc.storage_key)
                parts = document_parts(doc.filename, data)
                with ai_context(project_id=doc.project_id, document_id=doc.id):
                    slot = doc.slot if doc.slot_manual else None
                    if slot is None:
                        guess = await classify_slot(parts)
                        doc.slot_confidence = guess.confidence
                        if not guess.legible:
                            doc.slot_reason = "OCR-01 Can't read: the image has no legible text. Upload a clear scan or PDF."
                        elif guess.slot == "none" or guess.confidence < GUESS:
                            doc.slot_reason = f"CLS-01 Not a standard document ({guess.reason}) Assign it manually or remove it."
                        else:
                            slot = guess.slot
                            doc.slot_reason = (guess.reason if guess.confidence >= AUTO
                                               else f"Probably a {SLOT_NAMES[slot]}: {guess.reason} Please confirm.")
                    result = await extract_slot(slot, parts) if slot in SCHEMAS else None
            rejection = intake_rejection(slot, result) if result is not None else None
            if rejection:
                slot, doc.slot_reason = None, rejection
            doc.slot = slot
            doc.extraction = result.model_dump(mode="json") if result is not None else None
            low = result is not None and _low_confidence(doc.extraction)
            doc.status = DocStatus.NEEDS_REVIEW if low else DocStatus.EXTRACTED
        except TimeoutError:
            doc.status, doc.slot = DocStatus.FAILED, None
            doc.slot_reason = f"Reading took longer than {limit // 60} minutes. Assign the slot manually to read it again."
        except Exception as e:
            log.exception("assessment intake failed for %s", doc.filename)
            doc.status, doc.slot = DocStatus.FAILED, None
            doc.slot_reason = "Reading failed. Assign the slot manually to try again, or remove the file."
            doc.error = str(e)[:2000]
        await session.commit()
