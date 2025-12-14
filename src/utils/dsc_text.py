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


# src/utils/dsc_text.py

from typing import List
from src.models.models import DscSegment


def generate_dsc_summary(sample_name: str, segments: List[DscSegment]) -> str:
    """
    根据解析出的 segments 生成 DSC 英文描述文案。

    规则：
    - 开头统计 heating 的个数，只写 heating，不写 cooling；
    - 句式类似：
      For sample CF130G, we conducted a Differential Scanning Calorimetry (DSC) test with two heating cycles:
    - 每个 cycle：
      * 若只有一个事件，用 "Event: Starts at ..."（无序号）；
      * 若有多个事件，用 "Event 1: ..." / "Event 2: ..."；
    - heating / cooling 的句子格式完全一致：
      Event... Starts at xx.x°C with a peak at yy.y°C, showing an endothermic/exothermic reaction
      with an enthalpy change (ΔH) of xx.xx J/g.
    """
    if not segments:
        return ""

    # 统计 heating 个数
    types = [_classify_segment(seg) for seg in segments]
    heating_count = sum(1 for t in types if t == "heating")

    lines: list[str] = []

    # ===== 开头句 =====
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

    # ===== 各个 cycle =====
    for seg in segments:
        seg_type = _classify_segment(seg)

        # cycle 标题（先不加粗，加粗放到 templating 里做）
        if seg_type == "heating":
            heating_idx += 1
            header = f"{_ordinal_en(heating_idx)} heating cycle:"
        elif seg_type == "cooling":
            cooling_idx += 1
            header = "Cooling cycle:" if cooling_idx == 1 else f"{_ordinal_en(cooling_idx)} cooling cycle:"
        else:
            header = f"Segment {seg.index}:"

        lines.append(header)

        # 收集当前 cycle 下的有效事件
        events = [
            p for p in seg.parts
            if p.value_temp_c is not None
            and p.peak_c is not None
            and p.area_report is not None
        ]
        if not events:
            continue

        # 只有一个事件：用 "Event: ..."
        if len(events) == 1:
            p = events[0]
            start_t = f"{p.value_temp_c:.1f}"
            peak_t = f"{p.peak_c:.1f}"
            # area_report 已经是绝对值了，为稳妥再 abs 一下
            dH = f"{abs(p.area_report):.2f}"
            comment = (p.comment or "Endothermic").lower()  # endothermic / exothermic

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