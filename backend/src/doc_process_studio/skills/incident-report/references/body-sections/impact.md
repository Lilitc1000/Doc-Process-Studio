# Impact Section Reference

本段输出三个字段：`body_impact_scope` / `body_impact_severity` / `body_business_impact`。

Impact 是整份报告**证据密度最高**的段落。读者要能据此判断损失范围并复算损失。
影响段写空话，整份报告就失去价值——这是本模块最常见也最严重的缺陷。

---

## 1. 正向标准

按四层递进写，缺哪一层就写 `N/A`，**不要跳过、不要用形容词糊过去**：

1. **设备状态层** — 点名具体设备/组件（含型号或编号），说明它发生了什么、当前处于什么状态。
2. **业务后果层** — 说明**哪个业务行为停了或降级了**，以及精确起止时间。
   不是"系统受影响"，而是"什么动作做不了"。
3. **服务波及层** — 列出被连带影响的上下游服务。
4. **数据佐证层** — 凡提到数量，给出数据表格（`| 对象 | 时段 | 数量 |`）。

补充规则：

- 时间戳精确到分钟，统一 `DD/MM/YYYY HH:MM`。
- 数量、时段、设备编号没有确切数据就写 `N/A`，**绝不编造**。
- 严重级别用统一等级体系，与表单 `manual_severity` 保持一致（P0/P1/P2/P3 或 Major/Minor/Not Applicable）。
- `body_business_impact` 多行输出，每行一个业务后果。

**自测问题：写完后，读者能否复算出损失？** 不能，就是不合格。

---

## 2. ✅ 好例子（真实报告原文）

```text
body_impact_scope:
Both CHT Synology Data Storage NAS1 and NAS2 status were unstable.
NAS2 status was abnormal and shutdown automatically at 20:35, 12 Mar 2026.
NAS1 is now active as standalone.

body_impact_severity:
Major

body_business_impact:
Partial CHT transactions stopped uploading from 17:07 to 22:50, 12 Mar 2026.
Most of services includes time service was impacted due to Synology Data Storage abnormal.

| Toll Point | Time Range                       | No. of Transactions |
|------------|----------------------------------|---------------------|
| CHT1       | 17:14, 12/03/2026 - 17:46, 12/03 | 1,448               |
| CHT1       | 06:55, 13/03/2026 - 11:32, 13/03 | 13,088              |
| CHT3       | 17:07, 12/03/2026 - 22:15, 12/03 | 13,328              |
| CHT3       | 07:01, 13/03/2026 - 11:30, 13/03 | 12,554              |
| Total      |                                  | 40,418              |
```

**为什么好**：点名了 NAS1/NAS2 两台设备 → 给出了自动关机的时间点 →
说明了具体业务后果（transactions stopped uploading）及精确时段（17:07–22:50）→
用 40,418 笔的表格收尾，损失可复算。

---

## 3. ❌ 坏例子（现有生成常见套话，禁止这样写）

| 坏写法 | 为什么坏 |
|---|---|
| "The system was significantly impacted." | 无实体、无时间、无业务行为，不可验证 |
| "Service performance degraded." | "degraded" 无量化，没有说明降级成什么 |
| "Some users may have experienced issues." | "some" / "may" 是猜测，不是事实 |
| "The impact was severe and widespread." | 形容词堆砌，零信息量 |
| "Business operations were affected to some extent." | 没说清哪个业务动作停了 |
| "Impact: system unavailable for a period of time." | "a period of time" 没有起止时间 |

---

## 4. 禁止出现的表达清单

出现以下任一表达，本段判定为不合格：

- `significantly` / `severe(ly)` / `considerably` / `substantially` / `greatly`
- `to some extent` / `more or less` / `a period of time` / `recently`
- `some users` / `may have` / `might be` / `possibly`（无证据的推测）
- `impacted` 单独使用却不接具体对象与时段
- `degraded` / `unstable` 单独使用却不接量化指标或业务后果

**正确替代**：把上面的模糊表达换成「设备名 + 时间戳 + 业务动作 + 数量」。
拿不到数据的部分写 `N/A`，留空比编造好。
