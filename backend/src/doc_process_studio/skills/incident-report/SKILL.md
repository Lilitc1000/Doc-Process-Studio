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
3. 前端按 `agents/interaction.json` 的步骤一次性渲染完整表单。
4. 用户填写后点击“生成附件”，后端先做必填校验，再把生成的 `incident_data.json` 作为文件送入 skill 对话链路。

## 生成链路

1. 将表单答案映射为结构化 `incident_data.json`。
2. 把该 `incident_data.json` 作为会话上传文件注入到 incident-report skill 聊天上下文。
3. 模型必须先读取上传的 `incident_data.json`，在不改变 JSON 键结构的前提下润色其中叙述型文本字段（如事件描述、故障现象、根因、影响、处置措施等）。
4. 模型将润色后的完整 JSON 作为 `report_data` 调用 `generate_incident_report`，生成附件。
5. 后端把工具参数中的润色后 `report_data` 回写到会话快照。

## 数据与产物约束

- `report_data` 必须对齐 `examples/incident_data.json` 的键结构。
- 时间字段建议使用 `DD/MM/YYYY HH:MM`。
- 不得编造事实；缺失值可填 `N/A`。
- 产物仅允许 `.docx`（Word）附件。
- 生成后前端表单锁定，避免二次编辑造成状态不一致。

## 目录结构

```text
incident-report/
├── SKILL.md
├── agents/
│   ├── openai.yaml
│   └── interaction.json
├── scripts/
│   └── generate_incident_report.py
└── examples/
    └── incident_data.json
```
