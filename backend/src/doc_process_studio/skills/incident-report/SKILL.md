---
name: "incident-report"
description: "用于事故报告工作区：基于结构化表单收集事故信息，生成符合 DAS 模板的英文 Word 事故报告文档。"
skill_type: "workspace_incident"
---

# 事故报告技能（incident-report）

本技能仅用于“事故报告”工作区，不参与普通聊天通道的 `$skill` 选择与隐式规划。
在事故报告工作区内，每次正文生成都视为显式选择 `incident-report` skill。

## 使用方式

1. 用户在侧边栏切换到“事故报告”。
2. 进入欢迎页后点击“开始”，创建事故报告会话。
3. 前端按工作区新表单逻辑渲染（手工首页 / AI 正文 / 附录 / 历史版本）。
4. 用户填写后点击“生成附件”，后端先做必填校验，再把 `report_data` 直接传入工具生成文档。

## 正文生成（渐进披露）

### 1) 生成目标识别

- 后端接收本次生成目标（`quick` / `description` / `timeline` / `timeline_item` / `impact` / `root_cause` / `follow_up`）。
- 该目标来自工作区按钮点击行为，代表“本次显式 skill 调用的意图”。

### 2) 参考文档选择（第一阶段）

- 模型先读取本 `SKILL.md` + 参考目录摘要（不直接加载全部正文）。
- 模型输出本次应读取的 reference 文件列表（1~4 个）。
- 选择器实现复用后端统一规划器（与对话工作区同源的 `plan_skill_activation` 机制）。
- 若模型未返回有效列表，后端按目标做启发式兜底选择。

### 3) 分段生成（第二阶段）

- 后端仅加载第一阶段选中的 reference 正文，连同当前表单上下文一起给模型生成。
- 快填模式会生成并回填完整模式全部字段。
- 完整模式仅更新当前分段（时间线单条仅更新当前条目）。

## 附件生成链路

1. 将表单答案映射为结构化 `report_data`。
2. 必要时对中文正文做英文翻译。
3. 由后端以 tool call 方式调用 `generate_incident_report`，生成 DOCX。
4. 生成结果写入历史版本，支持预览与下载。

## 数据与产物约束

- 时间字段建议使用 `DD/MM/YYYY HH:MM`。
- 不得编造事实；缺失值可填 `N/A`。
- 产物仅允许 `.docx`（Word）附件。
- 生成后前端表单锁定，避免二次编辑造成状态不一致。

## 目录结构

```text
incident-report/
├── SKILL.md
├── agents/
│   └── config.yaml
├── references/
│   ├── DAS2 Fault Log Form Template.docx
│   └── body-sections/
│       ├── common.md
│       ├── quick-mode.md
│       ├── description.md
│       ├── timeline.md
│       ├── timeline-item.md
│       ├── impact.md
│       ├── root-cause.md
│       └── follow-up.md
├── scripts/
│   └── generate_incident_report.py
```
