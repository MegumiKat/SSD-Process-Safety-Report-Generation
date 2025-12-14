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