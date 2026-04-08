---
name: "incident-report"
description: "通过交互式向导采集事故信息，并生成符合 DAS 模板的英文事故报告文档。适用于生产故障、服务中断、事故复盘与合规留档场景。"
---

# 事故报告技能（incident-report）

本技能用于在对话中分步骤采集事故信息，并最终生成可下载的英文 Word 报告。

## 触发场景

当用户表达以下需求时应启用本技能：

- “帮我生成事故报告”
- “生成故障报告 / 事故复盘文档”
- “写一份 post-mortem”
- 需要按模板留档系统中断、性能异常、交易失败、网络故障等事件

## 交互模式（必须遵循）

1. 若用户未提供完整信息，不要直接生成文档。
2. 通过交互式步骤逐步采集，当前步骤未确认前不进入下一步。
3. 仅在必填信息采集完成后再调用生成工具。
4. 若用户明确同意缺省值，可在 `report_data` 中携带 `allow_incomplete=true` 后生成。

本技能的结构化步骤定义在：

- `agents/interaction.json`

其中包含：

- 步骤顺序
- 每步选项
- 字段映射（`field_path`）
- 最终工具调用配置（`final_tool`）

## 目标产物

生成英文 Word 文档（`.docx`），包含：

- Page 1: Fault Log Form（A/B/C 三个区块）
- Page 2: Detailed Incident Report（6 个章节）

## 6 个必填章节语义

1. Description of the Incident
2. Affected Date
3. Event Sequence
4. Impact
5. Root Cause
6. Follow-Up Actions

## 数据结构规范

`report_data` 建议尽量对齐：

- `examples/incident_data.json`

关键要求：

- 尽量不要省略关键字段
- 缺失值请使用 `N/A` 或空数组
- 时间字段建议统一格式 `DD/MM/YYYY HH:MM`

## 生成脚本

- `scripts/generate_incident_report.py`

脚本会对输入做归一化处理，并尽量补齐模板字段；但如果信息明显不完整，默认会阻止生成并提示缺失章节。

## 最佳实践

1. 先采集再生成，避免空白区域。
2. 生成后只提示用户在附件区下载，不输出本地临时路径。
3. 若用户要求英文报告，保持字段值与报告正文为英文表述。

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
