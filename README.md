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

## Offline/受限環境說明

若環境無法連外安裝 `fastapi`（如 proxy 受限），本專案內含極簡 `fastapi` 相容 shim（`fastapi/` 目錄），可先讓 `backend.main` 成功 import、完成本地開發與靜態檢查。

> 進入正式部署前，仍建議在可連網環境安裝真實 FastAPI 與完整依賴。
