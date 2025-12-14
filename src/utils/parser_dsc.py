# src/parser_dsc.py
import re
from typing import List
from src.models.models import DscBasicInfo, DscSegment, DscPeakPart


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

    # Sample identity / Sample name
    m = re.search(r"Sample identity:\s*(.+)", text)
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

    # Crucible: 只保留逗号前一段，并补回逗号
    # 例如 "Concavus Al, pierced lid" -> "Concavus Al,"
    m = re.search(r"Crucible:\s*(.+)", text)
    if m:
        full = m.group(1).strip()
        if "," in full:
            head = full.split(",", 1)[0].strip()
            info.crucible = head
        else:
            info.crucible = full

    # Temp.Calib.: 09-04-2025 14:25  ->  2025/04/09
    # 假设原格式为 DD-MM-YYYY HH:MM
    m = re.search(r"Temp\.Calib\.\s*:\s*([0-9]{2})-([0-9]{2})-([0-9]{4})", text)
    if m:
        day, month, year = m.groups()
        # 转成 YYYY/MM/DD，月日补 0
        y = year
        m2 = f"{int(month):02d}"
        d2 = f"{int(day):02d}"
        info.temp_calib = f"{y}/{m2}/{d2}"

    # End Date/Time: 2025/5/6 10:57:06 (UTC+8)
    # 只保留 YYYY/MM/DD，月日补 0，忽略时间与时区
    m = re.search(
        r"End Date/Time:\s*([0-9]{4})/([0-9]{1,2})/([0-9]{1,2})",
        text,
    )
    if m:
        year, month, day = m.groups()
        y = year
        m2 = f"{int(month):02d}"
        d2 = f"{int(day):02d}"
        info.end_date = f"{y}/{m2}/{d2}"

    return info



def parse_dsc_segments(txt_path: str) -> List[DscSegment]:
    """
    解析 txt 中的 Segments 部分：
    - 统计有几段；
    - 每段整理成  -20°C150°C@10K/min  格式；
    - 每段下面的小 part：配对 Value(DSC) 温度 + Onset / Peak / Area（Area 取相反数并生成 comment）。
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
        return segments

    # 把 "-20°C/10.0(K/min)/150°C" 转为 "-20°C150°C@10K/min"
    def normalize_segment_desc(desc: str) -> str:
        # desc 如："-20°C/10.0(K/min)/150°C"
        m = re.match(
            r"\s*(.+?°C)\s*/\s*([0-9.]+)\(K/min\)\s*/\s*(.+?°C)\s*",
            desc
        )
        if not m:
            return desc.strip()
        start, rate, end = m.groups()
        rate_txt = f"{float(rate):g}"   # 10.0 -> "10"
        return f"{start} ➜ {end}@{rate_txt}K/min"

    # ---- 2) 定义 Segment 内部的小 block 正则 ----

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

    # ---- 3) 遍历每一个 Segment ----
    for i, m in enumerate(header_matches):
        seg_idx = int(m.group(1))
        seg_total = int(m.group(2))
        raw_desc = m.group(3).strip()
        desc_display = normalize_segment_desc(raw_desc)

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

        # ---- 3.1 收集 Complex Peak blocks 和 Value 行 ----
        peak_matches = list(peak_block_re.finditer(seg_text))
        value_matches = list(value_re.finditer(seg_text))

        # ---- 3.2 按顺序“配对”生成小 part ----
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
                # value_dsc = float(vm.group(1))  # 你不需要这个，就不存了
                temp_c = float(vm.group(2))
                part.value_temp_c = temp_c

            seg.parts.append(part)

        segments.append(seg)

    return segments