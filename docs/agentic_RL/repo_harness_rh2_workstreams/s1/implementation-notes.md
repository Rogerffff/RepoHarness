# S1 implementation-notes（行车记录）

执行计划：`../03-s1-execution-plan.md`。三节制，发现即记。

## Decisions

- [S1-0, 2026-07-09] slime 镜像 pin 定为 `slimerl/slime@sha256:a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75`（U-H 验证通过的那个），F6 的双 pin 之一。远端保留镜像 + ~57GB HF 缓存供 S1-6/7 复用。
- [S1-1] **七维事实的具体映射**：§16.1 的 8 条硬门槛合并为 7 维——条 5（hidden verifier 未泄漏）与条 7（权限/篡改检查）合并为 `security_and_leakage`（同属安全面、同一批 finding 供事实），staleness 保留为独立一维（事实来自 BackendHandshake）。映射表写在 eligibility.py 模块 docstring 与 guide §7.1。
- [S1-1] **security 维失败强制 audit_only_or_rejected**（比"任一维失败即非 online"更严）：executed 级泄漏内容已进模型上下文，作 SFT/离线候选同样污染数据。schema 层直接锁死，不留给 gate 自由裁量。attempted_blocked（拦截成功）不扣该维，且 AntiCheatFinding 声明 attempted 必须回链 AntiHackEvent（防 executed 谎报成 attempted）。
- [S1-1] **infra_failure 与 reward 双重互锁**：GradingReport（failed_to_grade ⇒ reward=None + infra_failure_detail 必填）与 RewardFacts（scope=none ⇒ raw_reward=None）两处都拒收"infra 伪装成 reward=0"，单测各有点名用例。
- [S1-1] **引擎 routing 行数约定编进校验器**（承接 S1-0 New-Unknown）：RoutingTensorRef.alignment 必填，sglang=prompt-1+gen、vllm=prompt+gen，行数差一即拒收；dense 必须显式 `not_applicable_dense_model` 且与 tensor 字段互斥。BranchProjection 再互检 tape 计数与分支计数。top-p 侧同构：top_p<1.0 缺 tape 不可表示（stock SGLang 静默降级形态被 schema 挡死），offsets_len 必须 = response+1。
- [S1-1] **capture 层防静默降级**：GenerationCaptureRecord 里"请求了 tape（return_top_p_token_ids/return_routed_experts）但响应没带"时 capture_status 禁止为 complete，只能如实标 partial+mismatch（可表示、但 gate 会挡）。这是 U-H 回归的日常探测点。
- [S1-1] **marker 扫描继承旧 compact-substring 语义并接受误报**（fail-closed）："latest_patches" 紧凑后含 "testpatch" 会命中——宁误报（人工豁免）不漏报（污染训练数据）。已用单测把该取舍钉成回归锚点。名单 = A6 六项 + 旧 L4 evaluator-only + 旧 batch 私有 key，共 23 项。
- [S1-1] **runtime-private 审计资产默认豁免 marker 扫描**：grading_report / 两类 finding / anti_hack_event 的内容天然要描述 test_patch 等私有名词，`inspect-rh2-artifact` 对它们默认豁免（--force-marker-scan 可强制）；public projection 一侧的扫描（S1-5）不看豁免表。
- [S1-1] 全部契约对象 `frozen=True`（evidence 构造后不可变）+ 顶层对象带 `schema_id` 判别字段 + `SCHEMA_REGISTRY`（14 个顶层 schema），CLI 按 schema_id 选模型。"报告自证"字段（EligibilityReport.facts_digest、derived_view_*、BackendHandshake.staleness_within_threshold）一律由校验器重算互检，finalize() 便捷构造器不构成旁路。
- [S1-2] **version 字段归 private bundle**：A6 的 public 名单（题面/repo/base_commit/镜像 digest/允许工具/公开提示）没有 version；它实际是官方 MAP_REPO_TO_PARSER / MAP_REPO_VERSION_TO_SPECS 的 parser 配置键，按 fail-closed 原则划进 PrivateGradingBundle（模型解题不需要它）。同理 S0-7 挂在 Task 上的 fail_to_pass/pass_to_pass/test_cmd 全部移除——Task 会随 trace dump 序列化，评分材料只准经 `_pairs()` 的 private 半区取用。
- [S1-2] **frozen_v1 防漂移校验是默认加载行为**：`load_bundle_pairs()` 默认逐题重算题面 sha256/镜像 digest/两 bundle digest 与账本比对，不符即 FrozenRecordMismatch；薄壳 taskset 继承该默认。账本生成确定性（无运行期时间戳），重新生成题目数据后必须重跑 `python -m repoharness2.envpack.freeze`，否则加载当场炸——把"题目漂移"从静默事故变成显式动作。
- [S1-2] **A7 接口分工钉死**：scoring.grading_outcome_fields 只产出 resolved/tests_failed/patch_apply_failed 三态字段组（计数口径 = 官方 report 的 success/failure 桶，与 resolution 判定同口径），**infra_failure 永不由 parser 层产出**——parser 只看得见日志；容器级故障归 S1-4 manager 依据自己的证据改判。单测钉死"三态字段组均能构造出通过 GradingReport fail-closed 校验的报告"。
- [S1-2] **紧凑 marker 匹配实测 8 题真实题面 + 公开提示 0 误报**（S1-1 New-Unknown 关闭）：value 扫描无需降级为非紧凑匹配，扫描语义保持原样。

## Deviations

- [S1-0, 2026-07-09] 远端机器基础设施修复：Docker 登记了 nvidia runtime 但缺 NVIDIA Container Toolkit，装配 nvidia-container-toolkit 1.19.1-1 后 GPU 容器可用（属环境修复非计划偏离，记录备查——新租机器首日 checklist 应加这一条检查）。
- [S1-1] **rh2 packaging 从 `package = false` 翻转为可安装包**（pyproject 加 hatchling build + `[project.scripts]`）：一是 `inspect-rh2-artifact` 要成为真实命令（S1-9 的 inspect-rh2-s1 沿用同模式），二是 tests/contracts 与后续 governance/adapters 代码要能 `import repoharness2`。已验证 S0 的 17 个 contract_verifiers 用例不受影响（全套 222 用例绿）。
- [S1-1] WorkspaceHandle 只禁"rollout 工作区挂 private bundle"，**未强制** grading 工作区必须挂 private bundle：评分资产也可能走注入而非挂载，等 S1-4 实现定型后再决定是否收紧。
- [S1-1] 执行计划 §5 列的 `contracts_review.md`（设计要点 + fail-closed 单测清单）本次未单独成文：设计要点已完整落在 `contracts_object_guide.md`（A8 交付物）与本 notes，单测清单即 `rh2/tests/contracts/` 目录本身。若 S1-9 验收仍需要独立文件，可从这两处直接汇编。
- [S1-2] **题目数据文件迁移**：`taskset/data/swe_smoke_tasks.json` → `envpack/data/swe_smoke_tasks.json`（内容零改动，字节流 sha256:190fcde8c35e… 记入 frozen_v1 meta）。计划原文把"题目数据 + digest"划给库层，taskset 只留薄壳；`experiments/s0_swe_smoke_prep.py` 输出路径同步更新。s0 报告里引用的旧路径不回改（历史事实）。
- [S1-2] **远程整链回归递延到 S1-7a 前**：2026-07-07 两次 `ssh -p 19451 root@99.148.65.9` 均 Connection refused、ping 100% 丢包（vast 实例关机，用户自管电源）。本机层回归（parser 对 428KB 真实日志 + bundle/薄壳逻辑）已全绿，不阻塞后续任务；递延动作与判据记录在 `envpack_freeze_v1.md` §5（2 题建议 django-11099 + requests-2931，reward 数值受 deepseek 采样影响不作硬判据）。

## New-Unknowns

- [S1-0 核验, 2026-07-09] **引擎间 routing 行数约定不同（喂 S1-3）**：SGLang 路由行 = prompt_len - 1 + generated_len（本次 15-1+16=30，S0-6 的 [20,48,8] 同律）；vLLM（S0-5 probe）= prompt_len + generated_len（13+8=21）。TrajectoryProjection 的 tape 解码唯一点必须按引擎显式编码对齐约定（RoutingTensorRef.alignment 语义），不能假设两引擎同构。
- [S1 计划定稿, 2026-07-09] 两复核线程建议 A1~A10/B1/C1~C3 全部采纳（正式化为 s1/s1_supplementary_clauses.md，验收级效力）；F2~F6 定案，F5 按用户收紧版（并发 4/队列 8/可配置/实测后升）；F4 升四段式（B1 补 GPU pass-rate 预筛归 S2 末/S3-0）；uh_probe_result.json 已生成（A10）；8 题冻结状态已同步 swe_smoke_report.md（C2）。
- [S1-1] **多轮合并 tape 的行数守恒待实证（喂 S1-3）**：slime 把多轮 routing tape 合并为 Sample 级 rows = len(tokens)-1；单轮下与 RoutingTensorRef 的 sglang 公式（prompt-1+gen）同律，但多轮 + REALIGN/FORK 场景下"分支级 prompt/response 计数套同一公式"是否恒成立，需要 S1-3 用真实多轮 fixture 验证；不成立就要在投影层按轮拆 tape 再拼。
- [S1-1] **组信号与动态采样的交互（喂 S1-6）**：E2 动态采样会过滤零方差组——整组被过滤时 GroupSignal 怎么表示（delivered=0 + degraded=expected？还是不产生握手记录？）尚无定案，S1-6 mock 单测时定下来并回写契约（可能需要给 GroupSignal 加 filtered_by_dynamic_sampling 计数）。
- [S1-1] **marker 紧凑匹配在真实题面上的误报率未知（喂 S1-2）**：8 题 public bundle 过扫描时统计误报数；若真实题面频繁踩中（如 "latest_patches" 形态），再决定是否为 value 扫描单独降级为非紧凑匹配（key 扫描保持紧凑）。**[已关闭于 S1-2]** 实测 0 误报，扫描语义不动（见 Decisions）。
- [S1-2] **bundle 两 schema 未进 SCHEMA_REGISTRY（喂 S1-9）**：PublicTaskBundle/PrivateGradingBundle 带 schema_id（rh2.public_task_bundle.v1 / rh2.private_grading_bundle.v1）但没注册进 contracts.SCHEMA_REGISTRY——注册会让 contracts 反向 import envpack（依赖方向必须是 envpack -> contracts）。`inspect-rh2-s1`（S1-9）若要按 schema_id 校验 bundle 文件，应在 CLI 层聚合两处 registry，或给 envpack 配独立 registry；届时一并决定 private bundle 文件是否加入 marker 扫描豁免表（它天然含 test_patch 等私有名词，同 grading_report 处理）。
- [S1-2] **S1-4 评分隔离升级时的日志形态假设（喂 S1-4）**：库层 parse_eval_log 假设输入是 stdout+stderr 合并单流（`2>&1`）；manager 在 fresh sandbox 重放时必须保持同形态（官方 harness 以合并流写 test_output.txt），否则 django/sympy 的标记切段会失败。已写进 scoring.py docstring，此处留提醒。
