# src/tools/report_controller.py
from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton

class ReportController:
    """
    把 Confirm 汇总内容 + mapping 构建 + generate report 流程从 ui_main.py 抽离出来。
    view 里仍保留输入控件与状态；controller 负责组织数据与调用 ReportService。
    """

    def __init__(self, view):
        self.view = view

    # -----------------------------
    # Confirm 流程：弹窗 -> 点击 Generate report -> 生成报告
    # -----------------------------
    def run_confirm_dialog(self) -> bool:
        """
        返回：用户是否完成确认（点击了 Generate report）
        注意：这里会在用户点击 Generate report 时直接调用 generate_report()。
        """
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

        # 同步手动表单 -> sample.manual_fields
        v._sync_manual_fields_from_ui()

        # 生成确认 HTML
        confirm_html = self.build_confirm_html()
        v.confirm_block = confirm_html
        v.confirmed = True

        # 弹窗
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

        # 如果用户点了 cancel，confirmed 仍然为 True（你原逻辑也是这样）
        # 这里更稳妥：只有生成成功才算完成确认步骤
        # 但为了不改变你已有行为，我们只返回 v.confirmed
        return v.confirmed

    # -----------------------------
    # Confirm HTML
    # -----------------------------
    def build_confirm_html(self) -> str:
        v = self.view
        label_style = 'style="color:rgb(255,119,0);font-weight:bold;"'
        parts: list[str] = []

        parts.append("<div>")
        parts.append('<b>===== Automatically identified fields (final value) =====</b><br><br>')

        if not v.samples:
            parts.append(f'<span {label_style}>No samples.</span><br><br>')
        else:
            for idx, sample in enumerate(v.samples, start=1):
                af = sample.auto_fields
                parts.append(f'<span {label_style}>Sample {idx}: {sample.name}</span><br>')
                parts.append(f'<span {label_style}>Sample Name:</span>&nbsp;&nbsp;{af.sample_name}<br>')
                parts.append(f'<span {label_style}>Crucible:</span>&nbsp;&nbsp;{af.crucible}<br>')
                parts.append(f'<span {label_style}>Temp.Calib.:</span>&nbsp;&nbsp;{af.temp_calib}<br>')
                parts.append(f'<span {label_style}>End Date:</span>&nbsp;&nbsp;{af.end_date}<br>')
                parts.append("<br>")

            final_end_date = v._get_latest_end_date_from_samples()
            parts.append(
                f'<span {label_style}>Final End Date:</span>'
                f'&nbsp;&nbsp;{final_end_date}<br><br>'
            )

        parts.append('<b>===== Manual input =====</b><br><br>')

        parts.append(f'<span {label_style}>Test Code:</span>&nbsp;&nbsp;{v.input_lsmp_code.text().strip()}<br>')
        parts.append(f'<span {label_style}>Request Id:</span>&nbsp;&nbsp;{v.input_request_id.text().strip()}<br>')
        parts.append(f'<span {label_style}>Customer Information:</span>&nbsp;&nbsp;{v.input_customer.text().strip()}<br>')
        parts.append(f'<span {label_style}>Request Name:</span>&nbsp;&nbsp;{v.input_request_name.text().strip()}<br>')
        parts.append(f'<span {label_style}>Submission Date:</span>&nbsp;&nbsp;{v.input_submission_date.text().strip()}<br>')
        parts.append(f'<span {label_style}>Request Number:</span>&nbsp;&nbsp;{v.input_request_number.text().strip()}<br>')
        parts.append(f'<span {label_style}>Project Account:</span>&nbsp;&nbsp;{v.input_project_account.text().strip()}<br>')
        parts.append(f'<span {label_style}>Deadline:</span>&nbsp;&nbsp;{v.input_deadline.text().strip()}<br>')
        parts.append(f'<span {label_style}>Test Date:</span>&nbsp;&nbsp;{v.input_test_date.text().strip()}<br>')
        parts.append(f'<span {label_style}>Receive Date:</span>&nbsp;&nbsp;{v.input_receive_date.text().strip()}<br>')
        parts.append(f'<span {label_style}>Report Date:</span>&nbsp;&nbsp;{v.input_report_date.text().strip()}<br>')
        parts.append(f'<span {label_style}>Request Description:</span>&nbsp;&nbsp;{v.input_request_desc.toPlainText().strip()}<br>')
        parts.append("<br>")

        if v.samples:
            for idx, sample in enumerate(v.samples, start=1):
                mf = sample.manual_fields
                parts.append(f'<span {label_style}>Sample {idx}: {sample.name}</span><br>')
                parts.append(f'<span {label_style}>Sample Id:</span>&nbsp;&nbsp;{mf.sample_id}<br>')
                parts.append(f'<span {label_style}>Nature:</span>&nbsp;&nbsp;{mf.nature}<br>')
                parts.append(f'<span {label_style}>Assign To:</span>&nbsp;&nbsp;{mf.assign_to}<br>')
                parts.append("<br>")

        parts.append("</div>")
        return "".join(parts)

    # -----------------------------
    # mapping 构建
    # -----------------------------
    def build_mapping(self) -> dict[str, str]:
        v = self.view

        mapping: dict[str, str] = {}
        mapping["{{LSMP_code}}"] = v.input_lsmp_code.text().strip()
        mapping["{{Request_id}}"] = v.input_request_id.text().strip()
        mapping["{{Customer_information}}"] = v.input_customer.text().strip()
        mapping["{{Request_Name}}"] = v.input_request_name.text().strip()
        mapping["{{Submission_Date}}"] = v.input_submission_date.text().strip()
        mapping["{{Request_Number}}"] = v.input_request_number.text().strip()
        mapping["{{Project_Account}}"] = v.input_project_account.text().strip()
        mapping["{{Deadline}}"] = v.input_deadline.text().strip()

        # 手动样品字段：你原逻辑使用“当前样品”的 manual_fields
        v._sync_manual_fields_from_ui()
        current_sample = v.sample_ctrl.get_current_sample()
        mf = current_sample.manual_fields if current_sample is not None else None

        mapping["{{Sample_id}}"] = mf.sample_id if mf else ""
        mapping["{{Nature}}"] = mf.nature if mf else ""
        mapping["{{Assign_to}}"] = mf.assign_to if mf else ""

        mapping["{{Test_Date}}"] = v.input_test_date.text().strip()
        mapping["{{Receive_Date}}"] = v.input_receive_date.text().strip()
        mapping["{{Report_Date}}"] = v.input_report_date.text().strip()
        mapping["{{Request_desc}}"] = v.input_request_desc.toPlainText().strip()

        mapping["{{Sample_name}}"] = v.auto_sample_name.text().strip()
        mapping["{{Sample_mass}}"] = v.auto_sample_mass.text().strip()
        mapping["{{Operator}}"] = v.auto_operator.text().strip()
        mapping["{{Instrument}}"] = v.auto_instrument.text().strip()
        mapping["{{Atmosphere}}"] = v.auto_atmosphere.text().strip()
        mapping["{{Crucible}}"] = v.auto_crucible.text().strip()
        mapping["{{Temp.Calib}}"] = v.auto_temp_calib.text().strip()
        mapping["{{End_Date}}"] = v._get_latest_end_date_from_samples()

        return mapping

    # -----------------------------
    # 生成报告（核心业务）
    # -----------------------------
    def generate_report(self):
        v = self.view

        # 基础校验
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

        # 再存一次当前 UI -> sample（确保最新）
        current_sample = v.sample_ctrl.get_current_sample()
        if current_sample is not None:
            v.sample_ctrl.store_ui_to_sample(current_sample)

        # 确保 Segments 的编辑写回 parsed_segments
        v.segments_ctrl.apply(v.parsed_segments or [])

        segments = v.parsed_segments or []
        if not segments:
            v._add_file_log("[Segments 为空] 将不生成 segments 表格。")

        mapping = self.build_mapping()

        # segment 表格标题用的 sample_name（保持你原逻辑）
        current_sample = v.sample_ctrl.get_current_sample()
        mf = current_sample.manual_fields if current_sample is not None else None
        sample_name_for_segments = (
            v.auto_sample_name.text().strip()
            or (mf.sample_id if mf else "")
            or (current_sample.name if current_sample else "")
        )

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
            # ✅ 成功提示：带“打开文件/文件夹”按钮
            if hasattr(v, "show_report_success_dialog"):
                v.show_report_success_dialog(v.output_path)
            else:
                QMessageBox.information(v, "Successful", "Generate Successful!\nCan open word and check")
        except Exception as e:
            v._add_file_log(f"[Generate Failed] {os.path.basename(v.output_path)} - {e}")
            QMessageBox.critical(v, "Error", f"Generate Failed\n{e}")