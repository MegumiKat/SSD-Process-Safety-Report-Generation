# src/ui/widgets/toggle_switch.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, pyqtProperty, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._checked = True
        self._offset = 1.0  # 0.0 -> left, 1.0 -> right

        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # 默认尺寸（后续可由外部根据 fontMetrics 动态 setFixedSize）
        self.setFixedSize(46, 26)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, v: bool, emit_signal: bool = False):
        v = bool(v)
        if self._checked == v:
            return
        self._checked = v
        self._animate_to(1.0 if v else 0.0)
        if emit_signal:
            self.toggled.emit(self._checked)

    def toggle(self):
        self.setChecked(not self._checked, emit_signal=True)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.toggle()
        super().mousePressEvent(e)

    def _animate_to(self, end: float):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(end)
        self._anim.start()

    def getOffset(self) -> float:
        return self._offset

    def setOffset(self, v: float):
        self._offset = float(v)
        self.update()

    offset = pyqtProperty(float, fget=getOffset, fset=setOffset)

    def paintEvent(self, e):
        w = self.width()
        h = self.height()
        radius = h / 2

        track_off = QColor("#5f6368")
        track_on = QColor("#f58a42")
        knob = QColor("#ffffff")

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_on if self._checked else track_off)
        p.drawRoundedRect(0, 0, w, h, radius, radius)

        margin = 3
        knob_d = h - margin * 2
        x0 = margin
        x1 = w - margin - knob_d
        x = x0 + (x1 - x0) * self._offset

        p.setBrush(knob)
        p.drawEllipse(int(x), margin, knob_d, knob_d)
        p.end()