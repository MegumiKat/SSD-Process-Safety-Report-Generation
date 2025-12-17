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
from PyQt6.QtGui import QTextCursor, QPixmap, QIcon
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
        self.resize(1400, 800)

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

        # 伪输入框：一个有边框的容器，里面放气泡
        def _create_chip_box():
            box = QWidget()
            box.setObjectName("FileChipBox")
            layout = QHBoxLayout(box)
            layout.setContentsMargins(6, 2, 6, 2)
            layout.setSpacing(4)
            layout.addStretch()  # 让气泡靠左
            return box, layout

        def _new_path_edit() -> QLineEdit:
            e = QLineEdit()
            e.setReadOnly(True)
            e.setMinimumWidth(350)
            e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return e

        # 小工具：生成“气泡容器”（带水平布局 + stretch）
        def _new_chip_container():
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(4)
            layout.addStretch()  # 保证气泡靠左
            return container, layout

        # ===== TXT 行：多个 txt 文件 + 气泡显示 =====
        h_txt = QHBoxLayout()
        lbl_txt = QLabel("DSC Result txt:")

        self.txt_chip_box, self.txt_chip_layout = _create_chip_box()

        btn_txt = QPushButton("Add TXT")
        btn_txt.clicked.connect(self.choose_txt)

        h_txt.addWidget(lbl_txt)
        h_txt.addWidget(self.txt_chip_box, 1)
        h_txt.addWidget(btn_txt)
        file_layout.addLayout(h_txt)

        # 初始化 txt 文件列表
        self.txt_files: list[str] = []

        # ===== PDF 行：多个 pdf 文件 + 气泡显示 =====
        h_pdf = QHBoxLayout()
        lbl_pdf = QLabel("Curve Graph:")

        # 用伪输入框容器来承载气泡
        self.pdf_chip_box, self.pdf_chip_layout = _create_chip_box()

        btn_pdf = QPushButton("Add PDF")
        btn_pdf.clicked.connect(self.choose_pdf)

        h_pdf.addWidget(lbl_pdf)
        h_pdf.addWidget(self.pdf_chip_box, 1)
        h_pdf.addWidget(btn_pdf)
        file_layout.addLayout(h_pdf)

        # 初始化 pdf 文件列表
        self.pdf_files: list[str] = []

        # ===== 输出文件（保持单个路径框） =====
        h_out = QHBoxLayout()
        lbl_out = QLabel("Output Report")

        # 伪输入框 + label
        self.output_box = QWidget()
        self.output_box.setObjectName("OutputBox")
        out_layout = QHBoxLayout(self.output_box)
        out_layout.setContentsMargins(6, 0, 6, 0)
        out_layout.setSpacing(4)

        self.output_label = QLabel("No output file selected")
        out_layout.addWidget(self.output_label)

        btn_out = QPushButton("Choose Output Path")
        btn_out.clicked.connect(self.choose_output)

        h_out.addWidget(lbl_out)
        h_out.addWidget(self.output_box, 1)
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
        self.btn_generate.setObjectName("btn_generate")  # 让 QSS 的主按钮样式生效
        self.btn_generate.clicked.connect(self.on_generate)
        h_buttons.addWidget(self.btn_confirm)
        h_buttons.addWidget(self.btn_generate)
        left_layout.addLayout(h_buttons)

        left_layout.addWidget(_create_separator("h"))

        # ---------- 左侧：手动输入区域（黄色部分） ----------
                # ---------- 左侧：手动输入区域（Request / Sample 两个独立块，每个有自己的 scroll） ----------

        # 通用：单行输入组件
        def _new_input() -> QLineEdit:
            e = QLineEdit()
            e.setMinimumWidth(140)  # ⇐ 想多短可以自己调，比如 120/140/160
            e.setMaximumWidth(220)  # 控制一个上限，防止拉得太长
            e.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            return e

        # 通用：在 FormLayout 里加一行（支持 QLineEdit / QTextEdit 等任意 QWidget）
        def _add_form_row(form: QFormLayout, text: str, widget: QWidget):
            label = QLabel(text)
            form.addRow(label, widget)

        # ===== 字段定义（与之前相同，只是放到这里） =====
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

        # Request Description 换成多行文本
        self.input_request_desc = QTextEdit()
        self.input_request_desc.setAcceptRichText(False)
        self.input_request_desc.setMinimumWidth(140)          # 和 _new_input 一样
        self.input_request_desc.setMaximumWidth(220)          # 和 _new_input 一样
        self.input_request_desc.setSizePolicy(
            self.input_lsmp_code.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Fixed,
        )

        self.input_lsmp_code.setText("LSMP-21 F01v04")

        # ===== 手动输入总容器：水平放两个滚动块 =====
        manual_block = QWidget()
        manual_hbox = QHBoxLayout(manual_block)
        manual_hbox.setContentsMargins(0, 0, 0, 0)
        manual_hbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ---------- 左侧块：Request information + 独立 scroll ----------
        scroll_request = QScrollArea()
        scroll_request.setWidgetResizable(True)
        request_container = QWidget()
        self.request_form = QFormLayout(request_container)

        # Request information 内部字段
        _add_form_row(self.request_form, "Test Code:", self.input_lsmp_code)
        _add_form_row(self.request_form, "Request Id:", self.input_request_id)
        _add_form_row(self.request_form, "Customer Information:", self.input_customer)
        _add_form_row(self.request_form, "Request Name:", self.input_request_name)
        _add_form_row(self.request_form, "Submission Date:", self.input_submission_date)
        _add_form_row(self.request_form, "Request Number:", self.input_request_number)
        _add_form_row(self.request_form, "Project Account:", self.input_project_account)
        _add_form_row(self.request_form, "Deadline:", self.input_deadline)

        _add_form_row(self.request_form, "Receive Date:", self.input_receive_date)
        _add_form_row(self.request_form, "Test Date:", self.input_test_date)
        _add_form_row(self.request_form, "Report Date:", self.input_report_date)

        # Request information 的最后一项：多行描述
        _add_form_row(self.request_form, "Request Description:", self.input_request_desc)

        scroll_request.setWidget(request_container)

        # ---------- 右侧块：Sample information + 独立 scroll ----------
        scroll_sample = QScrollArea()
        scroll_sample.setWidgetResizable(True)
        sample_container = QWidget()
        self.sample_form = QFormLayout(sample_container)

        _add_form_row(self.sample_form, "Sample Id:", self.input_sample_id)
        _add_form_row(self.sample_form, "Nature:", self.input_nature)
        _add_form_row(self.sample_form, "Assign To:", self.input_assign_to)

        scroll_sample.setWidget(sample_container)

        # ---------- 把两个滚动块 + 中间竖线加入水平布局 ----------
        manual_hbox.addWidget(scroll_request, 1)
        manual_hbox.addWidget(_create_separator("v"), 0)  # 中间竖直分界线
        manual_hbox.addWidget(scroll_sample, 1)

        # 最终把整个手动输入模块加到左侧主布局
        left_layout.addWidget(manual_block, stretch=1)
        

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
        self.log.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.log.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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


    def _refresh_file_chips(self, kind: str):
        """
        根据当前文件列表刷新 txt/pdf 的气泡显示。
        kind: "txt" 或 "pdf"
        """
        if kind == "txt":
            layout = self.txt_chip_layout
            files = self.txt_files
            remove_slot = self._remove_txt_file
        else:
            layout = self.pdf_chip_layout
            files = self.pdf_files
            remove_slot = self._remove_pdf_file

        # 只保留最后一个 stretch，其余 item 清空
        while layout.count() > 1:
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # 没有文件时，可以放一个“无文件”灰字占位（可选）
        if not files:
            placeholder = QLabel("No file selected")
            placeholder.setStyleSheet("color: #777777;")
            layout.insertWidget(layout.count() - 1, placeholder)
            return

        for path in files:
            chip = QWidget()
            chip.setObjectName("FileChip")  # 让 QSS 的 FileChip 样式生效
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(4, 0, 4, 0)
            chip_layout.setSpacing(4)

            name_label = QLabel(os.path.basename(path))

            del_btn = QPushButton("✕")
            del_btn.setObjectName("FileChipCloseButton")
            del_btn.setFixedSize(18, 18)
            del_btn.clicked.connect(lambda _, p=path: remove_slot(p))

            chip_layout.addWidget(name_label)
            chip_layout.addWidget(del_btn)

            layout.insertWidget(layout.count() - 1, chip)

    def _remove_txt_file(self, path: str):
        if path in self.txt_files:
            self.txt_files.remove(path)

            # 如果删掉的是当前使用的 txt，就切换到剩余的最后一个，重新解析
            if self.txt_path == path:
                self.txt_path = self.txt_files[-1] if self.txt_files else ""
                self.clear_log()
                if self.txt_path:
                    self._parse_txt_and_fill()
                else:
                    self.parsed_info = None
                    self.parsed_segments = None

            self._refresh_file_chips("txt")

    def _remove_pdf_file(self, path: str):
        if path in self.pdf_files:
            self.pdf_files.remove(path)

            if self.pdf_path == path:
                self.pdf_path = self.pdf_files[-1] if self.pdf_files else ""

            self._refresh_file_chips("pdf")


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
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose TXT", "", "Text Files (*.txt);;All Files (*)"
        )
        if not paths:
            return

        added = False
        for path in paths:
            if path not in self.txt_files:
                self.txt_files.append(path)
                added = True

        if not added:
            QMessageBox.information(self, "Info", "All selected TXT files are already added.")
            return

        self.txt_path = self.txt_files[-1]

        self.clear_log()
        self._parse_txt_and_fill()
        self._refresh_file_chips("txt")

    def choose_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if not paths:
            return

        added = False
        for path in paths:
            if path not in self.pdf_files:
                self.pdf_files.append(path)
                added = True

        if not added:
            QMessageBox.information(self, "Info", "All selected PDF files are already added.")
            return

        # 当前激活 pdf 用最后一个新增的
        self.pdf_path = self.pdf_files[-1]

        # 每次 add pdf 清空 log
        self.clear_log()
        msg = (
            f'<span style="color:#33cc33;">[Choosing Successful]</span> '
            f'{os.path.basename(self.pdf_path)}'
        )
        self._add_file_log(msg)

        # 刷新气泡显示（“伪文本框”里就会出现这些 tag）
        self._refresh_file_chips("pdf")

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Choose Output WORD", "", "Word file (*.docx)"
        )
        if path:
            if not path.lower().endswith(".docx"):
                path += ".docx"
            self.output_path = path
            # 原来是 self.edit_output.setText(...)
            # 现在改成：
            self.output_label.setText(os.path.basename(path))

            msg = (
                f'<span style="color:#33cc33;">[Choosing Successful]</span> '
                f'Output: {os.path.basename(self.output_path)}'
            )
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
        lines.append(f"Request Description: {self.input_request_desc.toPlainText().strip()}")

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

        mapping["{{Request_desc}}"] = self.input_request_desc.toPlainText().strip()

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

    # icon
    base_dir = Path(__file__).resolve().parents[1]  # .../src
    icon_path_ico = base_dir / "assets" / "app.ico"
    icon_path_png = base_dir / "assets" / "app.png"

    icon_path = icon_path_ico if icon_path_ico.exists() else icon_path_png
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        print(f"[Warning] Icon file not found: {icon_path_ico} / {icon_path_png}")
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