# PDF to Editable PPTX Converter

A full-stack web app for converting NotebookLM-style presentation PDFs into **editable PPTX** files.

## Stack

- Frontend: HTML + Tailwind + PDF.js (served by FastAPI)
- Backend: FastAPI
- PDF parsing: PyMuPDF (`fitz`), optional `pdfplumber`
- OCR: optional `pytesseract`
- Imaging: Pillow, OpenCV (optional for inpainting)
- PPTX generation: `python-pptx`

## Features

- Drag/drop PDF upload
- 3 conversion modes:
  - Maximum Editable
  - Visual Fidelity
  - Hybrid Safe
- Advanced options (OCR, background inpainting, reference slide image, icon split, font priority, debug report)
- Conversion report (JSON)
- Download generated PPTX, assets ZIP, report JSON, error log
- Before/After preview

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Open: http://localhost:8000

## API

- `POST /api/convert` convert uploaded PDF to PPTX
- `GET /api/jobs/{job_id}` job metadata
- `GET /api/jobs/{job_id}/download/pptx`
- `GET /api/jobs/{job_id}/download/assets`
- `GET /api/jobs/{job_id}/download/report`
- `GET /api/jobs/{job_id}/download/errors`
- `GET /api/jobs/{job_id}/preview/before/{page}`
- `GET /api/jobs/{job_id}/preview/after/{page}`

## Notes

- This implementation favors editability first, with graceful fallback to image layers for complex vectors/backgrounds.
- For best OCR results, install Tesseract on the host OS.
