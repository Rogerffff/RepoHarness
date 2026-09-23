# 处置卡：python__mypy-17071

2026-09-23，按 `runs/base_probe_20260922/analysis/TASK_CARD_PROTOCOL.md`；只读，不替用户决定。材料：同目录 `deepseek-v4-pro/cell.md`（DSc）、`qwen3.6-35b-a3b/cell.md`（Q36c）、`qwen3-coder-30b-a3b-instruct/{a1,cell}.md`（Cr）；静态题卡 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch02/results/python__mypy-17071/`（CARD，limited_static_candidate / development_diagnostic）与同批 `cpu_queue.json` 项 `mypy17071-typeguard-unbound`（Q）；运行记录 `base_model_probe_run_20260922.md`（RR）。ADIR = `runs/base_probe_20260922/remote/runs/matrix/attempts/python__mypy-17071/<solver>/<a>`；BASE = `runs/swegym_quality_batch02_20260921_v2/public/python__mypy-17071/base`；x1 = `runs/base_probe_20260922/remote/runs/x1_controls/python__mypy-17071`。另核了 6 份候选 diff、gold、测试补丁、ledger、eval.log、x1 对照与 BASE 源码。

## 1. 一句话现状

S/V/N：DeepSeek 2/2/2、Qwen3.6 2/2/2、Coder 0/2/2 [00]；6/6 评分有效（同一派生镜像 `sha256:92e9a049…`，安装 rc 0，4 项全解析；同镜像 x1 noop 0 / gold 1），无 infra、无误拒，未观测到错误接收。建议：**参考覆盖不足（潜在）**——跨模型比较可原样用；作 RL 奖励前先补"真正未绑定 T"负例（T0）：2 项 P2P 都不经过被修的检查，"关掉检查"静态可得满分。

## 2. 本轮实测回答了题卡的哪些待验项

| 题卡怎么说 | 本轮证据 | 状态 |
| --- | --- | --- |
| Q 第 1 步（唯一优先实验）：补全原例，base 报目标诊断，gold 消除并保留 `str` | 6/6 在 base 复现 `[type-var]`（DS a1 call#15、a2 call#11；Q36 a1 T#24、a2 T#6；Coder a1 调用 5、a2 CALL#3）；gold 同义的 Q36 a1 修后 `Success`、reveal `str`（Q36c L1487–1520、L1669–1672） | 部分：actor 侧已答，grader 侧 CLI 对照未跑 |
| Q 第 2 步、card.md:16、review.md:17/42：未绑定负例；关闭检查可能满分 | 4 条通过候选都保留 `self.fail` 分支（BASE `checker.py:1429–1430`）；关闭型 0/6，负例无人跑 | 未回答（见 §3） |
| card.md:8/16、review.md:18/40：TypeGuard-only 可能被 TypeIs F2P 拒 | 无此类候选：4 条通过候选都遍历两字段，Coder 都没碰 | 未回答；按构造必挂，实跑无新信息，属规范裁定 |
| analysis_before_history.md:58、review.md:14：路线 A（局部 collector）未运行 | DS a1/a2 走路线 A，4 项全过 | 已回答 |
| review.md:34：helper 断言绕过 | 无候选触及 `mypy/test/` | 未回答 |
| card.md:3/14：actor 未验；MWE 缺导入 | `bash_env_v1` 下 uid 54321、py 3.12.4、`mypy` 从 `/testbed` 导入、pytest 8.1.1（`remote/runs/x1_devcheck/python__mypy-17071/bash_env_v1/dev_check_output.txt`）；6/6 自补导入 | 部分：正式 `original` 未验（RR §8.3 #1） |

## 3. 评分能否区分补丁质量

**reward=1 共 4 条：与 gold 同义 4，语义缺口 0。**
- Q36 a1/a2：`typetraverser.visit_callable_type` 末尾补访问两字段，两条逐字节相同（blob `020887f90`），与 gold 只差空行（路线 B）。
- DS a1/a2：`checker.py` 的 `CollectArgTypeVarTypes` 覆盖 `visit_callable_type`，访问两字段并调 `super()`（只差先后），任意嵌套深度生效，对本检查与 gold 等价；范围更窄（其余 5 类 `TypeTraverserVisitor` 子类仍跳过两字段），参考测试不覆盖、未见反例，题卡接受，不计缺口。
- **DS a1 交付质量缺陷（已核）**：`checker.py:1428` 留有 `import sys; print("DEBUG", …, file=sys.stderr)`（DS a1 候选 diff L9）。输入任意 `python -m mypy <file>` → 预期只有诊断 → 实际 stderr 至少多 9 行（每个返回裸 TypeVar 的泛型函数一行，含 typeshed 的 `final`）；评分 eval.log:563–607 共 36 行（DSc 记 35 行，按原件采信 36），不进诊断比较、不罚分。另留一条自己跑失败的用例 `testUnboundTypeVarWithTypeGuardArgument`（非官方文件，未被选中）。PR 不可合并，奖励照样 1。

**reward=0 共 2 条（Coder），误拒 0**：都没改既有源码（a1 7 个草稿，其一 `mypy/debug_traverser.py` 在包内但无人导入；a2 8 个根目录草稿），测的就是 base；F2P 失败与 noop 同形，只多一行 `main:5: error: A function returning TypeVar …`（Coder eval.log:518–542 / 519–543；x1 noop eval.log:508–528）。

**P2P 边界**：`testTypeGuardIsBool`（bool 表示）与 `testTypeIsUnionIn`（收窄）都不含返回裸 TypeVar 的函数；BASE 中断言该诊断的 15 处公开用例（8 个 `.test` 文件）无一在选集。noop 已推出 `str`、只多出该诊断（x1 noop eval.log:511–512），所以把 `check_unbound_return_typevar`（BASE `mypy/checker.py:1422`）改成直接 `return` 或"见到 guard/is 回调就放行"，静态上 4 项全过得 1 分，这 15 处诊断却全部消失；本轮未出现、未实测。

## 4. 环境与接口条件

- actor：原公开镜像 `xingyaoww/sweb.eval.x86_64.python_s_mypy-17071:latest`（无派生）+ `bash_env_v1` + `--harness-out out_of_tree`；无公网、git 已清洗。
- grader：`install_wave1:python__mypy-17071(rebuilt20260922)` → `92e9a049…`（只 COPY 离线 wheels），`pytest -rA -k '<4 个名字>'`；CARD 与 Q 引的是 09-19 的 `65be1535…`。
- 链路 0 infra、0 apply 失败；DS a2、Q36 a2 改的官方 `.test` 按 `official_test_file` 忽略并恢复（attempt.json `touches_tests=[]` 漏判 `test-data/unit/*.test`，聚合读 `projection.ignored_paths`）。
- 接口现象（thinking 不回传 / 被清空、`<|im_end|>` 泄漏、CC 改写参数）见各 cell，未影响分数；DS a2 修后的 `gh`/`curl`/`git log --all` 探测全被挡。

## 5. 对 RL 的含义

- 区分度只在跨模型（4/4 对 0/2），格子内无优势信号；奖励也分不出 DS a1 的残留、路线 A/B 的范围差，（静态）分不出正确修复与关掉检查——后者是最直接的 reward hacking 通道。
- Coder 稳定全 0（n=2）：T=0.7 下同一错误假设（把回调的 `TypeGuard[T]` 当成 `TypeGuardedType`，没跟进自己 grep 出的 `types.py:1802` 字段提示），最后撤回全部源码；两条都撞顶、无未截断对照，不能断言加预算也不会成。
- 预算：5/6 撞 60 回合（仅 Q36 a1 37 回合正常结束）；全轮 17 条撞顶里得 1 分的 3 条全在本题（DS a1/a2、Q36 a2，67 份 attempt.json × 最终 ledger）。补丁都在预算过半前定型，截断非因果；后半程都耗在同一陷阱：自写用例用 `fixtures/tuple.pyi`（无 `TypeError`）+ `raise TypeError`，修复后仍报目标错误（DS a1 24 轮、a2 15 轮、Q36 a2 约 11 轮），DS a1 的 DEBUG 残留即由此截断留下。
- **Q36c 的题目质量线索**（延迟重分析丢嵌套 `type_guard/type_is`）已有运行时证据：DS a1 自写用例里内层 Callable 成了 `def (Any) -> builtins.bool`、收集为 `set()`（DS a1 `transcript.md` L2525），同一补丁在 F2P（`exception.pyi`）里仍是 ``TypeGuard[T`-1]``、收集到 ``{T`-1}``（DS a1 评分 eval.log:571/583）；gold 同义的 Q36 a2 首版用例也仍报目标错误（Q36c T#86）。机制（BASE `semanal.py:867/897/6557–6571`、`typeanal.py:1066–1072`、`types.py:1926`）：函数体首轮有解析不了的名字就整函数延迟，重分析时 `anal_type_guard` 对已写回的 `bool` 返回 None 并覆盖原值。但函数体在全部模块顶层之后才分析（`semanal_main.py:93–94`、`278`），引用后定义的模块级名不触发，要靠未定义名这类本已报错的代码；被延迟函数自身的 `TypeGuard` 也会丢（推断）。因此它是 base 的独立缺陷，与本题正交，不据此判 gold 不完整；DSc / Q36c 建议的"函数体前向引用"复验预计阴性。

## 6. 处置选项（不决定）

- **A 原样保留**（跨模型比较 / 评测）：评分可信、区分稳定；作 RL 奖励时"关检查"捷径仍开着。
- **B 另版本补负例（T0，评分依据变更）**：(i) 把既有公开用例 `check-typevar-unbound.test::testUnboundTypeVar`（未绑定 T、带界 U 及 note、值约束 V）纳入 P2P 与选集；(ii) 新增"回调只含 `TypeGuard[U]`、返回 T"负例（review.md:42），堵"见到 guard 回调就放行"。静态预期 gold 与 4 条通过候选全过、校准候选挂（须实测）；`-k testUnboundTypeVar` 是子串匹配，会带上 DS a1 自加的失败用例（不计分但 rc=1），宜用完整节点 ID。
- **B′ 采用"只修 TypeGuard"窄契约、删 `testTypeIsTypeVarReturn`（T0）**：review.md:18/40 与 4/4 通过候选的自发行为都不支持。
- **B″ 题面补一句"`TypeIs` 回调同理"**（题面变更，T0）：消除规范歧义、不动 oracle，但偏离上游原文。
- **C 仅评测**：B 落地前不进训练池。
- **D 诊断旁路**：`checks/mypy17071.py` 的负例与 stderr 洁净度作奖励外信号。
- **E 淘汰**：无依据。

## 7. 待办（均无需模型）

1. 写 `rh2/experiments/base_probe_20260922/checks/mypy17071.py`，经 `behavior_check.sh` 在 `92e9a049…` 跑：补全原例的 TypeGuard / TypeIs 版；`def f() -> T`、带界 U、值约束 V；回调只含 U、返回 T；两层嵌套回调（应无错）；延迟探针（未定义名 / 后定义的模块级名）；stderr 非诊断行计数。变体：noop、gold、Q36 a1、DS a1/a2、校准 C1"直接 return"（BASE `mypy/checker.py:1423` 文档串后插 `return`；调用点 1162/1168）、可选 C2"任一参数是带 guard/is 的 Callable 就 return"。
2. 用 `rh2/scripts/replay_grade.py`（Q 的 `replay_entry`，镜像改 `92e9a049…`）评 C1/C2，预计 reward 1；据此再定 B；做 B 前同镜像重放 gold、4 条通过候选与 C1/C2。
3. 回填：Q 第 1 步标"actor 侧已答"，CARD / Q 补注 09-22 镜像；RR §8.2 称 Coder"每次验证…归因到循环导入"，按 Cr 更正：验证失败都读对了，循环导入只在 a1 误判一次（调用 40 后回退）。

```json
{"task": "python__mypy-17071", "cells": {"deepseek-v4-pro": "2/2/2", "qwen3-coder-30b-a3b-instruct": "0/2/2", "qwen3.6-35b-a3b": "2/2/2"}, "verdict": "coverage_gap", "gold_equivalent_successes": 4, "semantic_gap_successes": 0, "false_negatives": 0, "p2p_total": 2, "actor_requirements": ["原公开镜像 xingyaoww/sweb.eval.x86_64.python_s_mypy-17071:latest（无 actor 侧派生）", "bash_env_v1 诊断变体（uid 54321、py 3.12.4、mypy 从 /testbed 导入、pytest 8.1.1）；正式链 original 未验（RR §8.3 #1，A 线接缝）", "--harness-out out_of_tree；无公网、git 已清洗；本题无需安装", "grader：install_wave1:python__mypy-17071(rebuilt20260922) → sha256:92e9a049…（只 COPY 离线 wheels），pytest -rA -k 四项；CARD/Q 仍引 09-19 的 65be1535…"], "disposition_options": ["A 原样保留（跨模型比较/评测）；作 RL 奖励时关检查捷径仍开着", "B 另版本补负例：既有 check-typevar-unbound.test::testUnboundTypeVar 入 P2P 与执行选集 + 新增'回调只含 TypeGuard[U]、返回 T'负例（T0）", "B′ 窄契约：删 testTypeIsTypeVarReturn（T0；review.md 与 4/4 通过候选的自发行为都不支持）", "B″ 题面补'TypeIs 回调同理'（题面变更，T0）", "C 仅评测，B 落地前不进训练池", "D 诊断旁路 checks/mypy17071.py（负例 + stderr 洁净度）", "E 淘汰（无依据）"], "t0_items": ["B：扩 P2P/执行选集并新增未绑定 TypeVar 负例（评分依据变更）", "B′：删除 TypeIs F2P（评分依据变更）", "B″：题面变更（训练样本内容）"], "min_followup_experiments": ["写 checks/mypy17071.py，经 behavior_check.sh 在 92e9a049… 跑：原例 TypeGuard/TypeIs、f()->T/带界 U/值约束 V、回调只含 U 返回 T、两层嵌套回调、延迟探针（未定义名/后定义模块级名）、stderr 非诊断行；变体 noop/gold/Q36 a1/DS a1/DS a2/C1 直接 return（BASE mypy/checker.py:1423 文档串后插 return）/可选 C2 见 guard 回调即 return", "用 replay_grade.py 在 92e9a049… 上对 C1/C2 做 RH2 评分（静态预计 reward 1），据此再定 B；做 B 前同镜像重放 gold + 4 条通过候选 + C1/C2", "回填 Q 第 1 步（actor 侧已答）与 CARD/Q 的 grader 镜像注记；按 Cr 更正 RR §8.2 的 Coder 描述"], "confidence": "high"}
```
