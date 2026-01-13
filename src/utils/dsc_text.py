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


def _has_any_event_data(p) -> bool:
    """
    只要该 event 行不是“全 - / 全空”，就认为有数据。
    你目前用于文案的关键字段是这三个：
    - value_temp_c（start）
    - peak_c（peak）
    - area_report（ΔH）
    """
    return any(
        x is not None
        for x in (p.value_temp_c, p.peak_c, p.area_report)
    )


def _format_event_line(p, idx: int | None = None) -> str:
    """
    对缺失字段做 graceful fallback，不再要求三项齐全。
    """
    prefix = "Event:" if idx is None else f"Event {idx}:"

    # start / peak / dH 允许缺失
    if p.value_temp_c is not None:
        start_part = f"Starts at {p.value_temp_c:.1f}°C"
    else:
        start_part = "Starts at - °C"

    if p.peak_c is not None:
        peak_part = f"with a peak at {p.peak_c:.1f}°C"
    else:
        peak_part = "with a peak at - °C"

    # comment（如果没有 comment，就别强行 endothermic；更中性一点）
    comment_raw = (p.comment or "").strip().lower()
    if comment_raw:
        reaction_part = f"showing an {comment_raw} reaction"
    else:
        reaction_part = "showing an - reaction"

    if p.area_report is not None:
        dH = f"{abs(p.area_report):.2f}"
        dh_part = f"with an enthalpy change (ΔH) of {dH} J/g"
    else:
        dh_part = "with enthalpy change (ΔH) of - J/g"

    return f"{prefix} {start_part} {peak_part}, {reaction_part}, {dh_part}."


def generate_dsc_summary(sample_name: str, segments: List[DscSegment]) -> str:
    """
    - heating_count 仍按所有 heating segment 统计（保持你原设计）
    - 只要 event 行不是全空，就生成 event 描述
    - 只有当一个 segment 内完全没有任何可用 event 数据，才跳过该 segment
    """
    if not segments:
        return ""

    heating_count = sum(1 for seg in segments if _classify_segment(seg) == "heating")

    lines: list[str] = []

    sample_prefix = "For this sample" if not sample_name else f"For sample {sample_name}"
    if heating_count <= 0:
        opening = f"{sample_prefix}, we conducted a Differential Scanning Calorimetry (DSC) test."
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

    for seg in segments:
        # 更宽松：只要该行有任何一个字段，就算“有数据”
        events = [p for p in seg.parts if _has_any_event_data(p)]

        #  segment 内完全无任何数据，才跳过
        if not events:
            continue

        seg_type = _classify_segment(seg)

        if seg_type == "heating":
            heating_idx += 1
            header = f"{_ordinal_en(heating_idx)} heating cycle:"
        elif seg_type == "cooling":
            cooling_idx += 1
            header = "Cooling cycle:" if cooling_idx == 1 else f"{_ordinal_en(cooling_idx)} cooling cycle:"
        else:
            header = f"Segment {seg.index}:"

        lines.append(header)

        # 事件输出：允许字段缺失
        if len(events) == 1:
            lines.append(_format_event_line(events[0], idx=None))
        else:
            for i, p in enumerate(events, start=1):
                lines.append(_format_event_line(p, idx=i))

    return "\n".join(lines)