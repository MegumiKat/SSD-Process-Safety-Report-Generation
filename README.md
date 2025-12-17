# DSC 报告生成工具（DSC Report Generation Tool）

## 项目简介

**DSC 报告生成工具** 是一个基于 Python 和 PyQt6 的桌面应用，用于从 DSC（Differential Scanning Calorimetry，差示扫描量热法）仪器导出的 **TXT 结果文件** 和 **曲线 PDF 文件** 中，自动生成结构化、格式统一的 **Word 报告**（基于预设模板）。

项目的目标是：

- **减少人工复制粘贴** 工作量
- **统一报告格式与内容结构**，提升可追溯性与可读性
- 以模块化方式实现 **解析 → 数据建模 → 文本生成 → 模板填充 → 报告导出** 的完整流水线

## 主要特性

- **图形界面（GUI）操作**：基于 PyQt6 的桌面应用，无需命令行即可使用
- **多文件输入**：
  - DSC 结果 TXT 文件（仪器输出）
  - 曲线 PDF 文件（图谱/曲线）
  - Word 模板文件（`.docx`，在 `data/` 目录下）
- **自动解析与结构化**：
  - 解析 DSC TXT 文本，提取基础信息（如样品、测试日期等）与分段信息
  - 使用类型化数据模型（`DscBasicInfo`、`DscSegment` 等）管理解析结果
- **可编辑字段**：
  - 在界面中手动补充/修改请求信息与样品信息，确认数据后再生成报告
- **Word 报告自动生成**：
  - 基于模板 (`.docx`) 自动进行占位符替换
  - 支持根据解析结果生成文字描述段落
- **日志与状态反馈**：
  - 界面中展示文件日志、确认数据块、历史生成记录，便于追踪生成过程

## 目录结构

```shell
.
├── main.py                      # 应用入口
├── requirements.txt             # Python 依赖
├── README.md                    # 项目说明（本文件）
├── log.md                       # 开发过程记录 / 变更日志
├── problems.md                  # 已知问题 / TODO
│
├── src/
│   ├── config/
│   │   └── config.py            # 配置项（默认模板路径、Logo 路径等）
│   ├── models/
│   │   └── models.py            # 数据模型（解析后的结构化信息）
│   ├── utils/
│   │   ├── parser_dsc.py        # DSC TXT 解析逻辑
│   │   ├── templating.py        # Word 模板填充逻辑
│   │   └── dsc_text.py          # 根据数据生成文字描述
│   ├── ui/
│   │   └── ui_main.py           # PyQt6 图形界面
│   └── test/
│       └── test_segments.py     # 单元测试示例
│
├── data/                        # 报告模板（Word .docx）
│   ├── DSC Report-Empty-2511.docx
│   └── DSC Report-Empty-2512.docx
│
└── CF130G/                      # 示例输入数据
    ├── PrnRes_CF130G_2025-05-06.txt
    ├── CF130G.pdf
    └── DSC test for CF130G.docx
```

## 环境要求

- **操作系统**：Windows / macOS / Linux
- **Python 版本**：建议 Python **3.10+**
- **依赖库（核心）**：
  - `PyQt6`：桌面图形界面
  - `python-docx`：Word 文档模板读写
  - `PyMuPDF`（`PyMuPDF==1.26.6`）：处理 PDF 内容（如图像/截图）
  - 其他依赖见 `requirements.txt`

> 提示：`requirements.txt` 中包含了一些与其他实验/工具共享的依赖，如果只想安装本项目核心依赖，可按需精简。

## 安装步骤

1. **克隆仓库**

   ```bash
   git clone <your-repo-url>
   cd DSC_Report_Tool
   ```

2. **创建虚拟环境（推荐）**

   ```bash
   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows（PowerShell）
   python -m venv .venv
   .venv\\Scripts\\Activate.ps1
   ```

3. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

## 运行方式

在项目根目录下执行：

```bash
python main.py
```

成功启动后，将出现名为 **“DSC Reports Generation Tool (template + txt + pdf)”** 的窗口。

## 使用说明

1. **选择输入文件**（界面左上区域）：
   - `Choose TXT`：选择 DSC 仪器导出的 TXT 结果文件
   - `Choose PDF`：选择对应的曲线 PDF 文件
   - `Choose Output Path`：选择生成的报告保存路径（通常为 `.docx`）
   - `Current Template`：显示当前使用的 Word 模板文件名（默认由 `config.py` 中的 `DEFAULT_TEMPLATE_PATH` 决定）

2. **填写 / 校验信息**：
   - 在 `Request information` 与 `Sample information` 两个区域中检查并补充：
     - Request ID、Customer、Sample ID、Test Date、Report Date 等
   - 这些字段会被用于填充模板中的对应占位符

3. **确认数据**：
   - 点击 **“Confirm Data”** 按钮：
     - 锁定当前解析结果和手动输入字段
     - 在日志区域中生成当前确认数据块，便于回溯

4. **生成报告**：
   - 点击 **“Generate Report”**：
     - 程序会：
       1. 使用 `parse_dsc_txt_basic` / `parse_dsc_segments` 解析 TXT 文件
       2. 利用 `generate_dsc_summary` 生成文字说明
       3. 调用 `fill_template_with_mapping` 将数据映射到 Word 模板占位符
       4. 将最终报告保存到你指定的输出路径
   - 成功后，可在输出路径中打开生成的 `.docx` 报告进行校对与归档。

## 配置说明

核心配置位于 `src/config/config.py`，主要包括：

- **模板路径**：`DEFAULT_TEMPLATE_PATH`
- **Logo 路径**：`LOGO_PATH`（用于界面左上角 Logo 展示）

如需：

- 更换默认报告模板，只需将 `DEFAULT_TEMPLATE_PATH` 指向新的 `.docx` 模板
- 更换公司 Logo，只需调整 `LOGO_PATH` 指向新图像文件

## 开发与测试

- **代码结构**：
  - 解析逻辑、文本生成、模板填充分离，便于单独测试和扩展
  - 使用数据类/模型（在 `models.py` 中）统一管理解析后的结构化数据
- **单元测试**：
  - 示例测试位于 `src/test/test_segments.py`
  - 在虚拟环境中运行：

    ```bash
    python -m pytest src/test
    ```

## 后续改进方向

- 增强解析规则的鲁棒性，适配更多仪器/方法输出格式
- 增加更明确的错误提示（如缺失字段、解析失败等）
- 支持配置化的报告模板选择与多语言报告输出
- 引入 CI 以自动运行测试、检查代码质量

## 许可证

当前项目尚未显式指定开源许可证，如需对外发布或分享，请根据实际需求补充相应的 LICENSE 文件。