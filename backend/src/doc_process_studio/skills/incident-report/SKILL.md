---
name: "incident-report"
description: "用于事故报告工作区：基于结构化表单收集事故信息，生成符合 DAS 模板的英文 Word 事故报告文档。"
skill_type: "workspace_incident"
---

# 事故报告技能（incident-report）

本技能仅用于“事故报告”工作区，不参与普通聊天通道的 `$skill` 选择与隐式规划。

## 使用方式

1. 用户在侧边栏切换到“事故报告”。
2. 进入欢迎页后点击“开始”，创建事故报告会话。
3. 前端按工作区新表单逻辑渲染（手工首页 / AI 正文 / 附录 / 历史版本）。
4. 用户填写后点击“生成附件”，后端先做必填校验，再把 `report_data` 直接传入工具生成文档。

## 生成链路

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
│   └── openai.yaml
├── scripts/
│   └── generate_incident_report.py
└── references/
    └── DAS2 Fault Log Form Template.docx
```
