from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "low"]


class Entry(BaseModel):
    """Base for one extracted record. Every record points back to its source page."""

    page: int = Field(description="1-based page number the values were read from")
    confidence: Confidence = Field(
        description='"low" if any value was hard to read, ambiguous, or inferred rather than printed'
    )
