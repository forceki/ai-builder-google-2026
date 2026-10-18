"""Generate the example document sets in example-docs/: one pressure vessel (V-110, drawing HBK-PV-110 rev B) in two
versions, `acceptable` (every check passes) and `not-acceptable` (six planted defects, one per document type).

    uv run --with reportlab python -m scripts.make_example_documents [out_dir]

Each document follows the layout of its real counterpart:
    mill certificate   EN 10204 type 3.1, sections coded per EN 10168 (A commercial, B product, C tests, D, Z validation)
    WPS / PQR          ASME IX Form QW-482 / QW-483 (joints, base metals, filler metals, positions, preheat, PWHT, gas,
                       electrical characteristics; PQR test results)
    WPQ                ASME IX Form QW-484A (actual values and range qualified, test results) with a continuity log
    weld map           shop drawing with weld table, material list and design data
    as-built           weld log, furnace PWHT record with chart, NDE reports, UG-99 hydrotest report, thickness survey

Everything is fictional and every page says SYNTHETIC DOCUMENT.
"""

import math
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

INK = HexColor("#111111")
GREY = HexColor("#666666")
SHADE = HexColor("#EEEEEE")

FAB = "Kaneda Fabrication Works (fictional)"
CLIENT = "Northfield Refining (fictional)"
JOB = "Job 26-118 · Vessel V-110 · Drawing HBK-PV-110 rev B"
AI = "J. Hartono (fictional), Authorized Inspector"

# Planted defects in the not-acceptable set: (file, what is wrong, rule that catches it).
DEFECTS = [
    ("MTC_3C0954.pdf", "Tensile strength 385 MPa, below the 400 MPa minimum of SA-36", "S-MTC-04"),
    ("WPQ-204.pdf", "Welder 204 last used FCAW on 2026-03-02: continuity lapsed (more than 6 months)", "X-07"),
    ("ASB-01_Weld_Log.pdf", "W-14 welded by welder 131, who has no WPQ", "X-13"),
    ("PWHT-L01_Chart.pdf", "Soak held 35 min; 48 min required for 20 mm (1 h per 25 mm)", "X-15"),
    ("NDE_Reports.pdf", "RT-021 rejects W-15 (porosity); no repair or re-examination", "X-16"),
    ("HT-0412_Hydrotest.pdf", "Test pressure 1.90 MPa, below 1.3 × 1.6 = 2.08 MPa (UG-99(b))", "X-20"),
]


# Drawing helpers ------------------------------------------------------------------------------------------------

def text(c, x, y, s, size=7.5, bold=False, color=INK, anchor="left"):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    {"left": c.drawString, "centre": c.drawCentredString, "right": c.drawRightString}[anchor](x, y, s)


class Page:
    """An A4 form page: header with the issuer and the document references, a cursor `y` moving down the page."""

    def __init__(self, c, issuer, title, refs, subtitle=""):
        self.c, self.W, self.H = c, *A4
        self.x0, self.x1 = 14 * mm, self.W - 14 * mm
        c.setStrokeColor(INK)
        c.setLineWidth(0.8)
        c.rect(10 * mm, 10 * mm, self.W - 20 * mm, self.H - 20 * mm)
        text(c, self.x0, self.H - 18 * mm, issuer, 9, True)
        text(c, self.x0, self.H - 23.5 * mm, title, 12, True)
        if subtitle:
            text(c, self.x0, self.H - 28 * mm, subtitle, 7, color=GREY)
        # reference box, top right
        bw, rh = 62 * mm, 4.6 * mm
        bx, by = self.x1 - bw, self.H - 14 * mm
        for i, (k, v) in enumerate(refs):
            yy = by - (i + 1) * rh
            c.rect(bx, yy, bw, rh)
            text(c, bx + 1.5 * mm, yy + 1.4 * mm, k, 6.5, color=GREY)
            text(c, bx + 22 * mm, yy + 1.4 * mm, v, 7.5, True)
        self.y = min(by - len(refs) * rh, self.H - 31 * mm) - 5 * mm
        text(c, self.W / 2, 13 * mm, "SYNTHETIC DOCUMENT - generated for software testing - not a real record",
             6.5, color=GREY, anchor="centre")

    def section(self, label):
        c = self.c
        self.y -= 1.5 * mm
        c.setFillColor(SHADE)
        c.rect(self.x0, self.y - 5 * mm, self.x1 - self.x0, 5 * mm, fill=1, stroke=1)
        text(c, self.x0 + 1.5 * mm, self.y - 3.6 * mm, label, 7.5, True)
        self.y -= 5 * mm

    def grid(self, rows, h=8.5 * mm):
        """rows: [[(label, value, width_fraction), ...], ...]; a label above each value, like a filled-in form."""
        c, w = self.c, self.x1 - self.x0
        for row in rows:
            x = self.x0
            for label, value, frac in row:
                cw = w * frac
                c.rect(x, self.y - h, cw, h)
                text(c, x + 1.3 * mm, self.y - 2.9 * mm, label, 5.8, color=GREY)
                text(c, x + 1.3 * mm, self.y - h + 1.8 * mm, value, 7.8, True)
                x += cw
            self.y -= h

    def table(self, headers, rows, fracs, size=7, h=5 * mm):
        """Column widths as fractions of the page width."""
        c, w = self.c, self.x1 - self.x0
        widths = [w * f for f in fracs]
        c.setFillColor(SHADE)
        c.rect(self.x0, self.y - h, w, h, fill=1, stroke=1)
        x = self.x0
        for head, cw in zip(headers, widths, strict=True):
            text(c, x + 1.2 * mm, self.y - h + 1.6 * mm, head, size - 0.5, True)
            x += cw
        self.y -= h
        for row in rows:
            c.rect(self.x0, self.y - h, w, h)
            x = self.x0
            for v, cw in zip(row, widths, strict=True):
                c.line(x, self.y - h, x, self.y)
                text(c, x + 1.2 * mm, self.y - h + 1.6 * mm, str(v), size)
                x += cw
            self.y -= h

    def lines(self, items, size=7.2, gap=4 * mm):
        for s in items:
            text(self.c, self.x0 + 1 * mm, self.y - gap + 1 * mm, s, size)
            self.y -= gap

    def sign(self, boxes, h=16 * mm):
        """boxes: [(role, name, date)]; name None leaves the signature field blank."""
        c, w = self.c, (self.x1 - self.x0) / len(boxes)
        self.y -= 2 * mm
        for i, (role, name, when) in enumerate(boxes):
            x = self.x0 + i * w
            c.rect(x, self.y - h, w, h)
            text(c, x + 1.5 * mm, self.y - 3.2 * mm, role, 6, color=GREY)
            if name:
                text(c, x + 1.5 * mm, self.y - 9 * mm, name, 8, True)
                c.setFont("Helvetica-Oblique", 10)
                c.setFillColor(HexColor("#1F3A93"))
                c.drawString(x + 1.5 * mm, self.y - 13.5 * mm, "signed  " + name.split(" (")[0])
            text(c, x + w - 1.5 * mm, self.y - h + 1.8 * mm, when, 7, anchor="right")
        self.y -= h


# Mill certificates (EN 10204 3.1, EN 10168 layout) --------------------------------------------------------------

MATERIALS = {
    "4A7721": dict(mill="Northgate Steel Mill (fictional)", cert="NSM-26-48817", product="Plate, normalized",
                   spec="ASME SA-516/SA-516M Gr.70 (2023), normalized", size="20 x 2500 x 8000 mm", qty="3 plates, 9.42 t",
                   condition="Normalized 900 °C, 30 min, air cooled", thickness="20.0", yield_="345", yield_min="260",
                   tensile="520", tensile_req="485 - 620", elong="26", elong_min="21",
                   impact=("-29", ["64", "58", "66"], "62", "20 (average, CVN 10x10)"),
                   chem={"C": ".18", "Si": ".35", "Mn": "1.10", "P": ".012", "S": ".004", "Cr": ".02", "Ni": ".02",
                         "Mo": ".01", "Cu": ".03", "V": ".002", "Nb": ".001"},
                   use="Shell and heads (2:1 SE), vessel V-110"),
    "5B2210": dict(mill="Ardent Tube Co. (fictional)", cert="ATC-3.1-77302", product="Seamless pipe",
                   spec="ASME SA-106/SA-106M Gr.B (2023)", size='6 in SCH 80 (168.3 x 10.97 mm) x 6 m', qty="1 length",
                   condition="As-rolled (hot finished)", thickness="10.97", yield_="300", yield_min="240",
                   tensile="455", tensile_req="415 min.", elong="33", elong_min="30", impact=None,
                   chem={"C": ".20", "Si": ".25", "Mn": ".95", "P": ".010", "S": ".006", "Cr": ".03", "Ni": ".03",
                         "Mo": ".01", "Cu": ".05", "V": ".001"},
                   use="Nozzle neck N1"),
    "3C0954": dict(mill="Northgate Steel Mill (fictional)", cert="NSM-26-49120", product="Plate",
                   spec="ASME SA-36/SA-36M (2023)", size="12 x 2000 x 6000 mm", qty="2 plates, 2.26 t",
                   condition="As-rolled", thickness="12.0", yield_="285", yield_min="250",
                   tensile="470", tensile_req="400 - 550", elong="27", elong_min="20", impact=None,
                   chem={"C": ".17", "Si": ".22", "Mn": "1.00", "P": ".014", "S": ".008", "Cr": ".03", "Ni": ".04",
                         "Mo": ".01", "Cu": ".06", "V": ".003"},
                   use="Skid frame beams and base plates"),
}


def mtc(c, heat, bad):
    m = MATERIALS[heat]
    tensile = "385" if bad and heat == "3C0954" else m["tensile"]
    p = Page(c, m["mill"], "INSPECTION CERTIFICATE EN 10204 - 3.1",
             [("Certificate no.", m["cert"]), ("Date of issue", "2026-08-21"), ("Page", "1 / 1")],
             "Mill test certificate · sections coded per EN 10168")
    p.section("A  COMMERCIAL TRANSACTION")
    p.grid([[("A01 Manufacturer", m["mill"], .5), ("A02 Type of document", "EN 10204:2004 type 3.1", .5)],
            [("A06 Purchaser", FAB, .5), ("A07 Purchase order", "PO-26-0771 · " + JOB.split(" · ")[0], .5)]])
    p.section("B  DESCRIPTION OF PRODUCT")
    p.grid([[("B01 Product", m["product"], .3), ("B02 Steel grade / specification", m["spec"], .7)],
            [("B07 Heat (cast) no.", heat, .3), ("B09-B11 Dimensions", m["size"], .4), ("B13 Quantity", m["qty"], .3)],
            [("B03 Delivery condition", m["condition"], .6), ("Nominal thickness (mm)", m["thickness"], .4)]])
    p.section("C  INSPECTION - MECHANICAL TESTS (C00-C69)")
    p.table(["Test", "C11 Yield ReH (MPa)", "C12 Tensile Rm (MPa)", "C13 Elongation A (%)", "Direction / location"],
            [["Required", f"{m['yield_min']} min.", m["tensile_req"], f"{m['elong_min']} min.", ""],
             ["Result, heat " + heat, m["yield_"], tensile, m["elong"], "Transverse, 1/4 t"]],
            [.2, .18, .2, .2, .22])
    if m["impact"]:
        temp, vals, avg, req = m["impact"]
        p.y -= 2 * mm
        p.table(["C40 Charpy V (J)", "C42 Test temp (°C)", "C43 Single values (J)", "Average (J)", "Required (J)"],
                [["Transverse, 10x10", temp, " / ".join(vals), avg, req]], [.22, .16, .24, .14, .24])
    p.section("C  CHEMICAL COMPOSITION - LADLE ANALYSIS, % BY MASS (C70-C92)")
    els = list(m["chem"])
    p.table(["Heat", *els], [[heat, *m["chem"].values()]], [.16, *([.84 / len(els)] * len(els))])
    ce = float(m["chem"]["C"]) + float(m["chem"]["Mn"]) / 6 + (float(m["chem"]["Cr"]) + float(m["chem"]["Mo"]) +
                                                               float(m["chem"]["V"])) / 5 + (float(m["chem"]["Ni"]) +
                                                                                             float(m["chem"]["Cu"])) / 15
    p.lines([f"Carbon equivalent CE(IIW) = C + Mn/6 + (Cr+Mo+V)/5 + (Ni+Cu)/15 = {ce:.2f}"])
    p.section("D  OTHER TESTS")
    p.lines(["D01 Marking, visual inspection and dimensional check: satisfactory. Heat number hard-stamped on each piece.",
             "D02 Ultrasonic examination: not ordered." if heat != "4A7721" else
             "D02 Ultrasonic examination per SA-435: satisfactory.",
             f"Intended use (per purchase order): {m['use']}."])
    p.section("Z  VALIDATION")
    p.lines(["Z01 We hereby certify that the products described above comply with the terms of the order and the",
             "      material specification, based on specific inspection of the products supplied."])
    p.sign([("Z02 Date of issue", "", "2026-08-21"),
            ("Z03 Authorized inspection representative (independent of manufacturing)", "S. Varga (fictional), QA", "Stamp QA-07")])
    c.showPage()


# WPS (QW-482) and PQR (QW-483) ---------------------------------------------------------------------------------

PROCEDURES = {
    "WPS-07": dict(pqr="PQR-07", rev="1", date="2025-02-14", processes="GTAW (root) + SMAW (fill and cap)",
                   types="Manual / Manual", joint="Single-V groove, 60° included, root gap 2-3 mm, root face 1-2 mm",
                   backing="None (open root, GTAW)", p_no="1", group="1 or 2",
                   t_groove="5 to 50 mm", t_fillet="All", fillers=[
                       ("GTAW", "SFA-5.18", "ER70S-2", "6", "1", "2.4 mm", "max. 6 mm"),
                       ("SMAW", "SFA-5.1", "E7018", "4", "1", "3.2 / 4.0 mm", "max. 44 mm")],
                   positions="All (1G-6G)", fillet_pos="All", progression="Uphill",
                   preheat="95 °C minimum", interpass="250 °C maximum", pwht=True,
                   pwht_temp="620 ± 15 °C (605 - 635 °C)", pwht_time="1 h per 25 mm of thickness, 15 min minimum",
                   gas="GTAW: argon 99.99 %, 8-12 L/min. Backing gas: none.",
                   passes=[("Root", "GTAW", "ER70S-2", "2.4", "DCEN", "90 - 130", "10 - 14", "60 - 100"),
                           ("Fill", "SMAW", "E7018", "3.2", "DCEP", "100 - 140", "21 - 25", "100 - 160"),
                           ("Cap", "SMAW", "E7018", "4.0", "DCEP", "130 - 170", "22 - 26", "120 - 180")],
                   pqr_coupon="SA-516 Gr.70 to SA-516 Gr.70, 25 mm plate", pqr_pwht="620 °C, 60 min",
                   tensile=[("T-1", "19.0 x 25.0", "535", "Base metal, ductile"), ("T-2", "19.0 x 25.0", "528", "Base metal, ductile")],
                   bends="4 side bends (QW-462.2), 10 mm, 180°: no open discontinuities. Acceptable.",
                   charpy=("-29", "Weld 54 / 60 / 57 J · HAZ 72 / 80 / 76 J"), hardness="208"),
    "WPS-09": dict(pqr="PQR-09", rev="0", date="2024-05-20", processes="FCAW", types="Semi-automatic",
                   joint="Fillet welds, all sizes; single-bevel groove 45°, root gap 0-3 mm",
                   backing="Optional (steel)", p_no="1", group="1 or 2", t_groove="1.5 to 20 mm", t_fillet="All",
                   fillers=[("FCAW", "SFA-5.20", "E71T-1C", "6", "1", "1.2 mm", "max. 20 mm")],
                   positions="All (groove and fillet)", fillet_pos="All", progression="Uphill",
                   preheat="10 °C minimum (to 25 mm)", interpass="250 °C maximum", pwht=False,
                   pwht_temp="None", pwht_time="None",
                   gas="Shielding: CO2 100 %, 15-20 L/min.",
                   passes=[("All", "FCAW", "E71T-1C", "1.2", "DCEP", "180 - 260", "24 - 29", "250 - 400")],
                   pqr_coupon="SA-36 to SA-36, 10 mm plate", pqr_pwht="None",
                   tensile=[("T-1", "19.0 x 10.0", "498", "Base metal, ductile"), ("T-2", "19.0 x 10.0", "505", "Base metal, ductile")],
                   bends="2 face + 2 root bends (QW-462.3(a)), 180°: no open discontinuities. Acceptable.",
                   charpy=("-20", "Weld 47 / 52 / 49 J"), hardness="236"),
}


def wps(c, wid):
    w = PROCEDURES[wid]
    refs = [("WPS no.", wid), ("Revision", w["rev"]), ("Date", w["date"]), ("Supporting PQR", w["pqr"])]
    p = Page(c, FAB, "WELDING PROCEDURE SPECIFICATION (WPS)", refs,
             "Format per ASME BPVC Section IX, Form QW-482 (see QW-200.1)")
    p.grid([[("Welding process(es)", w["processes"], .6), ("Type(s)", w["types"], .4)]])
    p.section("JOINTS (QW-402)")
    p.grid([[("Joint design", w["joint"], .7), ("Backing", w["backing"], .3)]])
    p.section("BASE METALS (QW-403)")
    p.grid([[("P-No.", w["p_no"], .2), ("Group No.", w["group"], .2), ("to P-No.", w["p_no"], .2), ("Group No.", w["group"], .4)],
            [("Thickness range, base metal - groove", w["t_groove"], .5), ("Fillet", w["t_fillet"], .5)]])
    p.section("FILLER METALS (QW-404)")
    p.table(["Process", "Spec. No. (SFA)", "AWS No. (Class)", "F-No.", "A-No.", "Size", "Deposited thickness"],
            [list(f) for f in w["fillers"]], [.12, .15, .16, .1, .1, .17, .2])
    p.section("POSITIONS (QW-405)")
    p.grid([[("Position(s) of groove", w["positions"], .4), ("Position(s) of fillet", w["fillet_pos"], .3),
             ("Welding progression", w["progression"], .3)]])
    p.section("PREHEAT (QW-406)")
    p.grid([[("Preheat temperature, minimum", w["preheat"], .5), ("Interpass temperature, maximum", w["interpass"], .5)]])
    p.section("POSTWELD HEAT TREATMENT (QW-407)")
    p.grid([[("PWHT", "Required" if w["pwht"] else "None", .2), ("Temperature range", w["pwht_temp"], .4),
             ("Time range", w["pwht_time"], .4)]])
    p.section("GAS (QW-408)")
    p.lines([w["gas"]])
    p.section("ELECTRICAL CHARACTERISTICS (QW-409)")
    p.table(["Weld pass(es)", "Process", "Classification", "Diameter (mm)", "Current / polarity", "Amps (range)",
             "Volts (range)", "Travel (mm/min)"], [list(r) for r in w["passes"]], [.12, .1, .14, .12, .14, .13, .12, .13])
    p.section("TECHNIQUE (QW-410)")
    p.lines(["String or weave bead: stringer, weave max. 3 x electrode diameter. Multiple passes per side.",
             "Initial and interpass cleaning: brushing and grinding. Back gouging: grinding to sound metal."])
    p.sign([("Prepared by (welding engineer)", "K. Mori (fictional)", w["date"]),
            ("Approved by (QA manager)", "L. Ortega (fictional)", w["date"])])
    c.showPage()

    p = Page(c, FAB, "PROCEDURE QUALIFICATION RECORD (PQR)", [("PQR no.", w["pqr"]), ("WPS qualified", wid),
                                                             ("Date welded", "2024-05-02" if wid == "WPS-09" else "2025-01-28")],
             "Format per ASME BPVC Section IX, Form QW-483 · actual variables used to weld the test coupon")
    p.section("TEST COUPON - ACTUAL VARIABLES")
    p.grid([[("Base metals (QW-403)", w["pqr_coupon"], .6), ("P-No. to P-No.", "1 to 1", .4)],
            [("Process(es)", w["processes"], .6), ("PWHT (QW-407)", w["pqr_pwht"], .4)]])
    p.section("TENSILE TEST (QW-150)")
    p.table(["Specimen", "Width x thickness (mm)", "Ultimate tensile (MPa)", "Type of failure and location"],
            [list(t) for t in w["tensile"]], [.15, .25, .25, .35])
    p.section("GUIDED-BEND TESTS (QW-160)")
    p.lines([w["bends"]])
    p.section("TOUGHNESS TESTS (QW-170)")
    temp, vals = w["charpy"]
    p.table(["Specimen", "Test temperature (°C)", "Impact values"], [["CVN 10 x 10", temp, vals]], [.2, .25, .55])
    p.section("HARDNESS SURVEY (HV10)")
    p.table(["Location", "Maximum HV10"], [["Weld metal and HAZ, cap and root", w["hardness"]]], [.6, .4])
    p.y -= 3 * mm
    p.lines(["We certify that the statements in this record are correct and that the test welds were prepared, welded",
             "and tested in accordance with the requirements of Section IX of the ASME BPVC."])
    p.sign([("Mechanical tests by", "Halvorsen Test Lab (fictional)", "Lab report HTL-" + w["pqr"][-2:]),
            ("Certified by (QA manager)", "L. Ortega (fictional)", w["date"])])
    c.showPage()


# WPQ (QW-484A) with continuity log ----------------------------------------------------------------------------

WELDERS = {
    "118": dict(name="A. Santoso (fictional)", wps="WPS-07", date="2025-03-10", base="SA-106 Gr.B to SA-106 Gr.B",
                process="GTAW + SMAW", type_="Manual", backing="GTAW without; SMAW with (deposited weld metal)",
                form="Pipe, 6 in SCH 120 (OD 168.3 mm, t 14.27 mm)", diameter="73 mm OD and over",
                filler="SFA-5.18 ER70S-2 / SFA-5.1 E7018", fno="F-6 / F-4", deposit="GTAW 5 mm / SMAW 9.3 mm (3 layers)",
                deposit_range="GTAW max. 10 mm / SMAW unlimited", position="6G", pos_range="All positions, groove and fillet",
                thickness="14.27 mm", t_range="Unlimited",
                results="4 side bends (QW-462.2): acceptable",
                log=[("2026-04-14", "Job 26-061", "Shell seams", "GTAW + SMAW"), ("2026-07-02", "Job 26-090", "Nozzles", "GTAW + SMAW"),
                     ("2026-10-05", "Job 26-118", "W-11, W-14, W-15", "GTAW + SMAW"), ("2026-10-07", "Job 26-118", "W-12", "GTAW + SMAW")]),
    "204": dict(name="R. Wibowo (fictional)", wps="WPS-09", date="2024-06-12", base="SA-36 to SA-36",
                process="FCAW", type_="Semi-automatic", backing="With (steel backing)",
                form="Plate, 10 mm", diameter="Groove: pipe 610 mm OD and over; fillet: all",
                filler="SFA-5.20 E71T-1C", fno="F-6", deposit="10 mm", deposit_range="max. 20 mm",
                position="3G and 4G", pos_range="Groove F, V, O; fillet all positions",
                thickness="10 mm", t_range="max. 20 mm",
                results="2 face + 2 root bends (QW-462.3(a)) per coupon: acceptable",
                log=[("2025-11-18", "Job 25-204", "Platform frame", "FCAW"), ("2026-03-02", "Job 26-030", "Skid frame", "FCAW"),
                     ("2026-07-21", "Job 26-090", "Pipe supports", "FCAW"), ("2026-10-08", "Job 26-118", "W-17, W-22", "FCAW")]),
}


def wpq(c, welder, bad):
    q = WELDERS[welder]
    log = q["log"][:2] if bad and welder == "204" else q["log"]
    p = Page(c, FAB, "WELDER PERFORMANCE QUALIFICATION (WPQ)", [("WPQ no.", f"WPQ-{welder}"), ("Welder stamp", welder),
                                                                ("Test date", q["date"])],
             "Format per ASME BPVC Section IX, Form QW-484A (see QW-301)")
    p.grid([[("Welder's name", q["name"], .5), ("Identification no.", welder, .25), ("Test type", "Test coupon", .25)],
            [("Identification of WPS followed", q["wps"], .5), ("Date welded", q["date"], .5)],
            [("Specification and type/grade of base metal(s)", q["base"], .6), ("Thickness", q["thickness"], .4)]])
    p.section("TESTING VARIABLES AND QUALIFICATION LIMITS (QW-350)")
    p.table(["Welding variables", "Actual values", "Range qualified"], [
        ["Welding process(es)", q["process"], q["process"]],
        ["Type (manual, semi-automatic)", q["type_"], q["type_"]],
        ["Backing (with / without)", q["backing"], "With and without" if welder == "118" else "With"],
        ["Plate / pipe (diameter if pipe)", q["form"], q["diameter"]],
        ["Base metal P-Number to P-Number", "P-No.1 to P-No.1", "P-No.1 through P-No.15F, 34, 41-49"],
        ["Filler metal specification / class (info)", q["filler"], "-"],
        ["Filler metal F-Number(s)", q["fno"], q["fno"] + " and lower"],
        ["Deposit thickness for each process", q["deposit"], q["deposit_range"]],
        ["Position(s)", q["position"], q["pos_range"]],
        ["Vertical progression", "Uphill", "Uphill"],
        ["Base metal thickness", q["thickness"], q["t_range"]],
    ], [.36, .32, .32], size=6.8)
    p.section("RESULTS")
    p.lines(["Visual examination of completed weld (QW-302.4): acceptable.", q["results"] + ".",
             "Film or specimens evaluated by: Halvorsen Test Lab (fictional) · mechanical tests lab no. HTL-W" + welder])
    p.lines(["We certify that the statements in this record are correct and that the test coupons were prepared, welded",
             "and tested in accordance with the requirements of Section IX of the ASME BPVC."])
    p.sign([("Welding supervised by", "K. Mori (fictional)", q["date"]), ("Certified by (QA manager)", "L. Ortega (fictional)", q["date"])])
    p.section("CONTINUITY LOG (QW-322.1) - USE OF EACH PROCESS, AT LEAST ONCE EVERY 6 MONTHS")
    p.table(["Date", "Job", "Weld / work", "Process", "Verified by"], [[*r, "QC - T. Rahman"] for r in log],
            [.16, .16, .26, .18, .24])
    p.lines([f"Last recorded use of {q['process']}: {log[-1][0]}."])
    c.showPage()


# Weld map (A3 landscape) --------------------------------------------------------------------------------------

def dim_h(c, x1, x2, y, label, ext_from=None):
    """Horizontal dimension with arrowheads; extension lines drop to `ext_from` (y) when given."""
    c.setLineWidth(0.35)
    if ext_from is not None:
        for x in (x1, x2):
            c.line(x, ext_from, x, y + 1.5 * mm)
    c.line(x1, y, x2, y)
    for x, s in ((x1, 1), (x2, -1)):
        p = c.beginPath()
        p.moveTo(x, y)
        p.lineTo(x + s * 2.2 * mm, y + 0.7 * mm)
        p.lineTo(x + s * 2.2 * mm, y - 0.7 * mm)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
    text(c, (x1 + x2) / 2, y + 1.2 * mm, label, 6.8, anchor="centre")


def dim_v(c, x, y1, y2, label):
    c.setLineWidth(0.35)
    c.line(x, y1, x, y2)
    for y, s in ((y1, 1), (y2, -1)):
        p = c.beginPath()
        p.moveTo(x, y)
        p.lineTo(x - 0.7 * mm, y + s * 2.2 * mm)
        p.lineTo(x + 0.7 * mm, y + s * 2.2 * mm)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
    c.saveState()
    c.translate(x - 1.3 * mm, (y1 + y2) / 2)
    c.rotate(90)
    text(c, 0, 0, label, 6.8, anchor="centre")
    c.restoreState()


def weld_symbol(c, ax, ay, rx, ry, kind, size="", tail="", right=True, other_side=False):
    """AWS A2.4 weld symbol: arrow from the joint (ax, ay) to a reference line at (rx, ry), groove or fillet symbol,
    size, and a tail with the joint ID / WPS / NDE."""
    c.setStrokeColor(INK)
    c.setFillColor(INK)
    c.setLineWidth(0.5)
    c.line(rx, ry, ax, ay)
    # arrowhead at the joint
    a = math.atan2(ry - ay, rx - ax)
    p = c.beginPath()
    p.moveTo(ax, ay)
    p.lineTo(ax + 2.4 * mm * math.cos(a + 0.3), ay + 2.4 * mm * math.sin(a + 0.3))
    p.lineTo(ax + 2.4 * mm * math.cos(a - 0.3), ay + 2.4 * mm * math.sin(a - 0.3))
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    length = 22 * mm
    x2 = rx + length if right else rx - length
    c.line(rx, ry, x2, ry)
    mid = (rx + x2) / 2
    s = 1 if other_side else -1  # symbols below the line = arrow side
    if kind == "V":
        c.line(mid - 1.8 * mm, ry + s * 3 * mm, mid, ry)
        c.line(mid, ry, mid + 1.8 * mm, ry + s * 3 * mm)
    elif kind == "bevel":
        c.line(mid, ry, mid, ry + s * 3 * mm)
        c.line(mid, ry, mid + 2.4 * mm, ry + s * 3 * mm)
    elif kind == "fillet":
        p = c.beginPath()
        p.moveTo(mid, ry)
        p.lineTo(mid, ry + s * 3 * mm)
        p.lineTo(mid + 3 * mm, ry)
        c.drawPath(p, fill=0, stroke=1)
    if size:
        text(c, mid - 2.8 * mm, ry + s * 2.2 * mm - (1.8 * mm if s < 0 else 0), size, 6.5, anchor="right")
    if tail:  # tail fork at the far end
        c.line(x2, ry, x2 + (1 if right else -1) * 2 * mm, ry + 2 * mm)
        c.line(x2, ry, x2 + (1 if right else -1) * 2 * mm, ry - 2 * mm)
        text(c, x2 + (1 if right else -1) * 3 * mm, ry - 1, tail, 6.3, anchor="left" if right else "right")


def tag(c, x, y, label, r=4.6 * mm, square=False):
    c.setLineWidth(0.6)
    c.setFillColorRGB(1, 1, 1)
    if square:
        c.rect(x - r, y - r * 0.7, 2 * r, 1.4 * r, fill=1)
    else:
        c.circle(x, y, r, fill=1)
    text(c, x, y - 2.3, label, 7, True, anchor="centre")


def elevation(c):
    """Shop-drawing elevation: shell between 2:1 heads (wall shown), tangent lines, nozzle N1 with weld-neck flange,
    saddles welded to a skid, dimensions from the left tangent line, AWS weld symbols and joint tags."""
    s = 130 * mm / 6000  # 6000 mm T/T drawn over 130 mm
    tl, cy = 72 * mm, 196 * mm  # left tangent line, vessel centre line
    L, R, t = 6000 * s, 1220 * s, 1.2 * mm  # T/T length, outside radius, drawn wall
    tr = tl + L
    hd = R / 2  # 2:1 semi-elliptical head depth
    c.setStrokeColor(INK)
    # shell, outside and inside lines
    c.setLineWidth(1.3)
    c.line(tl, cy + R, tr, cy + R)
    c.line(tl, cy - R, tr, cy - R)
    c.setLineWidth(0.5)
    c.line(tl, cy + R - t, tr, cy + R - t)
    c.line(tl, cy - R + t, tr, cy - R + t)
    # heads: half ellipses outside each tangent line
    for x, start in ((tl, 90), (tr, 270)):
        c.setLineWidth(1.3)
        c.arc(x - hd, cy - R, x + hd, cy + R, start, 180)
        c.setLineWidth(0.5)
        c.arc(x - hd + t, cy - R + t, x + hd - t, cy + R - t, start, 180)
    # tangent lines and centre line
    c.setLineWidth(0.4)
    c.setDash([5, 1.5, 1, 1.5])
    c.line(tl - hd - 10 * mm, cy, tr + hd + 10 * mm, cy)
    c.setDash([1.5, 1.5])
    for x in (tl, tr):
        c.line(x, cy - R - 4 * mm, x, cy + R + 4 * mm)
    c.setDash()
    text(c, tl, cy - R - 7 * mm, "T.L.", 6.5, anchor="centre")
    text(c, tr, cy - R - 7 * mm, "T.L.", 6.5, anchor="centre")
    # circumferential seams at the tangent lines (heavy) and the long seam on top (dashed, 30° from top)
    c.setLineWidth(2)
    for x in (tl, tr):
        c.line(x, cy - R, x, cy - R + t)
        c.line(x, cy + R - t, x, cy + R)
    c.setLineWidth(0.6)
    c.setDash([3, 1.5])
    c.line(tl + 4 * mm, cy + R * 0.86, tr - 4 * mm, cy + R * 0.86)
    c.setDash()
    text(c, tl + 6 * mm, cy + R * 0.86 + 1.5 * mm, "LONG SEAM AT 30° FROM TOP", 5.8, color=GREY)

    # nozzle N1: 6in neck, weld-neck flange, at 2100 from the left T.L.
    nx = tl + 2100 * s
    nr = 168.3 / 2 * s * 3  # neck drawn 3x for legibility
    top = cy + R
    c.setLineWidth(1.1)
    c.line(nx - nr, top, nx - nr, top + 14 * mm)
    c.line(nx + nr, top, nx + nr, top + 14 * mm)
    c.rect(nx - nr - 3.5 * mm, top + 14 * mm, 2 * nr + 7 * mm, 3 * mm)  # flange
    c.setLineWidth(0.4)
    c.setDash([4, 1.5, 1, 1.5])
    c.line(nx, top - 4 * mm, nx, top + 21 * mm)
    c.setDash()
    tag(c, nx, top + 26 * mm, "N1")
    text(c, nx - 6 * mm, top + 27 * mm, '6" CL.300 WN RF  ·  SA-106 Gr.B SCH 80', 6.5, anchor="right")
    text(c, nx - 6 * mm, top + 23.5 * mm, "PROJECTION 350 FROM SHELL OD", 6.5, anchor="right")

    # saddles at 900 from each T.L., welded to the skid frame; vessel rests on them in clamp bands (not welded)
    sad = [tl + 900 * s, tr - 900 * s]
    base_y = cy - R - 16 * mm
    for x in sad:
        c.setLineWidth(1.1)
        c.line(x - 9 * mm, cy - R - 1, x - 11 * mm, base_y)
        c.line(x + 9 * mm, cy - R - 1, x + 11 * mm, base_y)
        c.line(x, cy - R - 1, x, base_y)  # web
        c.setLineWidth(0.4)
        c.rect(x - 10 * mm, cy - R - 2.2 * mm, 20 * mm, 1.2 * mm)  # clamp band (bolted)
    c.setLineWidth(1.3)
    c.rect(tl - 12 * mm, base_y - 7 * mm, L + 24 * mm, 7 * mm)  # skid main beam W 200
    c.rect(tl - 16 * mm, base_y - 9.5 * mm, L + 32 * mm, 2.5 * mm)  # base plate
    c.setLineWidth(0.5)
    for x in (tl + L * 0.33, tl + L * 0.66):  # cross beams
        c.rect(x - 2 * mm, base_y - 7 * mm, 4 * mm, 7 * mm)
    text(c, tl + L / 2, base_y - 4.8 * mm, "SKID FRAME  W200 x 46  ·  SA-36", 6.5, anchor="centre")

    # dimensions from the left T.L. (tailed dimensions)
    y1 = top + 34 * mm
    dim_h(c, tl, tr, y1 + 7 * mm, "6000  T/T", ext_from=cy + R + 5 * mm)
    dim_h(c, tl, nx, y1, "2100", ext_from=top + 18 * mm)
    dim_h(c, tl - hd, tl, cy - R - 12 * mm, "610")
    yb = base_y - 16 * mm
    dim_h(c, tl, sad[0], yb, "900", ext_from=base_y - 10 * mm)
    dim_h(c, sad[0], sad[1], yb, "4200  SADDLE CENTRES", ext_from=base_y - 10 * mm)
    dim_h(c, sad[1], tr, yb, "900", ext_from=base_y - 10 * mm)
    dim_v(c, tl - hd - 14 * mm, cy - R, cy + R, "2440 OD SHELL")
    text(c, tr + hd + 3 * mm, cy - R - 18 * mm, "ALL DIMENSIONS IN mm FROM LEFT T.L.", 6.2, color=GREY)

    # weld symbols with joint tags (tail: joint / WPS / NDE)
    weld_symbol(c, tl + 85 * mm, cy + R * 0.86, tl + 72 * mm, top + 10 * mm, "V", "20", "W-11 · WPS-07 · RT", True)
    weld_symbol(c, nx - nr, top + 0.5 * mm, nx - 14 * mm, top + 10 * mm, "bevel", "20", "W-12 · WPS-07 · UT", False)
    weld_symbol(c, tl, cy + R - 0.5 * mm, tl - 14 * mm, top + 14 * mm, "V", "20", "W-14 · WPS-07 · RT", False)
    weld_symbol(c, tr, cy + R - 0.5 * mm, tr - 12 * mm, top + 24 * mm, "V", "20", "W-15 · WPS-07 · RT", False)
    weld_symbol(c, sad[0] - 10.5 * mm, base_y, sad[0] - 26 * mm, base_y - 30 * mm, "fillet", "8", "W-17 · WPS-09 · VT", False)
    weld_symbol(c, tl + L * 0.66 + 2 * mm, base_y - 7 * mm, tl + L * 0.66 + 10 * mm, base_y - 30 * mm, "fillet", "8",
                "W-22 · WPS-09 · VT+MT", True, other_side=True)
    for label, x, y in (("W-11", tl + 84 * mm, top + 16 * mm), ("W-12", nx - 30 * mm, top + 16 * mm),
                        ("W-14", tl - 22 * mm, top + 22 * mm), ("W-15", tr - 8 * mm, top + 32 * mm),
                        ("W-17", sad[0] - 34 * mm, base_y - 24 * mm), ("W-22", tl + L * 0.66 + 22 * mm, base_y - 24 * mm)):
        tag(c, x, y, label, 4.4 * mm, square=True)
    text(c, tl + L / 2, top + 52 * mm, "ELEVATION  ·  NOT TO SCALE", 9, True, anchor="centre")

    # detail A: set-in nozzle, full penetration
    dx, dy = 150 * mm, 62 * mm
    c.setLineWidth(0.5)
    c.rect(dx, dy, 70 * mm, 36 * mm)
    text(c, dx + 2 * mm, dy + 32 * mm, "DETAIL A  ·  N1 SET-IN, FULL PENETRATION (W-12)", 6.8, True)
    c.setLineWidth(1.2)
    c.line(dx + 5 * mm, dy + 10 * mm, dx + 28 * mm, dy + 10 * mm)  # shell, left of opening
    c.line(dx + 42 * mm, dy + 10 * mm, dx + 65 * mm, dy + 10 * mm)
    c.line(dx + 5 * mm, dy + 18 * mm, dx + 26 * mm, dy + 18 * mm)
    c.line(dx + 44 * mm, dy + 18 * mm, dx + 65 * mm, dy + 18 * mm)
    c.line(dx + 30 * mm, dy + 6 * mm, dx + 30 * mm, dy + 28 * mm)  # neck walls
    c.line(dx + 40 * mm, dy + 6 * mm, dx + 40 * mm, dy + 28 * mm)
    c.setLineWidth(0.5)
    for x0, sgn in ((dx + 30 * mm, -1), (dx + 40 * mm, 1)):  # bevel + weld
        p = c.beginPath()
        p.moveTo(x0, dy + 10 * mm)
        p.lineTo(x0 + sgn * 4 * mm, dy + 18 * mm)
        p.lineTo(x0, dy + 18 * mm)
        p.close()
        c.setFillColor(HexColor("#999999"))
        c.drawPath(p, fill=1, stroke=1)
    text(c, dx + 46 * mm, dy + 21 * mm, "45° bevel, 2-3 root gap", 6)
    text(c, dx + 46 * mm, dy + 4 * mm, "SHELL t = 20", 6)
    text(c, dx + 4 * mm, dy + 22 * mm, "NECK t = 10.97", 6)



JOINTS = [
    # id, description, category, type, t (mm), OD (mm), position, WPS, welder, NDE, PWHT
    ("W-11", "Shell long seam", "A", "Groove", "20", "2440", "1G", "WPS-07", "118", "RT 100%", "Yes"),
    ("W-12", "Nozzle N1 (6in) to shell", "D", "Groove", "20", "168.3", "6G", "WPS-07", "118", "UT 100%", "Yes"),
    ("W-14", "Shell to head, left (circ)", "B", "Groove", "20", "2440", "1G", "WPS-07", "118", "RT 100%", "Yes"),
    ("W-15", "Shell to head, right (circ)", "B", "Groove", "20", "2440", "1G", "WPS-07", "118", "RT 100%", "Yes"),
    ("W-17", "Skid beam to base plate", "-", "Fillet", "12", "n/a", "2F", "WPS-09", "204", "VT 100%", "No"),
    ("W-22", "Skid cross beam, overhead", "-", "Fillet", "12", "n/a", "4F", "WPS-09", "204", "VT 100% + MT 10%", "No"),
]


def drawing(c):
    W, H = landscape(A3)
    c.setPageSize((W, H))
    c.setLineWidth(1)
    c.rect(10 * mm, 10 * mm, W - 20 * mm, H - 20 * mm)
    text(c, 14 * mm, H - 16 * mm, "SYNTHETIC DOCUMENT - generated for software testing - not a real drawing", 7, color=GREY)

    elevation(c)

    def table(x, y, cols, rows, title, size=7):
        rh = 5.4 * mm
        text(c, x, y + 2 * mm, title, 8.5, True)
        total = sum(w for _, w in cols)
        c.setLineWidth(0.5)
        c.setFillColor(SHADE)
        c.rect(x, y - rh, total, rh, fill=1, stroke=1)
        cur = x
        for head, w in cols:
            text(c, cur + 1.2 * mm, y - rh + 1.7 * mm, head, size, True)
            cur += w
        for i, row in enumerate(rows, 1):
            top = y - rh * (i + 1)
            c.rect(x, top, total, rh)
            cur = x
            for v, (_, w) in zip(row, cols, strict=True):
                c.line(cur, top, cur, top + rh)
                text(c, cur + 1.2 * mm, top + 1.7 * mm, v, size)
                cur += w
        return y - rh * (len(rows) + 1)

    cols = [("Joint", 11 * mm), ("Description", 40 * mm), ("Cat.", 8 * mm), ("Type", 12 * mm), ("t (mm)", 11 * mm),
            ("OD (mm)", 13 * mm), ("Pos.", 9 * mm), ("WPS", 14 * mm), ("Welder", 12 * mm), ("NDE", 26 * mm), ("PWHT", 11 * mm)]
    table(232 * mm, 282 * mm, cols, JOINTS, "WELD MAP / WELD TABLE", 6.6)
    y = table(232 * mm, 232 * mm, [("Item", 10 * mm), ("Part", 52 * mm), ("Material", 34 * mm), ("t (mm)", 16 * mm),
                                   ("Heat no.", 22 * mm)],
              [("1", "Shell, 1 course", "SA-516 Gr.70 N", "20", "4A7721"),
               ("2", "Heads, 2:1 SE (2)", "SA-516 Gr.70 N", "20", "4A7721"),
               ("3", "Nozzle neck N1, 6in SCH 80", "SA-106 Gr.B", "10.97", "5B2210"),
               ("4", "Skid beams and base plates", "SA-36", "12", "3C0954")], "MATERIAL LIST")
    design = [("Code", "ASME BPVC VIII-1, 2023 edition"), ("Shell", "2400 ID / 2440 OD x 20 mm (no process piping on this drawing)"),
              ("Design pressure", "1.6 MPa (16 bar)"),
              ("Design temperature", "210 °C"), ("MDMT", "-20 °C at 1.6 MPa"), ("Corrosion allowance", "3 mm"),
              ("Joint efficiency", "E = 1.0 (full RT, Cat. A and B)"),
              ("Hydrotest", "UG-99(b): 1.3 x MAWP = 2.08 MPa minimum, hold 30 min"),
              ("PWHT", "Required by service (caustic, client spec NR-210): 620 ± 15 °C, 1 h per 25 mm")]
    text(c, 232 * mm, y - 6 * mm, "DESIGN DATA", 8.5, True)
    for i, (k, v) in enumerate(design):
        yy = y - 12 * mm - i * 4.5 * mm
        text(c, 232 * mm, yy, k, 7, True)
        text(c, 266 * mm, yy, v, 7)
    notes = ["1. Construction per ASME BPVC VIII-1, 2023 edition. Welding per ASME IX; NDE per ASME V.",
             "2. Category A and B butt welds: full radiography per UW-11(a). Nozzle N1 weld: UT 100 %.",
             "3. PWHT of the vessel (W-11, W-12, W-14, W-15) after all pressure welding; no welding after PWHT.",
             "4. Skid frame (W-17, W-22) is a non-pressure structure; vessel saddles are bolted to it. No PWHT.",
             "5. Weld IDs in boxes and weld-symbol tails refer to the weld table. Production positions as listed."]
    text(c, 20 * mm, 100 * mm, "NOTES", 8.5, True)
    for i, n in enumerate(notes):
        text(c, 20 * mm, 94 * mm - i * 4.6 * mm, n, 7)
    bx, by, bw, bh = 232 * mm, 14 * mm, 174 * mm, 40 * mm
    c.setLineWidth(0.8)
    c.rect(bx, by, bw, bh)
    for yy in (by + 10 * mm, by + 20 * mm, by + 30 * mm):
        c.line(bx, yy, bx + bw, yy)
    c.line(bx + 87 * mm, by, bx + 87 * mm, by + 30 * mm)
    text(c, bx + 3 * mm, by + 33 * mm, "PRESSURE VESSEL V-110 ON SKID  ·  SHOP DRAWING / WELD MAP", 9.5, True)
    for i, (k, v) in enumerate([("Drawing no.", "HBK-PV-110"), ("Revision", "B"), ("Client", CLIENT), ("Scale", "NTS"),
                                ("Drawn", "M. Tanaka (fictional)  2026-09-18"), ("Checked", "R. Lindqvist (fictional)  2026-09-19")]):
        xx, yy = bx + 3 * mm + (i % 2) * 87 * mm, by + 23 * mm - (i // 2) * 10 * mm
        text(c, xx, yy + 3 * mm, k, 6, color=GREY)
        text(c, xx, yy - 1 * mm, v, 8, True)
    c.showPage()
    c.setPageSize(A4)


# As-built records ---------------------------------------------------------------------------------------------

WELD_LOG = [  # joint, date, welder, WPS, heat side A, heat side B, amps, volts, filler lot
    ("W-11", "2026-10-05", "118", "WPS-07", "4A7721", "4A7721", "125", "23", "E7018 L-5521"),
    ("W-14", "2026-10-06", "118", "WPS-07", "4A7721", "4A7721", "128", "23", "E7018 L-5521"),
    ("W-15", "2026-10-06", "118", "WPS-07", "4A7721", "4A7721", "126", "24", "E7018 L-5521"),
    ("W-12", "2026-10-07", "118", "WPS-07", "5B2210", "4A7721", "118", "22", "E7018 L-5521"),
    ("W-17", "2026-10-08", "204", "WPS-09", "3C0954", "3C0954", "215", "26", "E71T-1C L-0932"),
    ("W-22", "2026-10-08", "204", "WPS-09", "3C0954", "3C0954", "220", "27", "E71T-1C L-0932"),
]


def weld_log(c, bad):
    p = Page(c, FAB, "WELD LOG / FABRICATION RECORD", [("Record no.", "ASB-01"), ("Revision", "A"), ("Job", "26-118"),
                                                       ("Drawing", "HBK-PV-110 rev B")], JOB)
    p.section("PRODUCTION WELDS AS WELDED")
    rows = [list(r) for r in WELD_LOG]
    if bad:
        rows[1][2] = "131"
    p.table(["Joint", "Date welded", "Welder", "WPS", "Heat side A", "Heat side B", "Amps", "Volts", "Filler lot", "Visual"],
            [[*r, "Acc."] for r in rows], [.07, .12, .08, .09, .11, .11, .07, .07, .17, .11], size=6.8)
    p.y -= 3 * mm
    p.lines(["Amps and volts: average of the readings taken by the welding inspector on each pass.",
             "Heat numbers read from the hard stamping on each side of the joint at fit-up.",
             "Visual examination of each completed weld per ASME VIII-1 UW-35 and UW-38 by the welding inspector."])
    p.sign([("Welding inspector", "T. Rahman (fictional)", "2026-10-09"), ("QC manager", "L. Ortega (fictional)", "2026-10-09")])
    c.showPage()


def pwht_chart(c, bad):
    hold = 35 if bad else 65
    p = Page(c, FAB, "POSTWELD HEAT TREATMENT RECORD", [("Load no.", "L-01"), ("Furnace", "F-2 (gas fired)"),
                                                         ("Date", "2026-10-10"), ("Procedure", "HT-PROC-03 rev 2")], JOB)
    p.section("LOAD")
    p.grid([[("Items in load", "Vessel V-110 complete: joints W-11, W-12, W-14, W-15", .7), ("Governing thickness", "20 mm", .3)],
            [("Required (WPS-07 / drawing)", "620 ± 15 °C, 1 h per 25 mm, 15 min minimum = 48 min", .7),
             ("Thermocouples", "4 (TC1-TC4), on the vessel", .3)]])
    p.section("RECORDED CYCLE")
    p.table(["Stage", "Requirement (UCS-56(d))", "Recorded"], [
        ["Loading temperature", "425 °C maximum", "300 °C"],
        ["Heating rate above 425 °C", "222 °C/h maximum (222 x 25 / t, 222 max.)", "150 °C/h"],
        ["Soak temperature", "605 - 635 °C", "620 °C (TC range 612 - 626 °C)"],
        ["Holding time at soak", "48 min minimum", f"{hold} min"],
        ["Cooling rate above 425 °C", "278 °C/h maximum", "180 °C/h"],
        ["Below 425 °C", "-", "Still air"],
    ], [.3, .4, .3])
    # temperature-time chart
    c2 = p.c
    x0, y0, cw, ch = p.x0 + 12 * mm, p.y - 78 * mm, p.x1 - p.x0 - 20 * mm, 66 * mm
    text(c2, p.x0, p.y - 6 * mm, "CHART  (TC average, °C vs h)", 7.5, True)
    c2.setLineWidth(0.5)
    c2.rect(x0, y0, cw, ch)
    t_end = 10.0
    sx, sy = cw / t_end, ch / 700
    for t in range(0, 11):
        text(c2, x0 + t * sx, y0 - 3.5 * mm, str(t), 6, anchor="centre")
    for T in (0, 200, 425, 620, 700):
        text(c2, x0 - 1.5 * mm, y0 + T * sy - 1, str(T), 6, anchor="right")
        c2.setStrokeColor(SHADE)
        c2.line(x0, y0 + T * sy, x0 + cw, y0 + T * sy)
    c2.setStrokeColor(INK)
    heat_h = (620 - 425) / 150
    pts = [(0, 300), (0.6, 425), (0.6 + heat_h, 620), (0.6 + heat_h + hold / 60, 620),
           (0.6 + heat_h + hold / 60 + (620 - 425) / 180, 425), (t_end, 120)]
    c2.setLineWidth(1.3)
    for (ta, Ta), (tb, Tb) in zip(pts, pts[1:]):
        c2.line(x0 + ta * sx, y0 + Ta * sy, x0 + tb * sx, y0 + Tb * sy)
    p.y = y0 - 8 * mm
    p.sign([("Heat treatment operator", "D. Kowalski (fictional)", "2026-10-10"),
            ("QC manager", "L. Ortega (fictional)", "2026-10-11")])
    c.showPage()


NDE = [  # report, method, joint, extent %, technique, result
    ("RT-019", "RT", "W-11", "100", "Ir-192, DWSI, film class 1, wire IQI 1B", "ACCEPT"),
    ("RT-020", "RT", "W-14", "100", "Ir-192, DWSI, film class 1, wire IQI 1B", "ACCEPT"),
    ("RT-021", "RT", "W-15", "100", "Ir-192, DWSI, film class 1, wire IQI 1B", "ACCEPT"),
    ("UT-022", "UT", "W-12", "100", "Pulse echo, 45°/60°/70° probes, 4 MHz", "ACCEPT"),
    ("VT-031", "VT", "W-17", "100", "Direct visual, gauge and torch", "ACCEPT"),
    ("VT-031", "VT", "W-22", "100", "Direct visual, gauge and torch", "ACCEPT"),
    ("MT-033", "MT", "W-22", "10", "Yoke AC, wet fluorescent, 1 location 300 mm", "ACCEPT"),
]


def nde_reports(c, bad):
    rows = [list(r) for r in NDE]
    if bad:
        rows[2][5] = "REJECT"
    by_report: dict[str, list[list[str]]] = {}
    for r in rows:
        by_report.setdefault(r[0], []).append(r)
    p = Page(c, "Lumen NDT Services (fictional)", "NDE REPORT PACKAGE - INDEX",
             [("Package", "NDE-26-118"), ("Client", FAB.split(" (")[0]), ("Drawing", "HBK-PV-110 rev B")], JOB)
    p.table(["Report no.", "Method", "Joint(s)", "Result"],
            [[k, v[0][1], ", ".join(r[2] for r in v), " / ".join(dict.fromkeys(r[5] for r in v))] for k, v in by_report.items()],
            [.25, .2, .3, .25])
    c.showPage()
    for report, items in by_report.items():
        method = items[0][1]
        name = {"RT": "RADIOGRAPHIC", "UT": "ULTRASONIC", "VT": "VISUAL", "MT": "MAGNETIC PARTICLE"}[method]
        p = Page(c, "Lumen NDT Services (fictional)", f"{name} EXAMINATION REPORT",
                 [("Report no.", report), ("Date", "2026-10-09" if method in "RTUT" else "2026-10-08"),
                  ("Drawing / rev", "HBK-PV-110 / B"), ("Procedure", f"LN-{method}-01 rev 4")], JOB)
        p.grid([[("Code / acceptance", "ASME V Art. " + {"RT": "2", "UT": "4", "VT": "9", "MT": "7"}[method] +
                  "; acceptance ASME VIII-1 " + {"RT": "UW-51", "UT": "Appendix 12", "VT": "UW-35", "MT": "Appendix 6"}[method], .7),
                 ("Material / thickness", "SA-516 Gr.70, 20 mm" if method in "RTUT" else "SA-36, 12 mm", .3)]])
        p.section("RESULTS PER JOINT")
        p.table(["Joint", "Extent", "Technique", "Indications", "Result"],
                [[r[2], f"{r[3]} %", r[4], "Porosity cluster 12 mm at 840-852 mm" if r[5] == "REJECT" else "None relevant", r[5]]
                 for r in items], [.1, .1, .4, .28, .12], size=6.6)
        if any(r[5] == "REJECT" for r in items):
            p.lines(["Repair required. Re-examine after repair under a new report number."])
        p.sign([("Examined by (ASNT SNT-TC-1A Level II)", "P. Lindgren (fictional), Level II", "Cert. LN-2231"),
                ("Reviewed by (Level III)", "A. Moreau (fictional), Level III", "Cert. LN-0042")])
        c.showPage()


def hydrotest(c, bad):
    pressure = "1.90" if bad else "2.10"
    p = Page(c, FAB, "HYDROSTATIC TEST REPORT", [("Report no.", "HT-0412"), ("Date", "2026-10-13"),
                                                  ("Code", "ASME VIII-1 UG-99")], JOB)
    p.section("TEST DATA")
    p.grid([[("Item", "Vessel V-110 after PWHT", .5), ("Test medium", "Water, chloride < 50 ppm", .5)],
            [("Test pressure applied (at top)", f"{pressure} MPa", .34), ("Holding time", "30 min", .33), ("Metal temperature", "18 °C", .33)],
            [("Water temperature", "17 °C", .34), ("Inspection pressure", f"{pressure} MPa", .33), ("Leaks", "None", .33)]])
    p.section("GAUGES")
    p.table(["Gauge", "Range", "Serial no.", "Calibrated", "Due"],
            [["Test gauge 1", "0 - 4 MPa", "G-11-4471", "2026-07-02", "2027-01-02"],
             ["Test gauge 2", "0 - 4 MPa", "G-12-4480", "2026-07-02", "2027-01-02"]], [.2, .2, .2, .2, .2])
    p.section("PRESSURE / TIME")
    p.table(["Time", "Pressure (MPa)", "Note"], [["10:00", "0", "Start, vents closed"], ["10:20", pressure, "Test pressure reached"],
                                                ["10:50", pressure, "End of hold; examined all welds"], ["11:00", "0", "Depressurized"]],
            [.2, .3, .5])
    p.y -= 2 * mm
    p.lines(["Result: no leaks, no visible deformation."])
    p.sign([("Tested by", "T. Rahman (fictional), QC", "2026-10-13"), ("Witnessed by", AI, "2026-10-13")])
    c.showPage()


def thickness_survey(c):
    p = Page(c, "Lumen NDT Services (fictional)", "ULTRASONIC THICKNESS SURVEY",
             [("Report no.", "UTT-05"), ("Date", "2026-10-12"), ("Drawing / rev", "HBK-PV-110 / B")], JOB)
    p.grid([[("Instrument", "Olympus 38DL Plus (fictional unit 38-0991), calibrated 2026-06-30", .7), ("Couplant", "Gel", .3)]])
    p.section("READINGS (minimum of 4 points per location)")
    p.table(["Location", "Heat no.", "Measured minimum (mm)", "Required (design + CA, mm)", "Result"],
            [["Shell course 1", "4A7721", "19.8", "17.0", "Acceptable"], ["Head, left", "4A7721", "19.1", "16.9", "Acceptable"],
             ["Head, right", "4A7721", "19.2", "16.9", "Acceptable"]], [.24, .16, .2, .24, .16])
    p.sign([("Examined by (Level II)", "P. Lindgren (fictional), Level II", "2026-10-12")])
    c.showPage()


# Output -------------------------------------------------------------------------------------------------------

def render(path: Path, draw, *args, size=A4):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=size, invariant=1)  # same bytes every run
    c.setTitle(f"{path.stem} (synthetic)")
    c.setAuthor(FAB)
    draw(c, *args)
    c.save()


def build(root: Path, bad: bool) -> None:
    render(root / "1-mtc" / "MTC_4A7721.pdf", mtc, "4A7721", bad)
    render(root / "1-mtc" / "MTC_5B2210.pdf", mtc, "5B2210", bad)
    render(root / "1-mtc" / "MTC_3C0954.pdf", mtc, "3C0954", bad)
    render(root / "2-wps" / "WPS-07_PQR-07.pdf", wps, "WPS-07")
    render(root / "2-wps" / "WPS-09_PQR-09.pdf", wps, "WPS-09")
    render(root / "3-wpq" / "WPQ-118.pdf", wpq, "118", bad)
    render(root / "3-wpq" / "WPQ-204.pdf", wpq, "204", bad)
    render(root / "4-drawing" / "HBK-PV-110_RevB_WeldMap.pdf", drawing, size=landscape(A3))
    render(root / "5-asbuilt" / "ASB-01_Weld_Log.pdf", weld_log, bad)
    render(root / "5-asbuilt" / "PWHT-L01_Chart.pdf", pwht_chart, bad)
    render(root / "5-asbuilt" / "NDE_Reports.pdf", nde_reports, bad)
    render(root / "5-asbuilt" / "HT-0412_Hydrotest.pdf", hydrotest, bad)
    render(root / "5-asbuilt" / "UTT-05_Thickness_Survey.pdf", thickness_survey)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "../example-docs")
    build(out / "acceptable", bad=False)
    build(out / "not-acceptable", bad=True)
    print(f"Wrote {out / 'acceptable'} and {out / 'not-acceptable'}")
