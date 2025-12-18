# src/ui_main.py
import sys
import os
from typing import Optional, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QFormLayout,
    QMessageBox, QScrollArea, QSizePolicy, QFrame, QDialog, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor, QPixmap, QIcon
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

        # ==== status ====
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
        self._next_sample_id: int = 1  # 用于给 SampleItem 分配唯一 id

        # 手动样品表单：sample_id -> { "sample_id": QLineEdit, "nature": QLineEdit, "assign_to": QLineEdit }
        self.sample_manual_widgets: dict[int, dict[str, QLineEdit]] = {}

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

        # ---------- 顶部：左侧 Logo + 标题，右侧 Template + Output ----------
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 8, 8, 8)

        # ===== 左侧：Logo + 标题 =====
        left_header = QWidget()
        left_header_layout = QHBoxLayout(left_header)
        left_header_layout.setContentsMargins(0, 0, 0, 0)
        left_header_layout.setSpacing(8)

        target_height = 80  # 统一一个高度，避免 LOGO 不存在时报错
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
        # 即使没有图片，也给个固定高度，避免布局塌陷
        logo_label.setMinimumHeight(target_height)
        logo_label.setMaximumHeight(target_height + 10)
        left_header_layout.addWidget(logo_label)

        title_label = QLabel("DSC Reports Generation Tool")
        title_label.setObjectName("AppTitle")
        left_header_layout.addWidget(title_label)
        left_header_layout.addStretch(1)

        # ===== 右侧：Template + Output =====
        right_header = QWidget()
        right_header_layout = QVBoxLayout(right_header)
        right_header_layout.setContentsMargins(0, 0, 0, 0)
        right_header_layout.setSpacing(4)

        # --- 第一行：模板名称（Template 行：Label | ...... | [ value_box ] [ 按钮 ]） ---
        row_tpl = QHBoxLayout()
        lbl_tpl = QLabel("Template:")
        lbl_tpl.setObjectName("HeaderLabel")

        # 显示模板文件名的 label（右对齐）
        self.label_tpl = QLabel(os.path.basename(self.template_path))
        self.label_tpl.setObjectName("HeaderValue")
        self.label_tpl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # 和 Output 一样，用一个小 box 包住 value，控制宽度和边框样式
        self.template_box = QWidget()
        self.template_box.setObjectName("TemplateBox")
        self.template_box.setFixedWidth(260)  # 和 OutputBox 一样宽

        tpl_box_layout = QHBoxLayout(self.template_box)
        tpl_box_layout.setContentsMargins(6, 0, 6, 0)
        tpl_box_layout.setSpacing(4)
        tpl_box_layout.addWidget(self.label_tpl)

        # 预留 Change Template 按钮（功能暂不实现）
        btn_tpl = QPushButton("Change")
        btn_tpl.clicked.connect(self.choose_template)

        row_tpl.addWidget(lbl_tpl)
        # row_tpl.addStretch(1)                  # 中间撑开
        row_tpl.addSpacing(4) 
        row_tpl.addWidget(self.template_box)   # value box 列
        row_tpl.addWidget(btn_tpl)             # 按钮列

        # --- 第二行：输出路径 ---
        row_out = QHBoxLayout()
        lbl_out = QLabel("Output:")
        lbl_out.setObjectName("HeaderLabel")

        self.output_box = QWidget()
        self.output_box.setObjectName("OutputBox")
        # 让显示框本身更小一点
        self.output_box.setFixedWidth(260)

        out_layout = QHBoxLayout(self.output_box)
        out_layout.setContentsMargins(6, 0, 6, 0)
        out_layout.setSpacing(4)

        self.output_label = QLabel("< None >")
        self.output_label.setObjectName("HeaderValue")
        self.output_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._set_output_empty_style()
        out_layout.addWidget(self.output_label)

        btn_out = QPushButton("Choose")
        btn_out.clicked.connect(self.choose_output)

        row_out.addWidget(lbl_out)
        # row_out.addStretch(1)                         # 中间撑开
        row_out.addSpacing(4)
        row_out.addWidget(self.output_box, 0)         # 显示框靠右，宽度固定
        row_out.addWidget(btn_out, 0)                 # 按钮在最右

        right_header_layout.addLayout(row_tpl)
        right_header_layout.addLayout(row_out)

        # ---- 把左右两块放进 header_layout ----
        header_layout.addWidget(left_header, 2)
        header_layout.addStretch(1)
        header_layout.addWidget(right_header, 3)

        root_layout.addWidget(header_widget)
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
        # ---------- 左侧：Samples 大矩形（带滚动 + Add Sample 按钮） ----------
        sample_group = QWidget()
        sample_group.setObjectName("SampleGroup")
        sample_group_layout = QVBoxLayout(sample_group)
        sample_group_layout.setContentsMargins(8, 8, 8, 8)
        sample_group_layout.setSpacing(6)

        lbl_samples = QLabel("Samples")
        lbl_samples.setObjectName("sectionTitle")
        sample_group_layout.addWidget(lbl_samples)

        # 滚动区域
        self.sample_scroll = QScrollArea()
        self.sample_scroll.setWidgetResizable(True)

        self.sample_list_container = QWidget()
        self.sample_list_layout = QVBoxLayout(self.sample_list_container)
        self.sample_list_layout.setContentsMargins(0, 0, 0, 0)
        self.sample_list_layout.setSpacing(8)

        self.sample_scroll.setWidget(self.sample_list_container)
        sample_group_layout.addWidget(self.sample_scroll)

        left_layout.addWidget(sample_group, stretch=1)

        # 构建初始的样品列表 UI（只有一个“Add Sample”按钮）
        self._rebuild_sample_list_ui()

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

        # 每个样品一块，竖着排
        self.sample_manual_layout = QVBoxLayout(sample_container)
        self.sample_manual_layout.setContentsMargins(0, 0, 0, 0)
        self.sample_manual_layout.setSpacing(8)

        scroll_sample.setWidget(sample_container)

        # 初始化一次（此时还没有样品，会显示一个提示）
        self._rebuild_manual_sample_forms()

        # ---------- 把两个滚动块 + 中间竖线加入水平布局 ----------
        manual_hbox.addWidget(scroll_request, 2)
        manual_hbox.addWidget(_create_separator("v"), 0)  # 中间竖直分界线
        manual_hbox.addWidget(scroll_sample, 3)

        # 最终把整个手动输入模块加到左侧主布局
        left_layout.addWidget(manual_block, stretch=1)
        
        # ---------- 右侧：顶部标签栏 Auto / Log ----------
        right_top_bar = QHBoxLayout()
        right_top_bar.setContentsMargins(0, 0, 0, 0)
        right_top_bar.setSpacing(8)

        # 左侧两个「标签按钮」
        self.btn_tab_auto = QPushButton("Auto")
        self.btn_tab_log = QPushButton("Log")
        self.btn_tab_auto.setCheckable(True)
        self.btn_tab_log.setCheckable(True)
        self.btn_tab_auto.setObjectName("RightTabButton")
        self.btn_tab_log.setObjectName("RightTabButton")
        self.btn_tab_auto.setChecked(True)  # 默认 Auto

        self.btn_tab_auto.clicked.connect(lambda: self._switch_right_tab("auto"))
        self.btn_tab_log.clicked.connect(lambda: self._switch_right_tab("log"))

        right_top_bar.addWidget(self.btn_tab_auto)
        right_top_bar.addWidget(self.btn_tab_log)

        right_top_bar.addStretch(1)

        # 右上角「动态 actions」区域：Auto 时显示样品切换，Log 时显示 Clear
        self.right_top_actions = QHBoxLayout()
        self.right_top_actions.setContentsMargins(0, 0, 0, 0)
        self.right_top_actions.setSpacing(4)
        right_top_bar.addLayout(self.right_top_actions)

        right_layout.addLayout(right_top_bar)

        # ---------- 右侧：内容区，用 QStackedWidget 切换 Auto / Log ----------
        self.right_stack = QStackedWidget()
        right_layout.addWidget(self.right_stack, stretch=1)
        # ====== Page 0: Auto（自动识别 + Segments） ======
        auto_page = QWidget()
        auto_page_layout = QVBoxLayout(auto_page)
        auto_page_layout.setContentsMargins(0, 0, 0, 0)
        auto_page_layout.setSpacing(0)

        auto_scroll = QScrollArea()
        auto_scroll.setWidgetResizable(True)
        auto_container = QWidget()
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

        # 在这里加：
        self.auto_sample_name.textChanged.connect(self._on_auto_sample_name_changed)

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

        # Segments 区域
        seg_title = QLabel("Segments:")
        auto_vbox.addWidget(seg_title)

        self.segment_area_layout = QVBoxLayout()
        auto_vbox.addLayout(self.segment_area_layout)

        auto_scroll.setWidget(auto_container)
        auto_page_layout.addWidget(auto_scroll)

        self.right_stack.addWidget(auto_page)  # index 0 = Auto

        # ====== Page 1: Log ======
        log_page = QWidget()
        log_layout = QVBoxLayout(log_page)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.log.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        log_layout.addWidget(self.log)

        self.right_stack.addWidget(log_page)  # index 1 = Log

        # 默认显示 Auto 页
        self.right_stack.setCurrentIndex(0)
        # 初始化右上角 actions（Auto: 样品切换；Log: Clear）
        self._rebuild_right_top_actions()


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

        # 文件日志（已是 html）
        for msg in self.file_logs:
            self.log.append(msg)

        # 确认块：我们现在用 html 生成，用 insertHtml
        if self.confirm_block:
            self.log.append("")  # 空行分隔
            self.log.insertHtml(self.confirm_block)
            self.log.append("")  # 再加一个空行

        # 生成日志（也是 html）
        for block in self.generate_logs:
            self.log.append(block)

        self.log.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self):
        self.file_logs.clear()
        self.confirm_block = None
        self.generate_logs.clear()
        self.log.clear()
        # 可选：清空日志后切回 Auto 页
        self._switch_right_tab("auto")

    def _add_file_log(self, html_msg: str):
        self.file_logs.append(html_msg)
        self.render_log()

    def _set_output_empty_style(self):
        """未选择输出文件时：显示红色 None。"""
        self.output_label.setStyleSheet("color: #ff6666;")  # 红色
        self.output_label.setText("< None >")

    def _set_output_filled_style(self):
        """已选择输出文件时：显示绿色文件名。"""
        self.output_label.setStyleSheet("color: #33cc33;")  # 绿色

        # ===== 样品工具方法 =====
    def _get_current_sample(self) -> Optional[SampleItem]:
        """根据 current_sample_id 找到当前样品对象。"""
        if self.current_sample_id is None:
            return None
        for s in self.samples:
            if s.id == self.current_sample_id:
                return s
        return None

    def _get_current_sample_index(self) -> int:
        """返回当前样品在 self.samples 中的下标，找不到则 -1。"""
        if self.current_sample_id is None or not self.samples:
            return -1
        for idx, s in enumerate(self.samples):
            if s.id == self.current_sample_id:
                return idx
        return -1

    def _switch_right_tab(self, tab: str):
        """
        在 Auto / Log 两个视图之间切换。
        """
        if tab == "auto":
            self.right_stack.setCurrentIndex(0)
            self.btn_tab_auto.setChecked(True)
            self.btn_tab_log.setChecked(False)
        else:
            self.right_stack.setCurrentIndex(1)
            self.btn_tab_auto.setChecked(False)
            self.btn_tab_log.setChecked(True)

        self._rebuild_right_top_actions()

    def _rebuild_right_top_actions(self):
        """
        根据当前右侧 tab（Auto / Log）重建右上角按钮区域：
        - Auto: Sample X/N + Prev / Next
        - Log: Clear 按钮
        """
        # 清空右上角 layout
        while self.right_top_actions.count():
            item = self.right_top_actions.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        current_index = self.right_stack.currentIndex()

        # ===== Auto 页 =====
        if current_index == 0:
            if not self.samples:
                return

            idx = self._get_current_sample_index()
            total = len(self.samples)
            if idx < 0:
                info_label = QLabel("No sample selected")
                self.right_top_actions.addWidget(info_label)
                return

            label = QLabel(f"Sample {idx + 1} / {total}")
            self.right_top_actions.addWidget(label)

            btn_prev = QPushButton("<")
            btn_next = QPushButton(">")

            btn_prev.setFixedWidth(28)
            btn_next.setFixedWidth(28)

            btn_prev.clicked.connect(self._goto_prev_sample)
            btn_next.clicked.connect(self._goto_next_sample)

            if idx <= 0:
                btn_prev.setEnabled(False)
            if idx >= total - 1:
                btn_next.setEnabled(False)

            self.right_top_actions.addWidget(btn_prev)
            self.right_top_actions.addWidget(btn_next)

        # ===== Log 页 =====
        else:
            btn_clear = QPushButton("Clear")
            btn_clear.setFixedWidth(60)
            btn_clear.clicked.connect(self.clear_log)
            self.right_top_actions.addWidget(btn_clear)

    def _goto_prev_sample(self):
        """右上角 < 按钮：切到前一个样品。"""
        if not self.samples:
            return
        idx = self._get_current_sample_index()
        if idx <= 0:
            return
        new_sample = self.samples[idx - 1]
        self.on_sample_card_clicked(new_sample.id)
        self._rebuild_manual_sample_forms()
        self._rebuild_sample_list_ui()
        self._rebuild_right_top_actions()

    def _goto_next_sample(self):
        """右上角 > 按钮：切到后一个样品。"""
        if not self.samples:
            return
        idx = self._get_current_sample_index()
        if idx < 0 or idx >= len(self.samples) - 1:
            return
        new_sample = self.samples[idx + 1]
        self.on_sample_card_clicked(new_sample.id)
        self._rebuild_manual_sample_forms()
        self._rebuild_sample_list_ui()
        self._rebuild_right_top_actions()

    def _load_sample_to_ui(self, sample: SampleItem):
        """
        把某个样品的数据加载到右侧自动识别 UI：
        - auto_fields -> 右侧 QLineEdit
        - segments -> 右侧 Segments 区域
        """
        af = sample.auto_fields

        self.auto_sample_name.setText(af.sample_name)
        self.auto_sample_mass.setText(af.sample_mass)
        self.auto_operator.setText(af.operator)
        self.auto_instrument.setText(af.instrument)
        self.auto_atmosphere.setText(af.atmosphere)
        self.auto_crucible.setText(af.crucible)
        self.auto_temp_calib.setText(af.temp_calib)
        self.auto_end_date.setText(af.end_date)

        # 当前窗口级别的 parsed_info / parsed_segments 指向这个样品
        self.parsed_info = sample.basic_info
        self.parsed_segments = sample.segments

        # 根据 segments 重建右侧 segments 编辑 UI
        self._build_segments_auto_fields(self.parsed_segments or [])

    
    def _store_ui_to_sample(self, sample: SampleItem):
        """
        把右侧自动识别 UI 当前显示的内容，写回到这个样品对象：
        - QLineEdit -> sample.auto_fields
        - Segments：调用 _apply_segment_edits 写回 self.parsed_segments（它本身指向 sample.segments）
        """
        # 先把 segments 的修改写回 self.parsed_segments（里面是 DscSegment 的引用）
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

        # segments 已经通过 _apply_segment_edits 更新到 self.parsed_segments 内部
        # 保证 sample.segments 引用同一个列表即可：
        sample.segments = self.parsed_segments or []

    def _on_auto_sample_name_changed(self, text: str):
        """
        当右侧 Auto 区域的 Sample Name 被手动修改时：
        - 同步到当前 SampleItem.name
        - 同步到当前样品的 auto_fields.sample_name
        - 重新渲染左侧 Samples 卡片和左下 Sample information 标题
        """
        sample = self._get_current_sample()
        if sample is None:
            return

        new_name = text.strip()

        # 更新 Sample 模型里的名字
        sample.name = new_name
        sample.auto_fields.sample_name = new_name

        # 先把左下框里已经填的 Sample Id / Nature / Assign To 保存回各样品
        self._sync_manual_fields_from_ui()

        # 重新画左侧样品列表和左下 sample 信息标题
        self._rebuild_sample_list_ui()
        self._rebuild_manual_sample_forms()

    def _rebuild_sample_list_ui(self):
        """
        重新渲染左侧 Samples 区域的内容：
        - 最上方一个大号的 “Add Sample” 按钮
        - 下面一排排样品卡片
        """
        # 清空现有布局
        while self.sample_list_layout.count():
            item = self.sample_list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # 1) 顶部 Add Sample 按钮
        add_btn = QPushButton("+ Add Sample")
        add_btn.setObjectName("AddSampleButton")
        add_btn.clicked.connect(self.on_add_sample_clicked)
        self.sample_list_layout.addWidget(add_btn)

        # 2) 每个已有样品，生成一张卡片（后面第三步详细填充）
        for sample in self.samples:
            card = self._create_sample_card(sample)
            self.sample_list_layout.addWidget(card)

        # 占位 stretch，保证卡片靠上
        self.sample_list_layout.addStretch(1)

    def _create_sample_card(self, sample: SampleItem) -> QWidget:
        """
        用于 Samples 区域的单个样品小卡片：
        [图标] SampleName   [TXT ✅/❌] [PDF ✅/❌]      [Remove]
        点击卡片本身 = 选中样品；点击 Remove = 删除该样品。
        """
        card = QWidget()
        card.setObjectName("SampleCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # 左侧一个小图标（你后面可以换成真正的 icon）
        icon_label = QLabel("🧪")
        layout.addWidget(icon_label)

        # 中间：样品名
        name_label = QLabel(sample.name)
        name_label.setObjectName("SampleNameLabel")
        layout.addWidget(name_label, 1)

        # TXT 状态
        txt_status = QLabel("TXT: ✓" if os.path.exists(sample.txt_path) else "TXT: ✗")
        layout.addWidget(txt_status)

        # PDF 状态
        if sample.pdf_path:
            pdf_status = QLabel("PDF: ✓" if os.path.exists(sample.pdf_path) else "PDF: ✗")
        else:
            pdf_status = QLabel("PDF: -")
        layout.addWidget(pdf_status)

        # 右侧空一点
        layout.addStretch(1)

        # 删除按钮（只删样品，不触发 card 的 mousePressEvent）
        btn_remove = QPushButton("Remove")
        btn_remove.setObjectName("SampleRemoveButton")
        btn_remove.setFixedHeight(22)
        btn_remove.clicked.connect(lambda _, sid=sample.id: self.on_remove_sample(sid))
        layout.addWidget(btn_remove)

        # 点击卡片其他区域 = 切换当前样品
        card.mousePressEvent = lambda event, sid=sample.id: self.on_sample_card_clicked(sid)

        return card

    def on_sample_card_clicked(self, sample_id: int):
        # 1) 先保存当前样品的 UI 修改
        current = self._get_current_sample()
        if current is not None:
            self._store_ui_to_sample(current)

        # 2) 找到要切换到的样品
        sample = next((s for s in self.samples if s.id == sample_id), None)
        if not sample:
            return

        self.current_sample_id = sample.id
        self.txt_path = sample.txt_path
        self.pdf_path = sample.pdf_path or ""

        # 3) 如果这个样品还没解析过，解析一次；否则直接加载缓存
        if sample.basic_info is None:
            self.clear_log()
            self._parse_sample(sample)
        else:
            # 已经有数据：不再重新解析，直接用缓存数据刷新 UI
            self.parsed_info = sample.basic_info
            self.parsed_segments = sample.segments
            self._load_sample_to_ui(sample)

        # 新增：更新右上角导航
        self._rebuild_right_top_actions()

        # ===== 工具方法 =====
    def _get_latest_end_date_from_samples(self) -> str:
        """
        遍历所有样品的 auto_fields.end_date，取日期最大的那个。
        支持 2025/11/11、2025-11-11、2025.11.11 这几种格式。
        返回用于填模板和展示的字符串（可以是原始格式）。
        """
        if not self.samples:
            # 没有多样品，就用当前界面上的值兜底
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
                # 保存 (真正比较用的 datetime, 原始字符串)
                candidates.append((dt, raw))

        if not candidates:
            # 都解析失败，就仍然用当前 UI 的值
            return self.auto_end_date.text().strip()

        latest_dt, latest_raw = max(candidates, key=lambda x: x[0])
        # 也可以统一格式：latest_dt.strftime("%Y/%m/%d")
        return latest_raw


    def on_remove_sample(self, sample_id: int):
        """
        删除一个样品：
        - 可选：弹出确认
        - 从 self.samples 中移除
        - 如果删的是当前样品，切到另一个样品或清空右侧 UI
        - 重新构建样品列表 UI
        """
        # 1) 找到这个样品对象
        target = next((s for s in self.samples if s.id == sample_id), None)
        if not target:
            return

        # 2) 弹出确认对话框
        reply = QMessageBox.question(
            self,
            "Remove Sample",
            f"Are you sure to remove sample:\n\n{target.name} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 3) 从列表中移除
        self.samples = [s for s in self.samples if s.id != sample_id]

        # 4) 如果删的是当前样品，需要决定新的当前样品 & 刷新右侧 UI
        if self.current_sample_id == sample_id:
            if self.samples:
                # 选择一个新的当前样品（这里简单用第一个）
                new_sample = self.samples[0]
                self.current_sample_id = new_sample.id
                self.txt_path = new_sample.txt_path
                self.pdf_path = new_sample.pdf_path or ""
                self.parsed_info = new_sample.basic_info
                self.parsed_segments = new_sample.segments
                self._load_sample_to_ui(new_sample)
            else:
                # 已经没有任何样品了：清空当前状态和右侧 UI
                self.current_sample_id = None
                self.txt_path = ""
                self.pdf_path = ""
                self.parsed_info = None
                self.parsed_segments = None

                # 清空右侧自动识别文本
                self.auto_sample_name.clear()
                self.auto_sample_mass.clear()
                self.auto_operator.clear()
                self.auto_instrument.clear()
                self.auto_atmosphere.clear()
                self.auto_crucible.clear()
                self.auto_temp_calib.clear()
                self.auto_end_date.clear()
                # 清空 segments UI
                self._build_segments_auto_fields([])

        # 5) 重新绘制左侧样品卡片列表
        self._rebuild_sample_list_ui()
        self._rebuild_manual_sample_forms()

        # 6) 记一条日志（可选）
        msg = (
            f'<span style="color:#ffaa00;">[Sample Removed]</span> '
            f'{target.name}'
        )
        self._add_file_log(msg)
        self._rebuild_right_top_actions()


    def _rebuild_manual_sample_forms(self):
        """
        根据 self.samples 重新生成左下 Sample information 区域：
        每个样品一块：
        [SampleName 作为小标题]
        [Sample Id] [Nature] [Assign To] 三个一行
        """

        # 先把当前 UI 里的内容同步回各 SampleItem.manual_fields
        self._sync_manual_fields_from_ui()

        # 清空旧布局
        while self.sample_manual_layout.count():
            item = self.sample_manual_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.sample_manual_widgets.clear()

        if not self.samples:
            placeholder = QLabel("No samples. Please add samples above.")
            self.sample_manual_layout.addWidget(placeholder)
            self.sample_manual_layout.addStretch(1)
            return

                # 这里开始是循环部分
        for idx, sample in enumerate(self.samples):
            group = QWidget()
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(0, 4, 0, 4)
            group_layout.setSpacing(4)

            # 标题：Sample name
            title = QLabel(sample.name)
            title.setObjectName("SampleManualTitle")
            group_layout.addWidget(title)

            # 三个字段一行：Sample Id / Nature / Assign To
            row = QHBoxLayout()
            row.setSpacing(6)

            edit_sample_id = QLineEdit()
            edit_nature = QLineEdit()
            edit_assign_to = QLineEdit()

            # 初始值来自 SampleItem.manual_fields
            mf = sample.manual_fields
            edit_sample_id.setText(mf.sample_id)
            edit_nature.setText(mf.nature)
            edit_assign_to.setText(mf.assign_to)

            # placeholder
            edit_sample_id.setPlaceholderText("Sample Id")
            edit_nature.setPlaceholderText("Nature")
            edit_assign_to.setPlaceholderText("Assign To")

            # 宽度策略：让字段可以横向拉伸（按我们之前的建议）
            for e in (edit_sample_id, edit_nature, edit_assign_to):
                e.setMinimumWidth(120)
                # 如果你已经改成 Expanding，这里保持一致：
                # e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            row.addWidget(QLabel("Sample Id:"))
            row.addWidget(edit_sample_id)
            row.addWidget(QLabel("Nature:"))
            row.addWidget(edit_nature)
            row.addWidget(QLabel("Assign To:"))
            row.addWidget(edit_assign_to)

            group_layout.addLayout(row)
            self.sample_manual_layout.addWidget(group)

            # 记录到字典，后面同步用
            self.sample_manual_widgets[sample.id] = {
                "sample_id": edit_sample_id,
                "nature": edit_nature,
                "assign_to": edit_assign_to,
            }

            # ===== 在样品之间添加分界线（最后一个不加） =====
            if idx < len(self.samples) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setFrameShadow(QFrame.Shadow.Plain)
                # 用虚线风格，跟你上面 _create_separator 的风格接近
                sep.setStyleSheet(
                    "QFrame { border: none; border-top: 1px dashed #555555; }"
                )
                self.sample_manual_layout.addWidget(sep)

        self.sample_manual_layout.addStretch(1)

    def _sync_manual_fields_from_ui(self):
        """
        把左下 Sample information 区域当前填写的内容，
        写回到各自 SampleItem.manual_fields 中。
        """
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

        # 创建 SampleItem
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
        # 重新画左侧样品列表 UI
        self._rebuild_sample_list_ui()

        # 重新画左下 Sample information 区域
        self._rebuild_manual_sample_forms()
        self._rebuild_right_top_actions()

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
    def _parse_sample(self, sample: SampleItem):
        """
        解析某个样品的 txt，一次性填充：
        - sample.basic_info
        - sample.segments
        - sample.auto_fields（右侧 UI 的初始值）
        然后刷新当前 UI 到这个样品。
        """
        if not sample.txt_path:
            return

        try:
            basic = parse_dsc_txt_basic(sample.txt_path)
            sample.basic_info = basic

            # 2. Segments
            try:
                segments = parse_dsc_segments(sample.txt_path)
            except Exception as e_seg:
                segments = []
                msg_seg = (
                    f'<span style="color:#ff5555;">[Segments Parsed Failed]</span> '
                    f'{os.path.basename(sample.txt_path)} - {e_seg}'
                )
                self._add_file_log(msg_seg)

            sample.segments = segments

            # 3. 用解析结果初始化 auto_fields
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

            # 4. 同步 MainWindow 当前状态
            self.current_sample_id = sample.id
            self.txt_path = sample.txt_path
            self.pdf_path = sample.pdf_path or ""
            self.parsed_info = sample.basic_info
            self.parsed_segments = sample.segments

            # 5. 把数据投射到右侧 UI
            self._load_sample_to_ui(sample)

            self.confirmed = False
            self.confirm_block = None  # 重新确认前清空确认块

            # 日志增加样品名 + 文件情况
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

            msg = (
                f'<span style="color:#33cc33;">[Parsing Successful]</span> '
                f'{file_info}'
            )
            self._add_file_log(msg)

        except Exception as e:
            sample.basic_info = None
            sample.segments = []
            self.parsed_info = None
            self.parsed_segments = None

                        # 日志增加样品名 + 文件情况
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

            msg = (
                f'<span style="color:#ff5555;">[Parsing Failed]</span> '
                f'{file_info}'
            )
            self._add_file_log(msg)
            # QMessageBox.critical(self, "Error", f"[TXT]Parsing Failed\n{e}")

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
            self._set_output_filled_style()

            msg = (
                f'<span style="color:#33cc33;">[Choosing Successful]</span> '
                f'Output: {os.path.basename(self.output_path)}'
            )
            self._add_file_log(msg)

    def choose_template(self):
        """
        预留：修改模板的逻辑暂未实现。
        目前只是弹一个提示，确保按钮可点击，不会报错。
        """
        QMessageBox.information(
            self,
            "Info",
            "Change Template function is not implemented yet."
        )

    # ====== 确认数据：覆盖当前确认块 ======
        # ====== 确认数据：覆盖当前确认块 ======
    def on_confirm(self):
        if not self.txt_path:
            QMessageBox.warning(self, "Tips", "Please choose TXT")
            return

        if self.parsed_info is None:
            QMessageBox.warning(self, "Tips", "[TXT]Haven't parsed successful")
            return

        # 先把当前右侧 UI 的修改写回当前样品（auto + segments）
        current_sample = self._get_current_sample()
        if current_sample is not None:
            self._store_ui_to_sample(current_sample)

        # 同步左下所有样品的 manual 字段到 SampleItem.manual_fields
        self._sync_manual_fields_from_ui()

        # === 开始拼 HTML ===
        label_style = 'style="color:rgb(255,119,0);font-weight:bold;"'  # 字段名淡黄色
        parts: list[str] = []

        parts.append("<div>")

        # ---------- 自动识别字段（所有样品） ----------
        parts.append('<b>===== Automatically identified fields (final value) =====</b><br><br>')

        if not self.samples:
            parts.append(f'<span {label_style}>No samples.</span><br><br>')
        else:
            for idx, sample in enumerate(self.samples, start=1):
                af = sample.auto_fields

                # 每个样品一个小标题
                parts.append(
                    f'<span {label_style}>Sample {idx}: {sample.name}</span><br>'
                )
                parts.append(f'<span {label_style}>Sample Name:</span>&nbsp;&nbsp;{af.sample_name}<br>')
                parts.append(f'<span {label_style}>Crucible:</span>&nbsp;&nbsp;{af.crucible}<br>')
                parts.append(f'<span {label_style}>Temp.Calib.:</span>&nbsp;&nbsp;{af.temp_calib}<br>')
                parts.append(f'<span {label_style}>End Date:</span>&nbsp;&nbsp;{af.end_date}<br>')
                parts.append("<br>")
        

            # ★ 在这里加：所有样品中最晚的 End Date
            final_end_date = self._get_latest_end_date_from_samples()
            parts.append(
                f'<span {label_style}>Final End Date:</span>'
                f'&nbsp;&nbsp;{final_end_date}<br><br>'
            )

        # ---------- 手动输入（Request + 所有样品 manual） ----------
        parts.append('<b>===== Manual input =====</b><br><br>')

        # 先是公共 Request 字段（只出现一次）
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

        # 每个样品的 manual 字段
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

        # 保存为确认块（HTML），重绘 log
        self.confirm_block = "".join(parts)
        self.confirmed = True
        self.render_log()
        QMessageBox.information(self, "Info", "Compiled Successful. Please review and generate when ready")
        # 新增：自动切换到 Log 页，方便查看确认内容
        self._switch_right_tab("log")

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

        # 在生成之前，同步当前 UI -> 当前样品
        sample = self._get_current_sample()
        if sample is not None:
            self._store_ui_to_sample(sample)

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

        # 先同步左下 Sample information 到各样品
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

        # --- 自动部分（绿色基础字段，来自右侧可编辑栏） ---
        mapping["{{Sample_name}}"] = self.auto_sample_name.text().strip()
        mapping["{{Sample_mass}}"] = self.auto_sample_mass.text().strip()
        mapping["{{Operator}}"] = self.auto_operator.text().strip()
        mapping["{{Instrument}}"] = self.auto_instrument.text().strip()
        mapping["{{Atmosphere}}"] = self.auto_atmosphere.text().strip()
        mapping["{{Crucible}}"] = self.auto_crucible.text().strip()
        mapping["{{Temp.Calib}}"] = self.auto_temp_calib.text().strip()
        mapping["{{End_Date}}"] = self._get_latest_end_date_from_samples()

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
        current_sample = self._get_current_sample()
        mf = current_sample.manual_fields if current_sample is not None else None

        sample_name_for_segments = (
            self.auto_sample_name.text().strip()
            or (mf.sample_id if mf else "")
            or (current_sample.name if current_sample else "")
        )

        # === 生成 Discussion 文案（多样品优先） ===
        # 多个样品：对每个样品单独生成一段，然后用空行拼起来
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
            # 没有 samples 列表时，退回到“当前样品”逻辑
            if segments:
                discussion_text = generate_dsc_summary(sample_name_for_segments, segments)

        figure_number = "1"   # 单样品兼容用；多样品时实际编号在 templating 里自动递增
        
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
            block = (
                f'<span style="color:#33cc33;">[Generate Successful]</span> '
                f'{os.path.basename(self.output_path)}<br>========'
            )
            self.generate_logs.append(block)
            self.render_log()
            QMessageBox.information(self, "Successful", "Generate Successful!\nCan open word and check")
            # 新增：生成成功后自动切到 Log 页
            self._switch_right_tab("log")
        except Exception as e:
            block = (
                f'<span style="color:#ff5555;">[Generate Failed]</span> '
                f'{os.path.basename(self.output_path)} - {e}<br>========'
            )
            self.generate_logs.append(block)
            self.render_log()
            QMessageBox.critical(self, "Error", f"Generate Failed\n{e}")
            # 新增：生成成功后自动切到 Log 页
            self._switch_right_tab("log")


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
    win.showMaximized()
    sys.exit(app.exec())