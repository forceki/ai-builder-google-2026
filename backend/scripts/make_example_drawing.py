"""Draw a synthetic pressure-vessel shop drawing / weld map (A3, vector PDF) for testing the welding-drawing slot.

    uv run --with reportlab python -m scripts.make_example_drawing [out.pdf]

Matches the sample dossier: drawing HBK-PV-110 rev B, joints W-11…W-22, WPS-07 / WPS-09, welders 118 and 204.
Everything is fictional and every sheet says SYNTHETIC.
"""

import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

INK = HexColor("#111111")
GREY = HexColor("#666666")
W, H = landscape(A3)

JOINTS = [
    # id, description, category, type, thickness, position, WPS, welder, NDE, PWHT
    ("W-11", "Shell long seam", "A", "1", "40", "3G", "WPS-07", "118", "RT 100%", "Yes"),
    ("W-12", "Nozzle N1 to shell", "D", "7", "40", "6G", "WPS-07", "118", "UT 100% + RT 10%", "Yes"),
    ("W-13", "Nozzle N2 to shell", "D", "7", "40", "6G", "WPS-07", "118", "UT 100%", "Yes"),
    ("W-14", "Shell to head, left (circ)", "B", "1", "40", "2G", "WPS-07", "118", "RT 100%", "Yes"),
    ("W-15", "Shell to head, right (circ)", "B", "1", "40", "2G", "WPS-07", "118", "RT 100%", "Yes"),
    ("W-17", "Saddle to wear plate, fillet", "-", "fillet", "12", "2F", "WPS-09", "204", "VT 100%", "No"),
    ("W-22", "Wear plate to shell, fillet", "-", "fillet", "12", "4F", "WPS-09", "204", "VT 100% + MT 10%", "No"),
]
MATERIALS = [
    ("1", "Shell, 1 course", "SA-516 Gr.70 N", "40", "4A7721"),
    ("2", "Heads, 2:1 SE (2)", "SA-516 Gr.70 N", "40", "4A7721"),
    ("3", "Nozzle neck N1, N2  6in", "SA-106 Gr.B", "SCH 80", "5B2210"),
    ("4", "Flanges N1, N2  6in Cl.300 WN", "SA-105", "-", "5C1180"),
    ("5", "Saddles and wear plates", "S355J2+N", "12", "3C0954"),
]


def text(c, x, y, s, size=7, bold=False, color=INK, anchor="left"):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    {"left": c.drawString, "centre": c.drawCentredString, "right": c.drawRightString}[anchor](x, y, s)


def bubble(c, x, y, label, lx=None, ly=None):
    """Weld ID in a circle, with a leader line to the weld."""
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    if lx is not None:
        c.line(x, y, lx, ly)
        c.circle(lx, ly, 0.9, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.circle(x, y, 5.2 * mm, fill=1)
    text(c, x, y - 2.4, label, 7.5, True, anchor="centre")


def dim(c, x1, y, x2, label):
    c.setStrokeColor(INK)
    c.setLineWidth(0.4)
    c.line(x1, y, x2, y)
    for x in (x1, x2):
        c.line(x, y - 3, x, y + 3)
    text(c, (x1 + x2) / 2, y + 2.5, label, 7, anchor="centre")


def fillet_note(c, x, y, lx, ly, s):
    c.setLineWidth(0.4)
    c.line(x, y, lx, ly)
    text(c, x + 2, y + 2, s, 6.5)


def vessel(c):
    cx, cy = 50 * mm, 185 * mm  # left tangent line, centre line
    L, R = 160 * mm, 28 * mm  # shell length and radius (not to scale)
    hd = R / 2  # 2:1 head depth
    c.setStrokeColor(INK)
    c.setLineWidth(1.4)
    c.line(cx, cy + R, cx + L, cy + R)
    c.line(cx, cy - R, cx + L, cy - R)
    c.ellipse(cx - hd, cy - R, cx + hd, cy + R)
    c.ellipse(cx + L - hd, cy - R, cx + L + hd, cy + R)
    c.setFillColorRGB(1, 1, 1)
    c.rect(cx, cy - R + 0.8, L, 2 * R - 1.6, fill=1, stroke=0)  # hide the inner halves of the head ellipses
    c.setStrokeColor(INK)
    c.setLineWidth(0.5)
    c.setDash([6, 2, 1, 2])
    c.line(cx - hd - 8 * mm, cy, cx + L + hd + 8 * mm, cy)
    c.setDash()
    # seams: circ seams at the tangent lines, long seam along the top of the shell
    c.setLineWidth(0.6)
    c.setDash([2, 1.5])
    c.line(cx, cy - R, cx, cy + R)
    c.line(cx + L, cy - R, cx + L, cy + R)
    c.line(cx + 8 * mm, cy + R - 4 * mm, cx + L - 8 * mm, cy + R - 4 * mm)
    c.setDash()
    # nozzles N1 (top) and N2 (bottom) with weld-neck flanges
    for nx, up, tag in ((cx + 45 * mm, True, "N1"), (cx + 80 * mm, False, "N2")):
        s = 1 if up else -1
        y0 = cy + s * R
        c.setLineWidth(1.1)
        c.line(nx - 5 * mm, y0, nx - 5 * mm, y0 + s * 20 * mm)
        c.line(nx + 5 * mm, y0, nx + 5 * mm, y0 + s * 20 * mm)
        c.rect(nx - 10 * mm, y0 + s * 20 * mm - (0 if up else 5 * mm), 20 * mm, 5 * mm)
        text(c, nx + 12 * mm, y0 + s * 22 * mm, f"{tag}  6in Cl.300 WN", 7)
    # manway outline on the shell (dashed circle)
    c.setDash([3, 2])
    c.circle(cx + 118 * mm, cy, 15 * mm)
    c.setDash()
    text(c, cx + 118 * mm, cy - 20 * mm, "M1  18in manway", 6.5, anchor="centre")
    # saddles with wear plates
    for sx in (cx + 22 * mm, cx + 138 * mm):
        c.setLineWidth(1.1)
        c.rect(sx - 16 * mm, cy - R - 2 * mm, 32 * mm, 2 * mm)  # wear plate
        c.line(sx - 11 * mm, cy - R - 2 * mm, sx - 14 * mm, cy - R - 24 * mm)
        c.line(sx + 11 * mm, cy - R - 2 * mm, sx + 14 * mm, cy - R - 24 * mm)
        c.rect(sx - 19 * mm, cy - R - 27 * mm, 38 * mm, 3 * mm)  # base plate
    # weld bubbles
    bubble(c, cx + 20 * mm, cy + R + 14 * mm, "W-11", cx + 26 * mm, cy + R - 4 * mm)
    bubble(c, cx + 25 * mm, cy + R + 30 * mm, "W-12", cx + 40 * mm, cy + R)
    bubble(c, cx + 100 * mm, cy - R - 14 * mm, "W-13", cx + 85 * mm, cy - R)
    bubble(c, cx - 16 * mm, cy + R + 12 * mm, "W-14", cx, cy + R - 6 * mm)
    bubble(c, cx + L + 16 * mm, cy + R + 12 * mm, "W-15", cx + L, cy + R - 6 * mm)
    bubble(c, cx + 2 * mm, cy - R - 38 * mm, "W-17", cx + 10 * mm, cy - R - 14 * mm)
    bubble(c, cx + 40 * mm, cy - R - 38 * mm, "W-22", cx + 34 * mm, cy - R - 2 * mm)
    fillet_note(c, cx + 150 * mm, cy - R - 12 * mm, cx + 152 * mm, cy - R - 2 * mm, "8 FILLET, ALL ROUND")
    # dimensions
    dim(c, cx, cy + R + 46 * mm, cx + L, "7'-6\" (2286) SHELL LENGTH T/T")
    dim(c, cx + 22 * mm, cy - R - 48 * mm, cx + 138 * mm, "5'-0\" (1524) SADDLE CENTRES")
    c.setLineWidth(0.4)
    c.line(cx - hd - 14 * mm, cy - R, cx - hd - 14 * mm, cy + R)
    text(c, cx - hd - 16 * mm, cy - 2, "36in OD", 7, anchor="right")
    text(c, cx + L / 2, cy + R + 58 * mm, "ELEVATION  ·  NOT TO SCALE", 9, True, anchor="centre")


def table(c, x, y, cols, rows, title, size=7):
    """Simple grid: cols = [(header, width)]; y is the top edge."""
    row_h = 5.2 * mm
    widths = [w for _, w in cols]
    text(c, x, y + 2 * mm, title, 8.5, True)
    c.setStrokeColor(INK)
    c.setLineWidth(0.5)
    c.setFillColor(HexColor("#EEEEEE"))
    c.rect(x, y - row_h, sum(widths), row_h, fill=1, stroke=1)
    cur = x
    for (head, w) in cols:
        text(c, cur + 1.2 * mm, y - row_h + 1.6 * mm, head, size, True)
        cur += w
    for i, row in enumerate(rows, 1):
        top = y - row_h * (i + 1)
        c.rect(x, top, sum(widths), row_h, fill=0, stroke=1)
        cur = x
        for value, w in zip(row, widths, strict=True):
            c.line(cur, top, cur, top + row_h)
            text(c, cur + 1.2 * mm, top + 1.6 * mm, value, size)
            cur += w
    return y - row_h * (len(rows) + 1)


def draw(out: Path) -> None:
    c = canvas.Canvas(str(out), pagesize=(W, H))
    c.setTitle("HBK-PV-110 rev B - Pressure vessel V-110 weld map (synthetic)")
    c.setLineWidth(1)
    c.rect(10 * mm, 10 * mm, W - 20 * mm, H - 20 * mm)
    text(c, 14 * mm, H - 16 * mm, "SYNTHETIC DOCUMENT - generated for software testing - not a real drawing", 7, color=GREY)
    vessel(c)

    weld_cols = [("Joint", 11 * mm), ("Description", 45 * mm), ("Cat.", 8 * mm), ("Type", 10 * mm), ("t (mm)", 10 * mm),
                 ("Pos.", 8 * mm), ("WPS", 14 * mm), ("Welder", 11 * mm), ("NDE", 26 * mm), ("PWHT", 10 * mm)]
    table(c, 250 * mm, 278 * mm, weld_cols, JOINTS, "WELD MAP / WELD TABLE", 6.5)

    y = table(c, 250 * mm, 222 * mm, [("Item", 10 * mm), ("Part", 52 * mm), ("Material", 32 * mm), ("t (mm)", 15 * mm),
                                      ("Heat no.", 24 * mm)], MATERIALS, "MATERIAL LIST")

    design = [("Code", "ASME BPVC VIII-1, 2023 edition"), ("Design pressure", "1.6 MPa (16 bar)"),
              ("Design temperature", "210 °C"), ("MDMT", "-20 °C at 1.6 MPa"), ("Corrosion allowance", "3 mm"),
              ("Joint efficiency", "E = 1.0 (full RT, Cat. A and B)"), ("Hydrotest", "2.08 MPa, 30 min (UG-99)"),
              ("PWHT", "Required, UCS-56: 620 ± 15 °C, 1 h per 25 mm")]
    text(c, 250 * mm, y - 6 * mm, "DESIGN DATA", 8.5, True)
    for i, (k, v) in enumerate(design):
        yy = y - 12 * mm - i * 4.4 * mm
        text(c, 250 * mm, yy, k, 7, True)
        text(c, 284 * mm, yy, v, 7)

    notes = ["1. Construction per ASME BPVC VIII-1, 2023 edition. Welding per ASME IX; NDE per ASME V.",
             "2. All Category A and B butt welds: full radiography per UW-11(a).",
             "3. PWHT after all pressure welding is complete; no welding after PWHT.",
             "4. Weld IDs in circles refer to the weld table. Production positions as listed.",
             "5. Saddle and wear-plate welds are non-pressure attachments."]
    text(c, 20 * mm, 92 * mm, "NOTES", 8.5, True)
    for i, n in enumerate(notes):
        text(c, 20 * mm, 86 * mm - i * 4.6 * mm, n, 7)

    # title block, bottom right
    bx, by, bw, bh = 250 * mm, 14 * mm, 156 * mm, 40 * mm
    c.setLineWidth(0.8)
    c.rect(bx, by, bw, bh)
    for yy in (by + 10 * mm, by + 20 * mm, by + 30 * mm):
        c.line(bx, yy, bx + bw, yy)
    c.line(bx + 75 * mm, by, bx + 75 * mm, by + 30 * mm)
    text(c, bx + 3 * mm, by + 33 * mm, "PRESSURE VESSEL V-110  ·  SHOP DRAWING / WELD MAP", 9.5, True)
    cells = [("Drawing no.", "HBK-PV-110"), ("Revision", "B"), ("Client", "Northfield Refining (fictional)"),
             ("Scale", "NTS"), ("Drawn", "M. Tanaka (fictional)  2026-09-18"), ("Checked", "R. Lindqvist (fictional)")]
    for i, (k, v) in enumerate(cells):
        col, row = i % 2, i // 2
        xx, yy = bx + 3 * mm + col * 75 * mm, by + 23 * mm - row * 10 * mm
        text(c, xx, yy + 3 * mm, k, 6, color=GREY)
        text(c, xx, yy - 1 * mm, v, 8, True)
    c.showPage()
    c.save()


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "../example-docs/5-pressure-vessel/HBK-PV-110_RevB_WeldMap.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    draw(out)
    print(out)
