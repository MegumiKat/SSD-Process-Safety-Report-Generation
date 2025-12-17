import os
import tempfile
from typing import Dict, List, Optional
from copy import deepcopy

from docx import Document
from docx.shared import Inches
from src.models.models import DscSegment
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.text.paragraph import Paragraph


import fitz


def _replace_in_paragraphs(paragraphs, mapping: Dict[str, str]) -> None:
    """
    在给定的段落列表中做占位符替换。
    优先在 run 内替换（保持格式）；
    如果占位符被拆成多个 run，则用整段文本替换作为兜底。
    """
    for p in paragraphs:
        if not p.text:
            continue

        # 先尝试 run 级别替换
        for key, value in mapping.items():
            if key not in p.text:
                continue

            replaced_in_run = False
            for run in p.runs:
                if key in run.text:
                    run.text = run.text.replace(key, value)
                    replaced_in_run = True

            # 如果 run 里完全找不到 key，但整段里有，说明被拆成多个 run 了
            if not replaced_in_run:
                full_text = p.text.replace(key, value)
                # 尽量保留段落样式，用第一个 run 承载全部文本，其它 run 清空
                if p.runs:
                    p.runs[0].text = full_text
                    for r in p.runs[1:]:
                        r.text = ""


def _replace_in_tables(tables, mapping: Dict[str, str]) -> None:
    """
    在给定的表格列表中做占位符替换。
    不直接改 cell.text，而是对 cell.paragraphs 调用 _replace_in_paragraphs，
    这样可以最大程度保持单元格内已有格式。
    """
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_in_paragraphs(cell.paragraphs, mapping)


def replace_placeholders_everywhere(doc: Document, mapping: Dict[str, str]) -> None:
    """
    在整个文档（正文 + 各节的 header/footer）中替换占位符。
    """
    # 1. 正文
    _replace_in_paragraphs(doc.paragraphs, mapping)
    _replace_in_tables(doc.tables, mapping)

    # 2. 每个 section 的 header / footer
    for section in doc.sections:
        header = section.header
        footer = section.footer

        # header 里的段落和表格
        _replace_in_paragraphs(header.paragraphs, mapping)
        _replace_in_tables(header.tables, mapping)

        # footer（现在你可能没用到，但顺便支持）
        _replace_in_paragraphs(footer.paragraphs, mapping)
        _replace_in_tables(footer.tables, mapping)


def _bold_cycle_titles(doc: Document) -> None:
    """把 Discussion 里包含 'heating cycle:' / 'cooling cycle:' 的段落加粗。"""
    keywords = ("heating cycle:", "cooling cycle:")
    for p in doc.paragraphs:
        text_lower = p.text.lower()
        if any(k in text_lower for k in keywords):
            for r in p.runs:
                r.bold = True



def _fill_discussion_paragraph(doc: Document, text: str) -> List[Paragraph]:
    """
    找到包含 {{Discussion}} 的段落，把它替换成多行普通段落：
    - 每一行 text.splitlines() -> 一个 Paragraph（Word 里是 ¶）；
    - 段落 style 继承原段落；
    - 字体从原段落第一个 run 继承（尽量保持 Times New Roman 等）；
    - cycle 标题加粗。
    返回新插入的所有 Paragraph 列表。
    """
    marker = "{{Discussion}}"
    lines = text.splitlines()
    if not lines:
        return []

    for para in doc.paragraphs:
        if marker in para.text:
            base_style = para.style

            # 记录原段落第一个 run 的字体信息（可能包含 Times New Roman）
            base_font = None
            if para.runs:
                base_font = para.runs[0].font

            parent = para._p.getparent()
            idx = parent.index(para._p)

            # 删除原有占位符段落
            parent.remove(para._p)

            inserted_paras: List[Paragraph] = []

            # 逆序插入，保证顺序一致
            for line in reversed(lines):
                # 先建一个空段落，套用原 style
                new_para = doc.add_paragraph()
                new_para.style = base_style

                # 再加 run，并复制字体
                r = new_para.add_run(line)
                if base_font is not None:
                    if base_font.name:
                        r.font.name = base_font.name
                    if base_font.size:
                        r.font.size = base_font.size
                    # 是否要继承 bold/italic 看需求，一般让 style 控制即可

                parent.insert(idx, new_para._p)
                inserted_paras.append(new_para)
            
            inserted_paras.reverse()

            # cycle 标题加粗
            for p in inserted_paras:
                txt = p.text.strip().lower()
                if txt.endswith("heating cycle:") or txt.endswith("cooling cycle:"):
                    for r in p.runs:
                        r.bold = True

            return inserted_paras

    return []



def _insert_dsc_figure_after_discussion(
    doc: Document,
    pdf_path: str,          # 现在既可以是 pdf，也可以是 png/jpg
    figure_number: str,
    sample_name: str,
    discussion_paras: Optional[List[Paragraph]] = None,
) -> None:
    """
    在 Discussion 段落后面插入 DSC 曲线图 + 图注。
    pdf_path 既可以是：
    - 一张现成的 PNG/JPG；
    - 一份 PDF（用 PyMuPDF 渲染第一页）。
    """
    if not os.path.exists(pdf_path):
        print(f"[figure] 文件不存在: {pdf_path}")
        return

    ext = os.path.splitext(pdf_path)[1].lower()
    image_path = None

    # 1. 如果用户本来就选的是图片，直接用
    if ext in (".png", ".jpg", ".jpeg"):
        image_path = pdf_path

    # 2. 如果是 PDF，用 PyMuPDF 渲染第一页为 PNG
    elif ext == ".pdf":
        try:
            doc_pdf = fitz.open(pdf_path)
            page = doc_pdf.load_page(0)           # 第 0 页（第一页）
            pix = page.get_pixmap(dpi=250)        # 分辨率你可以调高或调低
            tmp_dir = tempfile.gettempdir()
            image_path = os.path.join(tmp_dir, "dsc_curve_tmp.png")
            pix.save(image_path)
            doc_pdf.close()
        except Exception as e:
            print(f"[figure] 渲染 PDF 出错: {e}")
            return
    else:
        print(f"[figure] 不支持的文件类型: {pdf_path}")
        return

    # 决定插入位置：Discussion 最后一段后面；
    # 如果没有 discussion_paras，就粗暴地在文档最后插。
    if discussion_paras:
        last_para = discussion_paras[-1]
        parent = last_para._p.getparent()
        idx = parent.index(last_para._p) + 1
    else:
        parent = doc.paragraphs[-1]._p.getparent()
        idx = len(parent)

    # 计算“页面内容区”的最大宽度
    section = doc.sections[0]
    max_width = section.page_width - section.left_margin - section.right_margin
    # 如果觉得太宽，可以打一折，比如 90%
    max_width = int(max_width * 0.9)

    # 插入图片段落（居中）
    fig_para = doc.add_paragraph()
    fig_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fig_para.add_run()

    # 关键：用 page_width - margin 作为 width，不再写死 Inches(4.5)
    run.add_picture(image_path, width=max_width)

    parent.insert(idx, fig_para._p)
    idx += 1

    # 插入图注段落（居中）
    # caption_text = f"Figure {figure_number}. DSC test curve of {sample_name}"

    # 用 pdf 文件名（去掉后缀）作为 sample name
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    caption_text = f"Figure {figure_number}. DSC test curve of {pdf_basename}"
    
    cap_para = doc.add_paragraph(caption_text)
    cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    parent.insert(idx, cap_para._p)

def fill_template_with_mapping(
    template_path: str,
    output_path: str,
    mapping: Dict[str, str],
    segments: Optional[List[DscSegment]] = None,
    sample_name_for_segments: str = "",
    discussion_text: str = "",
    pdf_path: Optional[str] = None,
    figure_number: str = "1",
) -> None:
    doc = Document(template_path)

    # 1) 普通占位符（不含 {{Discussion}}）
    mapping_no_disc = {
        k: v for k, v in mapping.items()
        if k != "{{Discussion}}"
    }
    replace_placeholders_everywhere(doc, mapping_no_disc)

    # 2) Segments 表格
    if segments:
        fill_segments_table(doc, segments, sample_name_for_segments)

    # 3) Discussion：拆成多段
    inserted_discussion_paras = None
    if discussion_text:
        inserted_discussion_paras = _fill_discussion_paragraph(doc, discussion_text)

    # 4) 在 Discussion 后面插入 pdf 图和图注
    if pdf_path and os.path.exists(pdf_path):
        sample_name = mapping_no_disc.get("{{Sample_name}}", "")
        _insert_dsc_figure_after_discussion(
            doc,
            pdf_path=pdf_path,
            figure_number=figure_number,
            sample_name=sample_name,
            discussion_paras=inserted_discussion_paras,
        )

    doc.save(output_path)


def _build_segment_rows(segments: List[DscSegment], sample_name: str) -> List[Dict[str, str]]:
    """
    把解析好的 segments 展平成表格行：
    每行包含：Sample、Test method、Value、Onset、Peak、Area、Comment。
    """
    rows: List[Dict[str, str]] = []
    first_row = True

    for seg in segments:
        for idx, p in enumerate(seg.parts):
            row: Dict[str, str] = {}

            # Sample 只在整张表的第一行显示，其余行留空
             # 现在每一行都写上 sample_label，后面用 merge 把这一列合并成一个单元格
            row["SEG_SAMPLE"] = sample_name

            # 同一个 segment 的每一行都写相同的 method，后面按“连续相同文本”合并
            row["SEG_METHOD"] = seg.desc_display

            # Start(Observed) = Value 对应温度，只要一位小数
            row["SEG_VALUE"] = (
                f"{p.value_temp_c:.1f}"
                if p.value_temp_c is not None else ""
            )

            row["SEG_ONSET"] = (
                f"{p.onset_c:.1f}"
                if p.onset_c is not None else ""
            )

            # Peak / Area / Comment
            row["SEG_PEAK"] = (
                f"{p.peak_c:.1f}"
                if p.peak_c is not None else ""
            )
            row["SEG_AREA"] = (
                f"{p.area_report:.3f}"
                if p.area_report is not None else ""
            )
            row["SEG_COMMENT"] = p.comment or ""

            rows.append(row)

    return rows



def _find_segment_template_row(doc: Document):
    """
    在文档中找到包含 {{SEG_VALUE}} 的那一行，作为模板行。
    返回 (table, row_index) 或 (None, None)。
    """
    marker = "{{SEG_VALUE}}"
    for table in doc.tables:
        for row_idx, row in enumerate(table.rows):
            for cell in row.cells:
                if marker in cell.text:
                    return table, row_idx
    return None, None


def _fill_row_with_data(row, data: Dict[str, str]) -> None:
    """用 SEG_* 数据填充某一行。"""
    replacements = {
        "{{SEG_SAMPLE}}": data.get("SEG_SAMPLE", ""),
        "{{SEG_METHOD}}": data.get("SEG_METHOD", ""),
        "{{SEG_VALUE}}": data.get("SEG_VALUE", ""),
        "{{SEG_ONSET}}": data.get("SEG_ONSET", ""),
        "{{SEG_PEAK}}": data.get("SEG_PEAK", ""),
        "{{SEG_AREA}}": data.get("SEG_AREA", ""),
        "{{SEG_COMMENT}}": data.get("SEG_COMMENT", ""),
    }
    for cell in row.cells:
        text = cell.text
        for k, v in replacements.items():
            text = text.replace(k, v)
        cell.text = text


def _merge_down_same_text(table, start_row: int, end_row: int, col_idx: int) -> None:
    """
    在 table 的第 col_idx 列，从 start_row 到 end_row（含）之间，
    把“连续文本相同”的单元格纵向合并。
    合并后只保留一份文本（放在合并后的单元格里）。
    """
    if start_row >= end_row:
        return

    current_text = table.cell(start_row, col_idx).text
    group_start = start_row

    for r in range(start_row + 1, end_row + 1):
        cell = table.cell(r, col_idx)
        text = cell.text

        if text == current_text:
            # 还在同一组，继续往下
            continue

        # 结束上一组：如果组里有多行且文本非空，则合并
        if r - 1 > group_start and current_text != "":
            top_cell = table.cell(group_start, col_idx)
            bottom_cell = table.cell(r - 1, col_idx)
            merged = top_cell.merge(bottom_cell)
            # 重要：重设一次文本，只留一份
            merged.text = current_text

        # 开启新的一组
        current_text = text
        group_start = r

    # 处理最后一组
    if end_row > group_start and current_text != "":
        top_cell = table.cell(group_start, col_idx)
        bottom_cell = table.cell(end_row, col_idx)
        merged = top_cell.merge(bottom_cell)
        merged.text = current_text


def fill_segments_table(doc: Document, segments: List[DscSegment], sample_label: str) -> None:
    """
    根据 segments 动态生成表格行。
    模板中只需要一行包含 {{SEG_*}} 占位符的“模板行”。
    - sample_label：用来显示在第一列（通常为 Sample name）。
    """
    if not segments:
        return

    table, tpl_row_idx = _find_segment_template_row(doc)
    if table is None:
        return

    rows_data = _build_segment_rows(segments, sample_label)
    if not rows_data:
        return

    # 1. 备份“原始模板行” XML（里面仍然是 {{SEG_*}}）
    tpl_row = table.rows[tpl_row_idx]
    tpl_tr_template = deepcopy(tpl_row._tr)

    # 2. 第一条数据直接用当前这一行
    _fill_row_with_data(tpl_row, rows_data[0])

    # 3. 后续数据：基于“原始模板行”克隆，然后替换
    for data in rows_data[1:]:
        new_tr = deepcopy(tpl_tr_template)
        table._tbl.append(new_tr)
        new_row = table.rows[-1]
        _fill_row_with_data(new_row, data)

    # 4. 合并相同文本的单元格
    start_row = tpl_row_idx
    end_row = tpl_row_idx + len(rows_data) - 1

    # 假设你的表格第一列是 Sample，第二列是 Test method：
    SAMPLE_COL = 0
    METHOD_COL = 1

    _merge_down_same_text(table, start_row, end_row, SAMPLE_COL)
    _merge_down_same_text(table, start_row, end_row, METHOD_COL)

        # 5. 设置合并后单元格的对齐方式为“居中”（水平 + 垂直）
    for r in range(start_row, end_row + 1):
        for c in (SAMPLE_COL, METHOD_COL):
            cell = table.cell(r, c)
            # 垂直居中
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            # 水平居中（防止某些样式没设）
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER


