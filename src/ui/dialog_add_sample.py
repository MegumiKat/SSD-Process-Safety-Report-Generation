# src/ui/dialog_add_sample.py
import os
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QFrame, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt
from src.utils.parser_dsc import parse_dsc_txt_basic


class AddSampleDialog(QDialog):
    """
    弹窗：为一个样品选择 TXT / PDF，并输入样品名。
    - TXT 必填
    - PDF 可选
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AddSampleDialog")
        self.setWindowTitle("Add Sample")
        self.setModal(True)

        self.txt_path: str = ""
        self.pdf_path: Optional[str] = None

        # ===== Root =====
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        # ===== Card =====
        card = QFrame()
        card.setObjectName("DialogCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(14)
        root.addWidget(card)

        # ===== Title / Hint =====
        title = QLabel("Add a Sample")
        title.setObjectName("DialogTitle")

        hint = QLabel("TXT is required. PDF is optional.")
        hint.setObjectName("DialogHint")

        card_layout.addWidget(title)
        card_layout.addWidget(hint)

        # ===== Form grid =====
        grid = QGridLayout()
        grid.setContentsMargins(0, 6, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        card_layout.addLayout(grid)

        def _mk_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setObjectName("AccentLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            return lbl

        def _mk_edit(placeholder: str, read_only: bool = False, obj: str = "") -> QLineEdit:
            e = QLineEdit()
            if obj:
                e.setObjectName(obj)
            e.setPlaceholderText(placeholder)
            e.setReadOnly(read_only)
            e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return e

        def _mk_browse_btn(text: str) -> QPushButton:
            b = QPushButton(text)
            b.setObjectName("BrowseButton")
            b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            return b

        # Row 0: Sample Name
        self.lbl_name = _mk_label("Sample Name:")
        self.edit_name = _mk_edit("e.g. CF130G (Batch A)", read_only=False, obj="NameEdit")
        grid.addWidget(self.lbl_name, 0, 0)
        grid.addWidget(self.edit_name, 0, 1, 1, 2)

        # Row 1: TXT
        self.lbl_txt = _mk_label("TXT:")
        self.edit_txt = _mk_edit("No TXT selected", read_only=True, obj="FilePathEdit")
        btn_txt = _mk_browse_btn("Browse TXT")
        btn_txt.clicked.connect(self.choose_txt)

        grid.addWidget(self.lbl_txt, 1, 0)
        grid.addWidget(self.edit_txt, 1, 1)
        grid.addWidget(btn_txt, 1, 2)

        # Row 2: PDF
        self.lbl_pdf = _mk_label("PDF:")
        self.edit_pdf = _mk_edit("No PDF selected", read_only=True, obj="FilePathEdit")
        btn_pdf = _mk_browse_btn("Browse PDF")
        btn_pdf.clicked.connect(self.choose_pdf)

        grid.addWidget(self.lbl_pdf, 2, 0)
        grid.addWidget(self.edit_pdf, 2, 1)
        grid.addWidget(btn_pdf, 2, 2)

        # ===== Buttons =====
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 6, 0, 0)
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("CancelButton")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Confirm")
        btn_ok.setObjectName("PrimaryButton")
        btn_ok.clicked.connect(self.on_confirm)

        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        btn_row.addStretch(1)

        card_layout.addLayout(btn_row)

        # 关键：按字体动态同步尺寸，跨设备/DPI 更稳
        self._sync_metrics()

    def _sync_metrics(self):
        fm = self.fontMetrics()

        # 控件高度：跟随字体变化
        h = max(34, int(fm.height() * 2.2))
        self.edit_name.setMinimumHeight(h)
        self.edit_txt.setMinimumHeight(h)
        self.edit_pdf.setMinimumHeight(h)

        # label 列宽：取最大文本宽度 + padding
        w = max(
            fm.horizontalAdvance("Sample Name:"),
            fm.horizontalAdvance("TXT:"),
            fm.horizontalAdvance("PDF:")
        ) + max(12, int(fm.height() * 0.6))

        self.lbl_name.setMinimumWidth(w)
        self.lbl_txt.setMinimumWidth(w)
        self.lbl_pdf.setMinimumWidth(w)

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_metrics()

    # ---------- slots ----------
    def choose_txt(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose TXT",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return

        self.txt_path = path
        self._set_file_to_edit(self.edit_txt, path)

        if not self.edit_name.text().strip():
            try:
                basic = parse_dsc_txt_basic(path)
                auto_name = basic.sample_name or ""
                if not auto_name:
                    auto_name = Path(path).stem
                self.edit_name.setText(auto_name)
            except Exception:
                self.edit_name.setText(Path(path).stem)

    def choose_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose PDF",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if not path:
            return

        self.pdf_path = path
        self._set_file_to_edit(self.edit_pdf, path)

    def _set_file_to_edit(self, edit: QLineEdit, full_path: str):
        base = os.path.basename(full_path)
        edit.setText(base)
        edit.setToolTip(full_path)

    def on_confirm(self):
        if not self.txt_path:
            QMessageBox.warning(self, "Tips", "Please choose a TXT file.")
            return

        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "Tips", "Please input sample name.")
            return

        self.accept()

    @property
    def sample_name(self) -> str:
        return self.edit_name.text().strip()