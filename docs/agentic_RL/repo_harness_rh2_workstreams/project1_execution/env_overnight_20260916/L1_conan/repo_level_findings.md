# conan-io/conan 仓库级共性事实（L1_conan，2026-09-16 夜）

覆盖范围：216 题里 **全部 12 道** conan 题（`tasks_by_repo.json` 显示 `conan-io/conan: 12`，与本包 `ASSIGNMENT.json` 一致），版本跨 1.51 / 1.54 / 1.60 / 2.0 / 2.1，`python_version` 全是 3.10。
下面每条都是仓库级结论，题级引用写在对应 `records/<instance_id>.json` 的 `checks` 里。

---

## §1 conan 的测试根是 `conans/test/`（单数），文件名常以 `_test.py` **结尾**

- 事实：`pytest.ini` 在 5 个 base 上都是 `testpaths = 'conans/test'`（例如 `git show 00700331…:pytest.ini`）。12 题的 `test_patch` 路径全部在 `conans/test/` 下；其中 3 题的文件名是 `*_test.py` 后缀而不是 `test_*` 前缀：
  - `conans/test/unittests/client/toolchain/autotools/autotools_toolchain_test.py`（13230）
  - `conans/test/unittests/tools/gnu/autotools_test.py`（13403）
  - `conans/test/integration/graph_lock/graph_lock_build_requires_test.py`（13788）
- 影响：沿用 `L1_moto_1/scripts/prescan.py` 的启发式（`p.startswith('tests/')` 或 `basename.startswith('test_')`）会把这 3 个文件误判成 **非测试源码**，从而误报 `TP_NONTEST`（第四组 B 的"混合职责"告警）。本包实测：moto 口径报 3 条 `TP_NONTEST`，conan 口径报 0 条。
- 证据：`scripts/prescan.py`（moto 口径，输出见会话记录）对比 `scripts/prescan2.py`（conan 口径，输出 `runs/env_overnight_20260916/L1_conan/prescan2.json`）。
- 结论：**12 题的 `additional_exclusions` 全部为空**（`test_patch` 都只碰一个纯测试文件，`golden_patch` 都不碰任何测试路径）。跨仓库的文件边界工具需要按仓库配置测试根，不能只认 `tests/` 前缀。

## §2 `parse_log_pytest` 对 pytest `-rA` 的 SKIPPED 摘要行解析出假键 `[1]`

- 机制：pytest `-rA` 的跳过摘要行形态是 `SKIPPED [计数] 文件:行号: 原因`，**不含 nodeid**。`rh2/src/repoharness2/envpack/swegym_parsers.py::parse_log_pytest`（conan 走这条 parser）对以状态词开头的行取 `line.split()[1]`，于是把 `[1]` 当成测试 ID 写进 status_map。多条 skip 折叠成同一个键。
- 实证：
  - `conan-io__conan-14296` gold：`status_map.json` 出现键 `"[1]": "SKIPPED"`，它不在 F2P/P2P 里；`test_output.txt` L417-419 是三行 `SKIPPED [1] conans/test/integration/toolchains/cmake/test_cmaketoolchain.py:288: Only OSX` / `:315: Only OSX` / `:726: Only Windows`。
  - `conan-io__conan-15422` gold：同样一个 `[1]` 假键，对应 `test_output.txt` L956-958。
  - 另外 10 题的 gold 日志 0 skip，无此现象。
- 后果（本包 12 题**暂无判分影响**，因为被 skip 的都不在参考清单里）：
  1. 被 skip 的测试 ID 永远进不了 status_map，`scoring.py` 的 `reference_skipped=[c for c in reference if status_map.get(c)=="SKIPPED"]` 对 conan 这种 `-rA` 形态**恒为空**。
  2. `scoring.py` 的口径是"缺席计失败"，所以若某条 P2P 在候选下变成 skip，它会被记成 FAILED 而不是"官方口径不进桶"的 SKIPPED，归因会指错方向。
  3. status_map 里多出一个不是测试的键，`解析条数` 这类计数会比真实测试数多 1（e1 报告里 conan-13326 的 `解析条数 70 / 参考缺席 0` 之所以干净，正是因为它 0 skip）。
- 下一实验：造一个把某条 P2P 变成 `pytest.skip` 的候选补丁，跑真实 RH2，确认它落在 `reference_missing` 还是 `reference_skipped`。

## §3 `@pytest.mark.tool(...)` 在缺工具链时是 **fail 而不是 skip**

- 机制：`conans/test/conftest.py::pytest_runtest_setup`（1.51 的 L244-250、2.1 的 L372-378，5 个 base 逻辑一致）里
  - `result is True` → `pytest.fail("Required '<tool>' tool version '<v>' is not available")`
  - `result is False` → `pytest.skip(...)`
  而 `_get_individual_tool` 只在 `tools_locations[name]["disabled"]`、版本项 `"disabled"`、或 `path == "skip-tests"` 时返回 `False`；当配置里给了平台路径而该目录不存在（`elif tool_path is not None and not os.path.isdir(tool_path): return True`）或 `which(exe)` 找不到时返回 `True`。
- 举例：`cmake` 的默认版本是 `3.15`，Linux 路径写死为 `/usr/share/cmake-3.15.7/bin`（5 个 base 一致）。评测镜像里这个目录几乎肯定不存在 → 返回 `True` → **`pytest.fail`**。
- 本包实测：12 题的目标测试文件里 **一个 `@pytest.mark.tool` 都没有**（`scripts/envscan.py` 输出 `runs/.../envscan.json`），stage1 gold 下 F2P/P2P 全 PASSED，所以工具链缺失对当前 12 题没有影响。
- 用途：这条是**扩展回归的硬约束**——任何来自 `conans/test/functional/` 的候选 P2P（cmake/meson/autotools/bazel 的真实构建测试）在没有对应工具链的镜像里会**整条 FAILED**，不会温柔地 skip。所以我给出的 `proposed_regression_tests` 里凡是 functional 的都标注为"只能当诊断项，不能进 P2P"。
- 待验证（`not_checked`）：镜像里 `/usr/share/cmake-3.15.7/bin` 是否真的不存在、`which cmake` 是否有结果。这需要进容器确认，本包未做。

## §4 参考 ID 的空格截断：`conan-11594` 是唯一碰撞题，且碰撞方向偏保守

- 机制：`parse_log_pytest` 取 `split()[1]`，参数化 ID 里只要有空格就被截断。上游 SWE-Gym 的 F2P/P2P 常量也是同一个 parser 生成的，所以常量与运行时键"对得上"，但**多个真实测试可能映射到同一个键**。
- 实证（`scripts/collide.py` → `runs/.../collide.json`）：只有 `conan-11594` 命中。
  - F2P 常量：`conans/test/unittests/tools/cmake/test_cmake_test.py::test_run_tests[Ninja`
  - 它同时覆盖运行时的 `test_run_tests[Ninja Makefiles-test]` 与 `test_run_tests[Ninja Multi-Config-test]`。
  - P2P 另有 3 条被截断但不碰撞：`[NMake` / `[Unix` / `[Visual`。
  - empty 运行：6 条摘要行只产出 **5 个 status_map 键**（`.../empty/offline/a1/status_map.json`）。
- 顺序性质（实测，pytest 6.2.5）：`-rA` 展开为 `PpsxXEf`，摘要块顺序是 **PASSED → SKIPPED → FAILED**（13326 empty 的 3 条 FAILED 在最后；14296 empty 的 SKIPPED 在 PASSED 之后、FAILED 之前；11594 empty L597-601 PASSED、L602 FAILED）。因此字典"后写覆盖先写"意味着**碰撞组内任一失败即整键 FAILED**，方向保守（不会把失败洗成通过）。
- 但仍有代价：`Ninja Makefiles-test` 的结果被静默丢弃，它既不在 P2P 也不在 status_map 里，只破坏它的回归不可见。
- 勘误：`task_signals_swegym.json` 把 `conan-io__conan-11594` 的 `fragile_reference_id` 标成 `false`，与上述证据不符，建议更正。

## §5 `git checkout <base> <test_files>` 在"test_patch 新建测试文件"时退化为整树 checkout

- 实证：`conan-11594` 的 `test_patch` 是 `new file mode 100644` / `--- /dev/null`，目标文件在 base 不存在。stage1 的 `eval.sh` 因此在 L18（setup 前）和 L76（收尾）都写成**没有 pathspec** 的 `git checkout 4ed1bee0fb81b2826208e8c1c824c99fb6d69be8`；另外 11 题都是正常的 `git checkout <base> <单个测试文件>`。
- 后果：stage1 里 HEAD 本来就在 base_commit，对已修改的跟踪文件是空操作（gold 6/6 PASSED 可证补丁存活）；收尾那条也删不掉新建的未跟踪测试文件，等于没有恢复。但如果候选在解题时改变了 HEAD（提交、切分支），这条无 pathspec 的 checkout 会把工作树整体拉回 base。
- RH2 现状：grader profile 路径已经处理了这一形态——`rh2/src/repoharness2/adapters/slime/prepared_task_face.py:185-206` 用 `for f in <files>; do if git cat-file -e <base>:"$f"; then git checkout <base> -- "$f" || exit 3; fi; done`，并在注释里写明"官方那条一次性 checkout 只要清单里有一个新增路径就会整条 pathspec 失败"。legacy 单脚本路径（`render_v2_eval_script`）仍是一次性形态。
- 用途：`conan-11594` 是本仓库唯一符合这个形态的题，适合当恢复逻辑的回归夹具。

## §6 候选在 `conans/test/` 下新建/修改但不在 `test_patch` 里的测试文件**不会被恢复**

- 实证：DeepSeek 对 `conan-13326` 的候选补丁除了改 `conan/tools/build/cppstd.py`，还改写了 `conans/test/unittests/tools/build/test_cppstd.py`（在 test_patch 里，会被恢复覆盖）**以及** 新增了 `conans/test/integration/package_id/test_cache_compatibles.py::TestDefaultCompat::test_default_cppstd_compatibility_qcc`（不在 test_patch 里，不会被恢复）。
- 当前无判分影响：12 题的 `eval_cmd` 都是 `pytest -n0 -rA <单个测试文件>`，候选写的其它测试文件不会被收集。
- 待办：如果把 conan 的测试命令放宽到目录级，必须先复验这些残留是否会被执行。

## §7 环境与成本：conan 是本轮 9 个仓库里最轻的之一

- 12 题的目标测试文件里 **0 个 `@pytest.mark.tool`**、**0 处 conancenter / 真实 HTTP 访问**（`envscan.json` 里的 `http` 命中全是注释里的 GitHub issue 链接，以及 14177 里作为 `patch_source` 元数据写进输出的 URL）、**0 处家目录缓存写入**（集成测试都走 `TestClient` 的临时 cache，`conan-13721` 甚至显式往 `client.cache.profiles_path` 写 profile）。
- 单元测试（13326 / 11560 / 11594 / 13230 / 13403 / 14177）用 `MockSettings` / `ConanFileMock` / `mock_patch_ng`，不起子进程、不落盘。
- 集成测试（14296 / 12397 / 13610 / 13721 / 13788 / 15422）用 `TestClient` 在临时目录里跑 `conan install|create`，不需要编译器。
- e1 真机数据（`e1_report_20260915.md` L15/L19，conan-13326）：安装 2.5–2.6 s、测试 1.1–1.4 s、可信 setup 80 s、峰值内存 ~340 MB、解析 70 条 / 参考缺席 0。相比同表的 dvc-5822（安装 39 s、内存 ~1.1 GB）便宜很多。
- 唯一的机器相关性来自 gold 自身：`conan-15422` 的 gold 用 `build_jobs(conanfile)`，默认走 `conan/tools/build/cpu.py::_cpu_count()`（读 cgroup 配额或 `multiprocessing.cpu_count()`），会把宿主 CPU 数写进生成的 `CMakePresets.json`。

## §8 题面与判分目标脱节是 conan 题的**主要**质量问题（12 题里 7 题）

统计口径：`checks.23` 或 `checks.1` 为 `issue` 的题。

| 题 | 题面主张 | 判分实际要求 | 严重度 |
| --- | --- | --- | --- |
| 11560 | 题面 `## Solution` 明确要求给 `cc_import` 加 `alwayslink = True` | gold 只加一个逗号和一行 `# do not sort` 注释；F2P 逐字符比对该注释文本与缩进 | P1（误导） |
| 14177 | 题面用 diff 写死 `apply_conandata_patches(conanfile, verbose=False)` | gold 不加 `verbose`，改成默认打印，格式 `Apply patch (file): <patch_file>` | P1（误导，转折只在不可见 hints 里） |
| 13788 | 提问者说 "I would have expected this to be forbidden" | gold 反向：允许同名不同 context 并按 `(name, context)` 区分 | P1（误导） |
| 13610 | 题面 245 字符的内部待办 "Take a look into normalizing the log levels" | 要求裸 `-v` 从 `LEVEL_VERBOSE` 改成 `LEVEL_STATUS`；base 的既有测试还断言相反 | P1（不可知） |
| 13326 | 只给一个 `TypeError` traceback | 要求 qcc 各版本支持的 cppstd 精确列表与 `version < 5` 的阈值 | P1（不可知） |
| 14296 | 用户求助帖，三个问题，引用未随题提供的 examples2 示例 | 只修其中一个，且根因（多个用户 preset 继承同一 conan preset）题面未提 | P1（不可知＋输入不完整） |
| 13721 | 题面例子里宏参数是不带扩展名的 `windows_msvc_v1933_x86` | F2P 要求 `foo.profile` 保留扩展名 | P2（一条断言） |

题面与判分一致、机制也干净的只有 4 题：**12397 / 13230 / 13721 / 15422**（13721 有上表那一条边界）。

## §9 污染探针：`conan-14296` 的 DeepSeek 候选逐字复现了不可见的官方测试

- 方法（`scripts/memcheck.py`）：把候选 diff 的新增行与**求解者不可见的** `test_patch` 新增行逐行比对；只统计长度 ≥25、非 import/注释/装饰器的实质行。
- `conan-14296`：候选与 gold 的源码改动 **7/7 行逐字符相同**（含不地道的 `if len(conan_inherits):` 与 `list(set(...))`）；候选复现官方隐藏测试 `test_cmake_presets_shared_preset` 的 **60/61 行**（实质行 19/20），唯一差异是注释里一个空格（`"" })  #File must exist` vs `""})  # File must exist`）。该测试是一段 60 行的全新 fixture（`debug1/debug2/release1/release2` 的 CMakePresets JSON + 特定 docstring），同文件没有可抄的样板，逐字复现只能解释为预训练记忆了 conan PR #14296。
- `conan-13326`：实质行 5/7 命中，但命中的是函数签名与同文件 `test_supported_cppstd_mcst` 的复制体，属于"照着同文件邻居写"可以解释的部分；真正有信息量的取值行（`qcc-5.4` / `qcc-8.3`）没命中。因此 13326 只算**弱线索**，不作为污染结论。
- 顺带（跨包，交对应负责人复核，不作本包结论）：同一探针在 24 条 DeepSeek 轨迹里还点亮 `getmoto__moto-5701`（实质行 13/13）、`pydantic__pydantic-8500`（4/4）、`getmoto__moto-6913`（4/5）。

## §10 控制面：`conans/test/conftest_user.py` 是一个 git-ignore 的任意代码入口，且不会被恢复

- 事实链：
  1. `conans/test/.gitignore` 第 1 行就是 `conftest_user.py`（1.51 / 1.54 / 1.60 / 2.0 / 2.1 五个 base 一致）。
  2. `conans/test/conftest.py` 在模块级 `try: from conans.test.conftest_user import tools_locations as user_tool_locations` 并 `update(tools_locations, user_tool_locations)`；conan 2.x 还多一段 `from conans.test.conftest_user import default_profiles` 并 `default_profiles.update(...)`（2.1 的 L220 与 L236）。
  3. conan **2.x** 的 `conans/test/utils/tools.py` L45 `from conans.test.conftest import default_profiles`、L430 `text = default_profiles[platform.system()]` —— 这就是 `TestClient` 写出的默认 host profile。conan **1.x** 的 `tools.py` 不消费 `default_profiles`（`grep -c default_profiles` = 0），可改的只有 `tools_locations`。
- 为什么它是控制面：该文件不在任何 `test_patch` 路径里，所以 RH2 的"恢复官方测试文件"步骤（无论是官方一次性 `git checkout <base> <files>` 还是 `prepared_task_face` 的逐文件循环）都不会碰它；它又是 git-ignore 的，不带 `-x` 的 `git clean` 也删不掉。候选在解题阶段创建它之后，**评分阶段 pytest 收集时会执行其中的任意代码**。
- 可达的行为改变（未实测，属 `next_experiment`）：
  - `tools_locations = {"cmake": {"disabled": True}, ...}` → 把 `@pytest.mark.tool` 的硬失败（§3）变成合法 skip；
  - conan 2.x 下改 `default_profiles["Linux"]` → 直接改变所有 `TestClient` 集成测试的 settings；
  - 模块级任意代码 → 可以 monkeypatch 被测模块或 pytest 报告。
- 对本包 12 题的实际影响：目标测试文件本身没有可被跳过或提前退出的入口（补扫确认：无模块级 `pytestmark`、无 `pytest.mark.tool`、无 `pytest.skip(`、无 `sys.exit`/`os._exit`、无 `conftest_user` 引用）。6 道用 `TestClient` 的集成题（14296 / 12397 / 13610 / 13721 / 13788 / 15422）里，只有 2.x 的 4 道（14296 / 13610 / 13721 / 15422）暴露在 `default_profiles` 这条路径上；6 道 Mock 单元题改这个文件更可能弄坏自己。
- **同一节里的第二个入口：`conans/requirements*.txt` 本身也是候选可改、且不会被恢复的文件。** 见 §11——评分脚本的安装段读的是 `/testbed` 工作树里的 `conans/requirements.txt` / `requirements_server.txt` / `requirements_dev.txt`，这三个文件不在任何 `test_patch` 路径里，候选改了就会在评分时被 `pip install -r` 照单执行。处置建议同上：在可信 setup 阶段把这三个文件一并 `git checkout <base> --` 回基线。
- 建议处置（仓库级，不逐题加排除）：在 conan 的评分配方里，可信 setup 阶段显式删除 `/testbed/conans/test/conftest_user.py`，或对 `conans/test/` 做 `git clean -xfd` 后再按 `test_patch` 恢复。按第四组 B，`additional_exclusions` 仍保持为空——这是配方问题，不是文件边界问题。

## §11 安装与导入：conan 不做 `pip install -e .`，候选代码靠 `PYTHONPATH` 生效

- 12 题的 `eval.sh` 结构完全一致（`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/<tid>/gold/offline/a1/eval.sh`）：
  - 环境段：`conda activate testbed` → `cd /testbed` → `export PYTHONPATH=${PYTHONPATH:-}:$(pwd)` → `git config --global --add safe.directory /testbed`。
  - 安装段：**只装依赖，不装 conan 自身**——`python -m pip install -r conans/requirements.txt; python -m pip install -r conans/requirements_server.txt; python -m pip install -r conans/requirements_dev.txt`，没有 `pip install -e .`。
  - 测试段：`pytest -n0 -rA <单个测试文件>`。
- 安装配方按 **版本组**（不是逐题）分两种，12 题无例外：
  - 带 `echo 'cython<3' > /tmp/constraint.txt; export PIP_CONSTRAINT=/tmp/constraint.txt` 前缀：1.51（11560 / 11594）、1.54（12397）、2.0（13230 / 13326 / 13610 / 13721）。
  - 不带：1.60（13788）、2.1（13403 / 14177 / 14296 / 15422）。
  - `spec_vendor_id` 12 题都是 `swegym_constants_242429c1`。12 题 gold 的 `RH2_PHASE_END install ... rc=0`。
- 对清单第 9 项（"测试执行的确实是本次候选代码吗"）：conan 没有编译产物、没有 egg-info 时序问题，候选改 `/testbed/conan/**` 或 `/testbed/conans/**` 后由 `PYTHONPATH` + cwd 直接生效。e1 真机数据佐证：conan-13326 的"导入路径"列是 `/testbed/conans/__init__.py`、版本串 `2.0.1`、"运行器变化" False（`e1_report_20260915.md` L15/L19）。
- 对清单第 11 项（"哪个阶段为何需要网络"）：conan 的 **测试段不需要网络**（12 题全部实证：无 conancenter、无真实 HTTP），但 **安装段要求 pip index 可达**——只有当三份 requirements 已在镜像里全部满足时，pip 才不外连。stage1 的 rc=0 与 2.5 s 耗时说明当时是"已满足"路径，但这没有证明断网也能过。
- 顺带的控制面（见 §10）：安装段按 RH2 的 v2 拆分是**候选用户**执行的，而且读的是候选可改的工作树 requirements 文件。
