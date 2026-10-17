"""Production records: travelers, fabrication records, PWHT register."""

from pydantic import BaseModel, Field

from app.schemas._base import Entry


class PartEntry(Entry):
    part_no: str = Field(description="Part / piece mark, e.g. P-101")
    description: str | None
    drawing: str | None = Field(description="Drawing number")
    heat_no: str | None = Field(description="Heat number recorded for this part, exactly as printed")


class PwhtEntry(Entry):
    weld_id: str
    temperature_c: float | None


class FitUpEntry(Entry):
    weld_id: str = Field(description="Weld / joint number, e.g. W-01")
    parts: list[str] = Field(
        description="Part numbers / piece marks the weld joins (e.g. Component A and B), not heat numbers"
    )


class ProductionRecords(BaseModel):
    parts: list[PartEntry]
    pwht_records: list[PwhtEntry]
    fitups: list[FitUpEntry] = Field(
        default_factory=list, description="Fit-up rows: which parts each weld joins, where the record lists it"
    )
