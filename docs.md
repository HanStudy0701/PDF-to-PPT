# Architecture & IR Design

## Pipeline

1. Upload PDF.
2. Parse each page into layers:
   - background
   - text
   - images/icons
   - vector shapes
3. Optional OCR supplements missing text.
4. Optional background reconstruction (inpainting).
5. Serialize IR to JSON.
6. Build PPTX from IR with element z-order.

## Coordinate mapping

- PDF coordinates from PyMuPDF text/image rects are top-left based in extracted dict/rect APIs used here.
- PPTX uses top-left origin.
- Unit conversion: PDF points (pt) to inches for `python-pptx`.

## Conversion modes

- `maximum_editable`: prioritize element decomposition + editable objects.
- `visual_fidelity`: keep stronger background image and safer placement.
- `hybrid_safe`: keep page-level reference background and overlay editable layers where safe.

## Intermediate Representation (IR)

```json
{
  "source_pdf": "input.pdf",
  "mode": "maximum_editable",
  "slides": [
    {
      "page_number": 1,
      "width": 960,
      "height": 540,
      "background": {
        "type": "image",
        "path": "/tmp/pdf_to_ppt_jobs/<id>/assets/slide_1/background_reconstructed.png"
      },
      "elements": [
        {
          "id": "text_001",
          "type": "text",
          "text": "Example title",
          "x": 100,
          "y": 80,
          "width": 800,
          "height": 100,
          "font_size": 36,
          "font_family": "Arial",
          "font_color": "#000000",
          "bold": true,
          "italic": false,
          "alignment": "left",
          "z_index": 10
        }
      ]
    }
  ],
  "diagnostics": {
    "pages": [
      {
        "page": 1,
        "elements": 25
      }
    ]
  }
}
```
