"""Plain-language explanation of a rule finding. Explains the status; never sets it."""

from google.genai import types
from pydantic import BaseModel, Field

from app.ai.client import generate
from app.config import get_settings
from app.rules.types import RuleFinding

SYSTEM = """You write short explanations of release-check findings for quality engineers.
The status (PASS / HOLD / REJECT) was set by a deterministic rule and is final; do not question or change it.
Explain in plain language what is wrong and what evidence is missing or conflicting, citing the source documents.
Then suggest one concrete next verification step the engineer can take.
Be specific and brief: at most two sentences for the explanation and one for the next step."""


class Explanation(BaseModel):
    explanation: str
    next_step: str = Field(description="One concrete action that would clear or confirm the finding")


async def explain(finding: RuleFinding, context: str = "") -> Explanation:
    s = get_settings()
    sources = "; ".join(str(src) for src in finding.sources) or "none"
    prompt = (
        f"Check {finding.check}, rule {finding.rule}, item {finding.item}\n"
        f"Status: {finding.status}\n"
        f"Rule message: {finding.message}\n"
        f"Sources: {sources}\n"
        + (f"Related records:\n{context}\n" if context else "")
    )
    return await generate(
        model=s.fast_model,
        system=SYSTEM,
        parts=[types.Part.from_text(text=prompt)],
        schema=Explanation,
        thinking=s.explain_thinking,
    )
