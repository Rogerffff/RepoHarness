# P2 包报告：datalad ×5、numpy ×7（R2E 环境审查第一轮，2026-09-24）

P2 sub-agent（B 线）。流程、检查项与决定分别见 [../../README.md](../../README.md)、[../../checks_r2e.md](../../checks_r2e.md)、[../../decisions.md](../../decisions.md)。文中路径一律相对仓库根。

状态用词：**已验证**（有运行证据）、**已实施**（本包写了文件或跑了命令）、**建议 / 提案**（等主会话合并或用户决定）。本包没有新的"已决定"事项，只沿用主会话的 E01–E10。

## 0. 摘要

- **已实施**：12/12 题都写了 `screening_record.json`、`findings.md` 与公开复现脚本 `repros/<iid>.py`；写了 1 份材料修订提案（datalad `58ba5165`）。`rh2/scripts/r2e_env/check_records.py` 核对 12/12，零问题。
- **已验证**：
  - 探针 12/12 满足十项最小条件（agent/54321、rollout 资源、无网络）。
  - 公开复现 12/12 `REPRO_OBSERVED=1`（REPRO_RC 0）。
  - numpy `2f4a9650` 在配方 v1 下 noop / gold 两次逐键一致。
  - datalad `58ba5165` 的根因经字节对照与沙盒 dry-run 确认。
- **分类**：`solver_condition` 10、`resource` 1（numpy `2f4a9650`）、`material` 1（datalad `58ba5165`）。
- **处置**：`unknown` 10（只差 R13，待中央复跑并入；逐键一致即 `environment_qualified`）、`qualified_with_recipe` 1、`held_material` 1。
- 派发说明写的是"numpy ×6"，本包实际是 numpy 7 题（12 = datalad 5 + numpy 7）。

## 1. 逐题表

| 题 | 分类 | 处置 | 关键 issue | 证据（`runs/r2e_env_repair_20260924/p2/` 下，另注） |
| --- | --- | --- | --- | --- |
| datalad `16c1ffc3` | solver_condition | unknown（待 R13） | 5 个期望 FAILED 键是隐藏 conftest `path` fixture 与 nose 装饰器冲突（确定性、非环境）；无 pip；agent 无 git 身份 | `dev_probe/…16c1…/`、`pubtests/…16c1….log`、`followups/followups.log` F1 |
| datalad `19f5b450` | solver_condition | unknown（待 R13） | M3 的"需 cwd"是误报；agent 无 git 身份，`create` 实测失败；题面示例导入写错（移交题意筛查） | `dev_probe/…19f5…/`（REPRO_OUTPUT）、`followups…` D |
| datalad `58ba5165` | material | held_material | 隐藏 `test_1` 用仓库内修复前的 `demo_doc`，gold 3/4；推荐 B1，决定前隔离 | `docs/…/material_revisions/datalad__58ba5165….md`、`dryrun_58ba/` |
| datalad `6b6fa389` | solver_condition | unknown（待 R13） | 期望 FAILED 键：Python ≥ 3.7 的 `quote` 不转义 `~`（上游在该版本本就失败） | `followups…` E / F2 |
| datalad `9ba5de09` | solver_condition | unknown（待 R13） | 同 16c1 的 5 个 fixture 冲突键 | `pubtests/…9ba5….log` |
| numpy `18b7cd9d` | solver_condition | unknown（待 R13） | `/testbed` 须在 sys.path 上；无 pip | `dev_probe/…18b7…/` |
| numpy `2f4a9650` | resource | qualified_with_recipe | 默认 `/tmp` 1 GiB 下 `test_big_arrays` 假阴性；配方 v1 两次通过；rollout 下公开 `test_io.py` 也会碰到这个用例失败 | `_rerun2/`、`followups/numpy_2f4a_fallocate_source.txt`、`docs/…/recipes/task_resources_v1.json` |
| numpy `43e333e2` | solver_condition | unknown（待 R13） | R09 issue：hypothesis 6.124.1 + `filterwarnings=error` 使仓库测试无法收集；绕过后还有 pytest 8 的 nose setup 失败 | `pubtests/…43e3….log`、`followups…` F3 |
| numpy `5e8301c2` | solver_condition | unknown（待 R13） | 同 numpy 共性 | `dev_probe/…5e83…/` |
| numpy `a5ea773e` | solver_condition | unknown（待 R13） | 同 numpy 共性；`test_ctypeslib.py` 1 个 nose 遗留 ERROR | `followups…` F5 |
| numpy `d805e9b6` | solver_condition | unknown（待 R13） | 同 numpy 共性 | `dev_probe/…d805…/` |
| numpy `d89bc4bb` | solver_condition | unknown（待 R13） | 同 numpy 共性；`test_histograms.py` 21 个 nose-setup ERROR | `followups…` F4 |

## 2. 焦点结论

### 2.1 datalad `58ba5165`：缺测试支撑材料（提案，T0）

隐藏 `r2e_tests/test_1.py` 从仓库内 `datalad.interface.tests.test_docs` 导入 `demo_doc` / `demo_paramdoc` / `demo_argdoc`。上游修复提交同时改了这个模块（加入方括号示例），但：

- gold 按 `is_gold_excluded_test_path` 排除测试路径；
- R2E 只把新版本放进了 `r2e_tests/test_2.py`（sha256 `2a3a29f7…`，与上游修复后的文件逐字节相同），`test_1` 的导入没有改指向它。

结果是 `test_alter_interface_docs_for_cmdline` 在任何源码修复下都 FAILED，gold 3/4，两个参考 runner 也是 0。这属于**缺测试支撑材料**，不是模型该做的改动：题面只要求修解析；要过这个键，只能按隐藏断言去反推并改测试夹具。

沙盒 dry-run（一次性容器，不是正式评分）：

| 方案 | noop | gold |
| --- | --- | --- |
| 原样 | 2/4 | 3/4 |
| B1：`test_1` 改为 `from .test_2 import (…)` | 2/4 | 4/4 |
| A：评分前恢复修复后的 `test_docs.py` | 2/4 | 4/4 |

**提案**：B1（一行改动，expected 不变，评分代码不变；需要新的材料版本、pins，并重建该题派生镜像）；用户决定前按 C2 隔离。备选：A（通用，但属评分契约变更）、B2（常量内联，更自包含）、C1（剔键，不推荐）。全文：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/material_revisions/datalad__58ba5165234cb16de0e8463ee75097362099835f.md`。

### 2.2 numpy `2f4a9650`：资源配方 v1 复验（已验证），以及"两个副本略大于 4 GiB、峰值约 4.3 GiB"的依据

- 中央复跑的 `numpy_bigtmp` 两行（本包回传到 `runs/r2e_env_repair_20260924/p2/_rerun2/`，与主会话目录下的副本 sha256 相同）：noop 141/142，只有目标键 `TestSaveTxt.test_0D_3D` 不符；gold 142/142、RESOLVED_FULL。镜像 ID（`3a64ae08…`）与 scripts_digest（`dd9dfcd7…`）都与 09-23 相同。加上 09-23 那两行，配方下 noop / gold 各 2 次一致；`reconcile_numpy_bigtmp` 2/2 与参考一致。
- 依据，逐项：
  1. 数组大小 2^31 + 100000 = 2,147,583,648 B。
  2. `_savez` 先在目标文件旁写临时 `.npy`，再复制进 ZIP_STORED 的 `.npz`，复制完才删临时文件。所以峰值时两份同时在 `/tmp` tmpfs，合计 ≥ 4,295,167,296 B = 4096.2 MiB，比 4 GiB 多 200,000 B（Codex 源码证据 `docs/…/r2e_rf_review_20260924/evidence_agent/numpy_source_and_profiles.json`）。
  3. tmpfs 页计入容器内存 cgroup。
  4. 4096.2 MiB 加上基线约 340 MiB（默认 profile 峰值 340.3 / 347.8 MiB）≈ 4436 MiB。实测 gold / noop 峰值 4435.1 / 4439.3 MiB（09-23）、4429.4 / 4437.3 MiB（09-24），即约 4.33 GiB。`mem_peak_mb` 是 cgroup `memory.peak` ÷ 1024²（`rh2/src/repoharness2/grading/manager.py:3342`），单位是 MiB。
  5. 默认运行为什么峰值只有 340 MiB：numpy 在 `convert.c:152` 对整个数组调 `npy_fallocate`，`fallocate` 失败就报 "Not enough free space to write 2147583648 bytes"（源码实证，`followups/numpy_2f4a_fallocate_source.txt`）。"tmpfs 在 fallocate 失败时释放已分配页"是内核行为推断，与实测吻合。
  6. 结论：`/tmp` 与内存都必须 > 4 GiB 才可能通过，6 GiB / 12 GiB 已验证，最小值未测（E04）。本包没有另跑放大资源的复跑。

### 2.3 "cwd 不在 /testbed 时导入失败"：numpy ×7 成立，datalad ×2 是误报（已验证）

- numpy 7 题：`install.sh` 用 `setup.py build_ext --inplace` 就地构建（in-tree `.so` 12 个，43e333e2 是 19 个），没有装进 venv；探针 `IMPORT_FROM_TMP_RC=1`。
- **更正 README §4 的说法**：条件是"`/testbed` 必须在 sys.path 上"，不只是"cwd=/testbed"。探针以 `cd /testbed && python /rh2/repro.py` 运行复现脚本，此时 sys.path[0] 是脚本所在目录 `/rh2`，7 题的普通导入全部失败（`IMPORT_PLAIN=fail`），脚本把 cwd 加进 sys.path 后才能导入。所以解题者把脚本放在 `/tmp` 之类的位置，即使在 `/testbed` 下执行也会 ModuleNotFoundError。可以用 `PYTHONPATH=/testbed`，或把脚本放进 `/testbed`。
- 跑测试同理：numpy 上裸 `pytest`（console script）收集即 `ModuleNotFoundError: No module named 'numpy'`（rc 2），`python -m pytest` 正常（10 passed）。原因是 `numpy/lib/tests/` 没有 `__init__.py`，pytest 把测试目录而不是 `/testbed` 放进 sys.path。18b7cd9d 实测，其余 6 题同一构建方式、按推断记。datalad 上两种都正常。这与 P1 在 aiohttp 上的发现一致。证据：`runs/r2e_env_repair_20260924/p2/followups/bare_pytest.log`。
- datalad `19f5b450` / `58ba5165`：探针 `IMPORT_FROM_TMP_RC=0`（editable finder）。M3 `pkgsrc.txt` 在 `/tmp` 下其实也导入到 `/testbed/datalad/__init__.py`，只是前面多一行 DataLad 的 git 身份警告；`collate_facts.py:171-176` 只取标记后的第一行，于是误判（见 §7）。

### 2.4 venv 无 pip（已验证，12/12）

本包 12 题的 venv 都没有 pip（`No module named pip`），pip / pip3 / uv 命令也都不存在（探针原始日志的 `WHICH_*` 行）。gcc / make / git 都有；datalad 镜像另有 git-annex。

### 2.5 期望 FAILED 键逐键分类（R06，已验证，都不是环境缺口，无提案）

- datalad `16c1ffc3`、`9ba5de09` 各 5 键（`test_dirty`、`test_paths_by_dataset`、`test_save_hierarchy`、`test_get_dataset_directories`、`test_filter_unmodified`）：`TypeError: …got multiple values for argument 'path'`。隐藏 conftest（5 题逐字相同，sha256 `551a34e5…`）的 `path` fixture 与 datalad nose 风格的 `@with_tempfile` / `@with_tree`（按位置追加临时路径）冲突，属 R2E 转 pytest 的产物，noop 与 gold 一致、确定性。公开模块里同样 5 个用例是 `fixture 'path' not found`。这些键永远 FAILED、不区分解答，只是覆盖打折。
- datalad `6b6fa389` 的 `test_get_local_file_url_linux`：`'file:///a~' != 'file:///a%7E'`。Python 3.7 起 `quote` 不转义 `~`（镜像 3.7.9 实测），上游用例按 ≤ 3.6 写，在该解释器下本就失败。它是 P2P-FAILED 键：解答若让 `~` 转义成 `%7E` 反而会判 0，风险低。
- 这 11 键里没有一个是缺依赖、缺资产、要网络或资源问题，datalad 需要的 git-annex 也在镜像里。

### 2.6 其它解题侧发现（已验证）

- **agent HOME 没有 git 身份**（datalad ×5）：`19f5b450` 复现实测 `create` 报 `Author identity unknown`；设 `GIT_AUTHOR_*` / `GIT_COMMITTER_*` 后可继续。评分不受影响（隐藏 conftest 自带临时 HOME 与身份）。
- **公开测试噪声**：不影响评分，但会误导本地验证。
  - numpy `43e333e2` 的仓库测试整体收集失败（`numpy/conftest.py:33` 的 `HealthCheck.all()` + hypothesis 6.124.1 + `filterwarnings = error`）。`-o filterwarnings=ignore` 或 `--noconftest` 能绕过，但 pytest 8.3.4 不再调用 nose 风格的 `setup(self)`，`test_extras.py` 仍有 10 failed。本批其它 numpy 镜像是 hypothesis 6.79.4 + pytest 7.4.4。
  - `d89bc4bb` 的 `test_histograms.py` 有 21 个 nose-setup ERROR。
  - `a5ea773e` 的 `test_ctypeslib.py` 有 1 个 `fixture 'self'` ERROR。
  - datalad `16c1` / `9ba5` 的 `test_utils.py` 各有 5 个 `fixture 'path'` ERROR。
  - numpy `2f4a9650` 在 rollout `/tmp` 1 GiB 下，公开 `test_io.py` 的 `test_big_arrays` 在 base 上就失败。
- **题面小问题**（移交后续题意筛查，不影响环境资格）：`19f5b450` 示例的三个导入位置不存在；`2f4a9650` 题面说 3D 数组也抛 IndexError，base 上 3D 实际不抛异常。

## 3. 本包提案清单（共享文件由主会话合并）

- **材料修订（T0，待用户）**：datalad `58ba5165` 按 §2.1。建议 `dispositions.json` 先登记隔离（C2），`decisions.md` 的"待用户决定"一节加入该条。
- **资源**：numpy `2f4a9650` 维持 `recipes/task_resources_v1.json` 现值，不改。可选：在 `why` 里补"fallocate 整数组（`convert.c:152/60/67`）→ 默认运行未写满 `/tmp`；峰值 ≈ 两份 4096.2 MiB + 基线 ≈ 340 MiB"，证据加 `runs/r2e_env_repair_20260924/p2/followups/numpy_2f4a_fallocate_source.txt`。
- **解题侧条件**（E10：进记录，不进题面）：
  - numpy ×7 的"`/testbed` 须在 sys.path"（跑测试用 `python -m pytest`，不用裸 `pytest`）；
  - 12/12 无 pip、无网络；
  - datalad ×5 无 git 身份（建议交 A 线 / 任务面决定是在 rollout 初始化写入身份，还是写进提示）；
  - `43e333e2` 仓库测试的绕法；
  - `2f4a9650` 的 rollout `/tmp` 用例。
- **`known_issues.json` 更新建议**：
  - `test_material:datalad_58ba5165` → `proposed`（证据：提案文件、`dryrun_58ba/`）。
  - `resource:numpy_2f4a9650_tmpfs` → `verified`（配方下两次）。
  - `solver_condition:import_requires_cwd_testbed`：numpy ×7 `verified`，措辞改为"须在 sys.path 上"；datalad `19f5b450` / `58ba5165` → `not_an_issue`（M3 解析误报）。
  - `solver_condition:no_pip_in_venv`：补 datalad ×5、numpy ×7。
  - `expected_non_passed_keys`：datalad 3 题已分类，无环境缺口。
  - 新增族：`solver_condition:git_identity_absent`（datalad ×5）、`solver_condition:repo_tests_broken_numpy_43e333e2`、`solver_condition:nose_style_public_test_noise`（16c1、9ba5、a5ea、d89b）、`test_conversion_artifact:datalad_path_fixture`（16c1、9ba5）、`prompt_quality`（19f5、2f4a，移交题意筛查）。
- **环境侧（后续派生配方，本轮不做）**：`43e333e2` 可把 hypothesis 固定到不弃用 `HealthCheck.all()` 的版本、pytest 固定到 < 8，须先验证 gold / noop 不变。

## 4. 未解决项

- R13：10 题只有 R-f 一次运行，待中央复跑并入（主会话）。
- datalad `58ba5165` 等用户 T0 决定；采纳 B1 后需要新材料版本、重建派生镜像，并做正式 noop / gold 各 ≥ 2 次。
- `43e333e2` 仓库测试问题只记了绕法，环境修复没做。
- numpy `2f4a9650` 最小资源未测（按 E04 不找）。
- 本包没有做定向 fresh 复跑：没有改变任何评分条件；`58ba5165` 的方案验证只是沙盒 dry-run，不是 RH2 正式评分。

## 5. 远端产物、本地回传、残留与磁盘

- 远端 `/work/envrepair/p2/`（656 KB）：
  - `repros/`（12 个，与本地 `docs/…/repros/` sha256 一致）；
  - `precheck.sh` + `precheck/`（非 root `--rm` 预检，发现并修掉 a5ea、d805 两个脚本错误）；
  - `dev_probe/`（12 题 + `summary.json`）与 `probe.log`；
  - `dryrun_58ba/`；
  - `pubtests.sh` + `pubtests/`（按 gold 触碰文件选相关公开测试模块，事后选择）；
  - `followups.sh` + `followups/followups.log`（本包所有 ad-hoc 核对的可复验版）、`followups/bare_pytest.log`（裸 pytest 对照）。
- 本地镜像：`runs/r2e_env_repair_20260924/p2/`（同上）。本地 `dev_probe/*/dev_probe.json` 已按 parser v2 重解析（带 `reparsed_at_utc` / `parser_version: 2`，`derived` 不变），所以与远端 v1 副本字节不同，原始 `agent_probe.log` 两边一致。另有：`_rerun2/`（中央复跑 `numpy_bigtmp` 两行与脚本、日志的副本）、`followups/numpy_2f4a_fallocate_source.txt`（本地 tee 保存）。
- systemd unit（远端时钟 UTC 09-23）：`r2e-p2-precheck-1824`、`r2e-p2-probe-1825`、`r2e-p2-dryrun58ba-1838`、`r2e-p2-pubtests-1840`、`r2e-p2-followups-1846`，都已退出。
- 探针命令：`/work/code/rh2/.venv/bin/python /work/code/rh2/scripts/r2e_env/run_dev_probe.py --repo-root /work/code --overlays /work/r2e_derived/overlays.jsonl --task-ids <12 个 iid> --out-dir /work/envrepair/p2/dev_probe --repro-dir /work/envrepair/p2/repros --activation none`。远端 `run_dev_probe.py` 与 `dev_probe_agent.sh` 的 sha256 与本机、`r2e_env_tools.sha256` 一致。
- 收尾检查：`docker ps -a` 里没有本包起的容器（`rh2-devprobe-<本包 12 题>`、`p2pre-*`、`p2pub-*`、`p2dry-*`、`p2fu-*` 都用了 `--rm` 或已由工具删除）。当时在跑的是中央复跑与 P3 的容器，本包没有碰。磁盘：开始 45 GB 可用，结束 44 GB 可用。没有构建或删除镜像，没有写 `/work/replay`、`/work/r2e_derived`、`/work/code`。
- 途中一次 ssh 被对端关闭（`Connection closed`），重试即恢复，疑似多会话并发连接触发 sshd 限流；没有影响结果。

## 6. 耗时（与中央复跑和其它包并发，不作校准）

- 包整体约 60 min（本机 +08 02:05–03:05）。
- 探针 12 题合计 681.8 s：datalad 66.6–123.3 s/题，其中 `chown -R /testbed` 60.8–111.9 s；numpy 23.9–36.9 s/题，其中 chown 18.5–28.5 s。chown 比 09-24 试跑（datalad 53 s、numpy 12 s）慢约 1.6–1.9 倍。
- 预检约 1 min；dry-run 约 1 min；相关公开测试约 5 min；follow-ups 约 2 min。

## 7. 流程 / 工具改进建议

1. **`run_dev_probe.py` 丢键（已由主会话修复）**：旧正则 `^[A-Z][A-Z0-9_]*=` 不收含小写或连字符的键，`WHICH_python`、`WHICH_gcc`、`WHICH_xvfb-run` 等没进 `dev_probe.json`。主会话已改为 parser v2 并加了 `--reparse`；本包本地 12 份 `dev_probe.json` 已用 `--reparse` 重建：`derived` 与重建前逐项相同，新增 10 个 `WHICH_*` 键。远端副本仍是 v1。
2. **探针公开测试与入口不同条件**：`PREFIX` 只取 `.venv/bin/python` 之前的环境变量，漏掉入口里的解释器参数 `-W ignore`。建议同时解析 `python` 与 `-m pytest` 之间的参数，按入口原样运行。
3. **公开测试选择太弱**：固定取测试目录里第一个 `test_*.py`（`numpy/tests/test_ctypeslib.py`、`datalad/tests/test__main__.py`），与题目无关。建议仿 `--repro-dir` 加 `--public-tests-dir <iid>.txt`，由审查者按题面列出相关模块。本包用 `pubtests.sh` 补做了这一步。
4. **复现脚本的导入语义**：`python /rh2/repro.py` 让 sys.path[0] = `/rh2`，就地构建的包（numpy）在 cwd=/testbed 下也导入失败。这本身就是真实的解题侧条件，建议在 `repros/README.md` 里写明：脚本先试普通导入并打印结果，失败再把 cwd 加进 sys.path。本包 12 个脚本都这样做了。
5. **`collate_facts.py` 的 M3 导入判断**（`:171-176`）只取标记后第一行，DataLad ≥ 0.17 的 git 身份警告会占据这一行，造成 `import_outside_testbed_ok_m3=false` 误报（19f5b450、58ba5165）。建议改成取下一个 `###` 之前最后一个非空行，或第一行以 `/` 开头 / 含 `Error` 的行。
6. **摄入期静态检查**（58ba5165 这类）：隐藏测试 import 的仓库测试模块，如果在上游 `modified_files` 里又被 gold 排除，就标记"缺支撑材料"。
7. **分类口径**：全池共性（无网络，以及大部分题无 pip）是否单独构成 `solver_condition`？P1 把有 pip 的 coveragepy 记为 `env_ok`；本包把无 pip 的题记为 `solver_condition`（README §5 的例子）。建议主会话统一：`solver_condition` 只用于超出全池基线的题 / 仓库特有条件，全池共性在 README 记一次。按这个口径，本包的 datalad 4 题可以归为 `env_ok`（git 身份算仓库级条件时除外）。
8. **探针可加两项**：`git config user.email` 是否存在（datalad 类任务需要），以及 hypothesis / pytest 版本。
9. **`checks_r2e.md` R14 措辞**：账本里的 `omitted_cache_count` 是 `{baseline, post}` 计数对象，不是 0 / 非 0，建议改为"baseline == post"。

先后声明（E06）：12 个复现脚本只依据公开 prompt 与镜像内公开源码（`/testbed`）写成，写在读 expected / 隐藏测试 / gold 之前。开工时按派发要求读过 `facts_summary.md`（只有计数），`facts.json` 只看了键结构（其中出现过一个测试名）。预检后修了两个脚本错误（numpy 1.10 没有 `np.shares_memory`；`"mask"` 切分误伤 `masked_array(`），都与隐藏材料无关。之后的分析读了隐藏测试、gold 与来源原始行（validation_only，只用于分析）。
