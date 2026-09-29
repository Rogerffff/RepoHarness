# 历史对照：pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96

2026-09-29 · R2E 私有主审（单题闭环试行，统一标准 v1）。

## 0. 依据与历史审查的性质

**读历史前的前稿**：`OUT/analysis_before_history.md`，协调者已按原样保存。

**历史来源**：都来自 `runs/r2e_static_prep_20260924/v3/history/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/refs.json` 的列表，除特别注明外，路径都在 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/` 下：
- 09-24 P4 包环境审查的 `tasks/pillow__2d01…/screening_record.json`、`findings.md`、`facts.json`；
- `known_issues.json` 中的三族：`expected_non_passed_keys`、`solver_condition:public_test_noise`、`solver_condition:no_pip_in_venv`；
- `decisions.md` 第 18 行（E14），`results_20260924.md` 第 49 行；
- `packages/p4/README.md` 第 17、49、59、66、117 行；
- 复现脚本 `repros/pillow__2d01….py`。

**历史审查的性质**：只做了**环境资格**。旧记录的 `disposition.scope` 明写"不含题目质量 / 训练准入"，没有做需求—断言对照，也没有做退化探测。所以下文"推翻"的，主要是"不需要材料修订"这句话被外推到题目质量层面的部分，不是说旧的环境结论错了。

**本轮新证据**：都在 `runs/r2e_lifecycle_20260929/` 下。
- 新机器正式复验：`env_verify/ledger_l1_noop.jsonl` 和 `ledger_l1_gold.jsonl` 各第 10 行。
- devcheck：`devcheck_rev/unrev/pillow__2d01…/`（真实 Claude Code 2.1.205 + 桩，agent 身份，正式启动路径，v6 任务面）。
- 候选评分：`inv/pillow_2d01/ledger_{D,C1,C3,C2}.jsonl` 与 `logs_*/`（v7 任务面，补丁与前稿附录 A 逐字节相同）。
- 私有行为对照：`inv/pillow_2d01/pcheck_*.json`（root 身份，不联网，一次性容器）。
- 以上各次运行用的都是同一张派生镜像 `sha256:2a98172896162bd7da0bd6fa95dacac1d656bbef0d4f54481f8ad2432d8db785`，配方 `r2e_derive_v1+sysconfig_v1`。

## 1. 旧主张逐条

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| 1 | 环境无缺口，`environment_qualified`（`findings.md` 的结论；旧 `screening_record.json` 的 `disposition`） | **确认（仅限环境层）** | 新机器、新派生镜像上 noop 为 0（60/62，只差两个目标键），gold 为 1（62/62）；devcheck 以 agent 身份走正式启动路径，所有公开命令都跑通（`all_commands_ran=true`）。环境层不需要 R-d。但这只是环境资格，不等于训练资格（v1 §2） |
| 2 | "不需要配方或材料修订"（`findings.md` 的建议） | **配方部分确认；材料部分推翻** | 退化候选 D 得 1（`inv/pillow_2d01/ledger_D.jsonl` 第 1 行，62/62）。私有对照显示 D 违例：`pcheck_explicit1_D.json` 输出 `tag262 0 pixel00 77` 后抛 `AssertionError: explicit BlackIsZero not kept`；`pcheck_default_photometric_kept_D.json` 输出 `L 0 77 \| 1 0 255 \| RGB 2 (1, 2, 3)` 后抛 `AssertionError`。结论：**S1（T2b）**。C3 得 1（`ledger_C3.jsonl` 第 1 行），但两种压缩保存都抛 `AttributeError: encoderconfig`（`pcheck_compressed_path_observe_C3.json`、`pcheck_g4_whiteiszero_roundtrip_C3.json`）。结论：**第 4 步 S1**。材料上需要 R-c1 + R-c2 |
| 3 | 2 个期望 FAILED 键是 `pytest.warns(None)` 死键，不改（旧记录 `checks.R06` 与 `issues[1]`；known_issues `expected_non_passed_keys`） | **确认** | 新机器上 noop、gold、D、C1、C3、C2 六次评分，都在 `T1:67,75` 抛同一个 `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`。失败发生在执行任何 Pillow 代码之前，正确修复翻不动它们。维持"不改"，R-a 只作可选项 |
| 4 | 公开 `Tests/test_file_tiff.py` 有 2 个与修复无关的预存失败（旧记录 `checks.R09`；`decisions.md` E14 的相关性复核） | **确认** | devcheck（agent 身份）`orig/captures/public_tiff_tests.out`：`2 failed, 80 passed, 2 skipped in 1.02s`，失败的正是 `test_closed_file` 和 `test_context_manager`。gold 私有对照（`private_control.json`）结果相同。补充：公开读者给 `public_tiff_tests` 写的 `expect: zero` 因此必然不成立，这也是 devcheck 唯一为假的检查项 `all_match_expect`。这是命令预期写错，按环境基线登记；修正后的命令见前稿 §8.1 |
| 5 | 公开复现 REPRO_OBSERVED=1：`'1'`、`'L'` 都读回 1（旧记录 `checks.R03`、`R09`） | **确认并补充** | devcheck `repro_issue_mode_l.out`、`repro_mode_1.out` 输出 `tag262 1 … pixel00 0` 后抛 `AssertionError`。gold 对照输出 `tag262 0 … pixel00 0`，说明原例修到了，像素也往返不变 |
| 6 | venv 里没有 pip，公开提示却说 pip 已就绪；另有 conda 措辞（旧记录 `issues[0]`；E09） | **过时（当前任务面已修正）** | 当前 `public_hints` 写的是 `.venv`，并且说 "`pip` may be unavailable"（`PUB/public_bundle.json`）。devcheck `env.out` 显示 `VIRTUAL_ENV=/testbed/.venv` 和 `No module named pip`；`attempt.json` 的激活检查前缀为 `/testbed/.venv` |
| 7 | 导入走 `.pth` 路径项指向 `/testbed/src`，`Image.core` 是树内 `.so`；gcc / make / git 都有（旧记录 `checks.R05`） | **导入部分确认；编译工具未在新镜像上核实** | devcheck `env_import.out`（agent 身份）：`PIL 8.4.0.dev0 /testbed/src/PIL/__init__.py`、`core /testbed/src/PIL/_imaging.cpython-39-x86_64-linux-gnu.so`、`libtiff True 4.3.0`。gcc 和 make 只有旧镜像探针的记录（`runs/r2e_env_repair_20260924/p4/dev_probe/pillow__2d01…/agent_probe.log:16-17`）。本题 gold 是纯 Python，不需要编译 |
| 8 | agent 可写 `/testbed/.venv` 里的 site-packages，"反作弊面另议"（旧记录 `checks.R07`） | **未核实** | 本轮没有查。这属于 A 线的通用链路问题（E3），与本题判分没有直接关系 |
| 9 | 重复运行一致，与独立参考对账一致（旧记录 `checks.R13`、`R15`） | **确认并扩展** | 旧机器 noop 与 gold 各 2 次，M3 gold 2 次，新机器 noop 与 gold 各 1 次，差异集合完全一致 |
| 10 | 泄漏面干净：HEAD 无子提交，无 refs、remote、reflog；`install.sh` 是通用脚本（旧记录 `checks.R17`） | **部分确认** | devcheck `attempt.json` 的 `git_sanitize`：HEAD 为 `5db0969f`，`REFS_REMAINING=0`、`REMOTES=0`、`REFLOG_ENTRIES=0`、`UNREACHABLE_OBJECTS=0`；预检 `RH2_PREFLIGHT_HIDDEN_TESTS=ok`、`RH2_PREFLIGHT_GIT_HISTORY=ok`。`fix_present` 与镜像自带 pyc 的来源，本轮没有复查（未核实） |
| 11 | 目标键 2 个，noop 失败原因与题面一致（旧记录 `checks.R16`） | **确认并补充** | 旧审查只核了标签断言 `T1:456`。目标键还有像素往返断言 `T1:457`：只改标签的 C2 在这里失败，报 "got different content"（`inv/pillow_2d01/logs_C2/…eval.log`，60/62）。据此新登记 P4 |
| 12 | 解题不需要改 `r2e_tests` 以外的测试辅助（旧记录 `checks.R04`） | **确认并补充** | 补充一点：根目录 `conftest.py:1` 会导入 base 的 `Tests.helper`，候选改坏它会导致收集失败。隐藏测试用的是自带 helper，候选无法通过改 helper 蒙混过关 |
| 13 | 本题不在题面质量候选族 `prompt_quality_candidates` 里（known_issues） | **一致，另有补充** | 题面没有与测试矛盾，不是 P2。但题面没写像素语义，记 P4（有公开依据）。不需要交用户，理由见 §3 |

## 2. 主审相对前稿的改判

| 前稿（`analysis_before_history.md`） | 定稿 | 理由与证据 |
| --- | --- | --- |
| §7 第 3 步："待实跑，预计得 1" | **S1（T2b），已确认** | D 正式评分 1.0（62/62）。这次评分有效：log 头部有 `M src/PIL/TiffImagePlugin.py`，`RH2_SETUP_APPLY_RC=0`，`included_paths=["src/PIL/TiffImagePlugin.py"]`，目标键和 `test_sanity` 都实际执行并 PASSED。违例证据见 §1 第 2 行 |
| §7 第 4 步："倾向 S1，取决于 libtiff；如果复核认为压缩属于罕见路径，则为 S2" | **S1，已确认** | libtiff 可用（4.3.0）。C3 正式评分 1.0，但文档里的两种压缩保存都会直接崩溃：`'L'` 配 `tiff_lzw`，以及 `'1'` 配 `group4`。后者正是 WhiteIsZero 最常见的真实用法，仓库自己的 `hopper_g4.tif` 就是这种文件。这是整条保存路径不可用，不是边缘输入上的细小差异，所以不再保留 S2 这个选项 |
| 处置 `needs_review` | **`needs_repair`** | 两个 S1 都有可复现的证据，也都有预授权的修订模板（R-c） |
| 开发需求："libtiff 未知""编译器未知" | libtiff 4.3.0 可用；旧镜像上有 gcc 和 make | devcheck `env_import.out`；历史探针 |
| §8.1："`public_tiff_tests` 必然非 0，且只有 2 个失败" | 已证实 | devcheck 和 gold 对照都是 2 failed、80 passed、2 skipped |
| P4（像素语义）的判断 | **不变，不交用户** | C2 实跑得 0，失败在 `T1:457`，与预测一致；历史材料里没有相反的依据 |
| C1 预计得 1 | 已证实（62/62） | 范围更窄、基于 packer 的替代实现没有被误拒 |

## 3. 像素是否需要反相：要不要交用户

**不需要交用户。** 测试采用的读法是：写 262=0 时把数据反相，保证图像往返不变。这个读法有充分的公开依据（前稿 §3.2 列了六条），最关键的三条是：

1. Pillow 读取端把 262=0 的 `'1'`/`'L'` 反相解码（`TIP:136,160`）；
2. 公开测试 `test_gray_semibyte_per_pixel` 断言 262=0 的 `hopper2I.tif` 与 262=1 的 `hopper2.tif` 解出同一张图（这两个标签值是我从文件头实读的）；
3. base 在题面原例上本来就往返一致。

另一种读法是只改标签、像素不动。按 Pillow 自己已有测试的语义，这样写出的文件会解码成原图的反相，与题面"accurately reflecting the specified photometric interpretation"相冲突，也破坏了 base 已有的往返行为。它不是一个有公开依据的任务目标，所以不按 P5（两种读法都有依据）处理，而是记 P4 登记。R-f 补一句说明是可选项，不作为进训练的前置条件。

只有当独立复核能给出支持"只改标签"的公开依据时，才按 P5 交用户；在那之前，本题按 R-c 路线推进。
