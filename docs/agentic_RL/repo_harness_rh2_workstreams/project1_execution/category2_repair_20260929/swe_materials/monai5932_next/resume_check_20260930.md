# MONAI5932：换机续接检查

2026-09-30。本轮仅做本地读取、摘要核对和续接方案，未改共享代码、原材料、历史结果或登记清单；未 SSH、下载、运行容器、项目测试、GPU 或模型。

**结论：题级材料及正误候选本地齐全，摘要吻合，可以继续准备下一片实现。正式“新增测试补丁”能力尚缺，不能直接激活候选。原镜像可按固定摘要恢复的说明齐全，但本地题级包没有镜像层备份或完整离线重建包；新机器取得原镜像及 actor 运行时仍是实际前置项。** 新版验收建议限定为三次候选正式 CPU 评分，加一次真实 actor 固定命令桩及其原工件直接评分。

[原准备说明](README.md)中的“等待首两道 mypy 收口”已由 [D6 最终验收](../../d6/acceptance_result.md)及[固定交接包](../../d6/handoff_mypy_v2.json)满足。原说明保留其历史时点；本轮不因此扩大到其它题，也不把 MONAI 候选标为已实施或已执行。

## 本地已确认的事实

本轮使用 Python 标准库逐项读取原文件、重算 SHA-256 和字节数；未重新运行旧实验，也未执行候选测试。

| 检查对象 | 本轮结果 | 结论范围 |
| --- | --- | --- |
| [材料清单](materials_manifest.json)的带路径 SHA／大小记录 | 37 项全部吻合，涉及 35 个唯一路径、286,664 字节 | 包括原件及冻结副本、候选补丁／参考、历史结论文件和五个实现接缝快照；重复路径未计为独立资产。 |
| 原 ingest 四份材料的第 20 行 | public、grading、validation、environment 的 canonical JSON digest 全部吻合 | 题目、base、原正对照和环境绑定仍对应同一题。 |
| T1 输入链 | pins 文件自身及其七项输入的 SHA 全部吻合 | 含本地原始 SWE JSONL、镜像身份记录和 vendor 配方；不需要向旧主机索取这些输入。 |
| 09-29 MONAI 证据清单 | 88 个本地原始文件全部存在，SHA／长度吻合，共 1,373,282 字节 | 可继续引用当时的 actor、行为对照、三次原材料评分和清理证据。 |
| 原隔离检查副本 | 五个 Python 文件 SHA 与 `static_checks.json` 一致 | 完整有效补丁结果与“原补丁＋增量补丁”仍相同；本轮没有重做 apply 或执行项目代码。 |
| D6 v2 固定交接 | code manifest、登记清单、产物 manifest、集成 patch 的 SHA 全吻合；固定代码 660 个文件逐个吻合；当前共享区 18 个 D6 overlay 全吻合 | 新片可在该版本基础上做窄增量；不应整树覆盖其它在制工作。MONAI 所需的五个接缝仍与原准备清单一致。 |

D6 code manifest SHA 为 `4110b196c8df1f0e8d51595b525eed17f6487977d83e59e2fddd68f5f11d965b`。这里核的是文件身份，不是重新执行 D6 的 130 项测试；历史验收按其原范围复用。

题级身份继续绑定 `Project-MONAI__MONAI-5932`，base `3c8f6c6b94ba26f8c9df5b7c96089494de6f69cb`，tree `20622b7558fea650c1224a972c03931f77a93836`。关键文件如下，完整来源路径和大小沿用材料清单：

| 资产 | SHA-256 |
| --- | --- |
| `original_test.patch` | `02d19ce0af297aa91a325ae216fcff1a1929f7a10a65ce7af79668141047d006` |
| `extra_tests.patch` | `cac57ff343f847e6eefea0343dd2b19f06778af446f94c31d8349a9ddd4df9d0` |
| `effective_test.patch` | `89e5866d51767720bac55dbacc80cebdfb5f2f82edd29445a6ff468d9bd1dbd5` |
| `references_candidate.json` | `b17d3a4c1acd5ec7af278ce2b7214e8ad224849e4e7715b8900073c9462ea33a` |
| `controls/gold.patch` | `811f539ac23d7a2a76fb6b541abfaa7912579730f8683574cf08cad634e2534e` |
| `controls/degenerate_reverse_order.patch` | `00e221311a9249e2a35bc24b171b9e1eac5581188f693d5451f03a9161d3b9cb` |
| `controls/noop.patch` | 空文件，`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

候选仍只追加 `tests/test_config_parser.py::TestConfigParser::test_substring_reference_long_first`：通过公开 `ConfigParser` API，断言长引用先出现的表达式 `2 + 1 + 1` 得到数值 **4**。原 F2P 和 14 个 P2P 均保留。公开语义、现有 unittest 风格、正误候选的来源与适用限制见原 README；本轮没有重新审题或绑定 gold 内部算法。

## 最小尚缺的正式能力

当前 `swe_material_revisions.py` 的 `SWERevisionRecord.operation` 仍是 `Literal["append_mypy_p2p"]`，repo 仅 `python/mypy`。`bundles_v2.py` 的修订模型同样只保存 `added_mypy_cases`，`_apply_one` 不替换原 `test_patch`。因此现成 mypy 通道不具备本题所需的“新增项目测试”执行能力；改参考列表或加私有 shell 后检都不能补齐它。

下一片只需增加受信的**完整有效测试补丁＋显式新增 P2P**操作，消费现有候选，不需要任意补丁插件或新奖励逻辑。具体接缝：

1. **登记、重放和父版本校验。** 在受信登记和私有修订模型中保存原／有效补丁及 SHA、唯一受测文件的 base SHA、原参考与精确新增 P2P。有效补丁从 immutable base 应用；原补丁原字节保留。当前父 digest 校验只还原原参考，新操作还必须还原原 `test_patch`，再核 `parent_grading_digest`。固定登记及产物另存新版本，重算材料／环境身份，不能继承旧资格。
2. **命令按操作分派。** `spec_vendor.derive_test_command_for_bundle` 当前把全部修订包送入 mypy `-k` 分支；新操作应复用已有通用文件派生。这里仍是原 vendor 命令 `pytest -rA  tests/test_config_parser.py`（原前缀尾部空格使文件前有两个空格），不需要新增 shell、parser alias 或参考重命名。
3. **可信恢复、保护和分区诊断。** `prepared_task_face.py` 的 `_v2_test_files`、`_v2_revision_baseline_checks` 和新增 P2P 投影目前都依赖 `added_mypy_cases`；须按新操作读取已登记文件与参考。仍仅保护 `tests/test_config_parser.py` 整个文件，核 base SHA、补丁应用、有效内容与权限；actor/replay 共用现有 builder、材料身份和私有诊断链。

实现和窄测试须覆盖父补丁恢复、文件／参考错配拒绝、新旧材料混配拒绝、原参考不变、effective patch 真正执行，以及 mypy 原操作兼容。保留完整 baseline 硬比较（含 `.git` 排除区摘要）、既有 HEAD 校验、权限／网络边界、公共 report 和二值奖励；没有理由再改 Git sanitizer。D6 已修好的同源初始化只在两道 mypy 的镜像／profile 上获 CPU 验证，MONAI 必须补自己的三端一致性证据。

## 原镜像与离线环境能恢复到什么程度

原镜像固定引用为：

```text
xingyaoww/sweb.eval.x86_64.project-monai_s_monai-5932@sha256:84a4d4afe3f663633da40359ddb8ff5c0e951144e103bed27b907481f9cee6f4
```

本地 `runs/swegym_cpu_preprobe_20260929/task_inputs/Project-MONAI__MONAI-5932/` 的 `buildplan.json`、`recovery.json`、`restore_original.sh` 与 `remote/inputs_v1/` 对应副本逐字节一致。模式是 `use_original_no_repair`；恢复脚本只拉取上述 digest、记录 inspect 和引用。本题没有新增依赖 pin 或派生镜像配方，不能套用 mypy 的 `install_wave1` 或其它 MONAI 题的 wheel 修复。

本地 `remote/results/Project-MONAI__MONAI-5932/mixed-v1/` 保存了以下历史事实：

- `pull_original.log` 证实 09-29 按该 digest 成功取得镜像，但其中 11 层显示 `Already exists`，只新取了最后两层；这不是空缓存冷机完整重建证据。`buildplan/recovery` 中旧的“仅语法检查／cold_rebuild_verified=false”不能覆盖后来成功拉取事实，也不能反过来把成功拉取说成完整离线构建。
- `original_image.json` 记录 Linux/amd64、13 层、配置 ID `sha256:833da815aeee5132d737c83e3af72b822b5a2e0498368287014919cef084dd49`、镜像大小 11,203,759,356 字节；大小不是下载量或新机磁盘需求总量。旧 `:latest` 当时与该 digest 对应，今后不以 tag 代替固定摘要。
- 三次 grader 均为 `deny_all`，原 `pip install -r requirements-dev.txt` 和 `python setup.py develop` 完成，安装约 9.58–9.88 秒；使用镜像内已有环境即可跑旧评分，无额外题级供应镜像。actor 激活 `/opt/miniconda3/envs/testbed`，Python 3.8.20、numpy 1.24.4、torch 1.13.1、pytest 8.3.3、parameterized 0.9.0，从 `/testbed/monai` 导入。
- 原镜像初态已有 `requirements-dev.txt` 修改。历史 gold 完整 eval log 的 490–498 行展示删除 `MetricsReloaded` URL 的 hunk，与恢复说明一致；这不是新候选改动。新机要记录实际初态 diff／SHA，不能称镜像 pristine，也不要在恢复后再手工制造一次未知差异。

**缺资产／尚未证明：** 在本次检查的本地仓库 `runs` 文件清单和本题输入包中，未找到可绑定该 digest 的 Docker/OCI 镜像层导出、完整依赖 wheel 仓或可离线从零造出同一镜像的构建配方。公开 base 自带的 `Dockerfile` 是 MONAI 项目容器配方，并非 SWE 固定镜像的复现配方。本地 inspect、SHA 和源码快照不能代替镜像层。新机可以尝试从 registry 按 digest 取得原镜像；本轮未联网，因此其当前可取得性未知。若该 digest 无法取得，应记录缺失资产，不能换 tag 或临时重装依赖后声称同版本恢复。

此外，旧执行器 `mixed_followups.py` 明确引用 `cc/claude-code-linux-x64-2.1.205.tgz`。本次仓库全文件名检索未找到该精确 Linux 包；版本证据在本地不等于安装包已备份。新机需由公共运行环境准备流程取得并核验固定 CC 运行时及 relay 等共享供应资产，再记录实际版本／摘要。这里没有检查系统外部缓存或全套主机供应链，不声称它们全局不存在；旧主机地址、端口和 `/work` 路径都只能当历史证据值。

## 新机器的最小补验

接线、窄测试及独立审查后，在新固定代码／材料版本下重新 prepare MONAI；不改旧 prepared，不给旧 actor 工件换材料标签。先取得固定镜像并核 manifest、配置 ID、HEAD、初态 diff、激活解释器和实际导入路径。若这些发生变化，先说明差异，不能继续沿用旧资格。

| 新运行 | 必须看到的结果（预期，尚未执行） | 为什么不能用旧证据替代 |
| --- | --- | --- |
| 修订版 replay noop | 原 F2P 失败、原 14 P2P 通过、新 P2P 通过；reward 0，1 failed／15 passed | 证明新测试是 base 已满足的回归要求，且新版材料真实执行。 |
| 修订版 replay gold | 原 15 条和新增 1 条全通过；reward 1，16 passed | 正对照通过有效补丁、安装和新选择／保护链。 |
| 修订版 replay reverse_order | 原 15 条通过、新 P2P 因目标长引用解析错误失败；reward 0，1 failed／15 passed | 把已证旧满分误解拒绝于正式评分；不能把缺包、collection 或准备错误当拒绝成功。 |
| 一次真实 CC 固定命令桩 actor，然后同次冻结工件交 fresh grader 直评 | actor 正式身份、公开开发检查、静止屏障和冻结导出有效；原样 noop 工件被接受，完整 baseline 相等，修订材料身份一致，16 参考实际执行、reward 0 | D6 的 actor/replay/grader 初始化一致性尚未在 MONAI 镜像证明；仅 replay 三行不覆盖 actor 工件直评。 |

这是**三次 replay 评分＋一次 actor 工件直评，共四次完整评分**，另含一轮 actor 公开开发检查，不是四个模型样本。actor 仅运行公开身份／导入及已有相关开发测试（旧证据为 18 passed）；新私有测试和 gold 不进入 actor 可见面。使用真实 CC 配合固定命令桩，不需要 GPU 或模型自主求解。

每行核完整 16 个精确 nodeid、原／新增分区、测试返回码、无缺失／skip／collection 错误，安装子命令、候选源码实物摘要、受保护测试字节和不可写性，以及账本／容器／网络清理。无需另起整库测试；真实 collection 可在这轮安装后的受信预检中核，不应为相同事实重复跑三套私有 shell 行为矩阵。若 actor→grader 因 baseline 不符而提前退出，它是运行无效，不是正常 0 分；应保留同次原工件定位，不重算替代 baseline。

历史成本仅作排程参考：2 CPU／4 GiB，trusted setup 约 477–722 秒、测试约 27–34 秒；历史 setup/reset 900 秒、整次 grading deadline 1800 秒。新片记录实际 profile、所有有效超时和资源事实，不把旧 900 秒结果回称为 300 秒通过；`resource_facts=null` 仍表示未知。本轮不改预算，也不将这些旧耗时承诺为新机性能。

## 可复用与不能沿用的结论

可以复用公开需求解释、数值断言依据、原／gold／reverse 精确补丁、09-29 原材料 0／1／1 结果及短／长引用行为对照、静态补丁应用和 D6 既有机制的独立审查。换机器本身不要求重审全题、重跑原材料三行或重造错误候选。

不能沿用的是 MONAI 新材料资格、候选项目测试已执行的结论、旧镜像拉取即等于今日冷机恢复的结论，以及仅在 mypy 验过的三端 baseline 一致性。新材料仍须一轮固定候选验收和独立复核，成功后才提交题级转类。

D6 最终验收 17:49 补充另记公共评分伪造阻塞。本轮没有复核其后续修复，因此不能借 MONAI 材料完整或题级 CPU 通过宣布普通能力比较／训练已可用；接收版本仍由公共链路负责人确认。该项与本次恢复准备分开，不扩展为本轮新任务。
