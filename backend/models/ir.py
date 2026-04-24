from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


ElementType = Literal["text", "image", "icon", "shape", "table_cell", "line"]


class Background(BaseModel):
    type: Literal["image", "shape", "none"] = "none"
    path: Optional[str] = None
    color: Optional[str] = None


class Element(BaseModel):
    id: str
    type: ElementType
    x: float
    y: float
    width: float
    height: float
    z_index: int = 0

    # text
    text: Optional[str] = None
    font_size: Optional[float] = None
    font_family: Optional[str] = None
    font_color: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    alignment: Optional[Literal["left", "center", "right", "justify"]] = None

    # image/icon
    path: Optional[str] = None

    # shape/line
    shape_type: Optional[str] = None
    fill_color: Optional[str] = None
    line_color: Optional[str] = None
    line_width: Optional[float] = None
    opacity: Optional[float] = None
    border_radius: Optional[float] = None

    meta: dict = Field(default_factory=dict)


class SlideIR(BaseModel):
    page_number: int
    width: float
    height: float
    background: Background = Field(default_factory=Background)
    elements: list[Element] = Field(default_factory=list)


class PresentationIR(BaseModel):
    source_pdf: str
    mode: Literal["maximum_editable", "visual_fidelity", "hybrid_safe"]
    slides: list[SlideIR]
    diagnostics: dict = Field(default_factory=dict)
