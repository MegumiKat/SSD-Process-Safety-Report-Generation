# src/tools/dsc_services.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict

from src.models.models import DscBasicInfo, DscSegment, SampleItem
from src.utils.parser_dsc import parse_dsc_txt_basic, parse_dsc_segments
from src.utils.templating import fill_template_with_mapping
from src.utils.dsc_text import generate_dsc_summary


@dataclass
class ParseResult:
    basic: DscBasicInfo
    segments: List[DscSegment]


class DscParseService:
    """负责：给定 txt/pdf 路径，解析出 basic + segments"""

    def parse_one(self, txt_path: str, pdf_path: Optional[str] = None) -> ParseResult:
        basic = parse_dsc_txt_basic(txt_path)
        segments = parse_dsc_segments(txt_path, pdf_path=pdf_path)  # 允许内部抛异常给上层处理
        return ParseResult(basic=basic, segments=segments)


class ReportService:
    """负责：discussion 文本生成 + 调用模板填充"""

    def build_discussion(self, samples: List[SampleItem]) -> str:
        pieces: list[str] = []
        for s in samples:
            if not s.segments:
                continue
            label = s.auto_fields.sample_name or s.manual_fields.sample_id or s.name or ""
            text_one = generate_dsc_summary(label, s.segments)
            if text_one:
                pieces.append(text_one)
        return "\n\n".join(pieces)

    def generate_report(
        self,
        template_path: str,
        output_path: str,
        mapping: Dict[str, str],
        *,
        segments: List[DscSegment],
        discussion_text: str,
        pdf_path: Optional[str],
        sample_name_for_segments: str,
        figure_number: str,
        samples: List[SampleItem],
    ) -> None:
        fill_template_with_mapping(
            template_path,
            output_path,
            mapping,
            segments=segments,
            sample_name_for_segments=sample_name_for_segments,
            discussion_text=discussion_text,
            pdf_path=pdf_path,
            figure_number=figure_number,
            samples=samples,
        )