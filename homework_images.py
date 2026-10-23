"""Render assignment questions from original PDF artwork, never reconstructed math."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from homework_material import PROBLEM_HEADINGS, homework_pdf_path


def question_regions(document, number: int, pages: tuple[int, ...]):
    """Use question headings as crop boundaries; fall back to original full pages."""
    import pymupdf

    headings = []
    for page_index, page in enumerate(document):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                match = next((m for pattern in PROBLEM_HEADINGS if (m := pattern.search(text))), None)
                if match:
                    headings.append((page_index, line["bbox"][1], int(match.group(1))))
    headings.sort()
    starts = [i for i, heading in enumerate(headings) if heading[2] == number]
    if len(starts) != 1:
        return [(p, document[p - 1].rect, False) for p in pages]
    start_index = starts[0]
    first_page, top, _ = headings[start_index]
    following = headings[start_index + 1] if start_index + 1 < len(headings) else None
    regions = []
    for page_number in pages:
        page_index = page_number - 1
        page = document[page_index]
        y0 = max(0, top - 6) if page_index == first_page else 0
        y1 = max(0, following[1] - 6) if following and following[0] == page_index else page.rect.height
        if page_index < first_page or (following and page_index > following[0]) or y1 <= y0:
            # Unexpected metadata: preserve the source page instead of guessing a crop.
            return [(p, document[p - 1].rect, False) for p in pages]
        region = pymupdf.Rect(0, y0, page.rect.width, y1)
        # Trim empty margins using rendered objects, including vector diagrams and
        # image content. Text-only bounds would risk cutting off mathematical artwork.
        ink = pymupdf.Rect()
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                box = pymupdf.Rect(line["bbox"])
                is_footer = (text == str(page_number) and box.y0 > page.rect.height * 0.85
                             and abs((box.x0 + box.x1) / 2 - page.rect.width / 2) < page.rect.width * 0.1)
                if not is_footer and text:
                    visible = box & region
                    if not visible.is_empty:
                        ink |= visible
        for kind, bounds in page.get_bboxlog():
            # A PDF text paint operation can span the entire page, including its
            # footer. Use individual text lines above, retaining artwork bounds here.
            if kind in ("fill-text", "stroke-text", "ignore-text"):
                continue
            visible = pymupdf.Rect(bounds) & region
            if not visible.is_empty:
                ink |= visible
        if not ink.is_empty:
            region = pymupdf.Rect(ink.x0 - 10, ink.y0 - 10, ink.x1 + 10, ink.y1 + 10) & region
        regions.append((page_number, region, True))
    return regions


@lru_cache(maxsize=48)
def _render(path: str, modified_ns: int, size: int, number: int, pages: tuple[int, ...], original: bool):
    import pymupdf

    with pymupdf.open(path) as document:
        if not pages or any(p < 1 or p > len(document) for p in pages):
            raise ValueError("Invalid PDF page references")
        regions = ([(p, document[p - 1].rect, False) for p in pages] if original
                   else question_regions(document, number, pages))
        return tuple({"page": page, "cropped": cropped,
                      "png": document[page - 1].get_pixmap(dpi=160, clip=clip, alpha=False).tobytes("png")}
                     for page, clip, cropped in regions)


def question_images(homework: dict, statement: dict, original: bool = False):
    path: Path = homework_pdf_path(homework)
    stat = path.stat()
    return _render(str(path), stat.st_mtime_ns, stat.st_size, statement["number"], tuple(statement["pages"]), original)
