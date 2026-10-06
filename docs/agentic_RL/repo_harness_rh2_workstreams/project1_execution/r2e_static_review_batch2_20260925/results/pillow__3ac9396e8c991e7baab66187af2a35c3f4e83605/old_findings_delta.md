# 历史对照：pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605

私有主审，2026-09-25。初判 `analysis_before_history.md` 已封存，本文不改动它。

**读取范围**

- `history/.../refs.json` 列出的全部材料：
  - 本题的 `screening_record.json`、`findings.md`、`facts.json`；
  - `known_issues.json` 中与本题相关的族（`solver_condition:public_test_noise`、`no_pip_in_venv`、`expected_provenance_mixed`、`prompt_quality_candidates`、`expected_non_passed_keys`，并逐族确认其余族没有提到本题）；
  - `decisions.md`、`results_20260924.md` 中本题那一行、复现脚本、`packages/p4/README.md` §0–§3。
- `known_issues` 引用的 `runs/r2e_t0_batch2_20260924/provenance/expected_provenance.md`，只看了本题所在的行。
- 协调者 09-25 在 derived9 上跑的 noop / gold 账本与日志。
- 为了核对未跟踪文件怎样交付，只读查看了 `rh2/src/repoharness2/grading/manager.py:325-373` 的导出脚本。

没有读：`reconcile.json`、P4 的 `dev_probe` / `targeted*` 原始日志、`image_readout`。

**历史的定位**：09-24 的 P4 环境审查。它的 scope 是"环境资格（不含题目质量 / 训练准入）"，结论是 `solver_condition` / `environment_qualified`。本轮是题意与评分的静态审查，两者范围不同，不冲突。

## 1. 旧主张逐条对照

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| H1 | 材料、镜像、HEAD 与评分面一致（R01） | 确认 | 隐藏测试 5 个文件、gold、`run_tests.sh`、期望映射的 sha256 与摄入面逐一相同。09-25 在 `c9ec14f7…` 上跑的 noop / gold 两份日志中，`RH2_SETUP_HIDDEN_TESTS_TREE=43f98461…`，recipe 摘要为 `0da821a1…`，与历史运行相同。 |
| H2 | noop 得 0 只因目标键 `test_exif_div_zero` 为 ERROR，原因是 `struct.error: required argument is not an integer`，与题面一致（R02、R16） | 确认，并扩大了范围 | 现在共有 5 次 noop，分布在 3 个 build 上：`74c3618c`（reps）、`7a80aa71`（requal / all / 环境轮复跑）、`c9ec14f7`（09-25，`ledger_p3ac9_noop.jsonl`，日志 `…ed969340eccc-pill_029f6ef4`）。5 次都只有这一个键为 ERROR，traceback 都停在 LONG writer（`TiffImagePlugin.py:571/546`）。 |
| H3 | R13"已 3 次一致"（findings、P4 README §0） | 过时 | `facts.json` 的 auto_checks 已记为 4 次；加上 09-25 的运行，noop 与 gold 各 5 次，reward 与差异集合全部一致；另有 M3 的 gold 2 次，均 11 passed。 |
| H4 | 与独立 runner 对账一致，noop 与 gold 两行都 agree（R15） | 部分核实 | gold：M3 a1 / a2 日志的 11 个键与 RH2 逐键相同（本人核过）。noop 的参考侧：没有打开 `reconcile.json`，未核实。 |
| H5 | 解释器 `/testbed/.venv/bin/python` 3.9.21；editable finder 安装；在 cwd=/tmp 下也能导入 `/testbed/PIL`；`_imaging` 是树内 `.so`；`pkg_version="?"` 属正常（R05） | 确认 | devcheck 走的是正式启动链，以 agent 54321 身份运行：`env.out` 与 `pr0_1_cmd.out` 显示 `PILLOW_VERSION` 为 3.1.0.dev0，`Image.core` 位于 `/testbed/PIL/_imaging.cpython-39-…so`。评分侧 `RH2_OBS_IMPORT_PATH=/testbed/PIL/__init__.py`，在 3 个 build 上都一样。 |
| H6 | venv 里没有 pip（R05，`no_pip_in_venv` 族） | 确认 | devcheck 输出 `No module named pip`。 |
| H7 | issue 1：公开提示写"`pip` already points at it"，还有 conda 措辞，与环境矛盾 | 过时 | 当前 v3 的 `public_hints` 已改为"`pip` may be unavailable"，并使用 `.venv` 措辞，不再提 conda（`public_bundle.json`）。"没有 pip"这一事实仍然成立，但提示已经不再矛盾。 |
| H8 | issue 2（R09，`public_test_noise` 族）：用 pytest 跑公开 Tests/ 会假失败，`test_file_tiff_metadata.py` 3 例假失败、4 例通过；`python Tests/test_x.py` 可用；`cd Tests && python -m unittest` 出 5 个 errors | pytest 部分确认，并提高严重度；另两条未核实 | devcheck pr7_4 中，metadata 文件为 `.F...FF`，即 3/7，与历史一致。范围比历史写的大：同目录的 `test_file_tiff.py` 另有 6 例；jpeg 用 `-k exif` 有 1 例；libtiff 有 13 个 FAILED 加 2 个 ERROR；base 与 gold 两侧计数相同。在 `/testbed` 下用 `PYTHONPATH=Tests python -m unittest …` 可跑 42 个、全 OK，这是新的可用方式。**严重度提高**：v3 提示明确要求"run them from /testbed with `python -m pytest`"，噪声恰好落在提示指定的路径上。历史把是否写进提示留给任务面决定（E10），目前仍未处理。另外两条（`python Tests/test_x.py` 与 `cd Tests` 的写法）本轮没有重跑。 |
| H9 | 期望 11 个键全部 PASSED；自定义 runner 的输出能被 parser 正确解析；"orphaned temp file"提示无害（R06、R09、P4 §3.2） | 确认 | 我读过 runner 源码（`_test_id`、short summary 段）和日志。"orphaned temp file"来自 helper 只在整场测试成功时才删除临时文件。 |
| H10 | 需要清理的测试文件共 6 个，与 gold 的触碰路径不相交（R04） | 确认 | `RH2_SETUP_EXPECTED_TEST_FILES=6`；gold 的 `included_paths` 只有 `PIL/TiffImagePlugin.py` 与 `PIL/TiffTags.py`。 |
| H11 | `/testbed` 可写，`/usr/local` 不可写；`site-packages` 在 `.venv` 内，chown 后 agent 可写，"反作弊面另议"（R07） | 权限部分确认；反作弊部分只做了静态补充 | devcheck 的 prelaunch 记录 `WORKDIR_WRITABLE=1`、`ACTIVATION_WRITE=DENIED`。导出候选用的是 `git add -N . && git diff --binary HEAD`（`manager.py:330-373`），遵守 ignore 规则；容器里 `git status` 看不到 `.venv`，所以对 venv 的改动不会交付到 fresh grader。这属于共享机制，本轮没有实跑。 |
| H12 | 没有出网（R10） | 确认 | 正式链里外部 DNS 与目标主机都 DENIED，只有 relay 可达（prelaunch）。历史探针用的是 `--network none`，与正式链是等价关系，不是同一条件。 |
| H13 | 资源足够（R12） | 确认 | 09-25 两次运行内存峰值约 362 MB，测试阶段约 0.08 s。 |
| H14 | 泄漏面：`fix_present=no`；HEAD 没有子提交；没有 refs / remote / reflog；`install.sh` 是通用脚本（R17） | git 部分确认，`install.sh` 未核实 | devcheck 的 preflight 与 prelaunch 探针（`GIT_REFS=0`、`GIT_REFLOG=0`、`GIT_REMOTES=0`）；在工作树里 grep 不到未来测试名或修复代码。`install.sh` 不在公开包里，我没有读。 |
| H15 | 镜像自带的 pyc 由 base 源码编译，不是泄漏载体（R14） | 未核实 | 本轮没有检查 pyc 头。 |
| H16 | 公开复现 `REPRO_OBSERVED=1`（复现脚本） | 确认 | devcheck 在正式启动链上跑了 pr3_2 与 pr6_3，得到同一个报错。 |
| H17 | 期望映射与镜像一致，但与来源宿主机记录差 1 个键：`Test_IFDRational.test_ifd_rational_save` 在宿主机上是 ERROR（`expected_provenance`，E=I≠H） | 确认其含义 | 这个键会走 libtiff 编码器（`WRITE_LIBTIFF=True` 那一轮）。镜像里有 libtiff（devcheck 中 `libtiff_encoder True`），3 个 build 上都 PASSED。**补充**：今后重建镜像时，如果缺少 libtiff，gold 会得 0。这是一个依赖环境的回归键。我没有重读宿主机记录本身。 |
| H18 | 本题没有题面问题（未列入 `prompt_quality_candidates`） | 不成立（历史没有审查题意，这里视作"未覆盖"，不是推翻） | 见 §3 的新发现 N1、N2。 |

## 2. 我对初判的修正

- **运行证据的 build**：初判说"4 组 current 运行都在 `7a80aa71` 上"，这不准确。reps 那组用的是重建前的 `74c3618c`。更正为：noop 与 gold 各 5 次，分布在 3 个 build 上，结论不变。
- **"评分镜像与 devcheck 镜像不同"这一缺口已关闭**：协调者在 `c9ec14f7` 上用正式评分代码各跑了 1 次，noop 为 0（10/11，目标键 ERROR），gold 为 1（11/11），`scripts_digest` 与 `grader_profile_digest` 都与历史运行相同。
- **"未跟踪的 `temp.tiff` 怎样投影"改为静态已答**：导出脚本先 `git add -N .` 再 `git diff --binary`，`*.tiff` 不在 `.gitignore` 里，所以这个文件会作为二进制新增文件被交付和重放。隐藏测试不读 `/testbed/temp.tiff`，预计不影响得分。建议队列里的 S2 从"必做"降为"可选实跑"。
- **`PIL` 的导入机制已查明**：是 editable finder（`facts.json` 的 `pth_line_m3`：`__editable___Pillow_3_1_0_dev0_finder`），不是把 `/testbed` 放进 `sys.path`。初判里"隐藏测试用 `r2e_tests/helper.py`"这一结论不受影响。
- 处置、K1–K4 的预测、其它问题判断：都不变。

## 3. 历史没有覆盖、本轮新增的发现

- **N1**：题面把原因归到"零分母"。devcheck 在 base 上实测：41988 写 1/2 同样失败，282 写 0/0 正常。这是误导性表述，但不构成冲突。
- **N2**：目标测试只覆盖题面的字面例子，只特判零分母（K2）或只注册 41988 并设长度 0 的部分修复也能得 1。目前是静态推断，待实跑。
- **N3**：gold 顺带把未注册整数标签的类型码从 LONG 改成了 SHORT，没有测试覆盖。
- **N4**：本题的修复（演化后的形态）和两个新增测试，已经出现在同仓另外 6 题的公开初态里：`2b061b68`、`2d01f7d0`、`4bc64835`、`3a61c9e9`、`f9d3ee0f`、`a682ceaf`，我逐个核对过。逐字比对的 gold 扫描漏掉了这一关系，因为上游后来重构过这段代码。历史的 `no_pip` 族虽然把这 7 题列在一起，但没有记录它们之间的包含关系。
- **N5**：上面 H8 的噪声现在正落在提示指定的运行路径上。
- **旁注**：设计对照 c（`pillow_sleep.patch`）在导入阶段就报了 SyntaxError，没有测到"期限耗尽"。

## 4. 处置是否改变

不改变。历史的 `environment_qualified` 属于环境资格，本轮在它之上补充题意层面的结论：作为开发诊断用的静态候选，保持 needs_review，理由是"静态候选，待 actor 验证"；不需要材料修订。与历史的主要分歧只有两点：一是历史的 issue 1 在当前 v3 提示下已经过时；二是历史没有覆盖题意与跨题包含关系（N1–N4）。
