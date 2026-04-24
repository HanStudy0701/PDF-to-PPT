# Architecture & IR

## Web App flow

1. User uploads a PDF in browser.
2. Frontend renders first-page preview via PDF.js.
3. Backend parses PDF per page into IR layers.
4. Optional OCR appends missing text blocks.
5. Optional background reconstruction performs inpainting.
6. IR -> PPTX generation with z-index ordering.
7. User downloads PPTX / assets / report / IR.

## Mode semantics

- `maximum_editable`: keep all parsed text/images/shapes.
- `visual_fidelity`: filter tiny noisy shapes to avoid layout jitter.
- `hybrid_safe`: keep stable editable layers only (text/images/icons), preserve background image.

## Coordinate mapping

- PDF unit: point (pt)
- PPTX unit: inch/EMU
- Conversion: `inch = pt / 72`
- Origin uses top-left in extracted rects and PPTX placement.

## IR Example

```json
{
  "source_pdf": "slides.pdf",
  "mode": "maximum_editable",
  "slides": [
    {
      "page_number": 1,
      "width": 960,
      "height": 540,
      "background": { "type": "image", "path": "assets/slide_1/background.png" },
      "elements": [
        {
          "id": "text_001",
          "type": "text",
          "text": "Title",
          "x": 100,
          "y": 80,
          "width": 420,
          "height": 56,
          "font_size": 36,
          "font_family": "Arial",
          "font_color": "#111111",
          "bold": true,
          "alignment": "left",
          "z_index": 40
        }
      ]
    }
  ],
  "diagnostics": { "pages": [{ "page": 1, "elements": 18 }] }
}
```
