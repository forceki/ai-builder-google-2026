"""Render the part of a source page a finding points at, so the reviewer sees the evidence next to the finding."""

import io
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from app.ai.inputs import IMAGE_TYPES

MARGIN_Y = 0.04  # of the page, around the box: Gemini's boxes can be a little tight
MARGIN_X = 0.12  # wider sideways, so a table row keeps its label column
ROW_HEIGHT = 0.06
PAGE_MARGIN = 0.05
MAX_WIDTH = 1100
SCALE = 2.0  # PDF render scale (144 dpi)


class NoPreview(ValueError):
    """The file has no page image (e.g. a spreadsheet)."""


def _page_image(filename: str, data: bytes, page: int) -> Image.Image:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        pdf = pdfium.PdfDocument(data)
        try:
            if not 1 <= page <= len(pdf):
                raise NoPreview(f"{filename} has no page {page}")
            return pdf[page - 1].render(scale=SCALE).to_pil().convert("RGB")
        finally:
            pdf.close()
    if suffix in IMAGE_TYPES:
        return Image.open(io.BytesIO(data)).convert("RGB")
    raise NoPreview(f"{filename} has no page image")


def snapshot(filename: str, data: bytes, page: int, box: tuple[int, int, int, int] | None) -> bytes:
    """PNG of the page area in box ([ymin, xmin, ymax, xmax], 0–1000) with a margin; the whole page without a box."""
    img = _page_image(filename, data, page)
    if box:
        w, h = img.size
        ymin, xmin, ymax, xmax = (v / 1000 for v in box)
        left, top = max(0.0, min(xmin, xmax) - MARGIN_X), max(0.0, min(ymin, ymax) - MARGIN_Y)
        right, bottom = min(1.0, max(xmin, xmax) + MARGIN_X), min(1.0, max(ymin, ymax) + MARGIN_Y)
        if abs(ymax - ymin) < ROW_HEIGHT:  # one table row: start at the page margin so its label is in view
            left = min(left, PAGE_MARGIN)
        if right - left > 0.01 and bottom - top > 0.01:
            img = img.crop((round(left * w), round(top * h), round(right * w), round(bottom * h)))
    if img.width > MAX_WIDTH:
        img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)))
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
