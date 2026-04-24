from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from backend.models.ir import SlideIR


def reconstruct_background(slide: SlideIR, enable_inpainting: bool) -> str | None:
    if slide.background.type != "image" or not slide.background.path:
        return None

    bg_path = Path(slide.background.path)
    if not bg_path.exists() or not enable_inpainting:
        return str(bg_path)

    img = cv2.imread(str(bg_path), cv2.IMREAD_COLOR)
    if img is None:
        return str(bg_path)

    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    h = slide.height
    scale = img.shape[0] / h if h else 1.0

    for el in slide.elements:
        if el.type in {"text", "image", "icon"}:
            x1 = int(max(0, el.x * scale))
            y1 = int(max(0, el.y * scale))
            x2 = int(min(img.shape[1] - 1, (el.x + el.width) * scale))
            y2 = int(min(img.shape[0] - 1, (el.y + el.height) * scale))
            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)

    if int(mask.sum()) == 0:
        return str(bg_path)

    inpainted = cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)
    out_path = bg_path.with_name("background_reconstructed.png")
    cv2.imwrite(str(out_path), inpainted)
    slide.background.path = str(out_path)
    return str(out_path)


def render_after_preview(slide: SlideIR, out_path: Path) -> Path:
    if slide.background.path and Path(slide.background.path).exists():
        base = Image.open(slide.background.path).convert("RGBA")
    else:
        base = Image.new("RGBA", (int(slide.width), int(slide.height)), (255, 255, 255, 255))

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    import PIL.ImageDraw as ImageDraw

    draw = ImageDraw.Draw(overlay)
    scale_x = base.width / slide.width if slide.width else 1
    scale_y = base.height / slide.height if slide.height else 1

    for el in sorted(slide.elements, key=lambda e: e.z_index):
        x1 = el.x * scale_x
        y1 = el.y * scale_y
        x2 = (el.x + el.width) * scale_x
        y2 = (el.y + el.height) * scale_y
        color = (47, 109, 246, 120) if el.type == "text" else (16, 185, 129, 110)
        draw.rectangle([x1, y1, x2, y2], outline=(255, 255, 255, 255), fill=color)

    out = Image.alpha_composite(base, overlay)
    out.save(out_path)
    return out_path
