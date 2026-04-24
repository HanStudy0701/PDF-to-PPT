from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz
from PIL import Image

from backend.models.ir import Background, Element, PresentationIR, SlideIR


def _rgb_to_hex(rgb: tuple[int, int, int] | None) -> str | None:
    if not rgb:
        return None
    return "#%02X%02X%02X" % rgb


def _pdf_color_to_hex(color: Any) -> str | None:
    if color is None:
        return None
    if isinstance(color, int):
        r = (color >> 16) & 255
        g = (color >> 8) & 255
        b = color & 255
        return _rgb_to_hex((r, g, b))
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return _rgb_to_hex(tuple(int(c * 255) if c <= 1 else int(c) for c in color[:3]))
    return None


def _pix_to_png(page: fitz.Page, out_path: Path, zoom: float = 2.0) -> None:
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    pix.save(out_path)


def _extract_text(page: fitz.Page, slide: SlideIR, prefer_fonts: bool) -> int:
    text_id = 0
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            bbox = line.get("bbox")
            if not bbox:
                continue
            x0, y0, x1, y1 = bbox
            first = spans[0]
            flags = int(first.get("flags", 0))
            text_id += 1
            slide.elements.append(
                Element(
                    id=f"text_{slide.page_number:03d}_{text_id:04d}",
                    type="text",
                    text=text,
                    x=float(x0),
                    y=float(y0),
                    width=float(x1 - x0),
                    height=float(y1 - y0),
                    font_size=float(first.get("size", 14)),
                    font_family=first.get("font", "Arial") if prefer_fonts else "Arial",
                    font_color=_pdf_color_to_hex(first.get("color")) or "#111111",
                    bold=bool(flags & 16),
                    italic=bool(flags & 2),
                    underline=bool(flags & 4),
                    alignment="left",
                    z_index=40,
                )
            )
    return text_id


def _extract_images(doc: fitz.Document, page: fitz.Page, page_dir: Path, slide: SlideIR, split_icons: bool) -> None:
    image_id = 0
    for img_idx, img in enumerate(page.get_images(full=True), start=1):
        xref = img[0]
        try:
            info = doc.extract_image(xref)
        except Exception:
            continue

        image_bytes = info.get("image")
        ext = info.get("ext", "png")
        if not image_bytes:
            continue

        img_path = page_dir / f"img_{img_idx}.{ext}"
        img_path.write_bytes(image_bytes)
        rects = page.get_image_rects(xref)
        rect = rects[0] if rects else fitz.Rect(0, 0, 100, 100)
        image_id += 1

        slide.elements.append(
            Element(
                id=f"image_{slide.page_number:03d}_{image_id:04d}",
                type="icon" if split_icons and max(rect.width, rect.height) < 64 else "image",
                path=str(img_path),
                x=float(rect.x0),
                y=float(rect.y0),
                width=float(rect.width),
                height=float(rect.height),
                z_index=30,
            )
        )


def _extract_shapes(page: fitz.Page, slide: SlideIR) -> None:
    shape_id = 0
    for d in page.get_drawings():
        rect = d.get("rect")
        if not rect:
            continue
        if rect.width < 1 or rect.height < 1:
            continue
        shape_id += 1
        slide.elements.append(
            Element(
                id=f"shape_{slide.page_number:03d}_{shape_id:04d}",
                type="shape",
                shape_type="rectangle",
                x=float(rect.x0),
                y=float(rect.y0),
                width=float(rect.width),
                height=float(rect.height),
                fill_color=_pdf_color_to_hex(d.get("fill")) or "#FFFFFF",
                line_color=_pdf_color_to_hex(d.get("color")) or "#000000",
                line_width=float(d.get("width", 1.0)),
                opacity=float(d.get("fill_opacity", 1.0)),
                border_radius=0,
                z_index=10,
            )
        )


def _append_ocr(bg_path: Path, slide: SlideIR, diagnostics: dict[str, Any], current_text_id: int) -> int:
    try:
        import pytesseract

        image = Image.open(bg_path)
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        for i, txt in enumerate(ocr_data.get("text", [])):
            text = (txt or "").strip()
            conf = float(ocr_data.get("conf", ["-1"])[i] or -1)
            if not text or conf < 60:
                continue
            current_text_id += 1
            x = float(ocr_data["left"][i]) / 2.0
            y = float(ocr_data["top"][i]) / 2.0
            w = float(ocr_data["width"][i]) / 2.0
            h = float(ocr_data["height"][i]) / 2.0
            slide.elements.append(
                Element(
                    id=f"ocr_text_{slide.page_number:03d}_{current_text_id:04d}",
                    type="text",
                    text=text,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    font_size=max(10, h * 0.8),
                    font_family="Arial",
                    font_color="#111111",
                    bold=False,
                    italic=False,
                    underline=False,
                    alignment="left",
                    z_index=41,
                    meta={"ocr": True, "confidence": conf},
                )
            )
    except Exception as exc:
        diagnostics.setdefault("warnings", []).append(f"OCR unavailable: {exc}")

    return current_text_id


def _apply_mode_filter(slide: SlideIR, mode: str) -> None:
    if mode == "maximum_editable":
        return
    if mode == "visual_fidelity":
        # Remove tiny noisy shapes that often hurt layout fidelity.
        slide.elements = [
            e for e in slide.elements if not (e.type == "shape" and (e.width < 8 or e.height < 8))
        ]
        return
    if mode == "hybrid_safe":
        # Keep stable editable layers only.
        slide.elements = [e for e in slide.elements if e.type in {"text", "image", "icon"}]


def extract_ir(
    pdf_path: Path,
    assets_dir: Path,
    mode: str,
    enable_ocr: bool,
    split_icons: bool,
    prefer_fonts: bool,
) -> PresentationIR:
    doc = fitz.open(pdf_path)
    diagnostics: dict[str, Any] = {"pages": []}
    slides: list[SlideIR] = []

    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        page_dir = assets_dir / f"slide_{page_num}"
        page_dir.mkdir(parents=True, exist_ok=True)

        bg_path = page_dir / "background.png"
        _pix_to_png(page, bg_path, zoom=2.0)

        slide = SlideIR(
            page_number=page_num,
            width=float(page.rect.width),
            height=float(page.rect.height),
            background=Background(type="image", path=str(bg_path)),
            elements=[],
        )

        text_id = _extract_text(page, slide, prefer_fonts)
        _extract_images(doc, page, page_dir, slide, split_icons)
        _extract_shapes(page, slide)

        if enable_ocr:
            text_id = _append_ocr(bg_path, slide, diagnostics, text_id)

        _apply_mode_filter(slide, mode)
        diagnostics["pages"].append({"page": page_num, "elements": len(slide.elements)})
        slides.append(slide)

    doc.close()
    return PresentationIR(source_pdf=str(pdf_path), mode=mode, slides=slides, diagnostics=diagnostics)
