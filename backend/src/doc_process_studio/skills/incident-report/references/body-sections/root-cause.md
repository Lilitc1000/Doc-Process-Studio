# Root Cause Section Reference

根因段拆分为两部分，二者**不得写成同一句话**：

- `body_trigger`：直接触发原因（近因），回答"是什么把故障引爆的"。
- `body_root_cause`：深层根因，写成**因果链**，回答"为什么会发展成这样"。

---

## 1. 正向标准

因果链写法要求：

1. **链条至少 3 环**：触发动作 → 至少 1 个中间传导环节 → 可观测终点。
   只写 1~2 句等同于没分析，判定不合格。
2. **每一环都必须是一个技术动作**，形如「A 导致 B」，B 又导致 C。
3. **链条终点是可观测的现象** —— auto-shutdown / failover loop / replication failed /
   data inconsistent / connection timeout 这类能被日志或监控证实的事件。
4. **不要停在黑箱标签** —— "hardware issue" / "system error" 不是根因，是没查下去。
5. 触发原因与根因分开描述；根因尽量指向**可改进项**（设计、容量、流程、监控、版本缺陷）。
6. **证据强度分层标注**（见第 1.1 节）：已证实的照实写，推断的标 `inferred`，
   真不知道的才写 `N/A`。

### 1.1 证据强度分层（重要）

上下文信息不完整是常态，**不要因此就把链条压缩成一句话**。按以下三档处理：

| 档位 | 适用场景 | 写法 |
|---|---|---|
| **confirmed** | 上下文中有日志/监控/时间戳直接支撑 | 直接陈述，不加标注 |
| **inferred** | 上下文未直接说明，但可由已知现象合理推导 | 陈述后加 `(inferred)` |
| **N/A** | 连合理推断都做不出 | 写 `N/A（待补充：需要 XX 日志）` |

**关键原则：`N/A` 是最后手段，不是首选出路。**
只要能从上下文的现象反推出技术上传得通的中间环节，就必须写出来并标 `inferred`。
推断错了可以后续修正，链条缺失则整段失去价值。

**信息不足时的标准写法模板**：

```text
body_root_cause:
<已证实的触发环节，直接陈述>。
<推断的中间传导环节> (inferred)。
<可观测终点，直接陈述>。
N/A（待补充：需要 <具体日志/指标名称> 以确认 <具体环节>）。
```

**自测问题：每一环是 confirmed 还是 inferred？** 能说清就可以写；
只有连推断都做不出时才允许 `N/A`。

---

## 2. ✅ 好例子（真实报告原文）

```text
body_trigger:
Extreme I/O load on CHT Synology Data Storage.

body_root_cause:
Extreme I/O load stalled NFS/filesystem, triggering HA failover loops.
Replication couldn't complete, causing data inconsistency.
HA detected data inconsistent on Node 2, marked volume crashed, then auto-shutdown.
```

**因果链拆解**（每一环都是技术动作，不是标签）：

```text
I/O 负载异常
  → NFS / 文件系统停滞
    → HA 反复 failover
      → 复制无法完成
        → 数据不一致
          → HA 判定 Node 2 volume crashed
            → 自动关机（可观测终点）
```

**为什么好**：七环完整，每环都是可在日志中查证的技术动作，
终点 `auto-shutdown` 是可观测现象，读者能顺着链条定位到每一层的加固点。

---

## 3. ❌ 坏例子（现有生成常见套话，禁止这样写）

| 坏写法 | 为什么坏 |
|---|---|
| "Root cause was a hardware issue." | 黑箱标签，没有因果链，无法据此加固 |
| "The system encountered an error." | 没说明什么错误、由什么引发 |
| "Caused by unknown reasons." | 未查证即放弃；应写出已确认的环节 + 待补充部分 |
| "Insufficient monitoring led to the incident." | 过于笼统，未说明具体缺失哪个指标 |
| "Human error during maintenance." | 未说明具体哪个操作、触发了什么 |
| "The root cause is the same as the trigger." | 近因与根因混为一谈，等于没分析 |

---

## 4. 禁止出现的表达清单

出现以下任一表达，本段判定为不合格：

- `hardware issue` / `software issue` / `system error` / `technical problem`
- `unknown reason` / `unclear` / `under investigation`（作为最终结论）
- `human error` 而不说明具体动作
- `root cause` 与 `trigger` 内容重复或互相复制
- 未展开的单个名词作为整段根因（如仅写 `disk failure`）
- **整段不足 3 环**（只写触发 + 终点，中间传导缺失）

> 注意：标注 `(inferred)` 的推断环节**不在此列**。
> 带标注的推断是合格写法，比留空有价值；禁止的是**未标注的编造**。

**正确替代**：把黑箱标签展开成「动作 → 后果 → 动作 → 后果」的链条；
能推断的中间环节写出来并标 `inferred`；
连推断都做不出的部分才写 `N/A（待补充：需要 XX 日志）`。
