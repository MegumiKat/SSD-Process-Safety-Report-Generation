# src/ui_main.py
import sys, os
from typing import Optional, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QFormLayout,
    QMessageBox, QScrollArea, QSizePolicy, QFrame, QDialog, QStackedWidget,
    QSpacerItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor, QPixmap, QIcon, QResizeEvent, QFont
from pathlib import Path
from datetime import datetime

from src.config.config import DEFAULT_TEMPLATE_PATH, LOGO_PATH
from src.utils.parser_dsc import parse_dsc_txt_basic, parse_dsc_segments
from src.models.models import DscBasicInfo, DscSegment, SampleItem
from src.utils.templating import fill_template_with_mapping
from src.utils.dsc_text import generate_dsc_summary
from src.ui.dialog_add_sample import AddSampleDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DSC Reports Generation Tool (template + txt + pdf)")
        self.resize(1400, 800)

        # ==== 状态 ====
        self.txt_path: str = ""
        self.pdf_path: str = ""
        self.template_path: str = DEFAULT_TEMPLATE_PATH
        self.output_path: str = ""
        self.parsed_info: Optional[DscBasicInfo] = None
        self.parsed_segments: Optional[List[DscSegment]] = None
        self.segment_widgets: list[dict] = []
        self.confirmed: bool = False  # 是否点击过“确认数据”

        # 多样品管理
        self.samples: list[SampleItem] = []
        self.current_sample_id: Optional[int] = None
        self._next_sample_id: int = 1  # 分配样品 id

        # 手动样品表单：sample_id -> { "sample_id": QLineEdit, "nature": QLineEdit, "assign_to": QLineEdit }
        self.sample_manual_widgets: dict[int, dict[str, QLineEdit]] = {}

        # 简单日志（只 print，不再 UI 展示）
        self.file_logs: List[str] = []
        self.confirm_block: Optional[str] = None
        # Step form 状态：0,1,2 对应 3 个步骤
        self.current_step: int = 0
        self.step_completed: List[bool] = [False, False, False]
        self.add_sample_btn: Optional[QPushButton] = None

        # ==== 根布局 ====
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(10)
        self.setCentralWidget(central)

        # 通用分割线
        def _create_separator(
            orientation: str = "h",
            thickness: int = 1,
            color: str = "#444444",
            dashed: bool = False,
        ) -> QFrame:
            line = QFrame()
            if orientation == "h":
                line.setFrameShape(QFrame.Shape.HLine)
                style_prop = "border-top"
            else:
                line.setFrameShape(QFrame.Shape.VLine)
                style_prop = "border-left"

            line.setFrameShadow(QFrame.Shadow.Plain)
            border_style = "dashed" if dashed else "solid"
            line.setStyleSheet(
                f"QFrame {{ border: none; {style_prop}: {thickness}px {border_style} {color}; }}"
            )
            return line

        # =====================================================================
        # 顶部：Logo + 标题（第一行），Step 进度条（第二行）
        # =====================================================================
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(4)

        # ---------- 第一行：左侧 Logo + 标题 ----------
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        # 左侧：LOGO
        target_height = 60
        logo_label = QLabel()
        if os.path.exists(LOGO_PATH):
            pixmap = QPixmap(str(LOGO_PATH))
            if not pixmap.isNull():
                logo_label.setPixmap(
                    pixmap.scaledToHeight(
                        target_height,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
        logo_label.setMinimumHeight(target_height)
        logo_label.setMaximumHeight(target_height + 6)
        top_row.addWidget(logo_label, 0)

        # 标题（最大一档字号）
        self.title_label = QLabel("DSC Reports Generation Tool")
        self.title_label.setObjectName("AppTitle")
        top_row.addWidget(self.title_label, 0)

        # 右侧留空，让标题稍微靠左
        top_row.addStretch(1)
        header_layout.addLayout(top_row)
        header_layout.addWidget(_create_separator("h"))

        # ---------- 第二行：居中的 Step 进度条 ----------
        step_bar_widget = QWidget()
        step_bar_layout = QHBoxLayout(step_bar_widget)
        step_bar_layout.setContentsMargins(8, 0, 8, 0)
        step_bar_layout.setSpacing(4)

        self.step_buttons: list[QPushButton] = []
        step_titles = [
            "1. Files & Samples",
            "2. Auto & Segments",
            "3. Manual & Confirm",
        ]
        for i, text in enumerate(step_titles):
            btn = QPushButton(text)
            btn.setObjectName("StepButton")
            btn.setCheckable(False)
            btn.setEnabled(False)  # 不允许点击跳转，只能上下一个一个走
            btn.setProperty("state", "todo")
            self.step_buttons.append(btn)
            step_bar_layout.addWidget(btn)

            if i < len(step_titles) - 1:
                arrow = QLabel(">>")
                arrow.setObjectName("StepArrow")
                step_bar_layout.addWidget(arrow)

        row_step = QHBoxLayout()
        row_step.setContentsMargins(0, 0, 0, 0)
        row_step.addStretch(1)
        row_step.addWidget(step_bar_widget)
        row_step.addStretch(1)
        header_layout.addLayout(row_step)

        # ---------- Step 导航按钮（这里只创建，不加到 header 里） ----------
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.setObjectName("StepNavButton")
        self.btn_prev.clicked.connect(self._on_prev_clicked)

        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("StepNavButtonPrimary")
        self.btn_next.clicked.connect(self._on_next_clicked)

        # header 只放 logo + 标题 + step 条
        root_layout.addWidget(header_widget)
        root_layout.addWidget(_create_separator("h"))

        # =====================================================================
        # 中央：Step 页面容器
        # =====================================================================
        self.step_stack = QStackedWidget()
        root_layout.addWidget(self.step_stack, stretch=1)

        # 底部：统一的 Step 导航条
        root_layout.addWidget(_create_separator("h"))

        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 8, 0, 0)
        nav_layout.setSpacing(12)
        nav_layout.addStretch(1)
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.btn_next)
        nav_layout.addStretch(1)

        root_layout.addWidget(nav_widget)

        # =====================================================================
        # 通用小工具：新建输入框 & form 行
        # =====================================================================
        def _new_input() -> QLineEdit:
            e = QLineEdit()
            e.setMinimumWidth(140)
            # 横向可扩展，跟随窗口宽度变化
            e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return e

        def _add_form_row(form: QFormLayout, text: str, widget: QWidget):
            label = QLabel(text)
            label.setObjectName("FieldLabel")
            form.addRow(label, widget)

        # =====================================================================
        # Step 1: Files & Samples
        # =====================================================================
        step1 = QWidget()
        s1_layout = QVBoxLayout(step1)
        s1_layout.setContentsMargins(24, 16, 24, 16)
        s1_layout.setSpacing(12)

        # ---- Files group：Template + Output（整体居中） ----
        files_group = QWidget()
        files_group_layout = QVBoxLayout(files_group)
        files_group_layout.setContentsMargins(0, 0, 0, 0)
        files_group_layout.setSpacing(4)
        

        # ---- Template 和 Output 行 ----
        # Template
        row_tpl = QHBoxLayout()
        row_tpl.setContentsMargins(0, 0, 0, 0)
        row_tpl.setSpacing(8)  # 行内控件的基础间距
        lbl_tpl = QLabel("Template:")
        lbl_tpl.setObjectName("HeaderLabel")

        self.label_tpl = QLabel(os.path.basename(self.template_path))
        self.label_tpl.setObjectName("HeaderValue")
        self.label_tpl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.template_box = QWidget()
        self.template_box.setObjectName("TemplateBox")
        tpl_box_layout = QHBoxLayout(self.template_box)
        tpl_box_layout.setContentsMargins(6, 0, 6, 0)
        tpl_box_layout.addWidget(self.label_tpl)

        # 字段名固定宽度
        lbl_tpl.setMinimumWidth(90)
        lbl_tpl.setMaximumWidth(120)
        # value 框可水平扩展
        self.template_box.setSizePolicy(QSizePolicy.Policy.Expanding,
                                        QSizePolicy.Policy.Fixed)

        # 按钮保持固定大小
        btn_tpl = QPushButton("Change")
        btn_tpl.clicked.connect(self.choose_template)
        btn_tpl.setSizePolicy(QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Fixed)

        row_tpl.addWidget(lbl_tpl)
        row_tpl.addSpacing(20)
        row_tpl.addWidget(self.template_box, 1)  # 让 value 部分吃宽度
        row_tpl.addSpacing(20)   
        row_tpl.addWidget(btn_tpl)

        # Output
        row_out = QHBoxLayout()
        row_out.setContentsMargins(0, 6, 0, 0)  # 比 Template 往下留 6px
        row_out.setSpacing(8)
        lbl_out = QLabel("Output:")
        lbl_out.setObjectName("HeaderLabel")

        self.output_box = QWidget()
        self.output_box.setObjectName("OutputBox")
        out_layout = QHBoxLayout(self.output_box)
        out_layout.setContentsMargins(6, 0, 6, 0)
        out_layout.setSpacing(4)

        self.output_label = QLabel("< None >")
        self.output_label.setObjectName("HeaderValue")
        self.output_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        out_layout.addWidget(self.output_label)

        self.output_box.setSizePolicy(QSizePolicy.Policy.Expanding,
                                    QSizePolicy.Policy.Fixed)

        btn_out = QPushButton("Choose")
        btn_out.clicked.connect(self.choose_output)
        btn_out.setSizePolicy(QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Fixed)

        lbl_out.setMinimumWidth(90)
        lbl_out.setMaximumWidth(120)

        row_out.addWidget(lbl_out)
        row_out.addSpacing(20)
        row_out.addWidget(self.output_box, 1)
        row_out.addSpacing(20)
        row_out.addWidget(btn_out)

        files_group_layout.addLayout(row_tpl)
        files_group_layout.addLayout(row_out)

        # 记录 header 字段 / value / 按钮，用于统一调字体
        self._header_field_labels = [lbl_tpl, lbl_out]
        self._header_field_values = [self.label_tpl, self.output_label]
        self._header_field_buttons = [btn_tpl, btn_out]

        # 给 Files group 一个上限宽度，整体居中
        # files_group.setMaximumWidth(700)
        s1_layout.addWidget(files_group, 0, Qt.AlignmentFlag.AlignHCenter)

        # ---- Samples 列表 ----
        sample_group = QWidget()
        sample_group.setObjectName("SampleGroup")
        sample_group_layout = QVBoxLayout(sample_group)
        sample_group_layout.setContentsMargins(16, 12, 16, 12)
        sample_group_layout.setSpacing(6)

        lbl_samples = QLabel("Samples")
        lbl_samples.setObjectName("sectionTitle")
        sample_group_layout.addWidget(lbl_samples)

        self.sample_scroll = QScrollArea()
        self.sample_scroll.setWidgetResizable(True)

        self.sample_list_container = QWidget()
        self.sample_list_layout = QVBoxLayout(self.sample_list_container)
        self.sample_list_layout.setContentsMargins(0, 0, 0, 0)
        self.sample_list_layout.setSpacing(8)

        self.sample_scroll.setWidget(self.sample_list_container)
        sample_group_layout.addWidget(self.sample_scroll)

        # 样品列表占据剩余空间
        s1_layout.addWidget(sample_group, stretch=1)

        self.step_stack.addWidget(step1)

        self._rebuild_sample_list_ui()
        self._set_output_empty_style()

        # =====================================================================
        # Step 2: Auto & Segments
        # =====================================================================
        step2 = QWidget()
        s2_layout = QVBoxLayout(step2)
        s2_layout.setContentsMargins(24, 16, 24, 16)  # Auto 页左右多留一些
        s2_layout.setSpacing(12)

        # 顶部：标题 + 当前样品切换
        auto_header_layout = QHBoxLayout()
        auto_header_layout.addStretch(1)

        self.label_current_sample = QLabel("No sample")
        self.label_current_sample.setObjectName("CurrentSampleLabel")

        self.btn_prev_sample = QPushButton("◀")
        self.btn_prev_sample.setObjectName("SampleNavButton")
        self.btn_prev_sample.clicked.connect(self._goto_prev_sample)

        self.btn_next_sample = QPushButton("▶")
        self.btn_next_sample.setObjectName("SampleNavButton")
        self.btn_next_sample.clicked.connect(self._goto_next_sample)

        auto_header_layout.addWidget(self.label_current_sample)
        auto_header_layout.addWidget(self.btn_prev_sample)
        auto_header_layout.addWidget(self.btn_next_sample)

        s2_layout.addLayout(auto_header_layout)

        # Auto + Segments 滚动区域
        auto_scroll = QScrollArea()
        auto_scroll.setWidgetResizable(True)
        auto_container = QWidget()
        auto_vbox = QVBoxLayout(auto_container)
        auto_vbox.setContentsMargins(0, 0, 0, 0)
        auto_vbox.setSpacing(8)

        auto_form = QFormLayout()
        auto_form.setHorizontalSpacing(12)
        auto_form.setVerticalSpacing(6)
        auto_vbox.addLayout(auto_form)

        def _new_auto_input() -> QLineEdit:
            e = QLineEdit()
            e.setMinimumWidth(400)
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

        self.auto_sample_name.textChanged.connect(self._on_auto_sample_name_changed)

        title_auto = QLabel("Automatically identified fields:")
        title_auto.setObjectName("sectionTitle")
        auto_form.addRow(title_auto)

        _add_form_row(auto_form, "Sample Name:", self.auto_sample_name)
        _add_form_row(auto_form, "Sample Mass:", self.auto_sample_mass)
        _add_form_row(auto_form, "Operator:", self.auto_operator)
        _add_form_row(auto_form, "Instrument:", self.auto_instrument)
        _add_form_row(auto_form, "Atmosphere:", self.auto_atmosphere)
        _add_form_row(auto_form, "Crucible:", self.auto_crucible)
        _add_form_row(auto_form, "Temp.Calib.:", self.auto_temp_calib)
        _add_form_row(auto_form, "End Date:", self.auto_end_date)

        seg_title = QLabel("Segments:")
        seg_title.setObjectName("sectionTitle")
        auto_vbox.addWidget(seg_title)

        self.segment_area_layout = QVBoxLayout()
        self.segment_area_layout.setContentsMargins(0, 0, 0, 0)
        self.segment_area_layout.setSpacing(4)
        auto_vbox.addLayout(self.segment_area_layout)

        auto_scroll.setWidget(auto_container)
        s2_layout.addWidget(auto_scroll, stretch=1)

        self.step_stack.addWidget(step2)

        # =====================================================================
        # Step 3: Manual & Confirm
        # =====================================================================
        step3 = QWidget()
        s3_layout = QVBoxLayout(step3)
        s3_layout.setContentsMargins(20, 16, 20, 16)
        s3_layout.setSpacing(12)

        lbl_manual_title = QLabel("Manual request & sample information")
        lbl_manual_title.setObjectName("sectionTitle")
        s3_layout.addWidget(lbl_manual_title)

        manual_block = QWidget()
        manual_hbox = QHBoxLayout(manual_block)
        manual_hbox.setContentsMargins(0, 0, 0, 0)
        manual_hbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Request 字段 ---
        self.input_lsmp_code = _new_input()
        self.input_request_id = _new_input()
        self.input_customer = _new_input()
        self.input_request_name = _new_input()
        self.input_submission_date = _new_input()
        self.input_request_number = _new_input()
        self.input_project_account = _new_input()
        self.input_deadline = _new_input()
        self.input_test_date = _new_input()
        self.input_receive_date = _new_input()
        self.input_report_date = _new_input()

        self.input_request_desc = QTextEdit()
        self.input_request_desc.setAcceptRichText(False)
        self.input_request_desc.setMinimumWidth(140)
        self.input_request_desc.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.input_lsmp_code.setText("LSMP-21 F01v04")

        # 左：Request + scroll
        scroll_request = QScrollArea()
        scroll_request.setWidgetResizable(True)
        request_container = QWidget()
        self.request_form = QFormLayout(request_container)
        self.request_form.setHorizontalSpacing(12)
        self.request_form.setVerticalSpacing(6)

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
        _add_form_row(self.request_form, "Request Description:", self.input_request_desc)

        scroll_request.setWidget(request_container)

        # 右：Sample manual + scroll
        scroll_sample = QScrollArea()
        scroll_sample.setWidgetResizable(True)
        sample_container = QWidget()

        self.sample_manual_layout = QVBoxLayout(sample_container)
        self.sample_manual_layout.setContentsMargins(0, 0, 0, 0)
        self.sample_manual_layout.setSpacing(8)

        scroll_sample.setWidget(sample_container)

        manual_hbox.addWidget(scroll_request, 2)
        manual_hbox.addWidget(_create_separator("v"), 0)
        manual_hbox.addWidget(scroll_sample, 3)

        s3_layout.addWidget(manual_block, stretch=1)
        self.step_stack.addWidget(step3)

        self._rebuild_manual_sample_forms()
        self._init_placeholders()

        # 初始更新 step 状态 & 导航按钮
        self._update_step_states()
        self._update_nav_buttons()

        # 模板检查
        if not os.path.exists(self.template_path):
            QMessageBox.warning(
                self,
                "Warning",
                f"Can't find the template:\n{self.template_path}\nPlease check data or modify config.DEFAULT_TEMPLATE_PATH."
            )

        # 初次字体自适应
        self._apply_font_scaling()

    # =====================================================================
    # Step 导航逻辑
    # =====================================================================
    def _goto_step(self, index: int):
        if index < 0 or index > 2:
            return
        prev = self.current_step
        if index == prev:
            return

        # 前进：认为之前 step 均完成
        if index > prev:
            for i in range(prev, index):
                self.step_completed[i] = True
        else:
            # 后退：将后面的 step 状态清空
            for i in range(index + 1, len(self.step_completed)):
                self.step_completed[i] = False
                if i == 2:
                    self.confirmed = False  # 回退时取消确认状态

        self.current_step = index
        self.step_stack.setCurrentIndex(index)
        self._update_step_states()
        self._update_nav_buttons()

    def _update_step_states(self):
        for i, btn in enumerate(self.step_buttons):
            if i == self.current_step:
                state = "current"
            elif self.step_completed[i]:
                state = "done"
            else:
                state = "todo"
            btn.setProperty("state", state)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_nav_buttons(self):
        self.btn_prev.setEnabled(self.current_step > 0)
        if self.current_step < 2:
            self.btn_next.setText("Next")
        else:
            self.btn_next.setText("Confirm Data")

    def _on_prev_clicked(self):
        self._goto_step(self.current_step - 1)

    def _on_next_clicked(self):
        # Step 0 校验：需要至少 1 个样品 + 输出路径
        if self.current_step == 0:
            if not self.output_path:
                QMessageBox.warning(self, "Info", "Please choose output file.")
                return
            if not self.samples:
                QMessageBox.warning(self, "Info", "Please add at least one sample.")
                return
            self._goto_step(1)
            return

        # Step 1：自动识别调整完成 → Step 2
        if self.current_step == 1:
            if not self.samples:
                QMessageBox.warning(self, "Info", "No samples. Please add samples first.")
                return
            self._goto_step(2)
            return

        # Step 2：点击 = 确认数据（弹出对话框）
        if self.current_step == 2:
            self.on_confirm()

    # =====================================================================
    # 字体缩放：标题最大，Step/模块标题第二层，字段/按钮第三层
    # =====================================================================
    def _apply_font_scaling(self):
        app = QApplication.instance()
        if app is None:
            return

        # 先按窗口宽度决定“字段/按钮”这一层的基础字号
        w = max(self.width(), 900)
        if w >= 1700:
            base = 20   # 字段/按钮/输入框
        elif w >= 1300:
            base = 18
        else:
            base = 16

        # 1）全局基础字体：字段名 / value / 按钮 / 输入框
        app_font = QFont(app.font())
        app_font.setPointSize(base)
        app.setFont(app_font)

        # 2）顶部标题：最大一档
        title_size = base + 6   # 比字段大一档
        tf = QFont(self.title_label.font())
        tf.setPointSize(title_size)
        tf.setBold(True)
        self.title_label.setFont(tf)

        # 3）Step 按钮 & sectionTitle / SampleManualTitle
        step_size = base + 2
        for btn in self.step_buttons:
            f = QFont(btn.font())
            f.setPointSize(step_size)
            btn.setFont(f)

        for lbl in self.findChildren(QLabel, "sectionTitle"):
            f = QFont(lbl.font())
            f.setPointSize(step_size)
            f.setBold(True)
            lbl.setFont(f)

        for lbl in self.findChildren(QLabel, "SampleManualTitle"):
            f = QFont(lbl.font())
            f.setPointSize(step_size - 1)
            f.setBold(True)
            lbl.setFont(f)

        # 4）底部导航按钮 / 样品切换按钮 / 当前样品标签
        nav_size = base
        for btn in (self.btn_prev, self.btn_next,
                    self.btn_prev_sample, self.btn_next_sample):
            f = QFont(btn.font())
            f.setPointSize(nav_size)
            btn.setFont(f)

        f_lbl = QFont(self.label_current_sample.font())
        f_lbl.setPointSize(nav_size)
        self.label_current_sample.setFont(f_lbl)

        # 5）Template/Output 左侧字段名
        for lbl in self.findChildren(QLabel, "HeaderLabel"):
            f = QFont(lbl.font())
            f.setPointSize(base)
            lbl.setFont(f)

        # 6）普通字段名（Sample Name / Sample Mass / …）
        for lbl in self.findChildren(QLabel, "FieldLabel"):
            f = QFont(lbl.font())
            f.setPointSize(base)
            lbl.setFont(f)

        # 7）所有单行/多行输入框，用同一个字号
        for e in self.findChildren(QLineEdit):
            f = QFont(e.font())
            f.setPointSize(base)
            e.setFont(f)

        for t in self.findChildren(QTextEdit):
            f = QFont(t.font())
            f.setPointSize(base)
            t.setFont(f)

        # 5）Template/Output 左侧 “Template: / Output:” 字段名
        for lbl in getattr(self, "_header_field_labels", []):
            f = QFont(lbl.font())
            f.setPointSize(base)   # 和普通字段一样大
            lbl.setFont(f)

        # 6）Template/Output 的 value 文本 + Change/Choose 按钮
        for w in getattr(self, "_header_field_values", []) + getattr(self, "_header_field_buttons", []):
            f = QFont(w.font())
            f.setPointSize(base)
            w.setFont(f)

        # 7）Add Sample 按钮：不要比 "Samples" 标题大
        if getattr(self, "add_sample_btn", None) is not None:
            f = QFont(self.add_sample_btn.font())
            f.setPointSize(base)  # 或者 base-1，看你视觉效果
            self.add_sample_btn.setFont(f)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_font_scaling()

    # =====================================================================
    # 基础 UI 辅助
    # =====================================================================
    def _set_output_empty_style(self):
        self.output_label.setStyleSheet("color: #ff6666;")
        self.output_label.setText("< None >")

    def _set_output_filled_style(self):
        self.output_label.setStyleSheet("color: #33cc33;")

    def _init_placeholders(self):
        # Request
        self.input_lsmp_code.setPlaceholderText("Test Code")
        self.input_request_id.setPlaceholderText("Request Id")
        self.input_customer.setPlaceholderText("Customer Information")
        self.input_request_name.setPlaceholderText("Request Name")
        self.input_submission_date.setPlaceholderText("YYYY/MM/DD")
        self.input_request_number.setPlaceholderText("Request Number")
        self.input_project_account.setPlaceholderText("Project Account")
        self.input_deadline.setPlaceholderText("YYYY/MM/DD")
        self.input_receive_date.setPlaceholderText("YYYY/MM/DD")
        self.input_test_date.setPlaceholderText("YYYY/MM/DD")
        self.input_report_date.setPlaceholderText("YYYY/MM/DD")
        try:
            self.input_request_desc.setPlaceholderText("Request Description")
        except AttributeError:
            pass

        # Auto
        self.auto_sample_name.setPlaceholderText("Sample Name")
        self.auto_sample_mass.setPlaceholderText("Sample Mass(mg)")
        self.auto_operator.setPlaceholderText("Operator")
        self.auto_instrument.setPlaceholderText("Instrument")
        self.auto_atmosphere.setPlaceholderText("Atmosphere")
        self.auto_crucible.setPlaceholderText("Crucible")
        self.auto_temp_calib.setPlaceholderText("YYYY/MM/DD")
        self.auto_end_date.setPlaceholderText("YYYY/MM/DD")

    # =====================================================================
    # 样品工具
    # =====================================================================
    def _get_current_sample(self) -> Optional[SampleItem]:
        if self.current_sample_id is None:
            return None
        for s in self.samples:
            if s.id == self.current_sample_id:
                return s
        return None

    def _get_current_sample_index(self) -> int:
        if self.current_sample_id is None or not self.samples:
            return -1
        for idx, s in enumerate(self.samples):
            if s.id == self.current_sample_id:
                return idx
        return -1

    def _update_auto_sample_header(self):
        total = len(self.samples)
        if total == 0 or self.current_sample_id is None:
            self.label_current_sample.setText("No sample")
            self.btn_prev_sample.setEnabled(False)
            self.btn_next_sample.setEnabled(False)
            return

        idx = self._get_current_sample_index()
        sample = self._get_current_sample()
        if sample is None:
            self.label_current_sample.setText("No sample")
            self.btn_prev_sample.setEnabled(False)
            self.btn_next_sample.setEnabled(False)
            return

        self.label_current_sample.setText(f"{sample.name} ({idx + 1}/{total})")
        self.btn_prev_sample.setEnabled(idx > 0)
        self.btn_next_sample.setEnabled(idx < total - 1)

    # =====================================================================
    # Step 2: 样品切换
    # =====================================================================
    def _goto_prev_sample(self):
        if not self.samples:
            return
        idx = self._get_current_sample_index()
        if idx <= 0:
            return
        new_sample = self.samples[idx - 1]
        self.on_sample_card_clicked(new_sample.id)

    def _goto_next_sample(self):
        if not self.samples:
            return
        idx = self._get_current_sample_index()
        if idx < 0 or idx >= len(self.samples) - 1:
            return
        new_sample = self.samples[idx + 1]
        self.on_sample_card_clicked(new_sample.id)

    def _load_sample_to_ui(self, sample: SampleItem):
        af = sample.auto_fields
        self.auto_sample_name.setText(af.sample_name)
        self.auto_sample_mass.setText(af.sample_mass)
        self.auto_operator.setText(af.operator)
        self.auto_instrument.setText(af.instrument)
        self.auto_atmosphere.setText(af.atmosphere)
        self.auto_crucible.setText(af.crucible)
        self.auto_temp_calib.setText(af.temp_calib)
        self.auto_end_date.setText(af.end_date)

        self.parsed_info = sample.basic_info
        self.parsed_segments = sample.segments
        self._build_segments_auto_fields(self.parsed_segments or [])

        self._update_auto_sample_header()

    def _store_ui_to_sample(self, sample: SampleItem):
        self._apply_segment_edits()

        af = sample.auto_fields
        af.sample_name = self.auto_sample_name.text().strip()
        af.sample_mass = self.auto_sample_mass.text().strip()
        af.operator = self.auto_operator.text().strip()
        af.instrument = self.auto_instrument.text().strip()
        af.atmosphere = self.auto_atmosphere.text().strip()
        af.crucible = self.auto_crucible.text().strip()
        af.temp_calib = self.auto_temp_calib.text().strip()
        af.end_date = self.auto_end_date.text().strip()

        sample.segments = self.parsed_segments or []

    def _on_auto_sample_name_changed(self, text: str):
        sample = self._get_current_sample()
        if sample is None:
            return
        new_name = text.strip()
        sample.name = new_name
        sample.auto_fields.sample_name = new_name

        self._sync_manual_fields_from_ui()
        self._rebuild_sample_list_ui()
        self._rebuild_manual_sample_forms()
        self._update_auto_sample_header()

    # =====================================================================
    # Step 1: 样品列表
    # =====================================================================
    def _rebuild_sample_list_ui(self):
        while self.sample_list_layout.count():
            item = self.sample_list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        add_btn = QPushButton("+ Add Sample")
        add_btn.setObjectName("AddSampleButton")
        add_btn.clicked.connect(self.on_add_sample_clicked)
        self.sample_list_layout.addWidget(add_btn)
        self.add_sample_btn = add_btn

        self.sample_list_layout.addSpacerItem(
            QSpacerItem(0, 12, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        )

        for sample in self.samples:
            card = self._create_sample_card(sample)
            self.sample_list_layout.addWidget(card)

        self.sample_list_layout.addStretch(1)

    def _create_sample_card(self, sample: SampleItem) -> QWidget:
        card = QWidget()
        card.setObjectName("SampleCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        icon_label = QLabel("🧪")
        layout.addWidget(icon_label)

        name_label = QLabel(sample.name)
        name_label.setObjectName("SampleNameLabel")
        layout.addWidget(name_label, 1)

        txt_status = QLabel("TXT: ✓" if os.path.exists(sample.txt_path) else "TXT: ✗")
        layout.addWidget(txt_status)

        if sample.pdf_path:
            pdf_status = QLabel("PDF: ✓" if os.path.exists(sample.pdf_path) else "PDF: ✗")
        else:
            pdf_status = QLabel("PDF: -")
        layout.addWidget(pdf_status)

        layout.addStretch(1)

        btn_remove = QPushButton("Remove")
        btn_remove.setObjectName("SampleRemoveButton")
        btn_remove.setFixedHeight(30)
        btn_remove.clicked.connect(lambda _, sid=sample.id: self.on_remove_sample(sid))
        layout.addWidget(btn_remove)

        def on_card_clicked(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.on_sample_card_clicked(sample.id)

        card.mousePressEvent = on_card_clicked
        return card

    def on_sample_card_clicked(self, sample_id: int):
        current = self._get_current_sample()
        if current is not None:
            self._store_ui_to_sample(current)

        sample = next((s for s in self.samples if s.id == sample_id), None)
        if not sample:
            return

        self.current_sample_id = sample.id
        self.txt_path = sample.txt_path
        self.pdf_path = sample.pdf_path or ""

        if sample.basic_info is None:
            self.clear_log()
            self._parse_sample(sample)
        else:
            self.parsed_info = sample.basic_info
            self.parsed_segments = sample.segments
            self._load_sample_to_ui(sample)

    def _get_latest_end_date_from_samples(self) -> str:
        if not self.samples:
            return self.auto_end_date.text().strip()

        candidates: list[tuple[datetime, str]] = []
        for s in self.samples:
            raw = (s.auto_fields.end_date or "").strip()
            if not raw:
                continue
            dt = None
            for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue
            if dt is not None:
                candidates.append((dt, raw))

        if not candidates:
            return self.auto_end_date.text().strip()

        latest_dt, latest_raw = max(candidates, key=lambda x: x[0])
        return latest_raw

    def on_remove_sample(self, sample_id: int):
        target = next((s for s in self.samples if s.id == sample_id), None)
        if not target:
            return

        reply = QMessageBox.question(
            self,
            "Remove Sample",
            f"Are you sure to remove sample:\n\n{target.name} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.samples = [s for s in self.samples if s.id != sample_id]

        if self.current_sample_id == sample_id:
            if self.samples:
                new_sample = self.samples[0]
                self.current_sample_id = new_sample.id
                self.txt_path = new_sample.txt_path
                self.pdf_path = new_sample.pdf_path or ""
                self.parsed_info = new_sample.basic_info
                self.parsed_segments = new_sample.segments
                self._load_sample_to_ui(new_sample)
            else:
                self.current_sample_id = None
                self.txt_path = ""
                self.pdf_path = ""
                self.parsed_info = None
                self.parsed_segments = None

                self.auto_sample_name.clear()
                self.auto_sample_mass.clear()
                self.auto_operator.clear()
                self.auto_instrument.clear()
                self.auto_atmosphere.clear()
                self.auto_crucible.clear()
                self.auto_temp_calib.clear()
                self.auto_end_date.clear()
                self._build_segments_auto_fields([])

        self._rebuild_sample_list_ui()
        self._rebuild_manual_sample_forms()
        self._update_auto_sample_header()

        msg = f"[Sample Removed] {target.name}"
        self._add_file_log(msg)

    # =====================================================================
    # Step 3: 手动样品表单
    # =====================================================================
    def _rebuild_manual_sample_forms(self):
        self._sync_manual_fields_from_ui()

        while self.sample_manual_layout.count():
            item = self.sample_manual_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.sample_manual_widgets.clear()

        if not self.samples:
            placeholder = QLabel("No samples. Please add samples in Step 1.")
            self.sample_manual_layout.addWidget(placeholder)
            self.sample_manual_layout.addStretch(1)
            return

        for idx, sample in enumerate(self.samples):
            group = QWidget()
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(0, 4, 0, 4)
            group_layout.setSpacing(4)

            title = QLabel(sample.name)
            title.setObjectName("SampleManualTitle")
            group_layout.addWidget(title)

            row = QHBoxLayout()
            row.setSpacing(6)

            edit_sample_id = QLineEdit()
            edit_nature = QLineEdit()
            edit_assign_to = QLineEdit()

            mf = sample.manual_fields
            edit_sample_id.setText(mf.sample_id)
            edit_nature.setText(mf.nature)
            edit_assign_to.setText(mf.assign_to)

            edit_sample_id.setPlaceholderText("Sample Id")
            edit_nature.setPlaceholderText("Nature")
            edit_assign_to.setPlaceholderText("Assign To")

            for e in (edit_sample_id, edit_nature, edit_assign_to):
                e.setMinimumWidth(120)
                e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            row.addWidget(QLabel("Sample Id:"))
            row.addWidget(edit_sample_id)
            row.addWidget(QLabel("Nature:"))
            row.addWidget(edit_nature)
            row.addWidget(QLabel("Assign To:"))
            row.addWidget(edit_assign_to)

            group_layout.addLayout(row)
            self.sample_manual_layout.addWidget(group)

            self.sample_manual_widgets[sample.id] = {
                "sample_id": edit_sample_id,
                "nature": edit_nature,
                "assign_to": edit_assign_to,
            }

            if idx < len(self.samples) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setFrameShadow(QFrame.Shadow.Plain)
                sep.setStyleSheet(
                    "QFrame { border: none; border-top: 1px dashed #555555; }"
                )
                self.sample_manual_layout.addWidget(sep)

        self.sample_manual_layout.addStretch(1)

    def _sync_manual_fields_from_ui(self):
        if not self.samples:
            return
        for sample in self.samples:
            widgets = self.sample_manual_widgets.get(sample.id)
            if not widgets:
                continue
            mf = sample.manual_fields
            mf.sample_id = widgets["sample_id"].text().strip()
            mf.nature = widgets["nature"].text().strip()
            mf.assign_to = widgets["assign_to"].text().strip()

    def on_add_sample_clicked(self):
        dlg = AddSampleDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        sample = SampleItem(
            id=self._next_sample_id,
            name=dlg.sample_name,
            txt_path=dlg.txt_path,
            pdf_path=dlg.pdf_path,
        )
        self._next_sample_id += 1

        self.samples.append(sample)
        self.current_sample_id = sample.id
        self._parse_sample(sample)
        self._rebuild_sample_list_ui()
        self._rebuild_manual_sample_forms()
        self._update_auto_sample_header()

    # =====================================================================
    # Segments 构建/保存
    # =====================================================================
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            child_layout = item.layout()
            if w is not None:
                w.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _build_segments_auto_fields(self, segments: List[DscSegment]):
        self._clear_layout(self.segment_area_layout)
        self.segment_widgets.clear()

        if not segments:
            label = QLabel("No valid segment detected.")
            self.segment_area_layout.addWidget(label)
            return

        count_label = QLabel(f"{len(segments)} segment(s) detected")
        self.segment_area_layout.addWidget(count_label)

        for si, seg in enumerate(segments, start=1):
            seg_box = QWidget()
            seg_box_layout = QVBoxLayout(seg_box)
            seg_box_layout.setContentsMargins(0, 4, 0, 4)

            seg_header = QLabel(f"Segment {si}: {seg.desc_display}")
            seg_header.setStyleSheet("font-weight:bold;")
            seg_box_layout.addWidget(seg_header)

            for pi, part in enumerate(seg.parts, start=1):
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)

                def _make_edit(placeholder: str, text: str = "") -> QLineEdit:
                    e = QLineEdit()
                    e.setPlaceholderText(placeholder)
                    e.setText(text)
                    # Segments 部分希望更短一点：限制最小和最大宽度，不要跟随整行拉长
                    e.setMinimumWidth(80)
                    e.setMaximumWidth(160)
                    e.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
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

                row_layout.addWidget(QLabel(f"Part {pi}:"))
                row_layout.addWidget(value_edit)
                row_layout.addWidget(onset_edit)
                row_layout.addWidget(peak_edit)
                row_layout.addWidget(area_edit)
                row_layout.addWidget(comment_edit)
                row_layout.addStretch(1)

                seg_box_layout.addWidget(row_widget)

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

    # =====================================================================
    # 解析样品 txt
    # =====================================================================
    def _parse_sample(self, sample: SampleItem):
        if not sample.txt_path:
            return

        try:
            basic = parse_dsc_txt_basic(sample.txt_path)
            sample.basic_info = basic

            try:
                segments = parse_dsc_segments(sample.txt_path, pdf_path=sample.pdf_path)
            except Exception as e_seg:
                segments = []
                msg_seg = f"[Segments Parsed Failed] {os.path.basename(sample.txt_path)} - {e_seg}"
                self._add_file_log(msg_seg)

            sample.segments = segments

            af = sample.auto_fields
            af.sample_name = basic.sample_name or ""
            if basic.sample_mass_mg is not None:
                af.sample_mass = f"{basic.sample_mass_mg:.3f} mg"
            else:
                af.sample_mass = ""
            af.operator = basic.operator or ""
            af.instrument = basic.instrument or ""
            af.atmosphere = basic.atmosphere or ""
            af.crucible = basic.crucible or ""
            af.temp_calib = basic.temp_calib or ""
            af.end_date = basic.end_date or ""

            self.current_sample_id = sample.id
            self.txt_path = sample.txt_path
            self.pdf_path = sample.pdf_path or ""
            self.parsed_info = sample.basic_info
            self.parsed_segments = sample.segments

            self._load_sample_to_ui(sample)

            self.confirmed = False
            self.confirm_block = None

            has_txt = bool(sample.txt_path)
            has_pdf = bool(sample.pdf_path)

            if has_txt and has_pdf:
                file_info = f"{sample.name} (TXT + PDF)"
            elif has_txt:
                file_info = f"{sample.name} (TXT)"
            elif has_pdf:
                file_info = f"{sample.name} (PDF)"
            else:
                file_info = sample.name

            msg = f"[Parsing Successful] {file_info}"
            self._add_file_log(msg)

        except Exception as e:
            sample.basic_info = None
            sample.segments = []
            self.parsed_info = None
            self.parsed_segments = None

            has_txt = bool(sample.txt_path)
            has_pdf = bool(sample.pdf_path)
            if not has_txt and not has_pdf:
                file_info = f"{sample.name} (TXT + PDF)"
            elif not has_txt:
                file_info = f"{sample.name} (TXT)"
            elif not has_pdf:
                file_info = f"{sample.name} (PDF)"
            else:
                file_info = sample.name

            msg = f"[Parsing Failed] {file_info} - {e}"
            self._add_file_log(msg)

    # =====================================================================
    # 文件选择 & 模板
    # =====================================================================
    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Choose Output WORD", "", "Word file (*.docx)"
        )
        if path:
            if not path.lower().endswith(".docx"):
                path += ".docx"
            self.output_path = path
            self.output_label.setText(os.path.basename(path))
            self._set_output_filled_style()

            msg = f"[Choosing Successful] Output: {os.path.basename(self.output_path)}"
            self._add_file_log(msg)

    def choose_template(self):
        QMessageBox.information(
            self,
            "Info",
            "Change Template function is not implemented yet."
        )

    # =====================================================================
    # 确认数据（Step3 Next）
    # =====================================================================
    def on_confirm(self):
        if not self.txt_path:
            QMessageBox.warning(self, "Tips", "Please choose TXT")
            return
        if self.parsed_info is None:
            QMessageBox.warning(self, "Tips", "[TXT]Haven't parsed successful")
            return

        current_sample = self._get_current_sample()
        if current_sample is not None:
            self._store_ui_to_sample(current_sample)
        self._sync_manual_fields_from_ui()

        label_style = 'style="color:rgb(255,119,0);font-weight:bold;"'
        parts: list[str] = []

        parts.append("<div>")
        parts.append('<b>===== Automatically identified fields (final value) =====</b><br><br>')

        if not self.samples:
            parts.append(f'<span {label_style}>No samples.</span><br><br>')
        else:
            for idx, sample in enumerate(self.samples, start=1):
                af = sample.auto_fields
                parts.append(
                    f'<span {label_style}>Sample {idx}: {sample.name}</span><br>'
                )
                parts.append(f'<span {label_style}>Sample Name:</span>&nbsp;&nbsp;{af.sample_name}<br>')
                parts.append(f'<span {label_style}>Crucible:</span>&nbsp;&nbsp;{af.crucible}<br>')
                parts.append(f'<span {label_style}>Temp.Calib.:</span>&nbsp;&nbsp;{af.temp_calib}<br>')
                parts.append(f'<span {label_style}>End Date:</span>&nbsp;&nbsp;{af.end_date}<br>')
                parts.append("<br>")

            final_end_date = self._get_latest_end_date_from_samples()
            parts.append(
                f'<span {label_style}>Final End Date:</span>'
                f'&nbsp;&nbsp;{final_end_date}<br><br>'
            )

        parts.append('<b>===== Manual input =====</b><br><br>')

        parts.append(f'<span {label_style}>Test Code:</span>&nbsp;&nbsp;{self.input_lsmp_code.text().strip()}<br>')
        parts.append(f'<span {label_style}>Request Id:</span>&nbsp;&nbsp;{self.input_request_id.text().strip()}<br>')
        parts.append(f'<span {label_style}>Customer Information:</span>&nbsp;&nbsp;{self.input_customer.text().strip()}<br>')
        parts.append(f'<span {label_style}>Request Name:</span>&nbsp;&nbsp;{self.input_request_name.text().strip()}<br>')
        parts.append(f'<span {label_style}>Submission Date:</span>&nbsp;&nbsp;{self.input_submission_date.text().strip()}<br>')
        parts.append(f'<span {label_style}>Request Number:</span>&nbsp;&nbsp;{self.input_request_number.text().strip()}<br>')
        parts.append(f'<span {label_style}>Project Account:</span>&nbsp;&nbsp;{self.input_project_account.text().strip()}<br>')
        parts.append(f'<span {label_style}>Deadline:</span>&nbsp;&nbsp;{self.input_deadline.text().strip()}<br>')
        parts.append(f'<span {label_style}>Test Date:</span>&nbsp;&nbsp;{self.input_test_date.text().strip()}<br>')
        parts.append(f'<span {label_style}>Receive Date:</span>&nbsp;&nbsp;{self.input_receive_date.text().strip()}<br>')
        parts.append(f'<span {label_style}>Report Date:</span>&nbsp;&nbsp;{self.input_report_date.text().strip()}<br>')
        parts.append(f'<span {label_style}>Request Description:</span>&nbsp;&nbsp;{self.input_request_desc.toPlainText().strip()}<br>')
        parts.append("<br>")

        if self.samples:
            for idx, sample in enumerate(self.samples, start=1):
                mf = sample.manual_fields
                parts.append(
                    f'<span {label_style}>Sample {idx}: {sample.name}</span><br>'
                )
                parts.append(f'<span {label_style}>Sample Id:</span>&nbsp;&nbsp;{mf.sample_id}<br>')
                parts.append(f'<span {label_style}>Nature:</span>&nbsp;&nbsp;{mf.nature}<br>')
                parts.append(f'<span {label_style}>Assign To:</span>&nbsp;&nbsp;{mf.assign_to}<br>')
                parts.append("<br>")

        parts.append("</div>")

        self.confirm_block = "".join(parts)
        self.confirmed = True

        # 弹出中央确认对话框
        dlg = QDialog(self)
        dlg.setWindowTitle("Confirm all data")
        dlg.resize(900, 600)

        vbox = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setHtml(self.confirm_block or "")
        vbox.addWidget(txt)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_cancel = QPushButton("Cancel")
        btn_ok = QPushButton("Generate report")
        btn_ok.setObjectName("PrimaryButton")
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        vbox.addLayout(btn_row)

        btn_cancel.clicked.connect(dlg.reject)

        def _do_generate():
            dlg.accept()
            self.on_generate()

        btn_ok.clicked.connect(_do_generate)

        dlg.exec()

        if self.confirmed:
            self.step_completed[2] = True
            self._update_step_states()

    # =====================================================================
    # 生成报告
    # =====================================================================
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

        sample = self._get_current_sample()
        if sample is not None:
            self._store_ui_to_sample(sample)

        mapping: dict[str, str] = {}
        mapping["{{LSMP_code}}"] = self.input_lsmp_code.text().strip()
        mapping["{{Request_id}}"] = self.input_request_id.text().strip()
        mapping["{{Customer_information}}"] = self.input_customer.text().strip()
        mapping["{{Request_Name}}"] = self.input_request_name.text().strip()
        mapping["{{Submission_Date}}"] = self.input_submission_date.text().strip()
        mapping["{{Request_Number}}"] = self.input_request_number.text().strip()
        mapping["{{Project_Account}}"] = self.input_project_account.text().strip()
        mapping["{{Deadline}}"] = self.input_deadline.text().strip()

        self._sync_manual_fields_from_ui()
        current_sample = self._get_current_sample()
        mf = current_sample.manual_fields if current_sample is not None else None

        mapping["{{Sample_id}}"] = mf.sample_id if mf else ""
        mapping["{{Nature}}"] = mf.nature if mf else ""
        mapping["{{Assign_to}}"] = mf.assign_to if mf else ""

        mapping["{{Test_Date}}"] = self.input_test_date.text().strip()
        mapping["{{Receive_Date}}"] = self.input_receive_date.text().strip()
        mapping["{{Report_Date}}"] = self.input_report_date.text().strip()
        mapping["{{Request_desc}}"] = self.input_request_desc.toPlainText().strip()

        mapping["{{Sample_name}}"] = self.auto_sample_name.text().strip()
        mapping["{{Sample_mass}}"] = self.auto_sample_mass.text().strip()
        mapping["{{Operator}}"] = self.auto_operator.text().strip()
        mapping["{{Instrument}}"] = self.auto_instrument.text().strip()
        mapping["{{Atmosphere}}"] = self.auto_atmosphere.text().strip()
        mapping["{{Crucible}}"] = self.auto_crucible.text().strip()
        mapping["{{Temp.Calib}}"] = self.auto_temp_calib.text().strip()
        mapping["{{End_Date}}"] = self._get_latest_end_date_from_samples()

        self._apply_segment_edits()
        segments = self.parsed_segments or []
        if not segments:
            self._add_file_log("[Segments 为空] 将不生成 segments 表格。")

        current_sample = self._get_current_sample()
        mf = current_sample.manual_fields if current_sample is not None else None
        sample_name_for_segments = (
            self.auto_sample_name.text().strip()
            or (mf.sample_id if mf else "")
            or (current_sample.name if current_sample else "")
        )

        discussion_text = ""
        if self.samples:
            pieces: list[str] = []
            for s in self.samples:
                if not s.segments:
                    continue
                label = (
                    s.auto_fields.sample_name
                    or s.manual_fields.sample_id
                    or s.name
                    or ""
                )
                text_one = generate_dsc_summary(label, s.segments)
                if text_one:
                    pieces.append(text_one)
            discussion_text = "\n\n".join(pieces)
        else:
            if segments:
                discussion_text = generate_dsc_summary(sample_name_for_segments, segments)

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
                samples=self.samples,
            )
            self._add_file_log(f"[Generate Successful] {os.path.basename(self.output_path)}")
            QMessageBox.information(self, "Successful", "Generate Successful!\nCan open word and check")
        except Exception as e:
            self._add_file_log(f"[Generate Failed] {os.path.basename(self.output_path)} - {e}")
            QMessageBox.critical(self, "Error", f"Generate Failed\n{e}")

    # =====================================================================
    # 简单日志（不再显示 UI，只 print）
    # =====================================================================
    def render_log(self):
        pass

    def clear_log(self):
        self.file_logs.clear()
        self.confirm_block = None
        self.generate_logs.clear()

    def _add_file_log(self, msg: str):
        self.file_logs.append(msg)
        print(msg)


# =====================================================================
# main 函数
# =====================================================================

def main():
    app = QApplication(sys.argv)

    # 全局基础字体：直接给一个相对舒适的起始值（后面 _apply_font_scaling 会接管）
    base_font = QFont()
    base_font.setPointSize(30)
    app.setFont(base_font)

    base_dir = Path(__file__).resolve().parents[1]  # .../src
    icon_path_ico = base_dir / "assets" / "app.ico"
    icon_path_png = base_dir / "assets" / "app.png"

    icon_path = icon_path_ico if icon_path_ico.exists() else icon_path_png
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        print(f"[Warning] Icon file not found: {icon_path_ico} / {icon_path_png}")

    qss_path = base_dir / "assets" / "app.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"[Warning] QSS file not found: {qss_path}")

    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()