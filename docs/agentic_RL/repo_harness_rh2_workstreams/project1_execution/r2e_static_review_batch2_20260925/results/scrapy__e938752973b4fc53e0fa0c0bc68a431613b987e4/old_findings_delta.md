# 旧主张核对：scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4

角色：R2E 私有主审（第二批）。日期：2026-09-25。前稿 `analysis_before_history.md` 写于读历史之前，本文不改它。

## 读了哪些历史

- **本题记录**：`refs.json` 列出的全部路径，包括本题的 `screening_record.json`、`findings.md`、`facts.json`（`r2e_env_repair_20260924`，P4 包，2026-09-24），以及复现脚本 `repros/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4.py`。
- **汇总文件**：
  - `known_issues.json` 里本题所在的两个族：`solver_condition:no_pip_in_venv`、`solver_condition:public_test_noise`；
  - `decisions.md` 里的 E09–E11 与 scrapy 相关行；
  - `results_20260924.md` 里的本题行；
  - `packages/p4/README.md`。
- **原始证据**：
  - P4 探针的三份 `agent_probe.log`，以及 `image_readout`；
  - 派生镜像的 `facts.json`；
  - `reconcile.json` 里本题的两行；
  - R-f `prompts.jsonl` 里的本题行。

旧记录的范围是**环境资格**，不含题目质量和训练准入。它的检查编号是环境清单 R01–R20，不是 40 项清单。

## 逐条判定

| # | 旧主张（来源） | 判定 | 新的决定性证据 |
|---|---|---|---|
| 1 | 分类 `solver_condition`，处置 `environment_qualified`（findings、disposition） | 确认 | 4 次 current 评分与 M3 两次参考逐键一致。本审的"静态候选、needs_review"属于题目质量范围，两者不冲突 |
| 2 | R01：派生镜像复核通过；探针容器镜像是 `1517a0c4…`；HEAD 等于 base | 确认（只对 `1517a0c4…` 成立） | 账本的 `image_id_actual` 与 P4 `image_readout` 都是 `1517a0c4…`。补充两点：本批 devcheck 和私有 gold 对照用的是 `a2fe6dfe…`，不是同一个 ID；R01 写"21 项"，而 facts.json 记 `checks_total: 20`（另有 3 行预检）。计数口径未核实，不影响结论 |
| 3 | R02、R16：noop 得 0 只因为目标键；失败原因与题面一致 | 确认 | R-f noop log 第 34 行是 AssertionError；账本 `mismatched` 只有 `PythonItemExporterTest.test_export_binary`；09-24 复跑结果相同 |
| 4 | R03：公开复现在 base 上成立；题面里的 `TestItem` 来自测试模块 | 确认 | devcheck `pr1_1_cmd.out`（agent 身份，镜像 `a2fe6dfe…`）；P4 探针 `REPRO_OBSERVED=1`（镜像 `1517a0c4…`） |
| 5 | R03 "conda 提示属全局 E09"；issue 1 "公开提示写 `pip` already points at it"；known_issues 的 no_pip 族也是这句 | 过时 | 当前 v3 公开包的 `public_hints` 已换成 R2E 措辞：写的是 `.venv`、"`pip` may be unavailable"，没有 conda（`public_bundle.json`，环境卡 §2 同）。"没有 pip"这个事实仍成立（devcheck `env.out`：No module named pip）。现在只剩一个未知：提示怎样送达模型 |
| 6 | R04：gold 只改 `scrapy/exporters.py`，与评分卫生文件不相交；解题不需要改测试辅助文件 | 确认 | gold 账本 `projection.included_paths` 为 `["scrapy/exporters.py"]`，`ignored_paths` 为空；隐藏测试文件自己定义 `TestItem`，不导入 `tests` 包 |
| 7 | R05 与 solver_conditions：`python` 是 `.venv` 里的 3.9.21，pytest 8.3.4，没有 pip，editable 安装，`cwd=/tmp` 时也导入 `/testbed/scrapy` | 确认 | P4 `agent_probe.log` 的 `IMPORT_FROM_TMP=/testbed/scrapy/__init__.py`；`image_readout` 里的 install.sh 含 `uv pip install -e .`；devcheck `env.out` 复现了前三项。这回答了我初判的未知项 5（只在 `1517a0c4…` 上实测） |
| 8 | R05、issue 2、public_test_noise 族：Scrapy 1.1 与镜像里的 Twisted 24.11 不兼容，抓取类公开测试恒失败；exporters 路径不受影响 | 确认（只在 `1517a0c4…` 上） | `targeted2_cmds` 日志：`tests/test_closespider.py` 3 failed / 1 passed，报 ImportError `HTTPClientFactory`；`tests/test_exporters.py` 在 P4 定向运行和 devcheck pr3 两处都是 61 passed。devcheck 没有跑 closespider，所以 `a2fe6dfe…` 上未复核。我的初判漏了这一条，已补进开发需求 |
| 9 | R06：期望 62 个键全部 PASSED | 确认 | `expected_output.json`；账本 `expected_total` 为 62 |
| 10 | R07：`/testbed`、home、`/tmp` 可写，根文件系统不可写 | 确认 | P4 探针的 `WRITE_*` 各行；devcheck `prelaunch.json`（`WORKDIR_WRITABLE=1`、`TMP_WRITABLE=1`） |
| 11 | R07 附注：venv 目录也可写，列为共享问题另议 | 未核实 | 属于共享机制，不在本题判定范围 |
| 12 | R08：评分时导入的是候选代码 | 确认 | 账本 `RH2_OBS_IMPORT_PATH` 为 `/testbed/scrapy/__init__.py`，版本 1.1.0dev1 |
| 13 | R09：公开测试与复现 | 确认 | 证据同第 7、8 行 |
| 14 | R10、R11：没有网络，也不依赖外部服务 | 确认 | P4 探针 `NET_CONNECT_RC=1`、`NET_DNS_RC=2`；devcheck `DNS_EXTERNAL=DENIED`；exporter 测试都只在内存里运行 |
| 15 | R12：内存峰值约 209 MB | 确认 | 账本 `resource.mem_peak_mb` 分别是 209.531 和 208.703 |
| 16 | R13：noop、gold 各跑两次，结果一致 | 确认 | 两对日志除时间戳和耗时外逐字相同 |
| 17 | R14：每次评分用新容器；探针没有弄脏工作区 | 确认 | 账本 `omitted_cache_count` 为 0；devcheck 运行后 `RH2_GIT_STATUS_LINES=2` |
| 18 | R15：与独立 runner 逐键一致 | 确认 | `reconcile.json` 里本题两行都是 agree；M3 两次都是 62 passed |
| 19 | R17：镜像里没有修复泄漏 | 确认 | 派生镜像 facts：`fix_present=no`、`children=1`、私有目录权限 700；devcheck 的 `git_sanitize` 与预检也通过。旧记录没有覆盖跨题可见性，本审新增了这一项：本题修复出现在 `a95a338e`、`75450e75` 的公开初态里，本题初态又含 `9a15fcf8` 的修复。这是数据集层面的问题，不是容器内泄漏 |
| 20 | P4 README §7.1：dev_probe.json 的 `pip_ok=true` 是工具误判 | 确认 | `agent_probe.log` 的 `PIP_VERSION` 是 "No module named pip" |
| 21 | 处置理由"无未归因 issue" | 确认（在环境范围内） | 题目质量层面有三项不在旧记录范围内：binary 模式只测了原例（C2 待实跑）、gold 有未测回归（E1 待实跑）、同仓包含关系。这些是新增，不是推翻 |

## 改判与理由

- **没有推翻任何旧主张。** 暂定处置不变：静态候选，`needs_review`，理由是"静态候选，待 actor 验证"。
- **更新 1**：初判的未知项 5（在 `/testbed` 以外能否导入）已由旧探针回答：scrapy 是 editable 安装，`cwd=/tmp` 时可以导入（在 `1517a0c4…` 上实测）。
- **更新 2**：开发需求补一条解题侧噪声：跑 `tests/` 下的抓取类测试会看到与本题无关的失败，而相关文件 `tests/test_exporters.py` 全部通过。影响低，因为公开提示已要求只跑单个测试文件。
- **更新 3**：清单第 3 项里"提示与环境矛盾"一条已经过时，剩下的只是送达方式没有验证。
- **与旧记录无关的部分**：旧记录没有做题意、测试或 gold 的对照，所以 C1、C2、C3、E1 和题目关系的结论都是本审新增，与历史没有冲突。
