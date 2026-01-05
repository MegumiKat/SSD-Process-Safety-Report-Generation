# src/tools/form_controller.py
from __future__ import annotations

from typing import Optional


class FormController:
    """
    负责：
    1) Step3 手动样品表单：把 UI 输入同步回 sample.manual_fields
    2) 收集 Request/Auto/Manual 字段，构建 mapping（用于 docx 占位符替换）
    3) 构建 Confirm 弹窗的 HTML（汇总展示）
    """

    def __init__(self, view):
        self.view = view

    # -----------------------------
    # Step3: 手动样品字段 UI -> sample.manual_fields
    # -----------------------------
    def sync_manual_fields_from_ui(self) -> None:
        v = self.view
        if not v.samples:
            return

        for sample in v.samples:
            widgets = v.sample_manual_widgets.get(sample.id)
            if not widgets:
                continue
            mf = sample.manual_fields
            mf.sample_id = widgets["sample_id"].text().strip()
            mf.nature = widgets["nature"].text().strip()
            mf.assign_to = widgets["assign_to"].text().strip()

    # -----------------------------
    # mapping：Request 区
    # -----------------------------
    def build_request_mapping(self) -> dict[str, str]:
        v = self.view
        return {
            "{{LSMP_code}}": v.input_lsmp_code.text().strip(),
            "{{Request_id}}": v.input_request_id.text().strip(),
            "{{Customer_information}}": v.input_customer.text().strip(),
            "{{Request_Name}}": v.input_request_name.text().strip(),
            "{{Submission_Date}}": v.input_submission_date.text().strip(),
            "{{Request_Number}}": v.input_request_number.text().strip(),
            "{{Project_Account}}": v.input_project_account.text().strip(),
            "{{Deadline}}": v.input_deadline.text().strip(),
            "{{Test_Date}}": v.input_test_date.text().strip(),
            "{{Receive_Date}}": v.input_receive_date.text().strip(),
            "{{Report_Date}}": v.input_report_date.text().strip(),
            "{{Request_desc}}": v.input_request_desc.toPlainText().strip(),
        }

    # -----------------------------
    # mapping：当前样品（manual）
    # -----------------------------
    def build_current_sample_manual_mapping(self) -> dict[str, str]:
        v = self.view

        # 确保 UI 已同步回 samples
        self.sync_manual_fields_from_ui()

        current = v.sample_ctrl.get_current_sample()
        mf = current.manual_fields if current is not None else None
        return {
            "{{Sample_id}}": mf.sample_id if mf else "",
            "{{Nature}}": mf.nature if mf else "",
            "{{Assign_to}}": mf.assign_to if mf else "",
        }

    # -----------------------------
    # mapping：Auto 区（当前 UI 中的 Auto 值）
    # -----------------------------
    def build_auto_mapping(self) -> dict[str, str]:
        v = self.view
        return {
            "{{Sample_name}}": v.auto_sample_name.text().strip(),
            "{{Sample_mass}}": v.auto_sample_mass.text().strip(),
            "{{Operator}}": v.auto_operator.text().strip(),
            "{{Instrument}}": v.auto_instrument.text().strip(),
            "{{Atmosphere}}": v.auto_atmosphere.text().strip(),
            "{{Crucible}}": v.auto_crucible.text().strip(),
            "{{Temp.Calib}}": v.auto_temp_calib.text().strip(),
            "{{End_Date}}": v._get_latest_end_date_from_samples(),
        }

    # -----------------------------
    # mapping：总组装
    # -----------------------------
    def build_mapping(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        mapping.update(self.build_request_mapping())
        mapping.update(self.build_current_sample_manual_mapping())
        mapping.update(self.build_auto_mapping())
        return mapping

    # -----------------------------
    # Confirm HTML
    # -----------------------------
    def build_confirm_html(self) -> str:
        v = self.view

        # 确保手动字段已同步
        self.sync_manual_fields_from_ui()

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
    # segment 表格标题用 sample name（保持你原逻辑）
    # -----------------------------
    def get_sample_name_for_segments(self) -> str:
        v = self.view

        current_sample = v.sample_ctrl.get_current_sample()
        mf = current_sample.manual_fields if current_sample is not None else None

        return (
            v.auto_sample_name.text().strip()
            or (mf.sample_id if mf else "")
            or (current_sample.name if current_sample else "")
        )