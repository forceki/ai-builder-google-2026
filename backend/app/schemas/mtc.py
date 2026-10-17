"""Material certificates (mill test certificates, EN 10204 3.1 / 3.2)."""

from pydantic import BaseModel, Field

from app.schemas._base import Entry


class Certificate(Entry):
    certificate_no: str | None = Field(description="Certificate number as printed, or null")
    heat_no: str = Field(description="Heat / cast / melt number exactly as printed")
    grade: str | None = Field(description="Material grade, e.g. SA-516 GR.70")
    product: str | None = Field(description="Product form and size, e.g. PLATE 12 MM, PIPE 4\" SCH40")
    cert_type: str | None = Field(description="Certificate type, e.g. EN 10204 3.1")


class MaterialCertificates(BaseModel):
    certificates: list[Certificate]
