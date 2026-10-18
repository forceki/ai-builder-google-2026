"""Run the example document sets through Gemini (slot sorting and extraction) and the assessment rules, and score them.

    uv run python -m scripts.eval_examples [path/to/example-docs] [--folder not-acceptable] [--refresh]

`acceptable` must conclude ACCEPTABLE with no findings; `not-acceptable` must catch every planted defect
(scripts/make_example_documents.py, DEFECTS). Extractions are cached in var/eval-cache by file hash, so only new or
changed files call Gemini again. The documents are synthetic; keep real customer files out of this script.
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
from app.assessment.engine import ACCEPTABLE, NOT_ACCEPTABLE, assess
from app.assessment.extraction import SCHEMAS, classify_slot, extract_slot

CACHE = Path("var/eval-cache")
CONDITIONS = {**default_conditions(), "confirmed": True}  # ASME VIII-1 vessel, 1.6 MPa / 210 °C, MDMT -20 °C
TODAY = date(2026, 10, 18)

# Planted defects in not-acceptable/: what a finding must be to count as caught.
DEFECTS = {
    "D1 MTC 3C0954 tensile 385 < 400 MPa": lambda f: f.rule_id == "S-MTC-04" and f.item == "3C0954",
    "D2 welder 204 continuity lapsed": lambda f: f.rule_id == "X-07" and "204" in f.statement,
    "D3 W-14 welded by unqualified welder 131": lambda f: f.rule_id == "X-13" and f.item.startswith("W-14") and "131" in f.statement,
    "D4 PWHT L-01 held 35 min < 48 min": lambda f: f.rule_id == "X-15" and "L-01" in f.item,
    "D5 RT-021 rejects W-15": lambda f: f.rule_id == "X-16" and f.item == "W-15" and "rejected" in f.statement,
    "D6 hydrotest 1.90 < 2.08 MPa": lambda f: f.rule_id == "X-20" and "below" in f.statement,
}
EXPECTED = {"acceptable": (ACCEPTABLE, set()), "not-acceptable": (NOT_ACCEPTABLE, {n.split()[0] for n in DEFECTS})}


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


async def run_folder(folder: Path, refresh: bool) -> bool:
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    gate = asyncio.Semaphore(4)
    results = await asyncio.gather(*(read(p, refresh, gate) for p in files))
    print(f"\n=== {folder.name}  ({len(files)} files)")
    docs: list[ExtractedDoc] = []
    for path, r in zip(files, results, strict=True):
        g = r["guess"]
        expected_slot = path.parent.name.split("-", 1)[-1]  # 1-mtc → mtc
        flag = "" if g["slot"] == expected_slot else f"  WRONG SLOT (expected {expected_slot})"
        print(f"  {r['file']:<32} → {g['slot']:<8} {g['confidence']:.2f}{flag}")
        if "data" in r and g["slot"] in ("mtc", "wps", "wpq", "drawing", "asbuilt"):
            docs.append(ExtractedDoc(g["slot"], r["file"], r["data"]))
    files_by_slot: dict[str, list[str]] = {}
    for d in docs:
        files_by_slot.setdefault(d.slot, []).append(d.filename)
    result = assess(CONDITIONS, files_by_slot, build_dossier(docs), TODAY)
    print(f"  VERDICT {result.verdict}  ({result.counts})")
    for f in result.findings:
        print(f"   {f.severity:<4} {f.rule_id:<8} {f.item:<20} {f.statement}")

    verdict, expected = EXPECTED.get(folder.name, (None, set()))
    caught = {name.split()[0] for name, test in DEFECTS.items() if any(test(f) for f in result.findings)}
    for name in DEFECTS:
        if name.split()[0] in expected:
            print(f"   [{'x' if name.split()[0] in caught else ' '}] {name}")
    ok = (verdict is None or result.verdict == verdict) and expected <= caught and bool(expected or not result.findings)
    print(f"  {'PASS' if ok else 'FAIL'}: expected {verdict}" + (f", {len(caught & expected)}/{len(expected)} defects" if expected else
                                                                   ", no findings"))
    return ok


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="../example-docs")
    ap.add_argument("--folder", action="append")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and call Gemini again")
    args = ap.parse_args()
    root = Path(args.root)
    folders = [root / f for f in args.folder] if args.folder else sorted(p for p in root.iterdir() if p.is_dir())
    results = [await run_folder(folder, args.refresh) for folder in folders]
    print(f"\n{sum(results)}/{len(results)} sets as expected")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
