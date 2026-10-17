"""Read one document into its type's extraction schema."""

from google.genai import types
from pydantic import BaseModel

from app.ai.client import generate
from app.config import get_settings
from app.models.document import DocType
from app.schemas import EXTRACTION_SCHEMAS

SYSTEM = """You extract records from fabrication quality documents for a traceability system.
Release decisions are made from what you return, so accuracy matters more than completeness:
- Copy identifiers (heat numbers, weld IDs, report numbers, WPS numbers) exactly as printed.
- Never infer, correct or complete a value. If a value is not on the page, return null (or an empty list).
- Set confidence to "low" for a record when any of its values is hard to read, handwritten, ambiguous,
  or was taken from a different place than expected.
- page is the 1-based page (or sheet) the record was read from.
- A signature field is signed when it is filled in: a handwritten signature, a typed or printed name, initials
  or a stamp. It is not signed when it is blank, a dash, or says "not signed" / "pending".
- Part numbers are piece marks (e.g. P1, E-1, P-101). Never put a heat number where a part number is asked.
- Read tables row by row; values in one row belong to the same record.
Return every matching record in the document."""

_HINTS: dict[DocType, str] = {
    DocType.MTC: "Extract every material certificate (one per heat number).",
    DocType.WELD: (
        "Extract every weld log row, every WPS with its PWHT requirement, and every welder qualification with its "
        "expiry date. If a WPS limits PWHT to certain welds (e.g. 'W-04 only'), set pwht_required and list those "
        "welds in pwht_welds. Fill a weld's parts only with part numbers printed in that row, not heat numbers."
    ),
    DocType.NDT: "Extract every NDT report, including each row of a report register.",
    DocType.INSPECTION: (
        "Extract every NDT requirement with the welds it applies to: from inspection and test plans, and also from "
        "notes on drawings or dossier indexes (e.g. '100 % radiography' means method RT on welds ['ALL'])."
    ),
    DocType.PRODUCTION: (
        "Extract every part with the heat number recorded for it, every PWHT record, and every fit-up row that "
        "says which parts (components / piece marks) a weld joins."
    ),
}


async def extract(doc_type: DocType, parts: list[types.Part]) -> BaseModel:
    s = get_settings()
    return await generate(
        purpose="extract",
        model=s.extract_model,
        system=SYSTEM,
        parts=[*parts, types.Part.from_text(text=_HINTS[doc_type])],
        schema=EXTRACTION_SCHEMAS[doc_type],
        thinking=s.extract_thinking,
    )


def needs_review(result: BaseModel) -> bool:
    """True if any extracted record came back with low confidence."""
    for value in result.model_dump().values():
        if isinstance(value, list) and any(isinstance(r, dict) and r.get("confidence") == "low" for r in value):
            return True
    return False
