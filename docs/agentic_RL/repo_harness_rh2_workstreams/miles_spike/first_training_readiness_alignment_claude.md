# 首训就绪范围：Claude 对齐意见书

日期：2026-09-01。对象：codex 的 `formal_first_training_readiness_scope.md`（下称"就绪稿"）。性质：**审读意见 + 补全 + 修剪**，不是重写；三路独立证据支撑——就绪稿四条新代码断言逐行核实（全部成立）、S2/数据/评测/配置全面盘点（会话报告，关键事实内嵌）、本地测试边界盘点（scope_v1 已用）。

## 1. 总立场：采纳就绪稿为基骨架

**采纳理由**：它对我此前两个判断的批驳经核实成立，我正式修正——

1. **"剩余大头只是验收"错了**。核实实锤了四个实现级缺口：(a) fa_formal 六字段身份在 miles 派发路径全仓零铸造点（`generate.py:2366-2378` 强制校验 vs 当年铸造分两级都不在 miles 路径上）；(b) **eligibility 无下游消费是正确性级的洞**——tier cap 封顶不触发 remove_sample（`generate.py:3827` 注释明说"S1 封顶不算降级"），封到 offline 的样本今天照常进 loss，`training_eligibility_class` 在 miles 全侧零消费者；(c) miles 恢复链三连断（无 joint commit、cursor 缺失静默从头、**updater 一律 version=0 且 bootstrap 把旧权重错标 v1**——直接摧毁 spans/staleness 审计，`(segment_id, numeric_version)` 复合身份因此是必要设计而非过度）；(d) 跨 publish 提前 drain 使 staleness 低一代（`train_async.py:153-154` 结构保证，限定=该间隔真发生 publish）。
2. **B6 编号碰撞**：零信号 B6 ≠ 旧 formal 评分组合 B6，后者未做且首训必须。

就绪稿的**范围收缩纪律也合格**：S2 裁到 reward-integrity 最小集（非 root/隔离网/隐藏测试隔离/拦截真进 gate），不做 microVM/claim-check/完整红队；§4 十五条"明确不做"清单符合"不用后移话术、要么做完要么明确不做"的要求。campaign 设计（Safety-Q→Eval-Q0→Segment A→预期 job death→Segment B→Eval-Q1）干净且每段"为何必须 GPU"成立。

## 2. 就绪稿缺的两块（我的补全）

### 2.1 数据/评测线的完整归属（就绪稿有意划界外，但路线图必须有归属）

盘点事实：R2E ingestion **从未发生**（全仓唯一 ingester 是 swegym_lite；R2E 需另一套 ingestion + scaleswe grader + ~2.3TiB 镜像面）；E5 frozen held-out **一题未冻结**（542 候选里 450 题依赖 R2E）；bring-up 筛题需要 ①四门 runner（S2-1 T2-d/e，未实现——就绪稿 §2.3 已覆盖）② x86 CPU 实例批量验证（~$15-40、1~2 天，**不需要 GPU**）③ **GPU pass-rate 预筛 + pre-RL 行为诊断 = 单卡 GPU 作业**（data_freeze 报告既定口径），就绪稿未安置。

**我的处置建议**：
- **D3 规模档位现在拍板（新增 T0）**：首训取**闭环档（150~200 题，纯 SWE-Gym Lite）**。理由：首训的既定目标是验证闭环而非主张能力提升（E5 primary Δ≥8pp 属 success run）；这使 **R2E ingestion 对首训"明确不做"**（success run 前再开范围），held-out 冻结改用 SWE-Gym 侧候选（hydra 66 + bokeh 26，够 T=50~80 的 SWE-Gym 半区），R2E 侧 held-out 推迟同步。若 owner 坚持首训即效果档，R2E ingestion 升为阻塞项，工期加一整块。
- **GPU 预筛/行为诊断作租期尾项或单卡独立作业**：优先方案=八卡租期主资格全绿后用 rollout 引擎跑（复用已资格化的栈，rollout-only）；租期不够则单卡单租（便宜，不阻塞八卡资格结论）。
- **评测执行链**：就绪稿 §2.9 本地闭合 + H10 已覆盖执行面；held-out **冻结**（选题+分层）是数据作业，依赖四门 runner 与预筛，排在同一条数据线上。

### 2.2 定案文书的迁移修订（具体条款清单）

E7/E10 的 slime 绑定条款需逐条改写（盘点 §4.2 已列：形态 B 载体、pin 对象、top-p 可用条件变为"miles router + spans 引擎"、U-H 回退梯、附录 A 注记）；E2 的"slime 默认三处差距"需 miles 对应物核对（dynamic filter 已接，**std 归一化与 clip-high 两项无核对记录——列入租前本地小项**）；D5（评测补充面）无定案，建议随 profile 一并拍板（推荐最小化：首训只 Verified held-out 内部面，补充面推迟）；`rh2_fully_async_training_path_verified` 目前无 JSON 账本（只在文档级）——闸门公式改造时一并给它账本落位。G 系列遗留的处置：G7（网络方案）被 §2.4 吸收、G6（解封口径）被 §0.2 公式吸收、G8（S2-6 验收资产）随"S2-6 不做"一并了结——就绪稿 §7 事实上接替 G 系列，批准时注明替代关系即可，不再单独走 G 流程。

## 3. 修剪意见（防过度设计，三处）

1. **§2.5 计时面**：只实现 H5 硬门真正读取的事实子集（就绪稿 §2.8 自己的原则）；prefetch on/off matched 对照保持"条件性、不可比即 NOT_COMPARABLE"的原文口径，不为它扩本地工作。
2. **§0.2 闸门三概念**：实现收敛为"授权 manifest 文件 + 一条准入公式改 inspector/preflight"，`formal_path_infrastructure_qualified` 等作为验收结论记账本，不建 gate 框架（与原文"不要求新增复杂通用 gate 系统"一致，此处是把它钉死成实现约束）。
3. **§2.8 资源闭包**：内存上界允许粗粒度保守估计 + 有界窗口，fsync 测量一次性取数，不做持续监测面。

## 4. 租前本地工作的批次形状（供排期）

按依赖序（每批 = 现行 agent 节奏 1~3 天 + codex 聚焦复核）：
B1 身份铸造 + eligibility 真准入（正确性核心，先行）→ B2 任务入口 + 四门 runner 最小闭环 + 资格 taskset 冻结（x86 批量验证可与后续批并行）→ B3 fa_formal 评分冻结（barrier 替换 + formal B6）→ B4 S2 最小安全链（≈1~2k 行 + CC 联调，最大不确定在容器内联调）→ B5 JIT drain + 最小计时 → B6 关停链 + checkpoint 合同 + crash matrix → B7 eval 运输链本地闭合 → B8 闸门公式/inspector + 证据/验收包从范围反向生成（launch/thresholds/judge 全部重写，不继承未审文件）。粗量级：2~3 周现行节奏。GPU 敏感值/profile 的 owner 冻结（就绪稿 §2.1）必须在 B8 前完成。

## 5. 合并后的待拍板清单（就绪稿 §7 十条 + 本文新增）

就绪稿 §7 的 1~10 全部维持；新增：
11. **D3 规模档位 = 闭环档（纯 Lite，R2E 首训不做）**——本文 §2.1 推荐；
12. D5 评测补充面最小化（首训只内部 held-out）；
13. E7/E10/E2/附录 A 的 miles 修订按 §2.2 条款清单执行（T1 实施、T0 确认修订发生）；
14. GPU pass-rate 预筛的载体（租期尾项 vs 单卡单租）；
15. G 系列由就绪稿 §7 接替的注记确认。


> **2026-09-01 取代注记（修订）**：本文 §2.2/§3 涉及的准入公式与闸门实现形态,06 计划 §6 防御清理**提议取代**（该提议为 Claude 起草+codex 复审,**owner 确认 06 决策包 A 后生效**,在此之前旧口径未被正式否决）;其余（数据线补全 D3 闭环档、E 系迁移条款、批次形状）由 06 收编。"三份已对齐"应理解为 06 之前的中间态,当前处理权威 = 06 草案。