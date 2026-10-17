"""NDT reports and registers (UT, RT, MT, PT, VT)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas._base import Entry


class NdtReport(Entry):
    report_no: str = Field(description="Report number, e.g. UT-0331")
    method: str = Field(description="Test method: UT, RT, MT, PT or VT")
    welds: list[str] = Field(description="Weld IDs covered by this report")
    result: Literal["accept", "reject", "unknown"]
    technician_level: str | None = Field(description="Technician certification level, e.g. LEVEL II")
    signed: bool = Field(description="True only if the report carries a signature for the responsible level")


class NdtReports(BaseModel):
    reports: list[NdtReport]
