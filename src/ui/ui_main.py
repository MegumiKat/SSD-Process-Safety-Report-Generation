# src/ui_main.py
import sys
import os
from typing import Optional, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QFormLayout,
    QMessageBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor

from src.config.config import DEFAULT_TEMPLATE_PATH
from src.utils.parser_dsc import parse_dsc_txt_basic, parse_dsc_segments
from src.models.models import DscBasicInfo
from src.utils.templating import fill_template_with_mapping
from src.utils.dsc_text import generate_dsc_summary


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DSC Reports Generation Tool (template + txt + pdf)")
        self.resize(1100, 650)

        # ==== status ====
        self.txt_path: str = ""
        self.pdf_path: str = ""
        self.template_path: str = DEFAULT_TEMPLATE_PATH
        self.output_path: str = ""
        self.parsed_info: Optional[DscBasicInfo] = None
        self.confirmed: bool = False  # 是否点击过“确认数据”

        # 日志内部结构：文件日志 / 当前确认块 / 历史生成块
        self.file_logs: List[str] = []       # html 字符串
        self.confirm_block: Optional[str] = None  # 纯文本字符串（多行）
        self.generate_logs: List[str] = []   # html 字符串（每块可能多行）

        # ==== 总体布局：左右分栏 ====
        central = QWidget()
        main_layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        left_layout = QVBoxLayout()   # 文件 + 手动输入
        right_layout = QVBoxLayout()  # 自动识别 + 日志
        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 2)

        # ---------- 左侧：文件选择区域 ----------
        file_layout = QVBoxLayout()

        def _new_path_edit() -> QLineEdit:
            e = QLineEdit()
            e.setReadOnly(True)
            e.setMinimumWidth(350)
            e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return e

        # 1. txt
        h_txt = QHBoxLayout()
        self.edit_txt = _new_path_edit()
        btn_txt = QPushButton("Choose TXT")
        btn_txt.clicked.connect(self.choose_txt)
        lbl_txt = QLabel("DSC Result txt:")
        lbl_txt.setStyleSheet("color: #bbbbbb;")
        h_txt.addWidget(lbl_txt)
        h_txt.addWidget(self.edit_txt)
        h_txt.addWidget(btn_txt)
        file_layout.addLayout(h_txt)

        # 2. pdf
        h_pdf = QHBoxLayout()
        self.edit_pdf = _new_path_edit()
        btn_pdf = QPushButton("Choose PDF")
        btn_pdf.clicked.connect(self.choose_pdf)
        lbl_pdf = QLabel("Curve Graph:")
        lbl_pdf.setStyleSheet("color: #bbbbbb;")
        h_pdf.addWidget(lbl_pdf)
        h_pdf.addWidget(self.edit_pdf)
        h_pdf.addWidget(btn_pdf)
        file_layout.addLayout(h_pdf)

        # 3. 输出文件
        h_out = QHBoxLayout()
        self.edit_output = _new_path_edit()
        btn_out = QPushButton("Choose Output Path")
        btn_out.clicked.connect(self.choose_output)
        lbl_out = QLabel("Output Report")
        lbl_out.setStyleSheet("color: #bbbbbb;")
        h_out.addWidget(lbl_out)
        h_out.addWidget(self.edit_output)
        h_out.addWidget(btn_out)
        file_layout.addLayout(h_out)

        # 4. 模板路径显示（默认，只显示文件名）
        h_tpl = QHBoxLayout()
        self.label_tpl = QLabel(os.path.basename(self.template_path))
        self.label_tpl.setStyleSheet("color: #bbbbbb;")
        lbl_tpl = QLabel("Current Template:")
        lbl_tpl.setStyleSheet("color: #bbbbbb;")
        h_tpl.addWidget(lbl_tpl)
        h_tpl.addWidget(self.label_tpl)
        file_layout.addLayout(h_tpl)

        left_layout.addLayout(file_layout)

        # ---------- 左侧：操作按钮 ----------
        h_buttons = QHBoxLayout()
        self.btn_confirm = QPushButton("Confirm Data")
        self.btn_confirm.clicked.connect(self.on_confirm)
        self.btn_generate = QPushButton("Generate Report")
        self.btn_generate.clicked.connect(self.on_generate)
        h_buttons.addWidget(self.btn_confirm)
        h_buttons.addWidget(self.btn_generate)
        left_layout.addLayout(h_buttons)

        # ---------- 左侧：手动输入区域（黄色部分） ----------
        scroll_manual = QScrollArea()
        scroll_manual.setWidgetResizable(True)
        form_container = QWidget()
        self.form_layout = QFormLayout(form_container)

        def _new_input() -> QLineEdit:
            e = QLineEdit()
            e.setMinimumWidth(260)
            e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return e

        def _add_form_row(form: QFormLayout, text: str, widget: QLineEdit):
            label = QLabel(text)
            label.setStyleSheet("color: #bbbbbb;")
            form.addRow(label, widget)

        # 这些字段对应模板里的 {{占位符}}
        self.input_lsmp_code = _new_input()
        self.input_request_id = _new_input()
        self.input_customer = _new_input()
        self.input_request_name = _new_input()
        self.input_submission_date = _new_input()
        self.input_request_number = _new_input()
        self.input_project_account = _new_input()
        self.input_deadline = _new_input()

        self.input_sample_id = _new_input()
        self.input_nature = _new_input()
        self.input_assign_to = _new_input()
        self.input_test_date = _new_input()

        self.input_receive_date = _new_input()
        self.input_report_date = _new_input()

        self.input_request_desc = _new_input()

        self.input_lsmp_code.setText("LSMP-21 F01v04")

        _add_form_row(self.form_layout, "Test Code:", self.input_lsmp_code)
        _add_form_row(self.form_layout, "Request Id:", self.input_request_id)
        _add_form_row(self.form_layout, "Customer Information:", self.input_customer)
        _add_form_row(self.form_layout, "Request Name:", self.input_request_name)
        _add_form_row(self.form_layout, "Submission Date:", self.input_submission_date)
        _add_form_row(self.form_layout, "Request Number:", self.input_request_number)
        _add_form_row(self.form_layout, "Project Account:", self.input_project_account)
        _add_form_row(self.form_layout, "Deadline:", self.input_deadline)

        _add_form_row(self.form_layout, "Request Description:", self.input_request_desc)
        _add_form_row(self.form_layout, "Sample_id:", self.input_sample_id)
        _add_form_row(self.form_layout, "Nature:", self.input_nature)
        _add_form_row(self.form_layout, "Assign To:", self.input_assign_to)
        
        _add_form_row(self.form_layout, "Receive Date:", self.input_receive_date)
        _add_form_row(self.form_layout, "Test Date:", self.input_test_date)
        _add_form_row(self.form_layout, "Report Date:", self.input_report_date)

        scroll_manual.setWidget(form_container)
        left_layout.addWidget(scroll_manual, stretch=1)

        # ---------- 右侧：自动识别结果（可修改） ----------
        auto_scroll = QScrollArea()
        auto_scroll.setWidgetResizable(True)
        auto_container = QWidget()
        auto_form = QFormLayout(auto_container)

        def _new_auto_input() -> QLineEdit:
            e = QLineEdit()
            e.setMinimumWidth(260)
            e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return e

        self.auto_sample_name = _new_auto_input()
        self.auto_sample_mass = _new_auto_input()
        self.auto_operator = _new_auto_input()
        self.auto_instrument = _new_auto_input()
        self.auto_atmosphere = _new_auto_input()
        self.auto_crucible = _new_auto_input()
        self.auto_temp_calib = _new_auto_input()
        self.auto_end_date = _new_auto_input()

        title_auto = QLabel("Automatically identified fields:")
        title_auto.setStyleSheet("color: #bbbbbb;")
        auto_form.addRow(title_auto)

        _add_form_row(auto_form, "Sample Name:", self.auto_sample_name)
        _add_form_row(auto_form, "Sample Mass:", self.auto_sample_mass)
        _add_form_row(auto_form, "Operator:", self.auto_operator)
        _add_form_row(auto_form, "Instrument:", self.auto_instrument)
        _add_form_row(auto_form, "Atmosphere:", self.auto_atmosphere)
        _add_form_row(auto_form, "Crucible:", self.auto_crucible)
        _add_form_row(auto_form, "Temp.Calib.:", self.auto_temp_calib)
        _add_form_row(auto_form, "End Date:", self.auto_end_date)

        auto_scroll.setWidget(auto_container)
        right_layout.addWidget(auto_scroll, stretch=1)

        # ---------- 右侧：日志 + 清空按钮 ----------
        log_header_layout = QHBoxLayout()
        lbl_log = QLabel("Log:")
        lbl_log.setStyleSheet("color: #bbbbbb;")
        log_header_layout.addWidget(lbl_log)
        btn_clear_log = QPushButton("Clear")
        btn_clear_log.setFixedWidth(60)
        btn_clear_log.clicked.connect(self.clear_log)
        log_header_layout.addWidget(btn_clear_log)
        log_header_layout.addStretch(1)
        right_layout.addLayout(log_header_layout)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        right_layout.addWidget(self.log, stretch=1)

        # 启动时检查模板
        if not os.path.exists(self.template_path):
            QMessageBox.warning(
                self,
                "Warning",
                f"Can't find the template:\n{self.template_path}\nPlease Check \data or modify config.DEFAULT_TEMPLATE_PATH。"
            )

    # ====== 日志渲染 ======
    def render_log(self):
        """根据 file_logs / confirm_block / generate_logs 重绘日志窗口。"""
        self.log.clear()
        for msg in self.file_logs:
            self.log.append(msg)
        if self.confirm_block:
            # 确认块是纯文本，多行
            self.log.append(self.confirm_block)
        for block in self.generate_logs:
            self.log.append(block)
        self.log.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self):
        self.file_logs.clear()
        self.confirm_block = None
        self.generate_logs.clear()
        self.log.clear()

    def _add_file_log(self, html_msg: str):
        self.file_logs.append(html_msg)
        self.render_log()

    # ====== 自动解析 txt 并填充右侧 ======
    def _parse_txt_and_fill(self):
        if not self.txt_path:
            return

        try:
            self.parsed_info = parse_dsc_txt_basic(self.txt_path)
            info = self.parsed_info

            # 填充右侧自动识别字段（可修改）
            self.auto_sample_name.setText(info.sample_name or "")
            if info.sample_mass_mg is not None:
                self.auto_sample_mass.setText(f"{info.sample_mass_mg:.3f} mg")
            else:
                self.auto_sample_mass.setText("")
            self.auto_operator.setText(info.operator or "")
            self.auto_instrument.setText(info.instrument or "")
            self.auto_atmosphere.setText(info.atmosphere or "")
            self.auto_crucible.setText(info.crucible or "")
            self.auto_temp_calib.setText(info.temp_calib or "")
            self.auto_end_date.setText(info.end_date or "")

            self.confirmed = False
            self.confirm_block = None  # 重新确认前清空确认块

            msg = f'<span style="color:#33cc33;">[Parsing Successful]</span> {os.path.basename(self.txt_path)}'
            self._add_file_log(msg)

        except Exception as e:
            self.parsed_info = None
            msg = f'<span style="color:#ff5555;">[Parsing Failed]</span> {os.path.basename(self.txt_path)} - {e}'
            self._add_file_log(msg)
            QMessageBox.critical(self, "Error", f"[TXT]Parsing Failed\n{e}")

    # ====== 文件选择 ======
    def choose_txt(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose TXT", "", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            self.txt_path = path
            self.edit_txt.setText(os.path.basename(path))  # 只显示文件名
            self._parse_txt_and_fill()

    def choose_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if path:
            self.pdf_path = path
            self.edit_pdf.setText(os.path.basename(path))
            msg = f'<span style="color:#33cc33;">[Choosing Successful]</span> {os.path.basename(self.pdf_path)}'
            self._add_file_log(msg)

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Choose Output WORD", "", "Word file (*.docx)"
        )
        if path:
            if not path.lower().endswith(".docx"):
                path += ".docx"
            self.output_path = path
            self.edit_output.setText(os.path.basename(path))
            msg = f'<span style="color:#33cc33;">[Choosing Successful]</span> Output: {os.path.basename(self.output_path)}'
            self._add_file_log(msg)

    # ====== 确认数据：覆盖当前确认块 ======
    def on_confirm(self):
        if not self.txt_path:
            QMessageBox.warning(self, "Tips", "Please choose TXT")
            return

        if self.parsed_info is None:
            QMessageBox.warning(self, "Tips", "[TXT]Haven't parsed successful")
            return

        lines = []
        lines.append("")
        lines.append("===== Automatically identify fields (final value) =====")
        lines.append("")
        lines.append(f"Sample Name: {self.auto_sample_name.text().strip()}")
        lines.append(f"Sample Mass: {self.auto_sample_mass.text().strip()}")
        lines.append(f"Operator: {self.auto_operator.text().strip()}")
        lines.append(f"Instrument: {self.auto_instrument.text().strip()}")
        lines.append(f"Atmosphere: {self.auto_atmosphere.text().strip()}")
        lines.append(f"Crucible: {self.auto_crucible.text().strip()}")
        lines.append(f"Temp.Calib.: {self.auto_temp_calib.text().strip()}")
        lines.append(f"End Date: {self.auto_end_date.text().strip()}")
        lines.append("")

        lines.append("===== Manual input =====")
        lines.append("")
        lines.append(f"Test Code: {self.input_lsmp_code.text().strip()}")
        lines.append(f"Request Id: {self.input_request_id.text().strip()}")
        lines.append(f"Customer Information: {self.input_customer.text().strip()}")
        lines.append(f"Request Name: {self.input_request_name.text().strip()}")
        lines.append(f"Submission Date: {self.input_submission_date.text().strip()}")
        lines.append(f"Request Number: {self.input_request_number.text().strip()}")
        lines.append(f"Project Account: {self.input_project_account.text().strip()}")
        lines.append(f"Deadline: {self.input_deadline.text().strip()}")
        lines.append(f"Sample Id: {self.input_sample_id.text().strip()}")
        lines.append(f"Nature: {self.input_nature.text().strip()}")
        lines.append(f"Assign To: {self.input_assign_to.text().strip()}")
        lines.append(f"Test Date: {self.input_test_date.text().strip()}")
        lines.append(f"Receive Date: {self.input_receive_date.text().strip()}")
        lines.append(f"Report Date: {self.input_report_date.text().strip()}")
        lines.append(f"Request Description: {self.input_request_desc.text().strip()}")

        # 覆盖当前确认块，然后重绘日志
        self.confirm_block = "\n".join(lines)
        self.confirmed = True
        self.render_log()
        QMessageBox.information(self, "Info", "Compiled Successful. Please review and generate when ready")

    # ====== 生成报告 ======
    def on_generate(self):
        if not self.txt_path:
            QMessageBox.warning(self, "Info", "Choosing TXT")
            return

        if not self.output_path:
            QMessageBox.warning(self, "Info", "Choosing Output")
            return

        if not os.path.exists(self.template_path):
            QMessageBox.warning(self, "Info", f"Template don't exist\n{self.template_path}")
            return

        if self.parsed_info is None:
            QMessageBox.warning(self, "Info", "[TXT]Parsed Failed")
            return

        if not self.confirmed:
            QMessageBox.warning(self, "Info", "Please confirm and generate")
            return

        # --------- 构造占位符映射：手动输入 + 自动识别（以界面为准） ----------
        mapping: dict[str, str] = {}

        # --- 手动部分（黄色） ---
        mapping["{{LSMP_code}}"] = self.input_lsmp_code.text().strip()
        mapping["{{Request_id}}"] = self.input_request_id.text().strip()
        mapping["{{Customer_information}}"] = self.input_customer.text().strip()
        mapping["{{Request_Name}}"] = self.input_request_name.text().strip()
        mapping["{{Submission_Date}}"] = self.input_submission_date.text().strip()
        mapping["{{Request_Number}}"] = self.input_request_number.text().strip()
        mapping["{{Project_Account}}"] = self.input_project_account.text().strip()
        mapping["{{Deadline}}"] = self.input_deadline.text().strip()

        mapping["{{Sample_id}}"] = self.input_sample_id.text().strip()
        mapping["{{Nature}}"] = self.input_nature.text().strip()
        mapping["{{Assign_to}}"] = self.input_assign_to.text().strip()
        mapping["{{Test_Date}}"] = self.input_test_date.text().strip()

        mapping["{{Receive_Date}}"] = self.input_receive_date.text().strip()
        mapping["{{Report_Date}}"] = self.input_report_date.text().strip()

        mapping["{{Request_desc}}"] = self.input_request_desc.text().strip()

        # --- 自动部分（绿色基础字段，来自右侧可编辑栏） ---
        mapping["{{Sample_name}}"] = self.auto_sample_name.text().strip()
        mapping["{{Sample_mass}}"] = self.auto_sample_mass.text().strip()
        mapping["{{Operator}}"] = self.auto_operator.text().strip()
        mapping["{{Instrument}}"] = self.auto_instrument.text().strip()
        mapping["{{Atmosphere}}"] = self.auto_atmosphere.text().strip()
        mapping["{{Crucible}}"] = self.auto_crucible.text().strip()
        mapping["{{Temp.Calib}}"] = self.auto_temp_calib.text().strip()
        mapping["{{End_Date}}"] = self.auto_end_date.text().strip()

        try:
            segments = parse_dsc_segments(self.txt_path)
        except Exception as e:
            segments = []
            block = (
                f'<span style="color:#ff5555;">[Segments Parsed Failed]</span> {e}<br>'
            )
            self.generate_logs.append(block)
            self.render_log()

        # 表格第一列用哪个作为 Sample ID 显示
        sample_name_for_segments = (
            self.auto_sample_name.text().strip()
            or self.input_sample_id.text().strip()
        )

        # === 生成 Discussion 文案 ===
        if segments:
            discussion_text = generate_dsc_summary(sample_name_for_segments, segments)
        else:
            discussion_text = ""
        

        figure_number = "1"

        try:
            fill_template_with_mapping(
                self.template_path,
                self.output_path,
                mapping,
                segments=segments,
                sample_name_for_segments=sample_name_for_segments,
                discussion_text=discussion_text,
                pdf_path=self.pdf_path if self.pdf_path else None,
                figure_number=figure_number,
            )
            block = (
                f'<span style="color:#33cc33;">[Generate Successful]</span> '
                f'{os.path.basename(self.output_path)}<br>========'
            )
            self.generate_logs.append(block)
            self.render_log()
            QMessageBox.information(self, "Successful", "Generate Successful!\nCan open word and check")
        except Exception as e:
            block = (
                f'<span style="color:#ff5555;">[Generate Failed]</span> '
                f'{os.path.basename(self.output_path)} - {e}<br>========'
            )
            self.generate_logs.append(block)
            self.render_log()
            QMessageBox.critical(self, "Error", f"Generate Failed\n{e}")


def main():
    app = QApplication(sys.argv)

        # ① 取当前默认字体
    font = app.font()
    # ② 放大一点，比如在原来的基础上 +2 号
    font.setPointSize(font.pointSize() + 4)
    # ③ 设置为整个应用的默认字体
    app.setFont(font)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())