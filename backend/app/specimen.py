"""Extractions for the HBK-2026-041 specimen dossier (the project shown in the UI).

Used by the seed command and the tests."""

from app.models.document import DocType
from app.pipeline.mapper import Extracted
from app.schemas.inspection import InspectionRecords, NdtRequirement
from app.schemas.mtc import Certificate, MaterialCertificates
from app.schemas.ndt import NdtReport, NdtReports
from app.schemas.production import PartEntry, ProductionRecords, PwhtEntry
from app.schemas.weld import Procedure, WeldEntry, WelderQualification, WeldingRecords

H = "high"


def cert(heat, grade):
    return Certificate(page=1, confidence=H, certificate_no=None, heat_no=heat, grade=grade, product=None,
                       cert_type="EN 10204 3.1")


def part(no, heat, page=2, conf=H):
    return PartEntry(page=page, confidence=conf, part_no=no, description=None, drawing=None, heat_no=heat)


def weld(wid, wps, welder, parts):
    return WeldEntry(page=1, confidence=H, weld_id=wid, wps=wps, welder_id=welder, joint="BUTT", parts=parts)


def ndt(no, method, welds, signed=True, result="accept"):
    return NdtReport(page=1, confidence=H, report_no=no, method=method, welds=welds, result=result,
                     technician_level="LEVEL II", signed=signed)


def specimen() -> list[Extracted]:
    return [
        Extracted("MTC_all.pdf", DocType.MTC, MaterialCertificates(certificates=[
            cert("4A7721", "SA-516 GR.70"), cert("5B2210", "SA-106 GR.B"),
            cert("7D4410", "SA-105N"), cert("HT 3C0954", "S355J2+N"),
        ])),
        Extracted("Traveler_PS-3.pdf", DocType.PRODUCTION, ProductionRecords(
            parts=[part("P-101", "4A7721"), part("P-102", "5B2210"), part("P-104", "7D4410"),
                   part("P-103", "3C0954")],
            pwht_records=[PwhtEntry(page=3, confidence=H, weld_id="W-17", temperature_c=620)],
        )),
        # The fabrication record disagrees with the traveler / certificate on P-103.
        Extracted("FAB-REC_031.pdf", DocType.PRODUCTION, ProductionRecords(
            parts=[part("P103", "3C0945", conf="low")], pwht_records=[],
        )),
        Extracted("WR_Batch.pdf", DocType.WELD, WeldingRecords(
            welds=[
                weld("W-11", "WPS-07", "118", ["P-101"]),
                weld("W-12", "WPS-07", "118", ["P-102", "P-104"]),
                weld("w14", "WPS-07", "118", ["P-101", "P-104"]),
                weld("W-17", "WPS-09", "204", ["P-103"]),
                weld("W-22", "WPS-09", "204", ["P-103"]),
            ],
            procedures=[
                Procedure(page=2, confidence=H, wps_id="WPS-07", pwht_required=False, pwht_temperature_c=None),
                Procedure(page=2, confidence=H, wps_id="WPS-09", pwht_required=True, pwht_temperature_c=620),
            ],
            qualifications=[
                WelderQualification(page=1, confidence=H, welder_id="118", processes=["GTAW"], valid_until=None),
                WelderQualification(page=1, confidence=H, welder_id="204", processes=["SMAW"], valid_until=None),
            ],
        )),
        Extracted("NDT.pdf", DocType.NDT, NdtReports(reports=[
            ndt("UT-0331", "Ultrasonic", ["W-11", "W-12"]),
            ndt("RT-0019", "RT", ["W-12"], signed=False),
            ndt("VT-0045", "VT", ["W-17"]),
            ndt("MT-0112", "MT", ["W-22"]),
        ])),
        Extracted("ITP_PRJ-041.pdf", DocType.INSPECTION, InspectionRecords(ndt_requirements=[
            NdtRequirement(page=4, confidence=H, welds=["W-11", "W-14"], methods=["UT"], extent="100%"),
            NdtRequirement(page=4, confidence=H, welds=["W-12"], methods=["UT", "RT"], extent=None),
            NdtRequirement(page=4, confidence=H, welds=["W-17"], methods=["VT"], extent="100%"),
            NdtRequirement(page=4, confidence=H, welds=["W-22"], methods=["MT"], extent="100%"),
        ])),
    ]
