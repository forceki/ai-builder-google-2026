"""Suggest a document type. The uploader confirms it; this is only a suggestion."""

import re
from typing import Literal

from google.genai import types
from pydantic import BaseModel, Field

from app.ai.client import generate
from app.config import get_settings
from app.models.document import DocType

SYSTEM = """You sort quality documents from steel fabrication projects into one of five types:
- mtc: material / mill test certificates (heat numbers, grades, EN 10204 3.1)
- weld: weld logs, WPS, PQR, welder qualifications
- ndt: non-destructive testing reports or registers (UT, RT, MT, PT, VT)
- insp: inspection and test plans (ITP), dimensional reports, hydro test reports, spool / isometric drawings
  with a weld map or NDT notes
- prod: travelers, fabrication records, fit-up records, PWHT records or registers, dossier indexes
Pick the single best type from the document content, not only the file name."""


class Classification(BaseModel):
    doc_type: Literal["mtc", "weld", "ndt", "insp", "prod"]
    confidence: Literal["high", "low"]
    reason: str = Field(description="One short sentence naming what in the document decided the type")


# Same heuristic the upload dialog uses, so the API can suggest a type without a model call.
_PATTERNS: list[tuple[re.Pattern[str], DocType]] = [
    (re.compile(r"MTC|CERT"), DocType.MTC),
    (re.compile(r"NDT|^UT|^RT|^MT|^PT|^VT-"), DocType.NDT),
    (re.compile(r"WPS|PQR|^WR_|WELD|^WQ"), DocType.WELD),
    (re.compile(r"ITP|DIM|HYDRO|INSP"), DocType.INSPECTION),
    (re.compile(r"TRAVEL|FAB|PWHT"), DocType.PRODUCTION),
]


def guess_from_filename(filename: str) -> DocType | None:
    name = filename.upper()
    return next((t for pattern, t in _PATTERNS if pattern.search(name)), None)


async def classify(parts: list[types.Part]) -> Classification:
    s = get_settings()
    return await generate(
        purpose="classify",
        model=s.fast_model,
        system=SYSTEM,
        parts=[*parts, types.Part.from_text(text="Classify this document.")],
        schema=Classification,
        thinking=s.classify_thinking,
    )
