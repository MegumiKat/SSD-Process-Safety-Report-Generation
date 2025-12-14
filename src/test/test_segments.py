from src.utils.parser_dsc import parse_dsc_segments

txt_path = "/Users/mark/Desktop/Projects/DSC_Report_Tool/CF130G/PrnRes_CF130G_2025-05-06.txt"  # 改成你的真实路径
segments = parse_dsc_segments(txt_path)

print("总段数：", len(segments))
for seg in segments:
    print(f"Segment {seg.index}/{seg.total}: {seg.desc_display}")
    for part in seg.parts:
       print(
    "  ValueTemp(°C)=",
    part.value_temp_c if part.value_temp_c is not None else "—",
    "| Onset=", part.onset_c if part.onset_c is not None else "—",
    "| Peak=", part.peak_c if part.peak_c is not None else "—",
    "| Area(report)=", part.area_report if part.area_report is not None else "—",
    "| Comment=", part.comment or "—",
)