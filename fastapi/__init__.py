from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class UploadFile:
    filename: str = ""
    _content: bytes = b""

    async def read(self) -> bytes:
        return self._content


class FastAPI:
    def __init__(self, title: str = "App"):
        self.title = title
        self.routes: list[tuple[str, str, Callable[..., Any]]] = []

    def mount(self, path: str, app: Any, name: str | None = None) -> None:
        self.routes.append(("MOUNT", path, app))

    def get(self, path: str):
        def decorator(fn: Callable[..., Any]):
            self.routes.append(("GET", path, fn))
            return fn

        return decorator

    def post(self, path: str):
        def decorator(fn: Callable[..., Any]):
            self.routes.append(("POST", path, fn))
            return fn

        return decorator


def File(default: Any = None):
    return default


def Form(default: Any = None):
    return default
