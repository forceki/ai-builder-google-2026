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
- A signature field counts as signed only if a signature or initials are actually present.
Return every matching record in the document."""

_HINTS: dict[DocType, str] = {
    DocType.MTC: "Extract every material certificate (one per heat number).",
    DocType.WELD: "Extract every weld log row, every WPS (with its PWHT requirement) and every welder qualification.",
    DocType.NDT: "Extract every NDT report, including each row of a report register.",
    DocType.INSPECTION: "Extract every NDT requirement in the inspection plan, with the welds it applies to.",
    DocType.PRODUCTION: "Extract every part with the heat number recorded for it, and every PWHT record.",
}


async def extract(doc_type: DocType, parts: list[types.Part]) -> BaseModel:
    s = get_settings()
    return await generate(
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
