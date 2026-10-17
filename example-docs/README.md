# Example documents to try Heatmark yourself

Four quality dossiers for one fictional piping spool (Spool 04, LOT 24-117). Everything is **synthetic**:
companies, people, heat numbers and results are invented, and every page says "SYNTHETIC DOCUMENT".
They come from `sample-docs/synthetic/` (regenerate with `generate_dossier.py` there).

## How to try one

1. Sign in, open **Projects**, click **New project** and give it a name (e.g. "Try: clean dossier").
2. Open the project, click upload in **A / Documents** (or drop files on it) and choose all files of one
   dossier folder at once. The dialog suggests a type from each file name; a few names are not recognised
   (the WPQ files, the drawing, the dossier index), so pick those yourself. The subfolders tell you the type:

   | Subfolder | Pick in the upload dialog | Files |
   |---|---|---|
   | `1-material-certificates/` | Material certificates | MTC 3.1 certificates (pipe, flange, fittings) |
   | `2-welding-records/` | Welding records / WPS / PQR | weld log (.xlsx), WPS-07, welder qualifications WPQ |
   | `3-ndt-reports/` | NDT reports | RT radiography reports |
   | `4-inspection-reports/` | Inspection reports | spool drawing with the "100 % radiography" requirement, hydrotest report |
   | `5-production-traveler/` | Production / traveler | fabrication record, PWHT record, dossier index |

   Folders 3 and 4 have fewer files on purpose: the missing RT, PWHT and hydrotest reports are planted defects.
3. Gemini reads each file (a few seconds each). When the last one is read, the checks run by themselves.
   You can also press **Run checks**.
4. Look at the map and the findings, then **Export report** to see the release decision.

Uploads go to the GCS bucket and use Gemini, so keep to these synthetic files on a free-tier key.

## The folders

| Folder | Files | What it is | Intended result |
|---|---|---|---|
| `1-accept-clean/` | 16 | Complete dossier, everything agrees | READY FOR SIGN-OFF |
| `2-hold-missing-papers/` | 14 | Same dossier without `RT-2232_W-03.pdf` and `WPQ_W-512.pdf` | HOLD: no RT for W-03, welder W-512 not qualified on file |
| `3-reject-defective/` | 13 | 12 planted defects | REJECT: heat number conflict on P1 (48213 vs 48231), RT-2233 rejects W-04, plus holds |
| `4-messy-scans/` | 13 | Same defects as 3, but 4 files are scans and one RT report is a phone photo | REJECT, if the extraction copes with the scans |

### Planted defects in folders 3 and 4

| ID | What is wrong | Caught by the current rules? |
|---|---|---|
| D01 | No RT report for weld W-03 | yes (HOLD) |
| D02 | Fabrication record heat 48231 vs certificate 48213 (digits swapped) | yes (REJECT) |
| D03 | PWHT record missing for W-04 | yes (HOLD) |
| D04 | W-02 welded at 168 A; WPS-07 allows 110-140 A | no |
| D05 | Welder W-512 qualification expired 2025-03-14 | no |
| D06 | RT-2233 cites drawing rev B; dossier has rev C | no |
| D07 | Weld W-05 in the weld log but not on the weld map, no RT | yes (HOLD) |
| D08 | Fittings certificate unsigned | no |
| D09 | RT-2233 result is REJECT, no repair | yes (REJECT) |
| D10 | W-03 cites WPS-08, which is not in the dossier | yes (HOLD) |
| D11 | Hydrostatic test report missing | no |
| D12 | Reducer tensile 395 MPa, below the 415 MPa minimum | no |

### Not defects (a good system must not flag these)

- `H-48213` instead of `48213` in the weld log (same heat)
- `W01` instead of `W-01` in RT-2230 (same weld)
- dates as DD/MM/YYYY in RT reports, ISO elsewhere
- `W409` in the WPQ title, `W-409` in the body (same welder)
- 11.13 mm wall on the drawing vs SCH 80 on the certificate (same pipe)

## Measured result

Uploaded with the types above and read by Gemini as-is (no hand corrections), on 2026-10-17:

- `1-accept-clean`: all four checks PASS.
- `3-reject-defective`: REJECT, catching D01, D02, D03, D07, D09 and D10; none of the valid variations was flagged.

Model output can vary between runs, so a document may occasionally come back as NEEDS REVIEW or with a
misread value. The defects marked "no" above need new rules (expiry dates, welding current, certificate
signatures, tensile limits, drawing revisions, required reports), not better reading.
