# src/ui_main.py
import sys
import os
from typing import Optional, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QFormLayout,
    QMessageBox, QScrollArea, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor, QPixmap
from pathlib import Path

from src.config.config import DEFAULT_TEMPLATE_PATH, LOGO_PATH
from src.utils.parser_dsc import parse_dsc_txt_basic, parse_dsc_segments
from src.models.models import DscBasicInfo, DscSegment
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
        self.parsed_segments: Optional[List[DscSegment]] = None
        self.segment_widgets: list[dict] = []
        self.confirmed: bool = False  # 是否点击过“确认数据”

        # 日志内部结构：文件日志 / 当前确认块 / 历史生成块
        self.file_logs: List[str] = []       # html 字符串
        self.confirm_block: Optional[str] = None  # 纯文本字符串（多行）
        self.generate_logs: List[str] = []   # html 字符串（每块可能多行）

        # ==== 总体布局：顶部 Header（Logo + 程序名） + 下方左右分栏 ====
        central = QWidget()
        # central.setStyleSheet("background-color: #bbbbbb;")  # 换成你想要的颜色
        root_layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # 通用分割线：orientation = "h" 或 "v"
        def _create_separator(
            orientation: str = "h",
            thickness: int = 2,
            color: str = "#f5f5f5",
            dashed: bool = True,
        ) -> QFrame:
            line = QFrame()
            if orientation == "h":
                line.setFrameShape(QFrame.Shape.HLine)
                # 水平线用 top 边
                style_prop = "border-top"
            else:
                line.setFrameShape(QFrame.Shape.VLine)
                # 垂直线用 left 边
                style_prop = "border-left"

            line.setFrameShadow(QFrame.Shadow.Plain)

            border_style = "dashed" if dashed else "solid"
            line.setStyleSheet(
                f"QFrame {{ border: none; {style_prop}: {thickness}px {border_style} {color}; }}"
            )
            return line

        # ---------- 顶部：公司 Logo + 程序标题 ----------
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 8, 8, 8)

        # 左侧：Logo
        logo_label = QLabel()
        if os.path.exists(LOGO_PATH):
            pixmap = QPixmap(str(LOGO_PATH))
            if not pixmap.isNull():
                target_height= 80
                # 控制 logo 高度，比如 40 像素，等比缩放
                logo_label.setPixmap(
                    pixmap.scaledToHeight(
                        target_height,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
        # 给一点固定高度，即使没图也不至于崩版
        logo_label.setMinimumHeight(target_height)
        logo_label.setMaximumHeight(target_height + 10) 
        header_layout.addWidget(logo_label)

        # 右侧：程序标题
        title_label = QLabel("DSC Reports Generation Tool")
        title_label.setObjectName("AppTitle")
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        root_layout.addWidget(header_widget)

        # ---------- 分割线（虚线） ----------
        root_layout.addWidget(_create_separator("h"))

        # ---------- 中间主体：左右分栏 ----------
        main_layout = QHBoxLayout()
        root_layout.addLayout(main_layout, stretch=1)

        left_layout = QVBoxLayout()   # 文件 + 手动输入
        right_layout = QVBoxLayout()  # 自动识别 + 日志
        main_layout.addLayout(left_layout, 3)
        main_layout.addWidget(_create_separator("v"))
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
        h_out.addWidget(lbl_out)
        h_out.addWidget(self.edit_output)
        h_out.addWidget(btn_out)
        file_layout.addLayout(h_out)

        # 4. 模板路径显示（默认，只显示文件名）
        h_tpl = QHBoxLayout()
        self.label_tpl = QLabel(os.path.basename(self.template_path))
        lbl_tpl = QLabel("Current Template:")
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

        left_layout.addWidget(_create_separator("h"))

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
        # 外层垂直布局：上半部分是原来的自动字段，下半部分放 segments
        auto_vbox = QVBoxLayout(auto_container)
        auto_form = QFormLayout()
        auto_vbox.addLayout(auto_form)

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
        auto_form.addRow(title_auto)

        _add_form_row(auto_form, "Sample Name:", self.auto_sample_name)
        _add_form_row(auto_form, "Sample Mass:", self.auto_sample_mass)
        _add_form_row(auto_form, "Operator:", self.auto_operator)
        _add_form_row(auto_form, "Instrument:", self.auto_instrument)
        _add_form_row(auto_form, "Atmosphere:", self.auto_atmosphere)
        _add_form_row(auto_form, "Crucible:", self.auto_crucible)
        _add_form_row(auto_form, "Temp.Calib.:", self.auto_temp_calib)
        _add_form_row(auto_form, "End Date:", self.auto_end_date)

        # ===== 新增：Segments 自动识别区域 =====
        seg_title = QLabel("Segments:")
        auto_vbox.addWidget(seg_title)

        # 这个 layout 里后面会动态塞每个 segment 的行
        self.segment_area_layout = QVBoxLayout()
        auto_vbox.addLayout(self.segment_area_layout)

        auto_scroll.setWidget(auto_container)
        right_layout.addWidget(auto_scroll, stretch=1)

        right_layout.addWidget(_create_separator("h"))

        # ---------- 右侧：日志 + 清空按钮 ----------
        log_header_layout = QHBoxLayout()
        lbl_log = QLabel("Log:")
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


    def _clear_layout(self, layout):
        """递归清空一个 layout 里的所有控件和子布局。"""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            child_layout = item.layout()
            if w is not None:
                w.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _build_segments_auto_fields(self, segments: List[DscSegment]):
        """根据 segments 动态生成右侧可编辑的行。"""
        self._clear_layout(self.segment_area_layout)
        self.segment_widgets.clear()

        if not segments:
            label = QLabel("未识别到有效的 segment。")
            self.segment_area_layout.addWidget(label)
            return

        # 顶部显示段数
        count_label = QLabel(f"共 {len(segments)} 段")
        self.segment_area_layout.addWidget(count_label)

        # 每个 segment 一个小块
        for si, seg in enumerate(segments, start=1):
            seg_box = QWidget()
            seg_box_layout = QVBoxLayout(seg_box)
            seg_box_layout.setContentsMargins(0, 4, 0, 4)

            seg_header = QLabel(f"Segment {si}: {seg.desc_display}")
            seg_header.setStyleSheet("font-weight:bold;")
            seg_box_layout.addWidget(seg_header)

            # 每个 part 一行（Value / Onset / Peak / Area / Comment）
            for pi, part in enumerate(seg.parts, start=1):
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)

                # 小工具函数：创建带占位提示的输入框
                def _make_edit(placeholder: str, text: str = "") -> QLineEdit:
                    e = QLineEdit()
                    e.setPlaceholderText(placeholder)
                    e.setText(text)
                    e.setMinimumWidth(70)
                    e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                    return e

                value_edit = _make_edit(
                    "Value(°C)",
                    "" if part.value_temp_c is None else f"{part.value_temp_c:.1f}",
                )
                onset_edit = _make_edit(
                    "Onset(°C)",
                    "" if part.onset_c is None else f"{part.onset_c:.1f}",
                )
                peak_edit = _make_edit(
                    "Peak(°C)",
                    "" if part.peak_c is None else f"{part.peak_c:.1f}",
                )
                area_edit = _make_edit(
                    "Area",
                    "" if part.area_report is None else f"{part.area_report:.3f}",
                )
                comment_edit = _make_edit(
                    "Comment",
                    part.comment or "",
                )

                # 布局里按顺序加上去
                row_layout.addWidget(QLabel(f"Part {pi}:"))
                row_layout.addWidget(value_edit)
                row_layout.addWidget(onset_edit)
                row_layout.addWidget(peak_edit)
                row_layout.addWidget(area_edit)
                row_layout.addWidget(comment_edit)

                seg_box_layout.addWidget(row_widget)

                # 记录这些控件，对应到原始数据的 index
                self.segment_widgets.append(
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

            self.segment_area_layout.addWidget(seg_box)

    def _apply_segment_edits(self):
        """把右侧 segments 编辑区域中的修改写回 self.parsed_segments。"""
        if not self.parsed_segments:
            return

        def _to_float(text: str) -> Optional[float]:
            t = text.strip()
            if not t:
                return None
            try:
                return float(t)
            except ValueError:
                return None

        for item in self.segment_widgets:
            si = item["seg_index"]
            pi = item["part_index"]
            if si >= len(self.parsed_segments):
                continue
            seg = self.parsed_segments[si]
            if pi >= len(seg.parts):
                continue
            part = seg.parts[pi]

            part.value_temp_c = _to_float(item["value_edit"].text())
            part.onset_c = _to_float(item["onset_edit"].text())
            part.peak_c = _to_float(item["peak_edit"].text())
            part.area_report = _to_float(item["area_edit"].text())
            comment = item["comment_edit"].text().strip()
            part.comment = comment or ""


    # ====== 自动解析 txt 并填充右侧 ======
    def _parse_txt_and_fill(self):
        if not self.txt_path:
            return

        try:
            self.parsed_info = parse_dsc_txt_basic(self.txt_path)
            info = self.parsed_info


            # 2. Segments
            try:
                self.parsed_segments = parse_dsc_segments(self.txt_path)
            except Exception as e_seg:
                self.parsed_segments = []
                msg_seg = f'<span style="color:#ff5555;">[Segments Parsed Failed]</span> {os.path.basename(self.txt_path)} - {e_seg}'
                self._add_file_log(msg_seg)

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

            # 3. 构建 segments 编辑区域
            self._build_segments_auto_fields(self.parsed_segments or [])

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

        # 在生成前，把 UI 中对 segments 的修改写回对象
        self._apply_segment_edits()

        # 优先使用已经解析好的 segments
        segments = self.parsed_segments or []
        if not segments:
            block = (
                '<span style="color:#ff5555;">[Segments 为空]</span> '
                '将不生成 segments 表格。<br>'
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

    
    # ===== 加载 QSS 样式 (mac 深色主题) =====
    # ui_main.py 在 src/ui 下，parents[1] 就是 src 目录
    base_dir = Path(__file__).resolve().parents[1]  # .../src
    qss_path = base_dir / "assets" / "app.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"[Warning] QSS file not found: {qss_path}")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())