# L1_conan 逐题静态审查小结

2026-09-16 夜 · **12/12 题全部完成**（216 题里 `conan-io/conan` 恰好 12 题，`tasks_by_repo.json`，本包即全量覆盖）。
题级记录：`records/<instance_id>.json`；仓库级共性事实：`repo_level_findings.md`；脚本：`scripts/`；中间产物：`runs/env_overnight_20260916/L1_conan/`（`mat/`、`prescan2.json`、`envscan.json`、`collide.json`）。

共同基线（12 题一致）：stage1 gold = RESOLVED_FULL（F2P/P2P 无缺席、无非 PASSED），empty = RESOLVED_NO；`eval_cmd` 都是 `pytest -n0 -rA <单个测试文件>`；`test_patch` 都只碰 **一个** 测试文件，`golden_patch` 都不碰测试路径 → **12 题的 `additional_exclusions` 全部为空**（第四组 B）。版本跨 1.51/1.54/1.60/2.0/2.1，`python_version` 全 3.10。

## 逐题结论

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| conan-13326 (2.0, e2:A/B) | 机制干净；但 F2P 要求 qcc 各版本支持的 cppstd 精确列表与 `version < 5` 阈值，题面只给一个 `TypeError` traceback，毫无依据。DeepSeek 写出更细阈值的合理实现，只在 `qcc-5.4` 一条上与 gold 不同 → PARTIAL。 | needs_review | 用 3 个合理阈值（<5 / <5.4 / <4.4）分别 patch 后跑官方 F2P，统计有多少合理实现被拒。 |
| conan-14296 (2.1, e2:B) | **污染**：DeepSeek 候选逐字复现 gold 源码 7/7 行，并复现不可见的官方测试 60/61 行（实质行 19/20），唯一差异是注释里一个空格。题面是用户求助帖，引用未随题提供的 examples2 示例，三问只修一问。 | needs_review（不可作能力评测） | 对候选基座做 no-context 探针：只给 PR 标题，看能否写出该 PR 的测试函数名与断言。 |
| conan-11560 (1.51) | **误导题面**：`## Solution` 明确要求 `alwayslink = True`，gold 只加一个逗号和一行 `# do not sort`；F2P 逐字符比对这段自由文本注释与其 8 空格缩进。照题面做必然 0 分。 | needs_repair | 写一个用 `alwayslink = True` 的合法替代解跑官方 F2P，记录被拒 ID，入库为过严测试反例。 |
| conan-11594 (1.51) | **参考 ID 截断碰撞**：F2P 的 `…::test_run_tests[Ninja` 同时覆盖 `[Ninja Makefiles-test]` 与 `[Ninja Multi-Config-test]`，empty 的 6 条摘要行只产出 5 个 status_map 键。另：唯一一道 `test_patch` 新建测试文件的题，stage1 eval.sh 因此退化成无 pathspec 的整树 checkout。 | needs_review（并更正 `task_signals` 的 `fragile_reference_id=false`） | 构造"修好 Multi-Config 但弄坏 Makefiles"的补丁跑官方 eval，量化碰撞的判分后果。 |
| conan-12397 (1.54) | 题面 Notes/Workaround 直接说明修法，gold 1 行，P2P 覆盖 native 场景。唯一杂音：P2P 里的 `test_extra_flags_via_conf` 是被同一个 test_patch 改写过的测试。 | ready_for_probe | 对 216 题统计 P2P 中被自身 test_patch 改写的条目数。 |
| conan-13230 (2.0) | 本包质量最好的一题：题面自足（profile+repro+日志）、gold 2 行、F2P 三条断言覆盖 min_version/arch/isysroot 三个泄漏出口、P2P 34 条守住 apple 既有行为、无任何 issue。 | ready_for_probe | —（可直接进真机探针） |
| conan-13403 (2.1) | `pass_to_pass` **为空**，整题判分只有 1 个测试，回归保护为零；F2P 用 `@patch('conan.tools.gnu.autotools.chdir')` 钉死了 chdir 的调用形态（模块、位置参数、未规范化路径）。 | needs_review | 在镜像里跑 `conans/test/unittests/tools/gnu/` 全量，取 gold 下全绿的 ID 补 P2P。 |
| conan-13610 (2.0) | **要求不可知**：题面 245 字符的内部待办 "Take a look into normalizing the log levels"，判分要求裸 `-v` 从 VERBOSE 改成 STATUS；base 的既有测试恰好断言相反。奖励基本是二选一。 | needs_repair | 盲解 3 次统计模型选 status / verbose 的比例；若接近随机即证明不可学。 |
| conan-13721 (2.0) | 机制完全干净、P2P 6 条充分。唯一边界：F2P 要求 `foo.profile` 保留扩展名，而题面例子里宏参数是不带扩展名的 `windows_msvc_v1933_x86`。 | ready_for_probe | 实现"去扩展名"版本跑 F2P，确认恰好只挂 `foo.profile` 一条。 |
| conan-13788 (1.60) | **误导题面**：提问者说 "I would have expected this to be forbidden"，gold 反向（允许并按 `(name, context)` 区分）；题面 545 字符无复现无日志，澄清全在 6010 字符的不可见 hints 里。P2P 9 条覆盖好。 | needs_repair | 实现"禁止并报错"的解跑官方 F2P 确认 0 分；对比补全复现条件后的盲解成功率。 |
| conan-14177 (2.1) | **误导题面**：题面用 diff 写死 `apply_conandata_patches(conanfile, verbose=False)`，gold 不加 `verbose` 改成默认打印，格式 `Apply patch (file): <patch_file>`；从 opt-in 到默认的转折只在不可见 hints 里。`test_single_patch_description` 还用 `==` 锁死整行输出。 | needs_repair | 实现题面版本跑官方 F2P，确认 3 条全挂。 |
| conan-15422 (2.1) | 题面给了明确 before/after JSON、gold 3 行、P2P 40 条。两点待办：gold 用 `build_jobs()` 把宿主 CPU 数写进生成的 `CMakePresets.json`（跨机器稳定性未验）；与 14296 同 gold 文件同测试文件，属同族。 | ready_for_probe | `docker run --cpus=2` 与不限制两种条件各跑一次 F2P+P2P 逐 ID 比对。 |

处置分布：`ready_for_probe` 4（12397 / 13230 / 13721 / 15422）、`needs_review` 4（13326 / 14296 / 11594 / 13403）、`needs_repair` 4（11560 / 13610 / 13788 / 14177）、`reject_revision` 0。

## 跨题发现

1. **题意与判分脱节是 conan 的主要质量问题，不是环境问题。** 12 题里 7 题的 `checks.23` 或 `checks.1` 是 issue，其中 4 题（11560 / 14177 / 13788 / 13610）属于"照题面做必然 0 分"。相对地，环境侧（安装、网络、工具链、资产、内存）12 题全部干净。详见 `repo_level_findings.md` §8。
2. **conan 的测试根命名会打翻跨仓库的文件边界启发式。** `conans/test/`（单数）＋ `*_test.py` 后缀，让 moto 口径的 `prescan.py` 对 13230 / 13403 / 13788 误报 `TP_NONTEST`。见 §1。
3. **`parse_log_pytest` 对 `-rA` 的 SKIPPED 摘要行解析出假键 `[1]`**（14296 / 15422 实证）。后果是被 skip 的测试 ID 永不入 status_map，`reference_skipped` 对 conan 形同虚设，而"缺席计失败"会把 skip 记成 FAILED。见 §2。
4. **参考 ID 空格截断只在 11594 造成碰撞，且方向保守。** 实测 pytest 6.2.5 的 `-rA` 摘要顺序是 PASSED → SKIPPED → FAILED，字典后写覆盖先写，所以碰撞组内任一失败即整键 FAILED。代价是组内另一个测试的结果被静默丢弃。见 §4。
5. **控制面：`conans/test/conftest_user.py` 是 git-ignore 的任意代码入口，而且任何恢复步骤都不会删它。** 官方 conftest 无条件 import 并 merge 它的 `tools_locations`（1.x+2.x）与 `default_profiles`（2.x，`TestClient` 的默认 host profile 就取自这里）。本包 12 题的目标测试文件本身没有可跳过/提前退出的入口，但这条建议在 conan 的评分配方里统一处理（可信 setup 删该文件），不要逐题加 `additional_exclusions`。见 §10。
6. **conan 不做 `pip install -e .`，候选代码靠 `export PYTHONPATH=…:$(pwd)` 生效；安装段只装 requirements，而且读的是候选可改的工作树文件。** 安装配方按版本组分两种（1.51/1.54/2.0 带 `PIP_CONSTRAINT=cython<3`，1.60/2.1 不带），12 题无例外。见 §11。
7. **污染是真实存在的，而且可以静态检出。** `scripts/memcheck.py` 用"候选复现不可见 test_patch 的实质行比例"作判据，conan-14296 命中 19/20。同一探针在 24 条 DeepSeek 轨迹里还点亮 moto-5701(13/13)、pydantic-8500(4/4)、moto-6913(4/5)——跨包线索，交对应负责人复核。见 §9。

## 三份佐证 JSON（在本包目录）

- `evidence_truncated_ids.json`：12 题逐运行重放 `parse_log_pytest` 的 `split()[1]`，列出摘要行数 vs status_map 键数、碰撞组（只有 11594）、被截断但不碰撞的键、以及被解析成 `[1]` 的 skip 摘要原文（14296 / 15422 各 3 条）。
- `evidence_contamination.json`：2 条有 DeepSeek 轨迹的 conan 题的候选 vs gold / vs 不可见 test_patch 的逐行重合，含未被复现的实质行清单与人工复核结论（14296 确认污染；13326 判为弱线索不作结论）。
- `evidence_new_test_files.json`：12 题 test_patch 每个路径在 base 是否存在、是否 `new file mode`，以及 `eval.sh` 里实际的 `git checkout` 行与是否退化成无 pathspec 整树 checkout（只有 11594 退化）。

## 中间产物（在 `runs/env_overnight_20260916/L1_conan/`）

- `prescan2.json`：12 题的 test_patch/gold 路径、非测试路径判定、截断/非 ASCII ID、gold 与 empty 的逐 ID 对账。
- `envscan.json`：12 个目标测试文件的 `@pytest.mark.tool` / `skipif` / HTTP / conancenter / 家目录 / 子进程静态命中。
- `collide.json`：从 stage1 真实 `-rA` 摘要行重建的截断键 → 真实 nodeid 映射、碰撞组、以及被解析成 `[1]` 的 skip 摘要原文。

## 未完成 / 未检查

- `checks.31` 已从静态侧给出结论（§10 的 `conftest_user.py` 入口），但**没有任何实跑验证**：写一个 `conftest_user.py` 后逐 ID 结果会不会变、RH2 恢复之后该文件是否仍在，都还没测。
- §3 里"缺 cmake 时 `@pytest.mark.tool` 会 fail 而非 skip"是从 `conans/test/conftest.py` 推出的，**镜像里 `/usr/share/cmake-3.15.7/bin` 是否存在未进容器确认**（`not_checked`）。本包 12 题都不含 tool 标记，所以不影响当前结论，但影响我给出的 functional 类扩展回归建议。
- 所有 `proposed_regression_tests` 只做了静态选择，未在 base/gold 上实跑确认它们在 gold 下全绿。
- 未做重复评分（清单 14）、缓存/并发（15）、非 root 身份（8）、真实交付（16）的任何验证——这些需要真机。

## 最值得用户裁定的三个问题

1. **"照题面做必然 0 分"的题（11560 / 14177 / 13788 / 13610）怎么处置？** 三个选项：(a) 直接剔除，conan 可用题从 12 降到 8；(b) 改写题面形成明确的"修订版"，但按清单 §37 这会让分数不能与公开 benchmark 比较；(c) 保留原样当记忆型训练信号。我倾向 (b) 用于训练、(a) 用于评测，但这需要用户定口径。
2. **污染题（至少 conan-14296，可能还有 moto-5701 / pydantic-8500 / moto-6913）是否要从评测侧剔除，以及要不要把 `memcheck.py` 这类静态探针固化成入池闸门？** 现在的判据（候选复现不可见 test_patch 的实质行比例 ≥ 0.5）是我临时定的，阈值需要用户或 Codex 校准。
3. **`parse_log_pytest` 的两个已知缺陷（skip 摘要行解析成 `[1]`、空格截断碰撞）是修 parser 还是修参考清单？** 修 parser 会让 RH2 与上游 SWE-Gym 的口径分家（影响与官方分数的可比性，清单 §22/§37）；只修参考清单则要逐题改 F2P/P2P 常量。这是 T0 级的训练语义问题，我不自行决定。
