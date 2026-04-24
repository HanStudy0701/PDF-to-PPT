from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path("/tmp/pdf_to_ppt_jobs")
ROOT.mkdir(parents=True, exist_ok=True)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def zip_dir(src: Path, out_zip: Path) -> Path:
    base_name = out_zip.with_suffix("")
    shutil.make_archive(str(base_name), "zip", src)
    return out_zip
