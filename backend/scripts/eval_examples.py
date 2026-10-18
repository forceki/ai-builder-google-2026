"""Run the example dossiers through Gemini extraction and the assessment rules, and score the planted defects.

    uv run python -m scripts.eval_examples [path/to/example-docs] [--folder 3-reject-defective] [--refresh]

Extractions are cached in var/eval-cache by file hash, so only new or changed files call Gemini again.
The example dossiers are synthetic (example-docs/README.md); keep real customer files out of this script.
"""

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from app.ai.inputs import document_parts
from app.assessment.adapter import ExtractedDoc, build_dossier
from app.assessment.catalog import default_conditions
from app.assessment.engine import assess
from app.assessment.extraction import SCHEMAS, classify_slot, extract_slot

CACHE = Path("var/eval-cache")
CONDITIONS = {**default_conditions(), "profile": "plant-refinery", "governing": "ASME B31.3", "design_pressure_mpa": 5.1,
              "design_temp_c": 200, "mdmt_c": -20, "confirmed": True}
TODAY = date(2026, 10, 18)

# Planted defects from example-docs/README.md: what a finding must contain to count as caught.
DEFECTS = {
    "D01 no RT for W-03": lambda f: f.rule_id == "X-16" and f.item == "W-03",
    "D02 heat 48231 vs certificate 48213": lambda f: f.rule_id == "X-14" and "48231" in (f.item + f.statement),
    "D03 PWHT record missing for W-04": lambda f: f.rule_id == "X-15" and f.item.startswith("W-04"),
    "D04 W-02 current 168 A outside 110-140 A": lambda f: f.rule_id == "S-ASB-01" and f.item.startswith("W-02"),
    "D05 W-512 qualification expired": lambda f: f.rule_id == "X-07" and "W-512" in f.statement,
    "D06 RT-2233 cites drawing rev B": lambda f: f.rule_id == "X-22" and "RT-2233" in f.item,
    "D07 W-05 in log, not on weld map": lambda f: f.rule_id == "X-13" and f.item.startswith("W-05"),
    "D08 fittings certificate unsigned": lambda f: f.rule_id == "S-MTC-03",
    "D09 RT-2233 rejects W-04": lambda f: f.rule_id == "X-16" and "RT-2233" in f.statement and "rejected" in f.statement,
    "D10 W-03 cites WPS-08": lambda f: f.rule_id == "S-WPS-01" and "WPS-08" in f.statement,
    "D11 hydrotest report missing": lambda f: f.rule_id == "X-20" and "No hydrotest" in f.statement,
    "D12 reducer tensile 395 < 415 MPa": lambda f: f.rule_id == "S-MTC-04" and "60232" in f.item,
}
ALL_TAGS = {name.split()[0] for name in DEFECTS}
EXPECTED = {"1-accept-clean": set(), "2-hold-missing-papers": {"D01"}, "3-reject-defective": ALL_TAGS,
            "4-messy-scans": ALL_TAGS}
# A good system must not flag these (README "Not defects").
TRAPS = {
    "H-48213 vs 48213": lambda f: "48213" in f.item and f.rule_id in ("X-14", "X-01"),
    "W01 vs W-01": lambda f: f.item.startswith("W-01") and f.rule_id == "X-16",
    "W409 vs W-409": lambda f: "W-409" in f.statement and f.rule_id in ("X-06", "X-13"),
}


async def read(path: Path, refresh: bool, gate: asyncio.Semaphore) -> dict:
    data = path.read_bytes()
    key = CACHE / f"{hashlib.sha256(data).hexdigest()[:20]}.json"
    if key.exists() and not refresh:
        return json.loads(key.read_text())
    async with gate:
        parts = document_parts(path.name, data)
        guess = await classify_slot(parts)
        out = {"file": path.name, "guess": guess.model_dump()}
        if guess.slot in SCHEMAS and guess.legible and guess.confidence >= 0.5:
            out["data"] = (await extract_slot(guess.slot, parts)).model_dump(mode="json")
    CACHE.mkdir(parents=True, exist_ok=True)
    key.write_text(json.dumps(out, indent=1))
    return out


async def run_folder(folder: Path, refresh: bool) -> tuple[int, int, int]:
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    gate = asyncio.Semaphore(4)
    results = await asyncio.gather(*(read(p, refresh, gate) for p in files))
    print(f"\n=== {folder.name}  ({len(files)} files)")
    docs: list[ExtractedDoc] = []
    for r in results:
        g = r["guess"]
        print(f"  {r['file']:<40} → {g['slot']:<8} {g['confidence']:.2f}{'' if g['legible'] else '  ILLEGIBLE'}")
        if "data" in r and g["slot"] in ("mtc", "wps", "wpq", "drawing", "asbuilt"):
            docs.append(ExtractedDoc(g["slot"], r["file"], r["data"]))
    dossier = build_dossier(docs)
    files_by_slot: dict[str, list[str]] = {}
    for d in docs:
        files_by_slot.setdefault(d.slot, []).append(d.filename)
    result = assess(CONDITIONS, files_by_slot, dossier, TODAY)
    print(f"  VERDICT {result.verdict}  ({result.counts})")
    for f in result.findings:
        print(f"   {f.severity:<4} {f.rule_id:<8} {f.item:<22} {f.statement}")

    expected = EXPECTED.get(folder.name, set())
    caught = {name.split()[0] for name, test in DEFECTS.items() if any(test(f) for f in result.findings)}
    print("  Planted defects:")
    for name in DEFECTS:
        tag = name.split()[0]
        if tag in expected or tag in caught:
            print(f"   [{'x' if tag in caught else ' '}] {name}{'' if tag in expected else '  (not expected here)'}")
    traps = [name for name, test in TRAPS.items() if any(test(f) for f in result.findings)]
    print(f"  Traps flagged by mistake: {', '.join(traps) or 'none'}")
    return len(caught & expected), len(expected), len(traps)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="../example-docs")
    ap.add_argument("--folder", action="append")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and call Gemini again")
    args = ap.parse_args()
    root = Path(args.root)
    folders = [root / f for f in args.folder] if args.folder else sorted(p for p in root.iterdir() if p.is_dir())
    total = [0, 0, 0]
    for folder in folders:
        for i, v in enumerate(await run_folder(folder, args.refresh)):
            total[i] += v
    print(f"\nCaught {total[0]}/{total[1]} expected defects · {total[2]} trap(s) flagged")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
