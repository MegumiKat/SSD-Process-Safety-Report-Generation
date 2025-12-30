# src/ui/dialog_add_sample.py
import os
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from src.utils.parser_dsc import parse_dsc_txt_basic


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

        # 橙色字段名
        orange_style = "color: rgb(255,119,0); font-weight: bold;"
        lbl_name.setStyleSheet(orange_style)

        row_name.addWidget(lbl_name)
        row_name.addWidget(self.edit_name, 1)
        main_layout.addLayout(row_name)

        # ===== TXT 选择 =====
        row_txt = QHBoxLayout()
        lbl_txt = QLabel("TXT:")
        self.lbl_txt_file = QLabel("No TXT selected")
        self.lbl_txt_file.setObjectName("FileNameLabel")

        # 橙色字段名
        lbl_txt.setStyleSheet(orange_style)

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

        # 橙色字段名
        lbl_pdf.setStyleSheet(orange_style)

        btn_pdf = QPushButton("Add PDF")
        btn_pdf.clicked.connect(self.choose_pdf)

        row_pdf.addWidget(lbl_pdf)
        row_pdf.addWidget(self.lbl_pdf_file, 1)
        row_pdf.addWidget(btn_pdf)
        main_layout.addLayout(row_pdf)

        # ===== 底部按钮：Cancel / Confirm =====
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 12, 0, 0)  # 顶部留一点空
        btn_row.setSpacing(12)                   # 两个按钮之间的间距

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Confirm")
        btn_ok.setObjectName("PrimaryButton") 
        btn_ok.clicked.connect(self.on_confirm)

        # 左右各一个 stretch，让按钮居中
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        btn_row.addStretch(1)

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


        # 如果「名字」目前是空的，则尝试用 TXT 里识别的样品名来填
        if not self.edit_name.text().strip():
            try:
                basic = parse_dsc_txt_basic(path)
                auto_name = basic.sample_name  # 解析出的样品名

                # 如果解析不到样品名，就退回到文件名（去掉后缀）
                if not auto_name:
                    auto_name = Path(path).stem

                self.edit_name.setText(auto_name)
            except Exception as e:
                # 解析出错时，为了不影响用户使用，可以只退回到文件名
                auto_name = Path(path).stem
                self.edit_name.setText(auto_name)

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