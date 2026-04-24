from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from PIL import Image

from backend.models.ir import Background, Element, PresentationIR, SlideIR


def _rgb_to_hex(rgb: tuple[int, int, int] | None) -> str | None:
    if not rgb:
        return None
    return "#%02X%02X%02X" % rgb


def _pdf_color_to_hex(color: Any) -> str | None:
    if not color:
        return None
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return _rgb_to_hex(tuple(int(c * 255) if c <= 1 else int(c) for c in color[:3]))
    return None


def _pix_to_png(page: fitz.Page, out_path: Path, zoom: float = 2.0) -> None:
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(out_path)


def extract_ir(
    pdf_path: Path,
    assets_dir: Path,
    mode: str,
    enable_ocr: bool,
    split_icons: bool,
    prefer_fonts: bool,
) -> PresentationIR:
    doc = fitz.open(pdf_path)
    slides: list[SlideIR] = []
    diagnostics: dict[str, Any] = {"pages": []}

    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        width = float(page.rect.width)
        height = float(page.rect.height)
        page_dir = assets_dir / f"slide_{page_num}"
        page_dir.mkdir(parents=True, exist_ok=True)

        bg_path = page_dir / "background.png"
        _pix_to_png(page, bg_path, zoom=2.0)

        slide = SlideIR(
            page_number=page_num,
            width=width,
            height=height,
            background=Background(type="image", path=str(bg_path)),
            elements=[],
        )

        text_id = 0
        image_id = 0
        shape_id = 0

        text_blocks = page.get_text("dict").get("blocks", [])
        for b in text_blocks:
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
                text_id += 1
                font_name = first.get("font", "Arial") if prefer_fonts else "Arial"
                flags = int(first.get("flags", 0))
                slide.elements.append(
                    Element(
                        id=f"text_{page_num:03d}_{text_id:04d}",
                        type="text",
                        text=text,
                        x=float(x0),
                        y=float(y0),
                        width=float(x1 - x0),
                        height=float(y1 - y0),
                        font_size=float(first.get("size", 14)),
                        font_family=font_name,
                        font_color=_pdf_color_to_hex(first.get("color")),
                        bold=bool(flags & 16),
                        italic=bool(flags & 2),
                        underline=bool(flags & 4),
                        alignment="left",
                        z_index=40,
                    )
                )

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
                    id=f"image_{page_num:03d}_{image_id:04d}",
                    type="icon" if split_icons and max(rect.width, rect.height) < 64 else "image",
                    path=str(img_path),
                    x=float(rect.x0),
                    y=float(rect.y0),
                    width=float(rect.width),
                    height=float(rect.height),
                    z_index=30,
                )
            )

        for d in page.get_drawings():
            rect = d.get("rect")
            if not rect:
                continue
            shape_id += 1
            slide.elements.append(
                Element(
                    id=f"shape_{page_num:03d}_{shape_id:04d}",
                    type="shape",
                    shape_type="rectangle",
                    x=float(rect.x0),
                    y=float(rect.y0),
                    width=float(rect.width),
                    height=float(rect.height),
                    fill_color=_pdf_color_to_hex(d.get("fill")),
                    line_color=_pdf_color_to_hex(d.get("color")) or "#000000",
                    line_width=float(d.get("width", 1.0)),
                    opacity=float(d.get("fill_opacity", 1.0)),
                    border_radius=0,
                    z_index=10,
                )
            )

        if enable_ocr:
            try:
                import pytesseract

                image = Image.open(bg_path)
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                for i, txt in enumerate(ocr_data.get("text", [])):
                    text = (txt or "").strip()
                    conf = float(ocr_data.get("conf", ["-1"])[i] or -1)
                    if not text or conf < 55:
                        continue
                    x = float(ocr_data["left"][i]) / 2.0
                    y = float(ocr_data["top"][i]) / 2.0
                    w = float(ocr_data["width"][i]) / 2.0
                    h = float(ocr_data["height"][i]) / 2.0
                    text_id += 1
                    slide.elements.append(
                        Element(
                            id=f"ocr_text_{page_num:03d}_{text_id:04d}",
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

        slides.append(slide)
        diagnostics["pages"].append({"page": page_num, "elements": len(slide.elements)})

    doc.close()
    return PresentationIR(source_pdf=str(pdf_path), mode=mode, slides=slides, diagnostics=diagnostics)
