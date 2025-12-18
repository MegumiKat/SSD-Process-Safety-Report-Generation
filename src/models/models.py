# src/models.py
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class DscBasicInfo:
    """保存从 DSC txt 解析出来的基础信息。"""
    sample_name: str = ""
    sample_mass_mg: Optional[float] = None
    operator: str = ""
    instrument: str = ""
    atmosphere: str = ""
    crucible: str = ""
    temp_calib: str = ""   # 例如 '2025/04/09'
    end_date: str = ""     # 例如 '2025/05/06'


@dataclass
class DscPeakPart:
    """
    每个小 peak / 小 part 的信息：
    - 可能有 Value(DSC) + 温度，
    - 也可能有 Onset / Peak / Area。
    """
    value_dsc: Optional[float] = None      # Value (DSC)，mW/mg
    value_temp_c: Optional[float] = None   # Value 对应温度，°C

    onset_c: Optional[float] = None        # Onset 温度
    peak_c: Optional[float] = None         # Peak 温度

    area_raw: Optional[float] = None       # 原始 Area（J/g）
    area_report: Optional[float] = None    # 取相反数后的 Area（用于报告）
    comment: str = ""                      # Endothermic / Exothermic / 空


@dataclass
class DscSegment:
    """
    每一段 Segment 的信息：
    - 段号 + 总段数，
    - 原始描述字符串，
    - 整理后的格式，如：-20°C→150°C@10K/min，
    - 该段下的所有小 part。
    """
    index: int                             # 段号（1,2,3,...）
    total: int                             # 总段数（例如 3）
    raw_desc: str                          # 原始描述：-20°C/10.0(K/min)/150°C
    desc_display: str                      # 整理后的描述：-20°C→150°C@10K/min
    parts: List[DscPeakPart] = field(default_factory=list)


@dataclass
class AutoFields:
    """
    右侧“自动识别字段”在 UI 中展示/编辑的最终值。
    专门存用户修改后的文本，避免每次切换样品被重新解析覆盖。
    """
    sample_name: str = ""
    sample_mass: str = ""
    operator: str = ""
    instrument: str = ""
    atmosphere: str = ""
    crucible: str = ""
    temp_calib: str = ""
    end_date: str = ""


@dataclass
class SampleManualFields:
    """
    左下 Sample information 区域中，每个样品对应的手动输入字段。
    """
    sample_id: str = ""
    nature: str = ""
    assign_to: str = ""


@dataclass
class SampleItem:
    id: int
    name: str           # UI 显示用 Sample name
    txt_path: str
    pdf_path: Optional[str] = None

    basic_info: Optional["DscBasicInfo"] = None
    segments: List["DscSegment"] = field(default_factory=list)
    auto_fields: AutoFields = field(default_factory=AutoFields)

    # 新增：每个样品自己的手动信息
    manual_fields: SampleManualFields = field(default_factory=SampleManualFields)