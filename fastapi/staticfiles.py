from __future__ import annotations


class StaticFiles:
    def __init__(self, directory: str, html: bool = False):
        self.directory = directory
        self.html = html
