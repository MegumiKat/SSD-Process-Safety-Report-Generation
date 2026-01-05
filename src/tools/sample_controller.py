# src/tools/sample_controller.py
from __future__ import annotations

from typing import Optional


class SampleController:
    def __init__(self, view):
        self.view = view

    # -----------------------------
    # 基础：当前样品/索引
    # -----------------------------
    def get_current_sample(self):
        v = self.view
        if v.current_sample_id is None:
            return None
        for s in v.samples:
            if s.id == v.current_sample_id:
                return s
        return None

    def get_current_sample_index(self) -> int:
        v = self.view
        if v.current_sample_id is None or not v.samples:
            return -1
        for idx, s in enumerate(v.samples):
            if s.id == v.current_sample_id:
                return idx
        return -1

    # -----------------------------
    # Step2：顶部样品 header 刷新
    # -----------------------------
    def update_auto_sample_header(self):
        v = self.view
        total = len(v.samples)
        if total == 0 or v.current_sample_id is None:
            v.label_current_sample.setText("No sample")
            v.btn_prev_sample.setEnabled(False)
            v.btn_next_sample.setEnabled(False)
            return

        idx = self.get_current_sample_index()
        sample = self.get_current_sample()
        if sample is None:
            v.label_current_sample.setText("No sample")
            v.btn_prev_sample.setEnabled(False)
            v.btn_next_sample.setEnabled(False)
            return

        v.label_current_sample.setText(f"{sample.name} ({idx + 1}/{total})")
        v.btn_prev_sample.setEnabled(idx > 0)
        v.btn_next_sample.setEnabled(idx < total - 1)

    # -----------------------------
    # Step2：上一个/下一个样品
    # -----------------------------
    def goto_prev_sample(self):
        v = self.view
        if not v.samples:
            return
        idx = self.get_current_sample_index()
        if idx <= 0:
            return
        new_sample = v.samples[idx - 1]
        self.on_sample_card_clicked(new_sample.id)

    def goto_next_sample(self):
        v = self.view
        if not v.samples:
            return
        idx = self.get_current_sample_index()
        if idx < 0 or idx >= len(v.samples) - 1:
            return
        new_sample = v.samples[idx + 1]
        self.on_sample_card_clicked(new_sample.id)

    # -----------------------------
    # UI <-> Sample 数据同步
    # -----------------------------
    def load_sample_to_ui(self, sample):
        v = self.view
        af = sample.auto_fields
        v.auto_sample_name.setText(af.sample_name)
        v.auto_sample_mass.setText(af.sample_mass)
        v.auto_operator.setText(af.operator)
        v.auto_instrument.setText(af.instrument)
        v.auto_atmosphere.setText(af.atmosphere)
        v.auto_crucible.setText(af.crucible)
        v.auto_temp_calib.setText(af.temp_calib)
        v.auto_end_date.setText(af.end_date)

        v.parsed_info = sample.basic_info
        v.parsed_segments = sample.segments

        # 用 SegmentsController 构建 UI
        v.segments_ctrl.build(v.parsed_segments or [])

        self.update_auto_sample_header()
        v._refresh_auto_edits_width()

    def store_ui_to_sample(self, sample):
        v = self.view

        # 用 SegmentsController 回写
        v.segments_ctrl.apply(v.parsed_segments or [])

        af = sample.auto_fields
        af.sample_name = v.auto_sample_name.text().strip()
        af.sample_mass = v.auto_sample_mass.text().strip()
        af.operator = v.auto_operator.text().strip()
        af.instrument = v.auto_instrument.text().strip()
        af.atmosphere = v.auto_atmosphere.text().strip()
        af.crucible = v.auto_crucible.text().strip()
        af.temp_calib = v.auto_temp_calib.text().strip()
        af.end_date = v.auto_end_date.text().strip()

        sample.segments = v.parsed_segments or []

    # -----------------------------
    # 样品卡片点击：保存当前 -> 切换 -> 加载/解析
    # -----------------------------
    def on_sample_card_clicked(self, sample_id: int):
        v = self.view

        current = self.get_current_sample()
        if current is not None:
            self.store_ui_to_sample(current)

        sample = next((s for s in v.samples if s.id == sample_id), None)
        if not sample:
            return

        v.current_sample_id = sample.id
        v.txt_path = sample.txt_path
        v.pdf_path = sample.pdf_path or ""

        if sample.basic_info is None:
            v.clear_log()
            v._parse_sample(sample)
        else:
            v.parsed_info = sample.basic_info
            v.parsed_segments = sample.segments
            self.load_sample_to_ui(sample)

    # -----------------------------
    # Step2：改样品名联动
    # -----------------------------
    def on_auto_sample_name_changed(self, text: str):
        v = self.view
        sample = self.get_current_sample()
        if sample is None:
            return

        new_name = text.strip()
        sample.name = new_name
        sample.auto_fields.sample_name = new_name

        v._sync_manual_fields_from_ui()
        v._rebuild_sample_list_ui()
        v._rebuild_manual_sample_forms()
        self.update_auto_sample_header()

    # -----------------------------
    # 新增样品
    # -----------------------------
    def add_new_sample(self, sample_name: str, txt_path: str, pdf_path: Optional[str]):
        v = self.view

        sample = v.SampleItem(
            id=v._next_sample_id,
            name=sample_name,
            txt_path=txt_path,
            pdf_path=pdf_path,
        )
        v._next_sample_id += 1

        v.samples.append(sample)
        v.current_sample_id = sample.id

        v._parse_sample(sample)
        v._rebuild_sample_list_ui()
        v._rebuild_manual_sample_forms()
        self.update_auto_sample_header()

    # -----------------------------
    # 删除样品
    # -----------------------------
    def remove_sample(self, sample_id: int):
        v = self.view
        target = next((s for s in v.samples if s.id == sample_id), None)
        if not target:
            return

        ok = v.ask_yes_no("Remove Sample", f"Are you sure to remove sample:\n\n{target.name} ?")
        if not ok:
            return

        v.samples = [s for s in v.samples if s.id != sample_id]

        if v.current_sample_id == sample_id:
            if v.samples:
                new_sample = v.samples[0]
                v.current_sample_id = new_sample.id
                v.txt_path = new_sample.txt_path
                v.pdf_path = new_sample.pdf_path or ""
                v.parsed_info = new_sample.basic_info
                v.parsed_segments = new_sample.segments

                if new_sample.basic_info is None:
                    v.clear_log()
                    v._parse_sample(new_sample)
                else:
                    self.load_sample_to_ui(new_sample)
            else:
                v.current_sample_id = None
                v.txt_path = ""
                v.pdf_path = ""
                v.parsed_info = None
                v.parsed_segments = None

                v.auto_sample_name.clear()
                v.auto_sample_mass.clear()
                v.auto_operator.clear()
                v.auto_instrument.clear()
                v.auto_atmosphere.clear()
                v.auto_crucible.clear()
                v.auto_temp_calib.clear()
                v.auto_end_date.clear()

                v.segments_ctrl.reset()

        v._rebuild_sample_list_ui()
        v._rebuild_manual_sample_forms()
        self.update_auto_sample_header()

        v._add_file_log(f"[Sample Removed] {target.name}")