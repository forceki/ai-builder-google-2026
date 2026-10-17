"""Inspection documents: inspection and test plans (ITP), dimensional, hydro test."""

from pydantic import BaseModel, Field

from app.schemas._base import Entry


class NdtRequirement(Entry):
    welds: list[str] = Field(description='Weld IDs the requirement applies to, or ["ALL"]')
    methods: list[str] = Field(description="Required NDT methods, e.g. UT, RT")
    extent: str | None = Field(description="Extent, e.g. 100%, 10%")


class InspectionRecords(BaseModel):
    ndt_requirements: list[NdtRequirement]
