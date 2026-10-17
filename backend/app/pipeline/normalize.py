"""Normalise identifiers so records from different documents can be matched."""

import re

_SEP = re.compile(r"[\s_\-./]+")
_ID = re.compile(r"^([A-Z]+)[\s_\-./]*0*(\d+)([A-Z]?)$")

_METHODS = {
    "UT": "UT", "ULTRASONIC": "UT", "PAUT": "UT", "PHASED ARRAY": "UT",
    "RT": "RT", "RADIOGRAPHY": "RT", "RADIOGRAPHIC": "RT", "X-RAY": "RT",
    "MT": "MT", "MPI": "MT", "MAGNETIC PARTICLE": "MT",
    "PT": "PT", "DPI": "PT", "PENETRANT": "PT", "DYE PENETRANT": "PT",
    "VT": "VT", "VISUAL": "VT",
}


def heat_no(value: str) -> str:
    """'Heat 4a-7721' -> '4A7721'. Heat numbers are compared without separators."""
    v = value.upper().strip()
    v = re.sub(r"^(HEAT|HT|CAST|MELT)\s*(NO\.?|NUMBER|#)?\s*[:.]?\s*", "", v)
    return _SEP.sub("", v)


def prefixed_id(value: str, width: int = 0) -> str:
    """'w14' / 'W 14' / 'W-014' -> 'W-14'; 'ut331' -> 'UT-331' (or 'UT-0331' with width=4)."""
    v = value.upper().strip()
    m = _ID.match(v)
    if not m:
        return _SEP.sub("-", v)
    prefix, num, suffix = m.groups()
    return f"{prefix}-{num.zfill(width)}{suffix}"


def weld_id(value: str) -> str:
    return prefixed_id(value)


def part_no(value: str) -> str:
    return prefixed_id(value, width=3)


def report_no(value: str) -> str:
    return prefixed_id(value, width=4)


def wps_id(value: str) -> str:
    return prefixed_id(value, width=2)


def welder_id(value: str) -> str:
    v = value.upper().strip()
    v = re.sub(r"^(WELDER\s*)?(ID|NO\.?|#)?\s*[:.]?\s*", "", v)
    return _SEP.sub("", v)


def ndt_method(value: str) -> str:
    v = value.upper().strip()
    if v in _METHODS:
        return _METHODS[v]
    for name, code in _METHODS.items():
        if v.startswith(name):
            return code
    return v
