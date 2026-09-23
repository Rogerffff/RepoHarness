# 处置卡：conan-io__conan-15422

2026-09-23。并排材料：同目录 `deepseek-v4-pro/{a1,cell}.md`、`qwen3-coder-30b-a3b-instruct/{a1,cell}.md`、`qwen3.6-35b-a3b/cell.md`；确定性对照 `runs/base_probe_20260922/remote/runs/conan15422_fp_check/`（FP）；静态题卡 `docs/…/quality_batch01_20260921/results/conan-io__conan-15422/`（CARD）；运行记录 `base_model_probe_run_20260922.md` §7.5d / §8.2 / §8.4 / §9.2.3（RR）。本卡不重做逐条审查，只补核了 12 条候选的 `presets.py` blob（各 diff 的 `index` 行）、12 份 `grading/ledger.jsonl`、gold、测试补丁与 base 源码。

## 1. 一句话现状

三款 S/V/N 均 4/4/4（12/12 官方 1 分：F2P 1/1、P2P 0 fail/40、`RESOLVED_FULL`，0 infra、0 截断）；题面无争议，但唯一 F2P 只测"显式 42 + 单配置 + 首次生成"，12 条里 5 条与 gold 语义不同仍满分。建议：**保留但标"参考覆盖不足"**；当前形态对三款都无区分度；补断言属 T0。

## 2. 本轮回答了题卡的哪些待验项

| 题卡怎么说 | 本轮证据 | 状态 |
| --- | --- | --- |
| CARD card.md L13、review.md 实验 2：只在显式配置时写 jobs 的部分实现"静态上可能满分"，需 grader 负对照 | 模型自然产出两条：Coder a1（FP `coder_a1/out.txt` no_conf=null，官方 1）、Coder a3（容器内自测 `Has 'jobs' field: False`，Coder cell §2 a3 / E17） | 已回答，升级为实测错误接收 |
| card.md L9：多配置追加条目的 jobs 未测 | DeepSeek a1 FP `jobs42_ninja_multi`=null（gold 42）；Coder a3 自测 VS2019 追加分支 jobs=8（Coder cell E18）。review.md 实验 1 的 Release=2→Debug=7→Debug=3 替换序列未跑 | 部分 |
| card.md L17、`cpu_queue.json` `actor-conan15422`：真实 actor 查解释器/包来源，比较显式 2/7、未配置 | 12 条在 `bash_env_v1` 下均从 `/testbed` 导入并生成；未配置：gold / DS a1 FP=2，DS a3、Coder a2、Q36 a3/a4 自测 2；显式值自测 4/8/10/16（非队列的 2/7）。正式 `original` 变体 import 失败（RR §8.3 #1），队列项"薄入口未实现"仍成立 | 部分：诊断变体已答，正式入口未答 |
| card.md L13：无条件跨生成器写 jobs 与 NMake/Visual 并行策略的兼容性待核 | DS a4 复制 `cmake.py:18` 的门（Makefiles/Ninja 写、NMake/VS/Xcode 不写），msvc 自测无 jobs（DS cell §2 a4）；无真实 MSBuild 消费 | 未回答，但已有需裁决的真实候选 |
| card.md L17：0/负数语义 | 10 条 `if jobs` 型在 jobs=0 时省略键（仅 Coder a3 `is not None`、Q36 a2 无条件写 0，同 gold）；未实跑，无公开依据 | 未回答 |
| public_read C5：cmake 3.23 门槛 | 镜像 cmake 3.22.1；跑到 functional 测试的尝试均 ERROR，模型均正确判为环境 | 已回答（已知，非阻断） |
| card.md："CPU 默认随机器变化即不稳定"不成立 | FP 宿主 30 核、容器配额 2，`build_jobs` 返 2；Q36 a4 用 `multiprocessing.cpu_count()` 断言先失败再放宽 | 已回答：默认断言须比对同进程 `build_jobs`，不硬编码 |

## 3. 评分能否区分补丁质量

12 条 reward=1 分四种缺口 + 同义：

| 范围 | 候选 | 输入 → gold 预期 / 实际 | 证据等级 |
| --- | --- | --- | --- |
| 漏未配置默认 | Coder a1、a3 | `conan install . -g CMakeToolchain`（无 conf）→ `build_jobs()`（容器 2）/ 无键 | a1 FP 实测；a3 自测 + 自写 `"jobs" not in` 单测 |
| 漏多配置 | DeepSeek a1 | `-c tools.build:jobs=42 -c tools.cmake.cmaketoolchain:generator="Ninja Multi-Config"` → 42 / 无键（`if not multiconfig`） | FP 实测 |
| schema 抬升 | Qwen3.6 a2 | 任意 install → `version` 3、`cmakeMinimumRequired` 3.15 / 4、3.25（jobs 本身同 gold）；CMake 3.23/3.24 按文档语义拒读，源码 `presets.py:168` 自称面向 ≥3.23 | 静态（diff L17–29），未实跑 cmake |
| 生成器门 | DeepSeek a4 | `-s os=Windows -s compiler=msvc … -c tools.build:jobs=10` → 10 / 无键；Makefiles/Ninja（含 Ninja Multi-Config）同 gold | 容器内自测 msvc；CARD 记生成器范围"未唯一规定"（public_read L18–19、L27）→ 待裁决 gold 分歧，不计假阳性 |
| ≈gold | DS a2、a3；Coder a2、a4；Q36 a1、a3、a4（7 条、5 种 blob；DS a3 = Q36 a1 = Q36 a4 逐字节同 `cc2d60dc9`） | 仅 jobs=0 时省略键 | 未配置：DS a3、Coder a2、Q36 a3/a4 实测 2；多配置：静态同函数 |

疑似假阳性 4（实测 2、自测 1、静态 1）+ 待裁决 1；误拒 0（无 reward=0）。P2P 40 项只保护结构（数量、名称、configuration、msvc 元数据），无一断言 jobs / version / cmakeMinimumRequired。报告矛盾：DS cell 与 Q36 cell 各称自己发现的是"第三种"缺口，本卡并为四种；RR §7.5d/§8.4 写"两种"是 cell 报告前的口径，应更新。DS a3 报告称 buildPresets.jobs "3.23 起才生效"（cmake 3.22.1 手工实验）、Q36 cell 称自 schema v2 / CMake 3.20 即存在：采信后者（与 CMake 3.20 引入 buildPresets 一致；审查者知识，未联网核），DS a3 的实验未复核。

## 4. 环境与接口条件

actor：原镜像（无派生）+ `bash_env_v1`（诊断变体；正式 `original` 下 import 失败，RR §8.3 #1）；a1/a2 in_tree、a3/a4 out_of_tree，harness 位置未影响本题；cmake 3.22.1 < 3.23 使 functional 测试 ERROR（已知）；2 CPU cgroup 配额；无公网。grader：原镜像，`pytest -n0 -rA conans/test/integration/toolchains/cmake/test_cmaketoolchain.py`，官方测试文件从 base 恢复后打测试补丁；DS a2/a3/a4 改官方测试文件被按 `official_test_file` 忽略，其余候选夹带的非官方测试与草稿（Coder a3 三个仓库根文件）纳入投影但不执行。链路 0 infra；接口观察（DS thinking 不回传、`<|im_end|>` 泄漏、CC 参数改写、Q36 thinking 清空、Coder 工具面绕路、DS a2 5 次 git 探测落空、DS a3 沙箱 `git stash`）均未影响补丁与分数。

## 5. 对 RL 的含义

三款组内优势为零；奖励把 5 条缺口候选与 7 条 ≈gold 同等强化，并放过"测试随实现走"样本（DS a4、Coder a3 把与 gold 相反的行为写成断言，评分不跑但会进轨迹）。预算无关：53–155 s、27–45 回合，远离 60 上限。稳定全 1 说明题目对三款都太易；静态预计补断言后 (i) 使 Coder a1/a3 为 0、(ii) 使 DS a1 为 0、(iii) 使 Q36 a2 为 0，12 条变 8/12，三款各出现混合格子。

## 6. 处置选项（不决定）

- A 原样保留，标"参考覆盖不足"：不动评分依据；训练无梯度且默认放行缺口。
- B 另版本修订参考测试（**T0**）：补 (i) 无 conf 时 `buildPresets[0]["jobs"] == build_jobs(conanfile)`（同进程取值，不硬编码；依据 `cpu.py:8–28`、`conf.py:55`）；(ii) Ninja Multi-Config + 显式 42 → 42（依据 `cmake.py:18` 对含 "Ninja" 生成器加 `-j`）；(iii) 守护 `version == 3`、`cmakeMinimumRequired == 3.15.0`（依据 base 既有值与 ≥3.23 提示）；VS/Xcode/NMake 不断言。利：4 条缺口可分；弊：(ii) 的"多配置也应写"由仓库惯例推出而非题面明示，须按 Codex §9.2.3 写明依据。
- B′ 题面补充"未配置采用 Conan CPU 默认；Conan 生成的每个 build preset 都带 jobs"再配 B（**T0**，题面变更）：争议最小，改动最大。
- C 仅评测：留作回归校准；当前无区分度，评测价值低。
- D 诊断旁路：用 `checks/conan15422.py` 行为矩阵作奖励外信号；不改 oracle；不进训练。
- E 淘汰：材料干净、无环境阻断，浪费。

## 7. 待办（无需模型，CPU / grader 可做）

1. `behavior_check.sh` + `rh2/experiments/base_probe_20260922/checks/conan15422.py`（no_conf / jobs42_single / jobs42_ninja_multi / jobs10_msvc_vs2022，各附 schema 行）对 12 条候选 + gold + noop 跑一遍：把 DS a4 msvc、Q36 a2 schema、Coder a3 默认从自测/静态升级为同脚本实测。
2. 核 CMake `cmake-presets(7)`：`buildPresets.jobs` 引入版本、`cmakeMinimumRequired` 语义、`jobs` 在 MSBuild/Xcode 的映射（Codex §9.2.3 引 3.27 文档）；有 CMake ≥3.23 时对 Q36 a2 生成文件 `cmake --preset` 实测拒读。
3. review.md 实验 1 后半：Ninja Multi-Config Release=2→Debug=7→Debug=3 三次安装，作为 (ii) 断言的设计依据。
4. 起草 B 的测试补丁 diff 与静态预期分数表（8/12）交决策包；更新 RR §7.5d / §8.4 为四种范围。

```json
{"task": "conan-io__conan-15422", "cells": {"deepseek-v4-pro": "4/4/4", "qwen3-coder-30b-a3b-instruct": "4/4/4", "qwen3.6-35b-a3b": "4/4/4"}, "verdict": "coverage_gap", "gold_equivalent_successes": 7, "semantic_gap_successes": 5, "false_negatives": 0, "p2p_total": 40, "actor_requirements": ["原镜像（无派生）", "bash_env_v1 诊断变体（正式 original 下 import 失败）", "cmake 3.22.1 < 3.23：functional 测试 ERROR 为已知非阻断", "无公网、git sanitize、2 CPU cgroup 配额"], "disposition_options": ["A 原样保留标参考覆盖不足", "B 另版本补参考断言：未配置默认（比对同进程 build_jobs）/ Ninja Multi-Config 42 / 守护 version 3 与 cmakeMinimumRequired 3.15", "B' 题面补充默认与多配置说明 + B", "C 仅评测", "D 诊断旁路 checks/conan15422.py", "E 淘汰"], "t0_items": ["B 参考测试断言 (i)(ii)(iii)", "B' 题面变更", "VS/Xcode/NMake 生成器范围若写入断言"], "min_followup_experiments": ["checks/conan15422.py 对 12 条候选 + gold + noop 跑 4 行 × jobs/schema", "核 cmake-presets(7) 文档并在 CMake ≥3.23 下读 Q36 a2 生成文件", "Ninja Multi-Config Release=2→Debug=7→Debug=3 追加/替换序列", "起草 B 测试补丁 diff 与静态预期 8/12"], "confidence": "high"}
```
