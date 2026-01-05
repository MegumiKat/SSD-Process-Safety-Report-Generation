# src/tools/segments_controller.py
from __future__ import annotations

from typing import Optional, List

from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QSizePolicy


class SegmentsController:
    """
    负责 Segments UI 的构建与回写（将 ui_main.py 中的 segments 相关逻辑拆出去）：
    - build(segments): 根据 segments 生成 UI
    - apply(segments): 将 UI 中的编辑值写回 segments
    - reset(): 清空 UI
    """

    def __init__(self, view, segment_area_layout: QVBoxLayout):
        self.view = view
        self.layout = segment_area_layout
        self.widgets: list[dict] = []

    # -----------------------------
    # 基础：清空 layout（递归清理子 layout）
    # -----------------------------
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            child_layout = item.layout()
            if w is not None:
                w.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def reset(self):
        self._clear_layout(self.layout)
        self.widgets.clear()

    # -----------------------------
    # 构建 Segments UI
    # -----------------------------
    def build(self, segments):
        self.reset()

        if not segments:
            self.layout.addWidget(QLabel("No valid segment detected."))
            return

        self.layout.addWidget(QLabel(f"{len(segments)} segment(s) detected"))

        for si, seg in enumerate(segments, start=1):
            seg_box = QWidget()
            seg_box_layout = QVBoxLayout(seg_box)
            seg_box_layout.setContentsMargins(0, 4, 0, 4)

            seg_header = QLabel(f"Segment {si}: {getattr(seg, 'desc_display', '')}")
            seg_header.setStyleSheet("font-weight:bold;")
            seg_box_layout.addWidget(seg_header)

            for pi, part in enumerate(getattr(seg, "parts", []), start=1):
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)

                def _make_edit(placeholder: str, text: str = "") -> QLineEdit:
                    e = QLineEdit()
                    e.setPlaceholderText(placeholder)
                    e.setText(text)
                    # Segments 区域：短输入框，不跟随整行拉长
                    e.setMinimumWidth(80)
                    e.setMaximumWidth(160)
                    e.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
                    return e

                value_edit = _make_edit(
                    "Value(°C)",
                    "" if getattr(part, "value_temp_c", None) is None else f"{part.value_temp_c:.1f}",
                )
                onset_edit = _make_edit(
                    "Onset(°C)",
                    "" if getattr(part, "onset_c", None) is None else f"{part.onset_c:.1f}",
                )
                peak_edit = _make_edit(
                    "Peak(°C)",
                    "" if getattr(part, "peak_c", None) is None else f"{part.peak_c:.1f}",
                )
                area_edit = _make_edit(
                    "Area",
                    "" if getattr(part, "area_report", None) is None else f"{part.area_report:.3f}",
                )
                comment_edit = _make_edit(
                    "Comment",
                    (getattr(part, "comment", "") or ""),
                )

                row_layout.addWidget(QLabel(f"Part {pi}:"))
                row_layout.addWidget(value_edit)
                row_layout.addWidget(onset_edit)
                row_layout.addWidget(peak_edit)
                row_layout.addWidget(area_edit)
                row_layout.addWidget(comment_edit)
                row_layout.addStretch(1)

                seg_box_layout.addWidget(row_widget)

                self.widgets.append(
                    {
                        "seg_index": si - 1,
                        "part_index": pi - 1,
                        "value_edit": value_edit,
                        "onset_edit": onset_edit,
                        "peak_edit": peak_edit,
                        "area_edit": area_edit,
                        "comment_edit": comment_edit,
                    }
                )

            self.layout.addWidget(seg_box)

    # -----------------------------
    # 将 UI 编辑写回 segments
    # -----------------------------
    def apply(self, segments):
        if not segments:
            return

        def _to_float(text: str) -> Optional[float]:
            t = (text or "").strip()
            if not t:
                return None
            try:
                return float(t)
            except ValueError:
                return None

        for item in self.widgets:
            si = item["seg_index"]
            pi = item["part_index"]

            if si >= len(segments):
                continue
            seg = segments[si]
            parts = getattr(seg, "parts", [])
            if pi >= len(parts):
                continue
            part = parts[pi]

            part.value_temp_c = _to_float(item["value_edit"].text())
            part.onset_c = _to_float(item["onset_edit"].text())
            part.peak_c = _to_float(item["peak_edit"].text())
            part.area_report = _to_float(item["area_edit"].text())
            comment = (item["comment_edit"].text() or "").strip()
            part.comment = comment or ""