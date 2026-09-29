# 处置卡：iterative__dvc-6954（基座探针 2026-09-22 第二轮，7 条尝试）

2026-09-23，Claude（Opus 5.5），按 `TASK_CARD_PROTOCOL.md` 编写；只读分析，不替用户做决定。

- **依据**：本目录 a1.md 与三份 cell.md（均为非严格盲审）；运行记录 §7.5b / §7.6 / §8 / §9；静态题卡四件、队列项；B3 验收 `batch03_dvc_review.md:9`、`morning_cpu_shortlist.md:13`。
- **另核原件**：7 份 attempt / ledger、6 份候选与 gold、x1 对照、Coder a2 transcript、base 源码。
- **本机 helper 重放**：CPython 3.9.6 + 公开导出的真实 base `_py.py`（blob `4911bf31`，与候选 diff 头一致）；gold 与 6 个源码段用 `patch -p1` 全部干净应用。脚本在会话 scratchpad，未入库。

## 1. 一句话现状

S/V/N：DeepSeek 2/2/3 [·11]（a1 为上游流中断，记 infra、不进 V；a3 是同条件重跑），Coder 2/2/2，Qwen3.6 2/2/2，合计 6/6/7。无争议，无误拒。六条通过候选都在 `_get_ast_value` 里递归处理 `ast.UnaryOp`，在题面需求、13 项参考与更新路径上与 gold（`ast.literal_eval`）同义。建议**保留**：本题已饱和、无区分度，宜作校准 / 对照题；队列项改为"部分已由轨迹实跑"。

## 2. 本轮实测回答了题卡的哪些待验项

| 题卡 / 队列 | 本轮证据 | 状态 |
| --- | --- | --- |
| `-1` repro 运行 stage，lock 记值（card:15；review:39；队列 steps[1]） | 修复后 5/6 跑通题面 repro（DS a2 #56、a3 #39，Coder a2 #34，Q36 a1 #51–56、a2 #65–68），Coder a1 没用 CLI。Q36 两条 `cat dvc.lock` 看到 `my_int: -1`。修复前的 CLI 红灯只有 Coder a2（#11） | 已回答 |
| 不变跳过 | 只有 Coder a2（#37、#42 `didn't change, skipping`） | 已回答（1 条） |
| 改值重跑（lock 已记 -1 → 改成 -2） | 规定方向无人做。**更正**：Coder a2 修复前的正数对照（#14）留下 `my_int: 1` 的 lock，修复后改回 -1（#33）再 repro，stage 重跑、lock 更新（#34），属反方向的顺带验证。DS a2 的 `modify_py` -1→-2（#58）只走写回。a1.md、三份 cell 与 §8.4 的"无人改值重跑"只对规定方向成立 | 部分 |
| `-0.5` 走 CLI / lock | 无人跟踪浮点参数（Coder a2 的 `-3.14` 是未跟踪变量，#36–39）。helper 层多条亲验，重放中 6/6 = gold（含 `-0.5→-0.25` 更新） | CLI 未回答；helper 已回答 |
| `dvc run`（public_read:13） | 0/6 使用；备好的检查脚本里也没有 | 未回答（与 repro 共用 `get_hash`） |
| int-only 修复会过参考而漏负 float（card:15） | 0/6 出现；反例补丁未构造、未评分 | 自然出现率 0/6；反例未执行 |
| actor 条件（card:3；队列 steps[0]） | `bash_env_v1` 下：testbed 3.9.19、导入 `/testbed/dvc`、pytest 6.2.5，工作区与 /tmp 可写（x1_devcheck）。原镜像 pathspec 0.9.0，CLI 正常。`tests/func/params` 因 pygit2 缺 `GIT_OBJ_COMMIT` 跑不了（Coder a1 L1634、Q36 a1 L2291）。正式链 `original` 仍缺解释器（§8.3 #1） | 已回答（限诊断条件） |
| "不得改测试"是否进 prompt（public_read:24–27） | 没进。5/6 往非官方测试文件加了用例；官方测试文件 base 中不存在，`ignored_paths` 全空 | 已回答 |

## 3. 评分能否区分补丁质量

reward=1 共 6 条：题面范围内与 gold 同义 6 条，语义缺口 0 条。有效 reward=0 共 0 条，误拒 0 条（a1 评的是 noop）。参考是新文件 `test_python.py` 的 1 F2P（`-1`）加 12 P2P，全查 `parse_py` 返回值，不覆盖 CLI、lock、负 float、容器 / 类中的负数和更新路径；这些位置 6/6 与 gold 一致。参考之外的差异（重放实测）：

| 输入 | gold | DS a2 | DS a3 / Coder a1 / Q36 a1 | Coder a2 | Q36 a2 |
| --- | --- | --- | --- | --- | --- |
| `x = -'a'`、`-None`、`[1, -'a']` | 跳过 | 跳过 | TypeError | TypeError | TypeError |
| 同文件 `my_int = -1` + `bad = -'a'` | `{'my_int': -1}` | 同 gold | 整个文件 TypeError | 同左 | 同左 |
| `x = +'a'`、`+None` | 跳过 | `'a'` / None | `'a'` / None | `'a'` / None | TypeError |
| `--1`、`-+2`、`-True` | 跳过 | 1 / -2 / -1 | 同 | 同 | 同 |
| `b'b'`、`...` ／ `set()`、`1+2j` | 收／收 | 跳过／跳过 | 跳过／跳过 | 收／跳过 | 收／跳过 |

- 五条候选抛 TypeError 时，同文件的合法参数也一并丢失。读码推断（未实跑）：`_read` 只转换 `ParseError`（param.py:91–102），`dvc repro` 下该异常被 `reproduce.py:212–213` 包成 `ReproductionError`，rc 255，原因是 `bad operand type` 而非缺参；cell 里"未处理异常退出"的说法不准确。这类输入在运行时本就报错，参考不覆盖，属**低危**。若把 P2P `CONSTRUCTOR/SUM` 的"不支持就跳过"视为公开约定，严格口径下是 5 条缺口，由用户定。
- **更正**：DS cell 说 a2"在非数值 operand 上与 gold 完全一致"，只对负号成立（`+'a'` 时 a2 得 `'a'`）。Q36 a2 在 `+'a'` 上也抛 TypeError，三份 cell 都没测到。
- 奖励看不见的卫生差：
  - Coder a2 在 `/testbed` 执行 `dvc init -f`，14 个残留文件（18190 / 20004 B）进了候选：**清空仓库自带的 `.dvc/config`**（删掉 `remote "dvc"`），`.gitignore` 多了 `/b.txt`；交付说明却称 "minimal, targeted"。
  - Coder a1 在仓库根留下 5 个草稿，占 6638 / 7413 B ≈ 90%。**更正** cell 的 88%：它误用了 a2 的 877 B 源码段，a1 实为 775 B。

## 4. 环境与接口条件

**actor**：用原公开镜像（id `e89b7320…`，digest `1cf3894f…`），无需派生；`bash_env_v1`；`--harness-out out_of_tree`。需解析 git 修订的命令走 pygit2 后端：`tests/func/params` 已实证失败；读码推断，提交后的 `params diff`、`exp` 同样失败，无提交时 `params diff` 直接返回 `{}`（diff.py:7–8）。所以 actor 侧可验的公开链只有 init / stage add / run / repro / status / lock。

**grader**：`dvc_install_v1c` 配方于 09-22 重建为 `local_build:sha256:ba0e5cb5…`；x1_controls 中 noop 0、gold 1；6 条候选安装 rc=0、`git_apply` 成功。

**链路**：a1 在第 11 次响应首字节后遇到 `ClientPayloadError`，CC 仍记 success、交出空补丁，按 noop 评为 0。已修网关、改记 infra、a3 重跑得 1；全量 SSE 仅此一份缺完结事件（§9.1），干净 EOF 缺完结事件的情形仍未覆盖（§9.2.5）。其余接口现象已回交 A 线，未影响分数。

## 5. 对 RL 的含义

三款组内优势都是 0；回合 24–51 / 60、用时 37–97 s，与预算无关，本题已饱和。全 1 组里唯一可能的 0 是 a1 这类运输噪声。静态估算：只补数值负数与更新路径断言，0/6 翻转；补"非数值 operand 应跳过"，5/6 翻成 0，但这类输入运行时本就非法，公开依据弱（public_read §2）。

## 6. 处置选项（不决定）

- **A 原样保留**，作校准 / 对照题：可靠，但占采样预算却不产生梯度。
- **B1 另版本补参考（T0）**：加负 float、容器 / 类 / self 中的负数、`parse_py_for_update` 往返断言。可关闭 int-only 风险，但本轮 0/6 翻转，宜先做 E3。
- **B2 另版本补"非数值 operand 跳过、同文件其他参数可读"断言（T0）**：会让 5/6 翻为 0、产生区分度，但依据弱，易诱导防御性 try/except。**不建议**，除非用户认定这是公开约定。
- **C 仅评测**：作饱和指示题，同时回归 actor 入口。
- **D 诊断旁路（非 T0）**：跑 E1 关闭队列项，并在题卡登记 pygit2 限制。
- **E 跨题候选卫生诊断**：给改动已跟踪非源码文件或在仓库根留草稿的候选打标记；若计入 reward，则属 T0。
- **F 淘汰**：无依据。题面无需修订。

## 7. 待办（均无需模型）

- **E1**：在原公开镜像上跑修订后的 `checks/dvc6954.py`，变体取 noop / gold / DS a2 / DS a3 / Coder a2 / Q36 a2，覆盖四种行为。脚本需改：
  1. 删掉 `params diff`（没有提交时恒为 `{}`，提交后又撞上 pygit2），改为改值后跑 `dvc status`。
  2. 加 `-0.5→-0.25` 的改值重跑，并把 `nested.v` 纳入跟踪（现在只写入、不跟踪）。
  3. helper 段逐输入调用、用 `repr` 输出（现在只调用一次，一行 TypeError 会掩盖整组；`set` / `bytes` 不能 JSON 化），补 `-'a'`、`-None`、`+'a'` 与同文件坏行。
  4. 加一次参数文件含 `bad = -'a'` 的 CLI repro，记录 rc 与报错。
  5. 加一步 `dvc run`。
  6. docstring 里的 `params.yaml` 应为 `params.py`。

  预期：数值链上 gold 与各候选一致，base 在 repro_1 报缺参。
- **E2**（文书）：回填题卡开发条件表、队列项状态，以及运行记录 §8.4 本题一行（不变跳过 1 条；改值重跑仅 1→-1 一次；`-0.5` 走 CLI 0 条）。
- **E3**（可选，为 B1 取证）：构造 int-only 补丁跑 RH2 官方 13 项。静态预测它得 1 分，而 `-0.5` 被丢。

## 8. 证据指针

- 分数：各 `grading/ledger.jsonl` 第 1 行；对照 `remote/runs/x1_controls/iterative__dvc-6954/{noop,gold}/ledger.jsonl`。
- 候选 / gold：各 `candidate/*.diff`（源码段 718/601/775/877/715/943 B）；`remote/gold/*.gold.patch`；Coder a2 diff L19–27（`.dvc/config`）、L598–618（lock）。
- 工作流：Coder a2 transcript L182–240、L1049–1219；Q36 a1 L1530–1552、a2 L1491–1511。
- actor：`remote/runs/x1_devcheck/iterative__dvc-6954/bash_env_v1/`；`remote/derived_images_x1.json:62–71`。
- infra：`remote/gateway/deepseek/bp22-deepseek-v4-pro-dvc-6954-a1/responses.jsonl` 第 11 行。
- base 源码：`runs/swegym_quality_batch03_20260921_v1/public/iterative__dvc-6954/base/dvc/`（`utils/serialize/_py.py:116–119,172–181`、`dependency/param.py:91–102`、`repo/params/diff.py:7–8`、`repo/reproduce.py:212–213`、`scm/git/__init__.py:289–290`）。

```json
{"task": "iterative__dvc-6954", "cells": {"deepseek-v4-pro": "2/2/3", "qwen3-coder-30b-a3b-instruct": "2/2/2", "qwen3.6-35b-a3b": "2/2/2"}, "verdict": "keep", "gold_equivalent_successes": 6, "semantic_gap_successes": 0, "false_negatives": 0, "p2p_total": 12, "actor_requirements": ["bash_env_v1：agent 可读的 BASH_ENV 副本并注入 CC 进程（正式链 original 拿不到 testbed 解释器，A 线接缝）", "原公开镜像即可（id e89b7320…，pathspec 0.9.0，dvc CLI 正常），无需 actor 派生；tests/func/params 以及需要解析 git 修订的命令（提交后的 params diff、exp）因 pygit2 缺 GIT_OBJ_COMMIT 不可用（后两者为读码推断）", "--harness-out out_of_tree", "grader：dvc_install_v1c 配方重建 local_build:sha256:ba0e5cb5…，pytest -rA tests/unit/utils/serialize/test_python.py，noop 0 / gold 1"], "disposition_options": ["A 原样保留，作饱和校准/对照题（无区分度）", "B1 另版本补负 float/容器/类/self/更新往返断言（T0；本轮 0/6 翻转）", "B2 另版本补非数值 operand 跳过、同文件其他参数可读断言（T0；5/6 翻为 0，依据弱，不建议）", "C 仅评测（饱和指示 + actor 入口回归）", "D 诊断旁路：跑 E1 关闭队列项，题卡登记 pygit2 限制（非 T0）", "E 跨题候选卫生诊断：标记改动已跟踪非源码文件与根目录草稿（计入 reward 则 T0）", "F 淘汰（无依据）"], "t0_items": ["B1：参考新增负 float/容器/类/self/parse_py_for_update 往返断言", "B2：参考新增非数值 operand 跳过与同文件其他参数可读断言", "E 若把候选卫生计入 reward（训练语义变更）"], "min_followup_experiments": ["E1：原公开镜像上跑修订后的 checks/dvc6954.py，变体 noop/gold/DS a2/DS a3/Coder a2/Q36 a2；删 params diff（无提交恒为 {}，提交后撞 pygit2）改为改值后跑 dvc status；加 -0.5→-0.25 改值重跑并跟踪 nested.v；helper 逐输入调用、用 repr，补 -'a'/-None/+'a'/同文件坏行；加含坏行的 CLI repro（记 rc 与报错）与一步 dvc run", "E2：回填静态题卡开发条件表、队列项状态与运行记录 §8.4 本题一行", "E3（可选）：int-only 补丁跑 RH2 官方 13 项，为 B1 取得已执行的误收证据"], "confidence": "high"}
```
