# src/ui/ui_main.py
import os
from typing import Optional, List
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QFormLayout,
    QMessageBox, QScrollArea, QSizePolicy, QFrame, QDialog, QStackedWidget,
    QSpacerItem, QGridLayout, QApplication, QStyle
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap, QResizeEvent, QFont, QDesktopServices

from src.config.config import DEFAULT_TEMPLATE_PATH, LOGO_PATH
from src.utils.parser_dsc import parse_dsc_txt_basic
from src.models.models import DscBasicInfo, DscSegment, SampleItem
from src.ui.dialog_add_sample import AddSampleDialog
from src.tools.dsc_services import DscParseService, ReportService

from src.tools.workflow_controller import WorkflowController
from src.tools.sample_controller import SampleController
from src.tools.segments_controller import SegmentsController
from src.tools.report_controller import ReportController

from src.tools.theme_controller import ThemeController
from src.ui.widgets.toggle_switch import ToggleSwitch


class MainWindow(QMainWindow):
    SampleItem = SampleItem

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
        self.confirmed: bool = False

        self.parse_service = DscParseService()
        self.report_service = ReportService()

        self._auto_edits: list[QLineEdit] = []

        self.samples: list[SampleItem] = []
        self.current_sample_id: Optional[int] = None
        self._next_sample_id: int = 1

        self.sample_manual_widgets: dict[int, dict[str, QLineEdit]] = {}

        self.file_logs: List[str] = []
        self.confirm_block: Optional[str] = None

        self.current_step: int = 0
        self.step_completed: List[bool] = [False, False, False]
        self.add_sample_btn: Optional[QPushButton] = None

        # ✅ Step1 files grid metrics
        self._files_grid: Optional[QGridLayout] = None
        self._btn_tpl: Optional[QPushButton] = None
        self._btn_out: Optional[QPushButton] = None
        self._tpl_box_layout: Optional[QHBoxLayout] = None
        self._out_box_layout: Optional[QHBoxLayout] = None

        # ==== Theme Controller ====
        app = QApplication.instance()
        project_root = Path(__file__).resolve().parents[2]  # src/ui/ui_main.py -> project root
        light_qss_path = project_root / "src" / "assets" / "app_light.qss"
        dark_qss = app.styleSheet() if app else ""
        self.theme_ctrl = ThemeController(app, dark_qss=dark_qss, light_qss_path=light_qss_path)

        # theme state: True=Night(Dark), False=Day(Light)
        self.is_dark: bool = True

        # ==== 根布局 ====
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(10)
        self.setCentralWidget(central)

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
        # 顶部：Logo + 标题 + Theme Switch + Step
        # =====================================================================
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

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

        self.title_label = QLabel("DSC Reports Generation Tool")
        self.title_label.setObjectName("AppTitle")
        top_row.addWidget(self.title_label, 0)

        top_row.addStretch(1)

        # ---- Theme switch (RIGHT) ----
        self.theme_mode_label = QLabel("Night")
        self.theme_mode_label.setObjectName("ThemeModeLabel")

        self.theme_switch = ToggleSwitch()
        self.theme_switch.setChecked(True)  # default dark/night
        self.theme_switch.toggled.connect(self.on_theme_toggled)

        top_row.addWidget(self.theme_mode_label, 0, Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self.theme_switch, 0, Qt.AlignmentFlag.AlignVCenter)

        header_layout.addLayout(top_row)
        header_layout.addWidget(_create_separator("h"))

        # ---- Step bar ----
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
            btn.setEnabled(False)
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

        self.btn_prev = QPushButton("Previous")
        self.btn_prev.setObjectName("StepNavButton")

        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("StepNavButtonPrimary")

        root_layout.addWidget(header_widget)
        root_layout.addWidget(_create_separator("h"))

        # =====================================================================
        # 中央：Step 页面容器
        # =====================================================================
        self.step_stack = QStackedWidget()
        root_layout.addWidget(self.step_stack, stretch=1)

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
        # 通用小工具
        # =====================================================================
        def _new_input() -> QLineEdit:
            e = QLineEdit()
            e.setMinimumWidth(140)
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

        files_group = QWidget()
        files_group_layout = QVBoxLayout(files_group)
        files_group_layout.setContentsMargins(0, 0, 0, 0)
        files_group_layout.setSpacing(8)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)

        lbl_tpl = QLabel("Template:")
        lbl_tpl.setObjectName("HeaderLabel")
        lbl_tpl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.label_tpl = QLabel(os.path.basename(self.template_path))
        self.label_tpl.setObjectName("HeaderValue")
        self.label_tpl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_tpl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.template_box = QWidget()
        self.template_box.setObjectName("TemplateBox")
        tpl_box_layout = QHBoxLayout(self.template_box)
        tpl_box_layout.setContentsMargins(6, 0, 6, 0)
        tpl_box_layout.setSpacing(0)
        tpl_box_layout.addWidget(self.label_tpl)
        self.template_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._tpl_box_layout = tpl_box_layout

        btn_tpl = QPushButton("Change")
        btn_tpl.clicked.connect(self.choose_template)
        btn_tpl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_tpl = btn_tpl

        grid.addWidget(lbl_tpl, 0, 0)
        grid.addWidget(self.template_box, 0, 1)
        grid.addWidget(btn_tpl, 0, 2)

        lbl_out = QLabel("Output:")
        lbl_out.setObjectName("HeaderLabel")
        lbl_out.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.output_box = QWidget()
        self.output_box.setObjectName("OutputBox")
        out_layout = QHBoxLayout(self.output_box)
        out_layout.setContentsMargins(6, 0, 6, 0)
        out_layout.setSpacing(0)

        self.output_label = QLabel("< None >")
        self.output_label.setObjectName("HeaderValue")
        self.output_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        out_layout.addWidget(self.output_label)

        self.output_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._out_box_layout = out_layout

        btn_out = QPushButton("Choose")
        btn_out.clicked.connect(self.choose_output)
        btn_out.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_out = btn_out

        grid.addWidget(lbl_out, 1, 0)
        grid.addWidget(self.output_box, 1, 1)
        grid.addWidget(btn_out, 1, 2)

        files_group_layout.addLayout(grid)
        self._files_grid = grid

        self._header_field_labels = [lbl_tpl, lbl_out]
        self._header_field_values = [self.label_tpl, self.output_label]
        self._header_field_buttons = [btn_tpl, btn_out]

        s1_layout.addWidget(files_group, 0, Qt.AlignmentFlag.AlignHCenter)

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

        s1_layout.addWidget(sample_group, stretch=1)
        self.step_stack.addWidget(step1)

        self._rebuild_sample_list_ui()
        self._set_output_empty_style()

        # =====================================================================
        # Step 2: Auto & Segments
        # =====================================================================
        step2 = QWidget()
        s2_layout = QVBoxLayout(step2)
        s2_layout.setContentsMargins(24, 16, 24, 16)
        s2_layout.setSpacing(12)

        auto_header_layout = QHBoxLayout()
        auto_header_layout.addStretch(1)

        self.label_current_sample = QLabel("No sample")
        self.label_current_sample.setObjectName("CurrentSampleLabel")

        self.btn_prev_sample = QPushButton("◀")
        self.btn_prev_sample.setObjectName("SampleNavButton")

        self.btn_next_sample = QPushButton("▶")
        self.btn_next_sample.setObjectName("SampleNavButton")

        auto_header_layout.addWidget(self.label_current_sample)
        auto_header_layout.addWidget(self.btn_prev_sample)
        auto_header_layout.addWidget(self.btn_next_sample)
        s2_layout.addLayout(auto_header_layout)

        auto_scroll = QScrollArea()
        auto_scroll.setWidgetResizable(True)
        auto_container = QWidget()
        auto_vbox = QVBoxLayout(auto_container)
        auto_vbox.setContentsMargins(0, 0, 0, 0)
        auto_vbox.setSpacing(6)

        auto_form = QFormLayout()
        auto_form.setHorizontalSpacing(12)
        auto_form.setVerticalSpacing(6)
        auto_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        auto_vbox.addLayout(auto_form)

        def _new_auto_input() -> QLineEdit:
            e = QLineEdit()
            e.setMinimumWidth(260)
            e.setMaximumWidth(520)
            e.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            self._auto_edits.append(e)
            e.textChanged.connect(lambda _t: self._refresh_auto_edits_width())
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
        self._refresh_auto_edits_width()

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
        self.input_request_desc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.input_lsmp_code.setText("LSMP-21 F01v04")

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

        if not os.path.exists(self.template_path):
            QMessageBox.warning(
                self,
                "Warning",
                f"Can't find the template:\n{self.template_path}\nPlease check data or modify config.DEFAULT_TEMPLATE_PATH."
            )

        self._apply_font_scaling()

        # =====================================================================
        # Controllers 初始化
        # =====================================================================
        self.workflow = WorkflowController(self)
        self.sample_ctrl = SampleController(self)
        self.segments_ctrl = SegmentsController(self, self.segment_area_layout)
        self.report_ctrl = ReportController(self)

        self.btn_prev.clicked.connect(self.workflow.on_prev_clicked)
        self.btn_next.clicked.connect(self.workflow.on_next_clicked)
        self.btn_prev_sample.clicked.connect(self.sample_ctrl.goto_prev_sample)
        self.btn_next_sample.clicked.connect(self.sample_ctrl.goto_next_sample)
        self.auto_sample_name.textChanged.connect(self.sample_ctrl.on_auto_sample_name_changed)

        self.workflow.update_step_states()
        self.workflow.update_nav_buttons()
        self.sample_ctrl.update_auto_sample_header()

        # 首帧：同步 switch 尺寸，避免第一次很大
        self._sync_theme_switch_metrics()

    # =====================================================================
    # Theme Switch logic
    # =====================================================================
    def on_theme_toggled(self, checked: bool):
        """
        checked=True => Night(Dark)
        checked=False => Day(Light)
        """
        self.is_dark = bool(checked)
        self.theme_mode_label.setText("Night" if self.is_dark else "Day")
        self.theme_ctrl.apply("dark" if self.is_dark else "light")

        # 切换后强制同步一次，避免控件sizeHint不一致
        self._sync_theme_switch_metrics()
        self._apply_font_scaling()
        self.updateGeometry()

    def _sync_theme_switch_metrics(self):
        """
        Switch 尺寸跟随字体/DPI，不写死（但控制一个合理范围）。
        """
        fm = self.fontMetrics()
        h = max(22, int(fm.height() * 1.20))
        w = max(44, int(h * 2.0))
        self.theme_switch.setFixedSize(w, h)

    # =====================================================================
    # UI helper：给 controller 使用
    # =====================================================================
    def warn(self, title: str, msg: str):
        QMessageBox.warning(self, title, msg)

    def ask_yes_no(self, title: str, msg: str) -> bool:
        reply = QMessageBox.question(
            self,
            title,
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    # =====================================================================
    # Step1 grid metrics
    # =====================================================================
    def _sync_files_grid_metrics(self):
        if self._files_grid is None:
            return
        if self._btn_tpl is None or self._btn_out is None:
            return

        fm = self.fontMetrics()

        hspace = max(18, int(fm.height() * 1.0))
        self._files_grid.setHorizontalSpacing(hspace)

        box_pad = max(10, int(fm.height() * 0.65))
        if self._tpl_box_layout is not None:
            self._tpl_box_layout.setContentsMargins(box_pad, 0, box_pad, 0)
        if self._out_box_layout is not None:
            self._out_box_layout.setContentsMargins(box_pad, 0, box_pad, 0)

        vspace = max(12, int(fm.height() * 0.65))
        self._files_grid.setVerticalSpacing(vspace)

        row_h = max(
            self._btn_tpl.sizeHint().height(),
            self._btn_out.sizeHint().height(),
            self.template_box.sizeHint().height(),
            self.output_box.sizeHint().height(),
            fm.height() + 12,
        )
        self._files_grid.setRowMinimumHeight(0, row_h)
        self._files_grid.setRowMinimumHeight(1, row_h)

        self.template_box.setMinimumHeight(row_h)
        self.output_box.setMinimumHeight(row_h)

    # =====================================================================
    # 字体缩放
    # =====================================================================
    def _apply_font_scaling(self):
        app = QApplication.instance()
        if app is None:
            return

        w = max(self.width(), 900)
        if w >= 1700:
            base = 20
        elif w >= 1300:
            base = 18
        else:
            base = 16

        app_font = QFont(app.font())
        app_font.setPointSize(base)
        app.setFont(app_font)

        title_size = base + 6
        tf = QFont(self.title_label.font())
        tf.setPointSize(title_size)
        tf.setBold(True)
        self.title_label.setFont(tf)

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

        nav_size = base
        for btn in (self.btn_prev, self.btn_next, self.btn_prev_sample, self.btn_next_sample):
            f = QFont(btn.font())
            f.setPointSize(nav_size)
            btn.setFont(f)

        f_lbl = QFont(self.label_current_sample.font())
        f_lbl.setPointSize(nav_size)
        self.label_current_sample.setFont(f_lbl)

        for lbl in self.findChildren(QLabel, "HeaderLabel"):
            f = QFont(lbl.font())
            f.setPointSize(base)
            lbl.setFont(f)

        for lbl in self.findChildren(QLabel, "FieldLabel"):
            f = QFont(lbl.font())
            f.setPointSize(base)
            lbl.setFont(f)

        for e in self.findChildren(QLineEdit):
            f = QFont(e.font())
            f.setPointSize(base)
            e.setFont(f)

        for t in self.findChildren(QTextEdit):
            f = QFont(t.font())
            f.setPointSize(base)
            t.setFont(f)

        for lbl in getattr(self, "_header_field_labels", []):
            f = QFont(lbl.font())
            f.setPointSize(base)
            lbl.setFont(f)

        for wdg in getattr(self, "_header_field_values", []) + getattr(self, "_header_field_buttons", []):
            f = QFont(wdg.font())
            f.setPointSize(base)
            wdg.setFont(f)

        if getattr(self, "add_sample_btn", None) is not None:
            f = QFont(self.add_sample_btn.font())
            f.setPointSize(base)
            self.add_sample_btn.setFont(f)

        self._refresh_auto_edits_width()

        if self._files_grid is not None:
            fm = self.fontMetrics()
            w_label = max(fm.horizontalAdvance("Template:"), fm.horizontalAdvance("Output:"))
            self._files_grid.setColumnMinimumWidth(0, w_label + 12)

        self._sync_files_grid_metrics()
        self._sync_theme_switch_metrics()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_font_scaling()

    # =====================================================================
    # Auto inputs width
    # =====================================================================
    def _refresh_auto_edits_width(self, padding: int = 36):
        if not self._auto_edits:
            return

        max_w = 0
        for e in self._auto_edits:
            fm = e.fontMetrics()
            text = e.text() or e.placeholderText() or ""
            w = fm.horizontalAdvance(text) + padding
            if w > max_w:
                max_w = w

        if max_w <= 0:
            return

        target = max(260, min(max_w, 520))
        for e in self._auto_edits:
            e.setMinimumWidth(target)
            e.setMaximumWidth(target)

    # =====================================================================
    # Basic UI helpers
    # =====================================================================
    def _set_output_empty_style(self):
        self.output_label.setStyleSheet("color: #ff6666;")
        self.output_label.setText("< None >")

    def _set_output_filled_style(self):
        self.output_label.setStyleSheet("color: #33cc33;")

    def _init_placeholders(self):
        # Step3 manual fields placeholders
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

        # Step2 auto fields placeholders
        self.auto_sample_name.setPlaceholderText("Sample Name")
        self.auto_sample_mass.setPlaceholderText("Sample Mass(mg)")
        self.auto_operator.setPlaceholderText("Operator")
        self.auto_instrument.setPlaceholderText("Instrument")
        self.auto_atmosphere.setPlaceholderText("Atmosphere")
        self.auto_crucible.setPlaceholderText("Crucible")
        self.auto_temp_calib.setPlaceholderText("YYYY/MM/DD")
        self.auto_end_date.setPlaceholderText("YYYY/MM/DD")

    # =====================================================================
    # Step 1: Sample list
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
        btn_remove.clicked.connect(lambda _, sid=sample.id: self.sample_ctrl.remove_sample(sid))
        layout.addWidget(btn_remove)

        def on_card_clicked(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.sample_ctrl.on_sample_card_clicked(sample.id)

        card.mousePressEvent = on_card_clicked
        return card

    def on_add_sample_clicked(self):
        dlg = AddSampleDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self.sample_ctrl.add_new_sample(
            sample_name=dlg.sample_name,
            txt_path=dlg.txt_path,
            pdf_path=dlg.pdf_path,
        )

    # =====================================================================
    # Step 3: Manual sample forms
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
                sep.setStyleSheet("QFrame { border: none; border-top: 1px dashed #555555; }")
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

    # =====================================================================
    # Parse sample txt
    # =====================================================================
    def _parse_sample(self, sample: SampleItem):
        if not sample.txt_path:
            return

        try:
            basic = parse_dsc_txt_basic(sample.txt_path)
            sample.basic_info = basic

            try:
                result = self.parse_service.parse_one(sample.txt_path, pdf_path=sample.pdf_path)
                segments = result.segments if result else []
            except Exception as e_seg:
                segments = []
                self._add_file_log(f"[Segments Parsed Failed] {os.path.basename(sample.txt_path)} - {e_seg}")

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

            self.sample_ctrl.load_sample_to_ui(sample)

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

            self._add_file_log(f"[Parsing Successful] {file_info}")

        except Exception as e:
            sample.basic_info = None
            sample.segments = []
            self.parsed_info = None
            self.parsed_segments = None
            self._add_file_log(f"[Parsing Failed] {sample.name} - {e}")

    # =====================================================================
    # File choose
    # =====================================================================
    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Choose Output WORD", "", "Word file (*.docx)")
        if path:
            if not path.lower().endswith(".docx"):
                path += ".docx"
            self.output_path = path
            self.output_label.setText(os.path.basename(path))
            self._set_output_filled_style()
            self._add_file_log(f"[Choosing Successful] Output: {os.path.basename(self.output_path)}")

    def choose_template(self):
        QMessageBox.information(self, "Info", "Change Template function is not implemented yet.")

    # =====================================================================
    # End date
    # =====================================================================
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

        _, latest_raw = max(candidates, key=lambda x: x[0])
        return latest_raw

    # =====================================================================
    # Logs
    # =====================================================================
    def render_log(self):
        pass

    def clear_log(self):
        self.file_logs.clear()
        self.confirm_block = None

    def _add_file_log(self, msg: str):
        self.file_logs.append(msg)
        print(msg)


    def show_report_success_dialog(self, output_path: str):
        """生成成功提示：Open File(橙色) + OK(灰色)，对勾 icon，路径橙色高亮。"""
        if not output_path:
            QMessageBox.information(self, "Success", "Report generated successfully.")
            return

        p = Path(output_path)

        box = QMessageBox(self)
        box.setWindowTitle("Success")
        box.setTextFormat(Qt.TextFormat.RichText)

        pm = self.style().standardPixmap(QStyle.StandardPixmap.SP_DialogApplyButton)
        box.setIconPixmap(pm)

        # 路径橙色高亮
        orange = "rgb(255,119,0)"
        box.setText(
            "Report generated successfully.<br>"
            f'<span style="color:{orange}; font-weight:700;">{p}</span>'
        )

        btn_open_file = box.addButton("Open File", QMessageBox.ButtonRole.AcceptRole)
        btn_ok = box.addButton("OK", QMessageBox.ButtonRole.RejectRole)

        # 按钮样式：Open File=主按钮(橙)，OK=上一页按钮(灰)
        btn_open_file.setObjectName("PrimaryButton")
        btn_ok.setObjectName("StepNavButton")

        # 强制刷新一次样式（QSS 已加载时很关键）
        for b in (btn_open_file, btn_ok):
            b.style().unpolish(b)
            b.style().polish(b)

        box.setDefaultButton(btn_open_file)
        box.exec()

        if box.clickedButton() == btn_open_file:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))