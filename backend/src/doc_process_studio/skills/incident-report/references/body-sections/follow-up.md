# Follow-up Actions Section Reference

本段输出 `body_follow_up`，**每行一个动作**，同时覆盖短期止血与长期治理。
判断标准很简单：**拿着这份清单，工程师能否直接开工？** 不能，就是不合格。

---

## 1. 正向标准

1. **每个动作动词开头**，写成可执行的祈使句（Upgrade / Rebuild / Move / Add / Review）。
2. **有序**：恢复类在前、加固类在后；同一批动作内部按依赖顺序排列。
3. **有版本/补丁号就写出来**：厂商建议必须带具体版本号或补丁号。
4. **有附件就引用**：详细方案作为附件时，写明附件名称。
5. 能给出责任人和截止时间就补齐；上下文中没有就写 `N/A`，不要编造人名和日期。
6. **【必须】同时覆盖短期止血与长期治理两类动作**（见第 1.1 节），缺任何一类判定不合格。

### 1.1 两类动作都必须有

| 类别 | 回答的问题 | 典型动作 |
|---|---|---|
| **短期止血** | 怎么让业务先跑起来 / 怎么防止明天再炸 | 迁移负载、重启服务、切换备用、回滚版本、补临时容量 |
| **长期治理** | 怎么让同类故障不再发生 | 升级版本/补丁、重建架构、补监控告警、改流程、补冗余 |

**数量下限**：总数 **不少于 4 条**，且两类各 **不少于 1 条**。
只写 2~3 条通常意味着遗漏了治理动作，不要因为上下文信息少就压缩清单 ——
信息不足时把缺失的人名/日期写成 `N/A`，动作本身照样要列全。

**自测问题**：这份清单里，哪几条能让业务立刻恢复？哪几条能防止复发？
答不出后者，就是只做了止血。

---

## 2. ✅ 好例子（真实报告原文）

```text
body_follow_up:
Synology advised upgrading NAS1 and NAS2 DSM version to 7.3.2 to improve storage stability and performance.
Supplement a detailed "Synology HA Remediation and Storage Rebuild Plan for CHT Incident on 12 Mar 2026" as attached.
Move all running servers VM to MSA (Temporary Storage).
Update the firmware of Synology.
Rebuild new HA cluster.
Move all running servers VM back to Synology HA Cluster.
```

**结构拆解**：

1. **厂商建议**（带具体版本号 7.3.2）
2. **附件引用**（详细整改方案名称）
3. **有序步骤列表**（4 步恢复动作，每步都是可执行动作，顺序即依赖顺序）

**为什么好**：版本号精确到 7.3.2、附件有名有姓、
四步动作构成完整的「迁移 → 升级 → 重建 → 回迁」闭环，工程师可直接照做。

---

## 3. ❌ 坏例子（现有生成常见套话，禁止这样写）

| 坏写法 | 为什么坏 |
|---|---|
| "Will follow up with vendor." | 不可执行，没有动作、没有版本、没有责任人 |
| "Monitor the situation." | 被动观望，不是整改动作 |
| "Improve system stability." | 无动作、无验收标准 |
| "Upgrade the system to the latest version." | "latest" 不是版本号，无法执行 |
| "Strengthen monitoring and alerting." | 未说明补哪个指标、什么阈值 |
| "Relevant team will handle it." | 无责任主体、无动作 |
| "Conduct a review later." | 无时间、无范围、无产出 |

---

## 4. 禁止出现的表达清单

出现以下任一表达，本段判定为不合格：

- `will follow up` / `will be handled` / `will be addressed` / `TBD`
- `monitor the situation` / `keep an eye on` / `observe closely`
- `improve` / `strengthen` / `optimize` 而不接具体对象与验收标准
- `latest version` / `recent patch`（未给出确切版本号）
- `as soon as possible` / `later` / `in the future`（无截止时间）
- `relevant team` / `responsible person`（无人名）
- **清单少于 4 条**
- **只有短期止血、没有长期治理动作**

**正确替代**：`Upgrade NAS1 and NAS2 DSM to 7.3.2 (owner: N/A, due: N/A)` ——
动作 + 对象 + 版本，缺失的人名和日期坦然写 `N/A`；
信息不足时压缩的是**字段**，不是**条数**。
