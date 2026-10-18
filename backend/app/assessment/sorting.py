"""Batch upload sorting: decide which document slot a file belongs to, or why it is rejected.

Sorting is by file name for now; content-based identification comes with extraction.
"""

import re
from dataclasses import dataclass

ALLOWED = {"pdf", "jpg", "jpeg", "png", "xlsx"}


@dataclass(frozen=True)
class Sorted:
    name: str
    slot: str | None = None
    reason: str = ""  # why it went to that slot, or why it was rejected

    @property
    def rejected(self) -> bool:
        return self.slot is None


def sort_file(name: str) -> Sorted:
    u = name.upper()
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED:
        return Sorted(name, reason=f"Unsupported format (.{ext}). Upload PDF, JPG, PNG or XLSX.")
    if re.search(r"2\.1|2\.2", u) and re.search(r"MTC|CERT", u):
        return Sorted(name, reason="Not a standard mill certificate: EN 10204 type 2.1/2.2 has no specific test results. "
                                   "Type 3.1 or 3.2 is required.")
    if re.search(r"DRAFT|UNSIGNED", u):
        return Sorted(name, reason="Draft document. An approved, signed revision is required.")
    if re.match(r"IMG_|SCAN_|DSC", u):
        return Sorted(name, reason="Can't read: the image has no legible text. Upload a clear scan or PDF.")
    if re.search(r"AS-?BUILT|^ASB", u):
        return Sorted(name, "asbuilt", "As-built record: joint log and PWHT charts")
    if re.search(r"WPQ|^WQ|WELDER", u):
        return Sorted(name, "wpq", "Welder qualification: test position, process, continuity")
    if re.search(r"WPS|PQR", u):
        return Sorted(name, "wps", "Welding procedure with PQR reference")
    if re.search(r"MTC|CERT|3\.1", u):
        return Sorted(name, "mtc", "Mill certificate EN 10204 3.1: heat no., chemistry, impact")
    if re.search(r"WELD.?MAP|DWG|DRAWING|HBK-PV", u):
        return Sorted(name, "drawing", "Welding drawing: joint list with WPS and welder")
    return Sorted(name, reason="Not a standard document: no mill certificate, WPS, WPQ, welding drawing or as-built content found.")
