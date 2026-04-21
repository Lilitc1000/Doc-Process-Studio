# Quick Mode Reference

快填模式用于将简短输入一次性扩展成完整模式字段。

建议生成策略：
- `description`：交代事故背景、主要症状、定位结论。
- `affected_date_summary`：给出受影响日期与起止时间范围。
- `timeline`：至少给出关键节点（发现、处置、恢复）。
- `impact_scope`：明确受影响系统/链路/区域。
- `impact_severity`：给出清晰等级（如 High / Medium / Low）。
- `business_impact`：说明业务侧影响，可按换行列点。
- `trigger`：描述直接触发因素。
- `root_cause`：描述根因与长期缺陷。
- `follow_up_actions`：给出后续改进行动，按换行输出。

若输入仅包含单段叙述，应补全必要结构，但不得凭空捏造具体证据编号、人员姓名、工单号等。
