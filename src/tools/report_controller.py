# src/tools/report_controller.py
from __future__ import annotations

import os
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton


class ReportController:
    """
    只负责：
    - Confirm 弹窗流程
    - 调用 ReportService.generate_report
    数据从 FormController 统一收集
    """

    def __init__(self, view):
        self.view = view

    # -----------------------------
    # Confirm 流程
    # -----------------------------
    def run_confirm_dialog(self) -> bool:
        v = self.view

        # 基础校验
        if not v.txt_path:
            QMessageBox.warning(v, "Tips", "Please choose TXT")
            return False
        if v.parsed_info is None:
            QMessageBox.warning(v, "Tips", "[TXT]Haven't parsed successful")
            return False

        # 保存当前样品 UI -> sample
        current_sample = v.sample_ctrl.get_current_sample()
        if current_sample is not None:
            v.sample_ctrl.store_ui_to_sample(current_sample)

        # 同步手动字段
        v.form_ctrl.sync_manual_fields_from_ui()

        # Confirm HTML
        confirm_html = v.form_ctrl.build_confirm_html()
        v.confirm_block = confirm_html
        v.confirmed = True

        dlg = QDialog(v)
        dlg.setWindowTitle("Confirm all data")
        dlg.resize(900, 600)

        vbox = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setHtml(confirm_html or "")
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
            self.generate_report()

        btn_ok.clicked.connect(_do_generate)

        dlg.exec()
        return v.confirmed

    # -----------------------------
    # 生成报告
    # -----------------------------
    def generate_report(self):
        v = self.view

        if not v.txt_path:
            QMessageBox.warning(v, "Info", "Choosing TXT")
            return
        if not v.output_path:
            QMessageBox.warning(v, "Info", "Choosing Output")
            return
        if not os.path.exists(v.template_path):
            QMessageBox.warning(v, "Info", f"Template don't exist\n{v.template_path}")
            return
        if v.parsed_info is None:
            QMessageBox.warning(v, "Info", "[TXT]Parsed Failed")
            return
        if not v.confirmed:
            QMessageBox.warning(v, "Info", "Please confirm and generate")
            return

        # 当前 UI -> sample（确保最新）
        current_sample = v.sample_ctrl.get_current_sample()
        if current_sample is not None:
            v.sample_ctrl.store_ui_to_sample(current_sample)

        # segments edits -> parsed_segments
        v.segments_ctrl.apply(v.parsed_segments or [])
        segments = v.parsed_segments or []
        if not segments:
            v._add_file_log("[Segments 为空] 将不生成 segments 表格。")

        # 同步手动字段
        v.form_ctrl.sync_manual_fields_from_ui()

        # mapping 从 FormController 统一构建
        mapping = v.form_ctrl.build_mapping()

        sample_name_for_segments = v.form_ctrl.get_sample_name_for_segments()
        discussion_text = v.report_service.build_discussion(v.samples)
        figure_number = "1"

        try:
            v.report_service.generate_report(
                v.template_path,
                v.output_path,
                mapping,
                segments=segments,
                discussion_text=discussion_text,
                pdf_path=v.pdf_path if v.pdf_path else None,
                sample_name_for_segments=sample_name_for_segments,
                figure_number=figure_number,
                samples=v.samples,
            )
            v._add_file_log(f"[Generate Successful] {os.path.basename(v.output_path)}")
            QMessageBox.information(v, "Successful", "Generate Successful!\nCan open word and check")
        except Exception as e:
            v._add_file_log(f"[Generate Failed] {os.path.basename(v.output_path)} - {e}")
            QMessageBox.critical(v, "Error", f"Generate Failed\n{e}")