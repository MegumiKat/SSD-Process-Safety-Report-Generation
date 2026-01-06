# src/tools/theme_controller.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QApplication


class ThemeController:
    """
    Apply theme by setting QApplication.setStyleSheet(...).

    - dark_qss: already-loaded dark theme string (e.g., current app.qss)
    - light_qss_path: path to app_light.qss
    """

    def __init__(
        self,
        app: Optional[QApplication],
        *,
        dark_qss: str,
        light_qss_path: Path,
    ) -> None:
        self._app = app
        self._dark_qss = dark_qss or ""
        self._light_qss_path = Path(light_qss_path)
        self._light_qss_cache: Optional[str] = None

    def _load_light_qss(self) -> str:
        if self._light_qss_cache is not None:
            return self._light_qss_cache
        if self._light_qss_path.exists():
            self._light_qss_cache = self._light_qss_path.read_text(encoding="utf-8")
        else:
            # fallback: if light qss missing, keep empty (won't crash)
            self._light_qss_cache = ""
        return self._light_qss_cache

    def apply(self, theme: str) -> None:
        """
        theme: "dark" | "light"
        """
        if self._app is None:
            return

        theme = (theme or "").lower().strip()
        if theme == "light":
            self._app.setStyleSheet(self._load_light_qss())
        else:
            self._app.setStyleSheet(self._dark_qss)