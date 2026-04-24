from __future__ import annotations

import traceback
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.utils.fs import ROOT, ensure_dir, write_json, zip_dir

app = FastAPI(title="PDF to Editable PPTX Converter")
JOBS: dict[str, dict] = {}

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def home():
    return FileResponse("frontend/index.html")


def merge_text_blocks(slide: Any, x_gap: float = 12, y_gap: float = 6) -> None:
    texts = sorted([e for e in slide.elements if e.type == "text"], key=lambda e: (round(e.y, 1), e.x))
    non_texts = [e for e in slide.elements if e.type != "text"]
    if not texts:
        return

    merged = []
    cursor = texts[0]
    for nxt in texts[1:]:
        same_line = abs(nxt.y - cursor.y) <= y_gap
        near = abs((cursor.x + cursor.width) - nxt.x) <= x_gap
        if same_line and near and (cursor.font_size == nxt.font_size):
            cursor.text = f"{cursor.text} {nxt.text}".strip()
            cursor.width = (nxt.x + nxt.width) - cursor.x
            cursor.height = max(cursor.height, nxt.height)
        else:
            merged.append(cursor)
            cursor = nxt
    merged.append(cursor)
    slide.elements = non_texts + merged


@app.post("/api/convert")
async def convert(
    file: UploadFile = File(...),
    mode: str = Form("maximum_editable"),
    enable_ocr: bool = Form(False),
    enable_inpainting: bool = Form(True),
    keep_reference_bg: bool = Form(False),
    merge_nearby_text: bool = Form(True),
    split_icons: bool = Form(True),
    prefer_fonts: bool = Form(True),
    debug_report: bool = Form(True),
):
    # Lazy imports keep app importable in limited/offline environments.
    from backend.services.background import reconstruct_background, render_after_preview
    from backend.services.pdf_parser import extract_ir
    from backend.services.ppt_builder import build_pptx

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF is supported")

    if mode not in {"maximum_editable", "visual_fidelity", "hybrid_safe"}:
        raise HTTPException(status_code=400, detail="Invalid mode")

    job_id = uuid.uuid4().hex[:12]
    job_dir = ensure_dir(ROOT / job_id)
    assets_dir = ensure_dir(job_dir / "assets")
    previews_dir = ensure_dir(job_dir / "previews")

    pdf_path = job_dir / file.filename
    pdf_path.write_bytes(await file.read())

    try:
        ir = extract_ir(
            pdf_path=pdf_path,
            assets_dir=assets_dir,
            mode=mode,
            enable_ocr=enable_ocr,
            split_icons=split_icons,
            prefer_fonts=prefer_fonts,
        )

        for slide in ir.slides:
            if merge_nearby_text:
                merge_text_blocks(slide)

            if mode != "hybrid_safe" and not keep_reference_bg:
                reconstruct_background(slide, enable_inpainting)

            bg = Path(slide.background.path) if slide.background.path else None
            if bg and bg.exists():
                before_target = previews_dir / f"before_{slide.page_number}.png"
                if bg.resolve() != before_target.resolve():
                    before_target.write_bytes(bg.read_bytes())
            render_after_preview(slide, previews_dir / f"after_{slide.page_number}.png")

        ir_path = job_dir / "ir.json"
        report_path = job_dir / "report.json"
        write_json(ir_path, ir.model_dump())
        write_json(
            report_path,
            {
                "job_id": job_id,
                "mode": mode,
                "settings": {
                    "enable_ocr": enable_ocr,
                    "enable_inpainting": enable_inpainting,
                    "keep_reference_bg": keep_reference_bg,
                    "merge_nearby_text": merge_nearby_text,
                    "split_icons": split_icons,
                    "prefer_fonts": prefer_fonts,
                    "debug_report": debug_report,
                },
                "slides": [
                    {"page": s.page_number, "size": [s.width, s.height], "elements": len(s.elements)}
                    for s in ir.slides
                ],
                "diagnostics": ir.diagnostics,
            },
        )

        pptx_path = build_pptx(ir, job_dir / "output.pptx")
        assets_zip_path = zip_dir(assets_dir, job_dir / "assets.zip")
        errors_path = job_dir / "errors.log"
        errors_path.write_text("", encoding="utf-8")

        JOBS[job_id] = {
            "job_id": job_id,
            "file": file.filename,
            "status": "done",
            "pages": len(ir.slides),
            "pptx": str(pptx_path),
            "assets": str(assets_zip_path),
            "report": str(report_path),
            "ir": str(ir_path),
            "errors": str(errors_path),
        }
        return JOBS[job_id]
    except Exception as exc:
        trace = traceback.format_exc()
        (job_dir / "errors.log").write_text(trace, encoding="utf-8")
        raise HTTPException(status_code=500, detail=f"convert failed: {exc}")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="job not found")
    return JOBS[job_id]


@app.get("/api/jobs/{job_id}/download/pptx")
def dl_pptx(job_id: str):
    return _download(job_id, "pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")


@app.get("/api/jobs/{job_id}/download/assets")
def dl_assets(job_id: str):
    return _download(job_id, "assets", "application/zip")


@app.get("/api/jobs/{job_id}/download/report")
def dl_report(job_id: str):
    return _download(job_id, "report", "application/json")


@app.get("/api/jobs/{job_id}/download/ir")
def dl_ir(job_id: str):
    return _download(job_id, "ir", "application/json")


@app.get("/api/jobs/{job_id}/download/errors")
def dl_errors(job_id: str):
    return _download(job_id, "errors", "text/plain")


@app.get("/api/jobs/{job_id}/preview/before/{page}")
def preview_before(job_id: str, page: int):
    target = ROOT / job_id / "previews" / f"before_{page}.png"
    if not target.exists():
        raise HTTPException(status_code=404, detail="preview not found")
    return FileResponse(target)


@app.get("/api/jobs/{job_id}/preview/after/{page}")
def preview_after(job_id: str, page: int):
    target = ROOT / job_id / "previews" / f"after_{page}.png"
    if not target.exists():
        raise HTTPException(status_code=404, detail="preview not found")
    return FileResponse(target)


def _download(job_id: str, key: str, media_type: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="job not found")
    path = Path(JOBS[job_id][key])
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path, media_type=media_type, filename=path.name)
