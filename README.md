# PDF to Editable PPTX Converter (Web App)

把 NotebookLM 產生的簡報型 PDF 轉為 **可編輯 PPTX** 的網站應用程式。

## 主要能力

- 每頁 PDF → 一頁 PPTX slide
- 拆解層級：背景 / 文字 / 圖片 / icon / shape
- 3 種模式：Maximum Editable / Visual Fidelity / Hybrid Safe
- 可選 OCR、背景補洞、相鄰文字合併
- 下載：PPTX、素材包、Report JSON、IR JSON、Errors
- 前端網頁提供拖拉上傳、即時 PDF 第一頁預覽、轉換後預覽

## 技術棧

- Backend: FastAPI
- PDF parsing: PyMuPDF
- OCR: pytesseract (optional)
- Image processing: OpenCV + Pillow
- PPTX generation: python-pptx
- Frontend: HTML + Tailwind + PDF.js

## 執行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

開啟：`http://localhost:8000`

## API

- `POST /api/convert`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/download/pptx`
- `GET /api/jobs/{job_id}/download/assets`
- `GET /api/jobs/{job_id}/download/report`
- `GET /api/jobs/{job_id}/download/ir`
- `GET /api/jobs/{job_id}/download/errors`
- `GET /api/jobs/{job_id}/preview/before/{page}`
- `GET /api/jobs/{job_id}/preview/after/{page}`
