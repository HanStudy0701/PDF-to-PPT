from __future__ import annotations

from pathlib import Path


class FileResponse:
    def __init__(self, path: str | Path, media_type: str | None = None, filename: str | None = None):
        self.path = str(path)
        self.media_type = media_type
        self.filename = filename
