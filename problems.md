# Promblem

## 1. txt 是 UTF-16 编码，解析不到内容 → 自动字段全是空字符串。

你现在的 txt 文件是这种形式（每个字符后面有一个 \x00）：

```shell
I�n�s�t�r�u�m�e�n�t�:� ...
```

这说明是 UTF-16（常见是 UTF-16LE），但我们在 parse_dsc_txt_basic 里用的是 encoding="utf-8"，正则当然什么都匹配不到，所以：

- sample_name、crucible、temp_calib 等全部是 ""
- 进入 mapping 后这些占位符被替换成空字符串，看起来就是“啥都没填进去”。

修改读取文件部分 有显示用UTF-16读 不行再退回使用UTF-8:

```python
try:
        with open(txt_path, "r", encoding="utf-16", errors="ignore") as f:
            text = f.read()
    except UnicodeError:
        # 万一遇到不是 UTF-16 的文件，再用 utf-8 兜底
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
```

## 2. Request_id 没有填入 Word：要处理“页眉”的占位符

之前的templating只对：

- doc.paragraphs（正文段落）
- doc.tables（正文里的表格）

现在修改成同时需改：

- section.header.paragraphs
- section.header.tables

## 3. 页眉字体变了：不要用 cell.text = ...，只改 run 文本

目前情况：

- {{Request_id}} 确实被替换成功了
- 但是页眉整体字体/字号/对齐被改掉了

最可能的原因：在 header 的表格里，我们用了 cell.text = new_text 去替换，而 python-docx 在给 cell 重新赋 text 时，会重建段落和 run，导致原来的样式丢失，用了默认样式。

修改思路：

```python
def _replace_in_paragraphs(paragraphs, mapping):  # run 级别，能保留格式
    ...

def _replace_in_tables(tables, mapping):          # 通过 cell.text 替换，会丢格式
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                cell_text = cell.text
                ...
                cell.text = cell_text
```
