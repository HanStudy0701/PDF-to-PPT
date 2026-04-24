from __future__ import annotations

import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.services.background import reconstruct_background, render_after_preview
from backend.services.pdf_parser import extract_ir
from backend.services.ppt_builder import build_pptx
from backend.utils.fs import ROOT, ensure_dir, write_json, zip_dir

app = FastAPI(title="PDF to Editable PPTX Converter")

JOBS: dict[str, dict] = {}

app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/")
def home():
    return FileResponse("frontend/index.html")


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
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF is supported")

    job_id = uuid.uuid4().hex[:12]
    job_dir = ensure_dir(ROOT / job_id)
    assets_dir = ensure_dir(job_dir / "assets")
    previews_dir = ensure_dir(job_dir / "previews")

    pdf_path = job_dir / (file.filename or "input.pdf")
    pdf_path.write_bytes(await file.read())

    errors: list[str] = []

    try:
        ir = extract_ir(
            pdf_path=pdf_path,
            assets_dir=assets_dir,
            mode=mode,
            enable_ocr=enable_ocr,
            split_icons=split_icons,
            prefer_fonts=prefer_fonts,
        )

        if merge_nearby_text:
            # Placeholder for NLP-based text merge; intentionally explicit in report.
            ir.diagnostics["merge_nearby_text"] = "enabled_placeholder"

        for slide in ir.slides:
            if mode == "hybrid_safe" or keep_reference_bg:
                pass
            reconstruct_background(slide, enable_inpainting and mode != "hybrid_safe")

            before = Path(slide.background.path) if slide.background.path else None
            if before and before.exists():
                target = previews_dir / f"before_{slide.page_number}.png"
                if before.resolve() != target.resolve():
                    target.write_bytes(before.read_bytes())

            render_after_preview(slide, previews_dir / f"after_{slide.page_number}.png")

        ir_json_path = job_dir / "ir.json"
        report_path = job_dir / "report.json"
        write_json(ir_json_path, ir.model_dump())
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
                    {
                        "page": s.page_number,
                        "size": [s.width, s.height],
                        "elements": len(s.elements),
                    }
                    for s in ir.slides
                ],
                "diagnostics": ir.diagnostics,
            },
        )

        pptx_path = build_pptx(ir, job_dir / "output.pptx")
        assets_zip_path = zip_dir(assets_dir, job_dir / "assets.zip")

        errors_path = job_dir / "errors.log"
        errors_path.write_text("\n".join(errors), encoding="utf-8")

        JOBS[job_id] = {
            "job_id": job_id,
            "file": file.filename,
            "status": "done",
            "pages": len(ir.slides),
            "pptx": str(pptx_path),
            "assets": str(assets_zip_path),
            "report": str(report_path),
            "errors": str(errors_path),
        }
    except Exception as exc:
        error_trace = traceback.format_exc()
        (job_dir / "errors.log").write_text(error_trace, encoding="utf-8")
        raise HTTPException(status_code=500, detail=f"convert failed: {exc}")

    return JOBS[job_id]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    data = JOBS.get(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="job not found")
    return data


@app.get("/api/jobs/{job_id}/download/pptx")
def dl_pptx(job_id: str):
    return _download(job_id, "pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")


@app.get("/api/jobs/{job_id}/download/assets")
def dl_assets(job_id: str):
    return _download(job_id, "assets", "application/zip")


@app.get("/api/jobs/{job_id}/download/report")
def dl_report(job_id: str):
    return _download(job_id, "report", "application/json")


@app.get("/api/jobs/{job_id}/download/errors")
def dl_errors(job_id: str):
    return _download(job_id, "errors", "text/plain")


@app.get("/api/jobs/{job_id}/preview/before/{page}")
def preview_before(job_id: str, page: int):
    p = ROOT / job_id / "previews" / f"before_{page}.png"
    if not p.exists():
        raise HTTPException(status_code=404, detail="preview not found")
    return FileResponse(p)


@app.get("/api/jobs/{job_id}/preview/after/{page}")
def preview_after(job_id: str, page: int):
    p = ROOT / job_id / "previews" / f"after_{page}.png"
    if not p.exists():
        raise HTTPException(status_code=404, detail="preview not found")
    return FileResponse(p)


def _download(job_id: str, key: str, media_type: str):
    data = JOBS.get(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="job not found")
    p = Path(data[key])
    if not p.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(p, media_type=media_type, filename=p.name)
