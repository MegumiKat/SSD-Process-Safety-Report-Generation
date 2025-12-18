# src/ui/dialog_add_sample.py
import os
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt


class AddSampleDialog(QDialog):
    """
    小弹窗：供用户为一个样品选择 TXT / PDF，并输入样品名。
    - TXT 必填
    - PDF 可选
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Sample")
        self.setModal(True)

        self.txt_path: str = ""
        self.pdf_path: Optional[str] = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # ===== 样品名 =====
        row_name = QHBoxLayout()
        lbl_name = QLabel("Sample Name:")
        self.edit_name = QLineEdit()
        row_name.addWidget(lbl_name)
        row_name.addWidget(self.edit_name, 1)

        main_layout.addLayout(row_name)

        # ===== TXT 选择 =====
        row_txt = QHBoxLayout()
        lbl_txt = QLabel("TXT:")
        self.lbl_txt_file = QLabel("No TXT selected")
        self.lbl_txt_file.setObjectName("FileNameLabel")

        btn_txt = QPushButton("Add TXT")
        btn_txt.clicked.connect(self.choose_txt)

        row_txt.addWidget(lbl_txt)
        row_txt.addWidget(self.lbl_txt_file, 1)
        row_txt.addWidget(btn_txt)

        main_layout.addLayout(row_txt)

        # ===== PDF 选择 =====
        row_pdf = QHBoxLayout()
        lbl_pdf = QLabel("PDF:")
        self.lbl_pdf_file = QLabel("No PDF selected")
        self.lbl_pdf_file.setObjectName("FileNameLabel")

        btn_pdf = QPushButton("Add PDF")
        btn_pdf.clicked.connect(self.choose_pdf)

        row_pdf.addWidget(lbl_pdf)
        row_pdf.addWidget(self.lbl_pdf_file, 1)
        row_pdf.addWidget(btn_pdf)

        main_layout.addLayout(row_pdf)

        # ===== 底部按钮：Cancel / Confirm =====
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Confirm")
        btn_ok.clicked.connect(self.on_confirm)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)

        main_layout.addLayout(btn_row)

    # ---------- 槽函数 ----------
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
        self.lbl_txt_file.setText(os.path.basename(path))

        # 如果样品名还没填，默认用 txt 文件名（去掉后缀）
        if not self.edit_name.text().strip():
            base = os.path.basename(path)
            name, _ = os.path.splitext(base)
            self.edit_name.setText(name)

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
        self.lbl_pdf_file.setText(os.path.basename(path))

    def on_confirm(self):
        if not self.txt_path:
            QMessageBox.warning(self, "Tips", "Please choose a TXT file.")
            return

        if not self.edit_name.text().strip():
            QMessageBox.warning(self, "Tips", "Please input sample name.")
            return

        self.accept()

    # 方便主窗口读取
    @property
    def sample_name(self) -> str:
        return self.edit_name.text().strip()