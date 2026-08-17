# 待批提案：审查比例原则（review-standards §10.5 + protocol 摘要最小 diff）

状态：**已按 codex 修订版落地权威文档（2026-08-17，用户授权）**——本文保留为提案历史；生效文本见 review-standards §10.5（2026-08-17，codex §12.3 八条 + 我的核验；
按其要求独立成文，批准前不改两份权威文档）。按 review-standards §9 分级：
第 1/2/4/8 条收紧自检与登记方式 = T1；第 3/5 条属安全边界与拒绝路径
表述 = 建议按 T0 一并批；第 6/7 条是既有熔断/subagent 规则的澄清 = T2。

## 拟加入 review-standards.md 的 §10.5（逐字）

```text
### 10.5 比例原则与 stop condition（2026-08-17）

1. finding 除生产可达性标签外必须给出：触发前提、合理发生频率、最坏
   影响、现有探测能力、修复成本、主线延误、对吞吐与训练分布的影响。
2. 阻塞优先级 = 生产可达性 × 影响 × 合理可能性，与修复成本共同裁决；
   纯理论反例、需未计划能力才可达的反例，默认 residual risk 或
   deferred，不得只因最小单测可复现就定 P0。
3. 安全例外仅适用于已批准 trust boundary 且后果为高权限执行/秘密泄漏/
   reward 污染；即便适用也优先删除能力、缩小权限或 fail-stop，不建设
   完整自动恢复。
4. no_fix / accept_residual_risk 是合法处置；选择 accepted 时必须说明
   为什么必须现在修、为什么不是删除/延后/fail-stop。
5. 每个 fail-closed 修复必须报告拒绝哪类正常轨迹、预计拒绝率、延迟与
   GPU 利用率影响；无法量化先加可观测性，不得把 fatal 静默变 missing。
6. 同一 ownership boundary 完成一次聚焦复核后，新 P1/P2 默认进阶段
   backlog 不阻塞；新 P0 须先经 Production Tracer + Falsifier 证明当前
   生产可达且非上一修复制造的复杂度。
7. subagent 沿用 §10.4：强制触发场景最多一对；schema/纯函数/文案/T2
   不用。
8. 每轮审查必须给出 stop condition：哪些已足以进入下一切片、哪些只
   登记——"还能想出反例"不构成继续阻塞理由。
```

## 拟加入 collaboration-protocol.md 的摘要行（逐字）

```text
（§5 分歧收敛补充）finding 处置四选一：accepted / rejected_with_evidence
/ deferred_with_owner_and_gate / no_fix_accept_residual_risk；阻塞按
review-standards §10.5 比例原则裁决，每轮审查须附 stop condition。
```

## 我的核验意见

八条全部采纳建议批准。其中第 4 条直接纠正我本阶段的系统性偏差
（F2-2 十轮里我对全部 finding 无一例外 accepted——包括两条后被证明
生产不可达的）；第 8 条把"无限审查"从节奏问题变成每轮的显式产物。
AGENTS.md 不复制正文（按 codex 要求）。
