"""Welding records: weld logs, WPS / PQR and welder qualifications."""

from pydantic import BaseModel, Field

from app.schemas._base import Entry


class WeldEntry(Entry):
    weld_id: str = Field(description="Weld / joint number, e.g. W-14")
    wps: str | None = Field(description="WPS reference used for this weld")
    welder_id: str | None = Field(description="Welder ID or stamp")
    joint: str | None = Field(description="Joint type, e.g. BUTT, FILLET, NOZZLE")
    parts: list[str] = Field(description="Part numbers joined by this weld")


class Procedure(Entry):
    wps_id: str = Field(description="WPS number, e.g. WPS-07")
    pwht_required: bool = Field(description="True if the WPS requires post-weld heat treatment")
    pwht_temperature_c: float | None = Field(description="PWHT holding temperature in °C, if stated")


class WelderQualification(Entry):
    welder_id: str
    processes: list[str] = Field(description="Qualified welding processes, e.g. GTAW, SMAW")
    valid_until: str | None = Field(description="Expiry date as YYYY-MM-DD, if stated")


class WeldingRecords(BaseModel):
    welds: list[WeldEntry]
    procedures: list[Procedure]
    qualifications: list[WelderQualification]
