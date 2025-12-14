# Placeholders

| 占位符                   | 含义 / 字段说明              | 填充值来源                              | 备注                                                   |
|--------------------------|------------------------------|-----------------------------------------|--------------------------------------------------------|
| {{Customer_information}}| 委托方信息 / Customer        | GUI 手动输入                            | 模板里多了一个 `)`，建议后续改成 `{{Customer_information}}` |
| {{Request_Name}}         | 项目名称 / Request Name      | GUI 手动输入（可默认 “DSC test for {{Sample_name}}”） |                                                        |
| {{Submission_Date}}      | 提交日期 / Submission Date   | GUI 手动输入                            | 可默认当前日期或与 Test_Date 保持一致                 |
| {{Request_Number}}       | 申请编号 / Request Number    | GUI 手动输入                            | 实验/业务内部编号                                     |
| {{Project_Account}}      | 项目号 / Project Account     | GUI 手动输入                            |                                                        |
| {{Deadline}}             | 截止日期 / Deadline          | GUI 手动输入                            |                                                        |
| {{Sample_id}}            | 样品编号 / Sample #          | GUI 手动输入                            | 若有 LIMS / 内部样品号可填此处                        |
| {{Sample_name}}          | 样品名称 / Sample Name       | **自动**：来自 txt 中 `Sample identity` 或 `Sample name` | 如 CF130G                                              |
| {{Nature}}               | 样品性质 / Nature            | GUI 手动输入                            | 如 powder, liquid 等                                   |
| {{Assign_to}}            | 负责人员 / Assigned to       | GUI 手动输入（可默认 txt 中 `Operator`） | 例如默认填入 WX，用户可在界面修改                     |
| {{Receive_Date}}         | 收样日期 / Receive Date      | GUI 手动输入                            | 若有系统可对接，也可自动生成                          |
| {{Test_Date}}            | 测试日期 / Test Date         | GUI 手动输入      | 例如 2025/5/6                                          |
| {{Report_Date}}          | 出报告日期 / Report Date     | GUI 手动输入（可默认当前日期）          |                                                        |
| {{Crucible}}             | 坩埚类型 / Crucible          | **自动**：来自 txt 中 `Crucible:` 行    | 如 Concavus Al, pierced lid                            |
| {{Temp.Calib}}           | 温度标定时间 / Temp.Calib.   | **自动**：来自 txt 中 `Temp.Calib.:` 行 | 模板占位符包含点号，代码替换时需按原样写              |
| {{Request_desc}}         | 检测申请描述 / Request Description | GUI 手动输入                       | 对应模板中 “检测申请描述(REQUEST DESCRIPTION)” 一行    |
| {{End_Date}}            | 测试日期 / Test Date         | **自动**：来自 txt 中 `nd Date/Time:` 行      | 例如 2025/5/6                                          |


## DSC 结果表（Result Table）行内占位符

| 占位符      | 含义 / 列说明                           | 填充值来源                                        | 备注                                                 |
|-------------|------------------------------------------|---------------------------------------------------|------------------------------------------------------|
| {{Segments}}| 测试段信息 / Segments                   | **自动**：来自 txt 中各个 `Segments: 1/3, 2/3, 3/3` | 可写成 “1st heating / cooling / 2nd heating” 或温程描述 |
| {{Value}}   | 起始温度 / Start observed (Value)       | **自动**：对应 `Value (DSC) ... °C`               | 每个 Complex Peak 的起点温度                         |
| {{Onset}}   | Onset 温度                              | **自动**：对应 `Onset: ... °C`                    | 若模板中有多余字符（如 `{{Onset}}t`），建议改模板    |
| {{Peak}}    | 峰温 / Peak temperature                 | **自动**：对应 `Peak: ... °C`                     | 例如 21.5°C, 34.3°C, 44.3°C 等                       |
| {{End}}     | 结束温度 / End temperature              | **自动**：可来自该峰对应的 Range(max) / 结束点    | 若 txt 没有明确 End，可用事件范围或自行定义规则     |
| {{- Area}}  | 峰面积/焓变 ΔH (J/g)                    | **自动**：对应 `Area ... J/g`                     | 包含正负号；负值一般为 endothermic，正值为 exothermic；模板名里带 `-`，代码替换时需用原样 `{{- Area}}` |



