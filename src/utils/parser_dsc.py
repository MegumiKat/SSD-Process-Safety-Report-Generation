# src/utils/parser_dsc.py
import re
from typing import List, Optional

import fitz
from src.models.models import DscBasicInfo, DscSegment, DscPeakPart


# ================== PDF Range 解析 ==================

_RANGE_PATTERN = re.compile(
    r"-?\d+\.?\d*°C/\d+\.?\d*\(K/min\)/-?\d+\.?\d*°C"
)


def parse_segment_ranges_from_pdf(pdf_path: str) -> list[str]:
    """
    从 NETZSCH 导出的 PDF 底部读取所有 Range 行：
        Range
        -20°C/10.0(K/min)/150°C
        150°C/10.0(K/min)/-20°C
        ...
    返回每一段的原始字符串列表。
    """
    if not pdf_path:
        return []

    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        text = page.get_text("text")
        doc.close()
    except Exception:
        return []

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    ranges: list[str] = []

    i = 0
    while i < len(lines):
        if lines[i] == "Range":
            j = i + 1
            # 连续若干行满足 “xx°C/yy(K/min)/zz°C” 视为 Range
            while j < len(lines) and _RANGE_PATTERN.search(lines[j]):
                ranges.append(lines[j])
                j += 1
            i = j
        else:
            i += 1

    return ranges


def _normalize_segment_desc(desc: str) -> str:
    """
    把 "-20°C/10.0(K/min)/150°C" 转成 "-20°C ➜ 150°C@10K/min" 这种展示用文本。
    TXT header 和 PDF Range 都复用这个逻辑。
    """
    m = re.match(
        r"\s*(.+?°C)\s*/\s*([0-9.]+)\(K/min\)\s*/\s*(.+?°C)\s*",
        desc
    )
    if not m:
        return desc.strip()
    start, rate, end = m.groups()
    rate_txt = f"{float(rate):g}"   # 10.0 -> "10"
    return f"{start} ➜ {end}@{rate_txt}K/min"


def _merge_segments_with_pdf_ranges(
    segments_from_txt: List[DscSegment],
    pdf_ranges: List[str],
) -> List[DscSegment]:
    """
    已有：TXT 解析出来的 segments_from_txt（主数据）。
    额外：PDF 读出来的每段 Range 字符串 pdf_ranges。

    逻辑：
    - TXT 里已有的段，原样保留（不改 onset / peak / area 等数值）
    - 如果 pdf_ranges 比 TXT 段数多：
        为每一个“多出来”的 Range 新建一个 DscSegment：
          * raw_desc / desc_display 来自 Range
          * parts 放一个占位 DscPeakPart，所有数值字段都是 None
    - 最后把所有 segment.total 统一成 len(pdf_ranges)，方便后续使用。
    """
    if not pdf_ranges:
        return segments_from_txt

    segments = list(segments_from_txt)
    n_txt = len(segments)
    n_pdf = len(pdf_ranges)

    if n_pdf <= n_txt:
        # PDF 段数没有更多，只是补充信息的话，这里先不覆盖 TXT 的 header
        return segments

    final_total = n_pdf

    # 为“多出来”的 Range 新建 dummy segment
    for idx in range(n_txt, n_pdf):
        rng = pdf_ranges[idx]
        desc_display = _normalize_segment_desc(rng)

        seg = DscSegment(
            index=idx + 1,
            total=final_total,
            raw_desc=rng,
            desc_display=desc_display,
        )
        # 占位 part：所有温度和 ΔH 字段为 None，后续填表就会是空
        dummy_part = DscPeakPart()
        seg.parts.append(dummy_part)

        segments.append(seg)

    # 可选：统一更新一下前面已有段的 total
    for seg in segments:
        seg.total = final_total

    return segments


# ================== TXT 基础信息 ==================

def parse_dsc_txt_basic(txt_path: str) -> DscBasicInfo:
    """
    解析 DSC 仪器导出的 txt 文件，提取基础信息：
    - Sample identity
    - Sample Mass
    - Operator
    - Instrument
    - Atmosphere
    - Crucible（只取逗号前一段）
    - Temp.Calib.（YYYY/MM/DD）
    - End Date/Time（YYYY/MM/DD）
    """
    # 优先按 UTF-16 读取
    try:
        with open(txt_path, "r", encoding="utf-16", errors="ignore") as f:
            text = f.read()
    except UnicodeError:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

    info = DscBasicInfo()

    # Sample name
    m = re.search(r"Sample name:\s*(.+)", text)
    if m:
        info.sample_name = m.group(1).strip()

    # Sample Mass: 8.496 mg
    m = re.search(r"Sample Mass:\s*([\d\.]+)\s*mg", text)
    if m:
        try:
            info.sample_mass_mg = float(m.group(1))
        except ValueError:
            info.sample_mass_mg = None

    # Operator:
    m = re.search(r"Operator:\s*(.+)", text)
    if m:
        info.operator = m.group(1).strip()

    # Instrument:
    m = re.search(r"Instrument:\s*(.+)", text)
    if m:
        info.instrument = m.group(1).strip()

    # Atmosphere:
    m = re.search(r"Atmosphere:\s*(.+)", text)
    if m:
        info.atmosphere = m.group(1).strip()

    # Crucible: 只保留逗号前一段
    m = re.search(r"Crucible:\s*(.+)", text)
    if m:
        full = m.group(1).strip()
        if "," in full:
            head = full.split(",", 1)[0].strip()
            info.crucible = head
        else:
            info.crucible = full

    # Temp.Calib.: 09-04-2025 14:25  ->  2025/04/09
    m = re.search(r"Temp\.Calib\.\s*:\s*([0-9]{2})-([0-9]{2})-([0-9]{4})", text)
    if m:
        day, month, year = m.groups()
        info.temp_calib = f"{year}/{int(month):02d}/{int(day):02d}"

    # End Date/Time: 2025/5/6 10:57:06 (UTC+8)
    m = re.search(
        r"End Date/Time:\s*([0-9]{4})/([0-9]{1,2})/([0-9]{1,2})",
        text,
    )
    if m:
        year, month, day = m.groups()
        info.end_date = f"{year}/{int(month):02d}/{int(day):02d}"

    return info


# ================== TXT Segments + PDF Range 补齐 ==================

def parse_dsc_segments(txt_path: str, pdf_path: Optional[str] = None) -> List[DscSegment]:
    """
    解析 txt 中的 Segments 部分：
    - 统计有几段；
    - 每段整理成  -20°C ➜150°C@10K/min  格式；
    - 每段下面的小 part：配对 Value(DSC) 温度 + Onset / Peak / Area；
    再根据 pdf_path（如果提供）去 PDF 底部读取 Range：
    - 若 PDF 段数更多，则为多出来的段生成“空值” segment（只有 desc，有一个空的 part）。
    """
    # 读取全文
    try:
        with open(txt_path, "r", encoding="utf-16", errors="ignore") as f:
            text = f.read()
    except UnicodeError:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

    segments: List[DscSegment] = []

    # ---- 1) 找每个 Segment 的头 ----
    # 例如：Segments:             1/3   :   -20°C/10.0(K/min)/150°C
    seg_header_re = re.compile(r"Segments:\s*(\d+)\s*/\s*(\d+)\s*:\s*(.+)")
    header_matches = list(seg_header_re.finditer(text))
    if not header_matches:
        # 如果 TXT 里完全没有 Segments，就直接看 PDF 有没有 Range
        segments = []
    else:
        # Complex Peak (DSC) block：包含 Area / Peak / Onset
        peak_block_re = re.compile(
            r"Complex Peak \(DSC\).*?\n"
            r"Area\s+([-\d\.]+)\s+J/g.*?\n"
            r"Peak:\s+([-\d\.]+)\s+°C.*?\n"
            r"Onset:\s+([-\d\.]+)\s+°C",
            re.S,
        )

        # Value (DSC) 行：Value 数值 + 温度
        value_re = re.compile(
            r"Value \(DSC\)\s+([-\d\.]+)\s+mW/mg\s+([-\d\.]+)\s+°C"
        )

        # ---- 2) 遍历每一个 Segment ----
        for i, m in enumerate(header_matches):
            seg_idx = int(m.group(1))
            seg_total = int(m.group(2))
            raw_desc = m.group(3).strip()
            desc_display = _normalize_segment_desc(raw_desc)

            # 当前 segment 的文本范围：从当前 header 结束到下一个 header 开始
            start_pos = m.end()
            end_pos = header_matches[i + 1].start() if i + 1 < len(header_matches) else len(text)
            seg_text = text[start_pos:end_pos]

            seg = DscSegment(
                index=seg_idx,
                total=seg_total,
                raw_desc=raw_desc,
                desc_display=desc_display,
            )

            # ---- 2.1 收集 Complex Peak blocks 和 Value 行 ----
            peak_matches = list(peak_block_re.finditer(seg_text))
            value_matches = list(value_re.finditer(seg_text))

            # ---- 2.2 按顺序“配对”生成小 part ----
            n = max(len(peak_matches), len(value_matches))
            for idx in range(n):
                part = DscPeakPart()

                # 有对应的 Complex Peak -> 填 Onset / Peak / Area / Comment
                if idx < len(peak_matches):
                    pm = peak_matches[idx]
                    area_raw = float(pm.group(1))
                    peak_c = float(pm.group(2))
                    onset_c = float(pm.group(3))

                    area_report = -area_raw  # 取相反数

                    if area_report > 0:
                        comment = "Endothermic"
                    elif area_report < 0:
                        comment = "Exothermic"
                    else:
                        comment = ""

                    part.onset_c = onset_c
                    part.peak_c = peak_c
                    part.area_raw = area_raw
                    part.area_report = area_report
                    part.comment = comment

                # 有对应的 Value 行 -> 只要温度，不要 mW/mg 数值
                if idx < len(value_matches):
                    vm = value_matches[idx]
                    temp_c = float(vm.group(2))
                    part.value_temp_c = temp_c

                seg.parts.append(part)

            segments.append(seg)

    # ---- 3) 如果提供了 PDF，尝试用 Range 补齐缺失的段 ----
    if pdf_path:
        pdf_ranges = parse_segment_ranges_from_pdf(pdf_path)
        if pdf_ranges:
            segments = _merge_segments_with_pdf_ranges(segments, pdf_ranges)

    return segments