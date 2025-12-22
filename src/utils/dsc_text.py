# src/utils/dsc_text.py

import re
from typing import List
from src.models.models import DscSegment


def _ordinal_en(n: int) -> str:
    mapping = {1: "First", 2: "Second", 3: "Third"}
    return mapping.get(n, f"{n}th")


def _classify_segment(seg: DscSegment) -> str:
    """根据 desc_display 判断是加热还是冷却。"""
    m = re.search(r"([\-0-9\.]+)\s*°C.*?([\-0-9\.]+)\s*°C", seg.desc_display)
    if not m:
        return "unknown"
    start = float(m.group(1))
    end = float(m.group(2))
    if start < end:
        return "heating"
    elif start > end:
        return "cooling"
    else:
        return "unknown"


def generate_dsc_summary(sample_name: str, segments: List[DscSegment]) -> str:
    """
    根据解析出的 segments 生成 DSC 英文描述文案。

    - 开头 heating 次数 = 所有被判定为 heating 的 segment 数（包括没有有效峰值的 cycle）；
    - 后面只对“有事件”的 segment 写 cycle 标题 + Event 描述；
      没有事件的 heating cycle 被计入总数，但不展开具体描述。
    """
    if not segments:
        return ""

    # ===== 1. 开头统计 heating 个数：所有 heating 段都算 =====
    heating_count = sum(1 for seg in segments if _classify_segment(seg) == "heating")

    lines: list[str] = []

    # ===== 2. 开头句 =====
    sample_prefix = "For this sample" if not sample_name else f"For sample {sample_name}"
    if heating_count <= 0:
        opening = (
            f"{sample_prefix}, we conducted a Differential Scanning Calorimetry (DSC) test."
        )
    elif heating_count == 1:
        opening = (
            f"{sample_prefix}, we conducted a Differential Scanning Calorimetry (DSC) test "
            f"with one heating cycle:"
        )
    else:
        opening = (
            f"{sample_prefix}, we conducted a Differential Scanning Calorimetry (DSC) test "
            f"with {heating_count} heating cycles:"
        )
    lines.append(opening)

    heating_idx = 0
    cooling_idx = 0

    # ===== 3. 各个 cycle 详细描述 =====
    for seg in segments:
        # 先收集当前 cycle 下的“有效事件”
        events = [
            p for p in seg.parts
            if p.value_temp_c is not None
            and p.peak_c is not None
            and p.area_report is not None
        ]

        # 如果这个 segment 完全没有事件（比如只是 PDF Range 补出的 dummy cycle），
        # 直接跳过，不写标题和 Event。
        if not events:
            continue

        seg_type = _classify_segment(seg)

        # cycle 标题
        if seg_type == "heating":
            heating_idx += 1
            header = f"{_ordinal_en(heating_idx)} heating cycle:"
        elif seg_type == "cooling":
            cooling_idx += 1
            header = (
                "Cooling cycle:" if cooling_idx == 1
                else f"{_ordinal_en(cooling_idx)} cooling cycle:"
            )
        else:
            header = f"Segment {seg.index}:"

        lines.append(header)

        # 只有一个事件：用 "Event: ..."
        if len(events) == 1:
            p = events[0]
            start_t = f"{p.value_temp_c:.1f}"
            peak_t = f"{p.peak_c:.1f}"
            dH = f"{abs(p.area_report):.2f}"
            comment = (p.comment or "Endothermic").lower()

            line = (
                f"Event: Starts at {start_t}°C with a peak at {peak_t}°C, "
                f"showing an {comment} reaction with an enthalpy change (ΔH) of {dH} J/g."
            )
            lines.append(line)

        # 多个事件：Event 1 / Event 2 / ...
        else:
            for idx, p in enumerate(events, start=1):
                start_t = f"{p.value_temp_c:.1f}"
                peak_t = f"{p.peak_c:.1f}"
                dH = f"{abs(p.area_report):.2f}"
                comment = (p.comment or "Endothermic").lower()

                line = (
                    f"Event {idx}: Starts at {start_t}°C with a peak at {peak_t}°C, "
                    f"showing an {comment} reaction with an enthalpy change (ΔH) of {dH} J/g."
                )
                lines.append(line)

    return "\n".join(lines)