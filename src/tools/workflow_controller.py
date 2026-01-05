# src/tools/workflow_controller.py
from __future__ import annotations

class WorkflowController:
    def __init__(self, view):
        self.view = view

    def goto_step(self, index: int):
        v = self.view
        if index < 0 or index > 2:
            return
        prev = v.current_step
        if index == prev:
            return

        # 前进：认为之前 step 均完成
        if index > prev:
            for i in range(prev, index):
                v.step_completed[i] = True
        else:
            # 后退：将后面的 step 状态清空
            for i in range(index + 1, len(v.step_completed)):
                v.step_completed[i] = False
                if i == 2:
                    v.confirmed = False

        v.current_step = index
        v.step_stack.setCurrentIndex(index)
        self.update_step_states()
        self.update_nav_buttons()

    def update_step_states(self):
        v = self.view
        for i, btn in enumerate(v.step_buttons):
            if i == v.current_step:
                state = "current"
            elif v.step_completed[i]:
                state = "done"
            else:
                state = "todo"
            btn.setProperty("state", state)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def update_nav_buttons(self):
        v = self.view
        v.btn_prev.setEnabled(v.current_step > 0)
        if v.current_step < 2:
            v.btn_next.setText("Next")
        else:
            v.btn_next.setText("Confirm Data")

    def on_prev_clicked(self):
        self.goto_step(self.view.current_step - 1)

    def on_next_clicked(self):
        v = self.view

        # Step 0 校验：需要至少 1 个样品 + 输出路径
        if v.current_step == 0:
            if not v.output_path:
                v.warn("Info", "Please choose output file.")
                return
            if not v.samples:
                v.warn("Info", "Please add at least one sample.")
                return
            self.goto_step(1)
            return

        # Step 1：直接进入 Step 2（你原逻辑）
        if v.current_step == 1:
            if not v.samples:
                v.warn("Info", "No samples. Please add samples first.")
                return
            self.goto_step(2)
            return

        # Step 2：Confirm Data
        if v.current_step == 2:
            ok = v.report_ctrl.run_confirm_dialog()
            if ok:
                v.step_completed[2] = True
                self.update_step_states()