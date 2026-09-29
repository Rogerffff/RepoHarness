# coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266 · 复核者独立初判

2026-09-25 · R2E 第二批独立复核，第一步。写作前没有读 `OUTPUT_DIR` 里的其它文件（公开读者、主审产物）、`history/`、环境阶段记录和任何审查目录。本文只做静态阅读和已有原件核对，没有运行项目代码或容器。读取范围与暴露见附录 A。

证据级别写法：**静态**＝读源码/测试推断；**评分运行**＝`run_refs.json` 中 `material=current` 的 RH2 账本行与日志；**devcheck**＝协调者提供的真实 Claude Code 2.1.205 + 桩端点执行事实（agent 身份）和私有 gold 对照（root）；**M3**＝独立 runner 在来源镜像上的参考日志。

## 0. 初判摘要

| 项 | 初判 | 证据 |
| --- | --- | --- |
| 目标键 | 只有 1 个：`ConfigTest.test_tweaks_paths_after_constructor`。44 个期望键全是 PASSED；其余 43 个就是 base 版 `tests/test_config.py` 的原有测试（回归键） | 评分运行 2 组 noop/gold；隐藏测试与 base 的 diff（只多 1 个测试和 1 行 import） |
| 材料 | 一致，无修订 | 摘要与前像 blob 核对（附录 B1） |
| 初态问题 | 成立：noop 目标键的失败原因就是题面报错。小偏差：先抛错的是 `get_option`，题面说是 set 时抛 | 评分运行日志 |
| gold | 最小且正确：在 `CoverageConfig.set_option/get_option` 特判 `"paths"`；`Coverage` 的两个方法只是委托，所以两个入口都修到 | 静态；devcheck 私有对照 |
| 误拒 | 未发现 | 静态 |
| **漏测（主要问题）** | 目标测试只经 `Coverage` 包装、从空 `paths` 起步：① 只改 `control.py` 包装、`CoverageConfig` 仍报错的部分修复也会得 1，而配置器插件大约一半时间拿到的正是 `CoverageConfig`（`coverage/control.py:276`）；② set 的"替换"与"合并"两种语义无法区分 | 静态；待正式评分实跑候选 B、M |
| 错误回归 | 未发现 | 静态 + 43 个回归键两组都 PASSED |
| 开发条件 | 可开发。`setup.cfg` 的 addopts 让带 `-p no:cacheprovider` 的 pytest 以 rc 4 退出；`-o addopts=""` 实测可用 | devcheck |
| 题目关系 | 本题修复和加强版目标测试出现在 `coveragepy__ea6906b0…` 的公开工作树；与 `coveragepy__f5eb5f21…` 同 base，公开工作树逐字节相同；本题工作树含 `016af5f6`、`5dbbe143` 的修复（机械比对） | 公开包核对 |
| 暂定处置 | 静态候选，可作开发诊断或链路探针；记录漏测和题目关系。不建议拒绝；是否改题等候选 B 实跑后再定 | — |

## 1. 公开目标（只据公开包）

- **题面**（`user_prompt.txt`）：`coverage.Coverage()` 构造后，`get_option("paths")` 应返回当前 `[paths]` 配置，默认是空 `OrderedDict`（16–17、27 行）；`set_option("paths", new_paths)` 之后再 `get_option("paths")` 应返回更新后的 `OrderedDict`（19–23、27 行）；目的是让插件能动态修改 `paths`（5、8、34 行）；现状报 `coverage.misc.CoverageException: No such option: 'paths'`（30–32 行）。
- **读代码可知**：选项查找只认 `CONFIG_FILE_OPTIONS` 里的 `section:option`，以及已登记插件的 `plugin:key`（`coverage/config.py:414-463`）；`"paths"` 没有冒号，落到 463 行抛错。`Coverage.get_option/set_option` 只是委托（`coverage/control.py:363-400`）。配置器插件的 `configure(config)` 拿到的对象按 `int(time.time()) % 2` 在 `Coverage` 与 `CoverageConfig` 之间二选一（`control.py:271-276`；接口约定见 `coverage/plugin.py:207-219`）。`paths` 默认是 `OrderedDict()`（`config.py:231`、`542-545`），由 `combine()` 消费（`control.py:673-678`）。
- **约束**：不改测试文件、不联网、使用 `.venv`（`public_bundle.json` 的 `public_hints`）。
- **题面未规定**：返回拷贝还是原对象；set 是替换还是合并（"set" 这个名字和 23 行注释 "Expected to output the new_paths OrderedDict" 指向替换，但示例从空起步）；是否校验值类型；是否支持 `paths:<name>` 单项；set 进来的路径是否做 `~` 展开（构造时从文件读到的值会展开，`config.py:542-545`）。这些都能从公开材料判断，隐藏测试也都不检查。

## 2. 八方面：看了什么、结论

| 方面 | 看了什么 | 结论 |
| --- | --- | --- |
| 公开需求 | 题面全文、`public_hints`、`config.py` 全文、`control.py` 的 `_init`/`get_option`/`set_option`/`combine`、`plugin.py` 的 `configure` 文档、`doc/config.rst` 的 `[paths]`、`CHANGES.rst` 开头 | 需求清楚，示例就是测试体。"插件会拿到 `CoverageConfig`"需要读 `control.py:276` 才知道，但不需要隐藏材料 |
| 材料与初始问题 | 各摘要、gold 前像 blob、manifest 的 `initial_diff`、4 份评分日志 | 一致。题面说 set 时抛错，实际示例和测试里先抛的是 get（同一消息；set 同样抛，devcheck `pr7_7_cmd.out:1`）。措辞偏差不影响求解 |
| 测试是否测到要求 | 隐藏测试全文；与 base `tests/test_config.py` 的 diff；目标测试的 3 个断言点 | 覆盖题面示例本身；缺 `CoverageConfig`/插件入口、非空起点下的替换、`combine()` 实际使用新值 |
| 误拒 | 目标断言形态 | 只用 `assertEqual` 比较映射内容；`dict == OrderedDict` 不看顺序，也不要求类型相同。拷贝、普通 dict、原对象都能过。未发现误拒 |
| 回归与 gold 完整性 | gold 6 行；43 个回归键覆盖的接口；gold 未触及的相关测试 | gold 无无关改动、无回归。回归键保护普通选项、插件选项、未知选项报错、配置文件读取与 `[paths]` 解析、`~` 展开。不在隐藏集：`tests/test_plugins.py:874-886`（配置器插件）、`tests/test_api.py:470` `test_ordered_combine`（`[paths]` 顺序）；devcheck 里这两条因命令参数错误没有真正执行（见 §6） |
| agent 开发条件 | `environment_brief.md`；devcheck orig 全部 captures、`prelaunch.json`、`attempt.json`、`activation_check.json`；私有对照 | 见 §6 |
| 交付与评分边界 | 评分口径；隐藏测试的导入链；`setup.cfg`；账本诊断字段 | 合法修复只需改 `coverage/config.py`，不涉及测试路径。隐藏测试依赖 base 版 `tests/coveragetest.py`、`tests/helpers.py`、`tests/__init__.py`，源码 `coverage/backunittest.py`（`TestCase` 基类，非测试路径），以及 `setup.cfg` 的 `[tool:pytest]`；它们都可被候选修改且评分不重置。账本有 `candidate_test_like_paths` 诊断（gold/noop 为空）。平台机制未重审，只核了本题适用 |
| 题目关系与用途 | 跨题比对文件；同仓其它 4 题的公开包 | 见 §7 |

## 3. 需求—断言双向表

| 需求 / 旧行为 | 公开依据 | 测试与决定性断言 | 覆盖 | 执行证据 / 下一步 |
| --- | --- | --- | --- | --- |
| R1 默认 `get_option("paths")` 不报错，返回空 `OrderedDict` | 题面 16–17、27 行；`config.py:231,542-545` | `test_1.py:345-347` `assertEqual(paths, OrderedDict())` | 覆盖（只比内容，`{}` 也能过） | noop 在 346 行抛错；gold PASSED（B2） |
| R2 `set_option("paths", new)` 后 get 返回新值 | 题面 19–23、27 行 | `test_1.py:349-353` `assertEqual(cov.get_option("paths"), new_paths)` | 覆盖（只在空起点下） | gold 两组 PASSED |
| R3 插件（配置器）可改 paths；插件可能拿到 `Coverage` 或 `CoverageConfig` | 题面 5、8、34 行；`plugin.py:213-216`；`control.py:271-276` | 无：隐藏测试只调用 `cov.get_option/set_option` | **缺失** | 私有对照 `pr1_1`、`pr4_2` 证明 gold 两个入口都通；候选 B 待跑 |
| R4 新值确实被使用（`combine()` 的路径别名） | `control.py:673-678`；`doc/config.rst:218-246` | 无 | 缺失 | 私有对照 `pr7_7` 输出 `['girder/g1.py']`，说明 gold 下生效 |
| R5 set 为替换而非合并（由 "set" 与题面 23 行推出，未明说） | 题面 23 行；其它选项在 `config.py:426-430` 用 `setattr` 替换 | 无：起点为空时两种语义结果相同 | 缺失；规格也偏弱 | 候选 M 待跑 |
| O1 未知选项仍报 `No such option: '...'` | `config.py:438-439,462-463` | `test_1.py:355-365` | 覆盖 `run:xyzzy`、`xyzzy:foo`；不覆盖 `paths:xxx` | 两组 PASSED |
| O2 普通选项 get/set | `control.py:377-400` 文档 | `test_1.py:331-342` | 覆盖 | 同上 |
| O3 插件选项 get/set | `config.py:432-436,457-460` | `test_1.py:367-379` | 覆盖 | 同上 |
| O4 配置文件 `[paths]` 解析与 `~` 展开 | `config.py:306-310,542-545` | `test_1.py:297`、`559-562` | 覆盖 | 同上 |
| O5 配置器插件改其它选项 | `tests/plugin_config.py:11-17` | 不在隐藏集（`tests/test_plugins.py:874-886`） | 缺失（gold 不触及） | devcheck `pr5_4` 未执行（rc 4） |

反查：目标测试的每个断言都能从题面示例直接得到，没有"只读隐藏材料才知道"的要求。

## 4. R2E 专项

- **(a) 非 PASSED 期望键**：无（44 个都是 PASSED）。更完整的修复不会因为把 FAILED 键翻成 PASSED 而判 0。键集合必须完全相同，所以改变收集结果的改动会判 0（例如在 `tests/coveragetest.py` 加 `test_*` 方法、让测试变 skip）；正常修复不涉及。
- **(b) 题面报错是否出现在 noop 目标键**：是。R-f noop 日志 20–63 行：`test_1.py:346` 调 `get_option("paths")` → `control.py:375` → `config.py:463` 抛 `coverage.misc.CoverageException: No such option: 'paths'`；环境轮 rerun2 noop 日志 29–63 行相同。偏差只在于题面把抛错归到 set。
- **(c) 修法泄漏**：题面没给文件、函数或实现方式；但示例（题面 11–24 行）与目标测试体（`test_1.py:344-353`）逐行同构：同样的输入 `{'magic': ['src', 'ok']}`、同样的比较。这属于"测试泄漏"而不是修法泄漏：任务很容易，区分度有限。修法读 `config.py:414-463` 即可得出。
- **(d) 测试支撑、搬迁伪影、撞键**：隐藏测试导入 base 版 `tests.coveragetest`（`CoverageTest`、`UsingModulesMixin`；它再导入 `tests.helpers`、第三方 `unittest_mixins` 和源码 `coverage/backunittest.py`）、第三方 `mock`、源码 `coverage.optional.without`。`tests/conftest.py:22-78` 的三个 autouse fixture（`set_warnings`、`reset_sys_path`、`fix_xdist_sys_path`）搬迁到 `r2e_tests/` 后不生效；但 noop/gold 两组加 M3 两次，43 个回归键都 PASSED，没有观测到影响。单文件，两个类共 26 + 18 个测试，无重名；AST 核对得到 44 个键，与期望完全相同，无撞键。`setup.cfg:1-2` 的 addopts（`-q -n3 --strict --no-flaky-report -rfe --failed-first`）在评分时生效（日志里有 `bringing up nodes...`），不影响键。
- **(e) 时间、随机、资源**：隐藏键不涉及。`control.py:276` 按秒的奇偶选配置器拿到的对象，只影响插件入口（隐藏测试不加载配置器）；它让候选 B 的缺陷在真实使用中表现为间歇失败。单次运行约 1 s、内存峰值约 270–280 MB（账本 `resource.mem_peak_mb`），6 次运行结果一致。
- **(f) 修订**：无（`revisions.json` 为 `[]`，`run_refs.json` 的 `material_revisions` 为空），不适用。

## 5. 可区分候选（供协调者用正式评分实跑）

- **A 合理替代解（拷贝语义）**：`coverage/config.py` 中 `CoverageConfig.set_option` 的 docstring 之后、`# Check all the hard-coded options.` 之前插入 `if option_name == "paths": self.paths = collections.OrderedDict(value); return`；`CoverageConfig.get_option` 同一位置插入 `if option_name == "paths": return collections.OrderedDict(self.paths)`。预期 44/44、reward 1，无不符键。用途：确认拷贝和类型规范化不会被误拒。
- **B 可能蒙混的部分修复（只修包装）**：`config.py` 不动；在 `coverage/control.py` 的 `Coverage.get_option` 中，`return self.config.get_option(option_name)`（375 行）之前插入 `if option_name == "paths": return self.config.paths`；在 `Coverage.set_option` 中，`self.config.set_option(option_name, value)`（400 行）之前插入 `if option_name == "paths": self.config.paths = value; return`。预期 44/44、reward 1，无不符键。但 `coverage.Coverage().config.get_option("paths")` 仍抛 `No such option: 'paths'`；配置器在奇数秒拿到 `self.config` 时失败，违反题面的插件诉求。附加对照：devcheck 的 `pr1_1` 命令在 B 下应仍打印 `CoverageConfig ERROR`。
- **M 合并语义**：与 gold 相同，只是 set 分支改成 `self.paths.update(value); return`。预期 44/44、reward 1，无不符键。对照：在临时目录写入含 `[paths]` 段、`first = /first/1 /first/2`（多行）的 `.coveragerc`，构造 `Coverage()` 后 `set_option("paths", new_paths)`：gold 的 `get_option("paths")` 只剩 `magic`，M 返回 `first` 加 `magic`。上游后来的加强版测试正好检查这一点（见 §7）。
- （可选，不必跑）**D 错误实现**：把 `('paths', 'paths')` 加进 `CONFIG_FILE_OPTIONS`。`_set_attr_from_config_option` 的 `where.split(":")`（`config.py:403`）会抛 `ValueError`，被 `config.py:286-288` 转成 `Couldn't read config file`；所有读配置文件的回归键（如 `ConfigTest.test_config_file`、`ConfigFileTest.test_config_file_settings`）变 FAILED → 0。静态上已能确定回归键会拦住这类改法。

如果 B 实跑得 1：记为"漏测，已执行确认"。这只是筛出一个规格覆盖缺口，不是按失败键自动免责，原始 reward 保留。修订方向（由用户决定）：在目标测试里对 `cov.config` 也做一次 get/set 往返，依据是题面的插件诉求、`plugin.py:213-216` 和 `control.py:276`，没有扩大需求。是否加"非空起点仍替换"的检查需要用户判断：题面只写了 "containing the new paths"，这一条有扩大需求之嫌。

## 6. 开发需求（逐题）

| 项 | 内容 | 证据 |
| --- | --- | --- |
| 解释器与导入 | `python` 是 `/testbed/.venv/bin/python`（3.7.9）；`coverage` 从 `/testbed/coverage/__init__.py` 导入（cwd 为 `/` 时也是），改源码立即生效，不需要构建 | devcheck `env.out:1-6`（agent） |
| 依赖 | pytest 4.6.6、xdist 1.30.0、flaky 3.6.1、hypothesis 4.41.2、forked 1.6.0；`mock`、`unittest_mixins`、`toml` 已装（回归键能跑） | `pr6_6_pytest.out:2-5`；评分日志 |
| pip 与网络 | pip 20.0.2 可用，但无外网（`DNS_EXTERNAL=DENIED`，只有桩 relay 可连） | `env.out:7`；`prelaunch.json` 的 `probe_facts` |
| 权限与资源 | agent uid 54321；`/testbed` 属主 54321、可写；`/tmp` 1 GiB，home 为 256 MiB tmpfs；2 CPU、4 GiB、pids 512；激活文件 agent 不可写 | `prelaunch.json` |
| git | HEAD 为 base `17204597…`，历史 4503 个提交，无子提交、无 remote、无 reflog；初态 `git status` 只有 `?? install.sh`、`?? run_tests.sh` | `attempt.json`；`env.out:9-10`；`r2e_preflight.out` |
| 测试命令 | `python -m pytest -o addopts="" tests/test_config.py`：agent 实测 43 passed。带 `-p no:cacheprovider` 的形式以 rc 4 退出（`unrecognized arguments: --failed-first`，来自 `setup.cfg:2`）。公开提示给出的普通形式 `python -m pytest tests/test_config.py`（addopts 生效，含 `-n3`）没有以 agent 身份实测；评分侧用同一 inifile 能跑，推断可用 | `pr5_3/5_4/5_5_pytest.out:1-4`；`pr6_6_pytest.out`；评分日志 15–18 行 |
| 构建 | 不需要（纯 Python 改动，不涉及 C tracer） | 静态 |
| 提交边界 | 改 `coverage/config.py`（可选同步 `control.py` 的 docstring）；不改 `tests/` | 公开提示 |
| 缺口与待验 | `install.sh` 在容器里，但不在公开导出里（manifest `untracked_missing`），与求解无关。`tests/test_plugins.py`、`tests/test_api.py` 的相关子集在 devcheck 中 base 与 gold 都没真正执行。devcheck 里的配置器两次都拿到 `Coverage`，没有经真实插件走到 `CoverageConfig`（`pr1_1` 已直接覆盖该对象）。devcheck 镜像 `sha256:59ba6725…` 与评分账本镜像 `sha256:ab9a4d0f…` 不同（都是 `r2e_derive_v1` 派生、跨机重建）；本文没核到二者的配方摘要是否相同。真实模型求解、Qwen adapter 链路、实际渲染的完整消息都未验：devcheck 首条用户消息是桩指令，不是本题题面 | actor 待验 |

## 7. 题目关系与用途

- **本题答案出现在别题初态**：`coveragepy__ea6906b0…`（base `7fd1ea39`，版本 6.1.0a0）的公开工作树里，`coverage/config.py:427-430,458-460` 逐字含 gold 逻辑；`tests/test_config.py:339-360` 是加强版目标测试（从含 `[paths]` 的 `.coveragerc` 起步，再 set 并断言等于 `new_paths`）；`coverage/control.py:398-399,426-427` 的 docstring 写明 `"paths"` 特例会"replace the entire `[paths]` section"；`doc/changes.rst:85-88` 是 5.1 的 changelog（issue 967）。结论：两题应放在同一数据划分；如果训练集含 ea6906b0，本题不宜作为独立评测。
- **本题初态含别题答案**：机械比对显示，本题工作树含 `coveragepy__016af5f6…`（3/3 行）和 `coveragepy__5dbbe143…`（7/7 行）的 gold。我只核了这两题的 base 更早（5.0.2a1；base 分别为 `5bb5da50`、`8240c58c`），没有读它们的私有 gold，所以逐行包含没有独立复核。
- **同 base**：`coveragepy__f5eb5f21…`（JSON 报告缺分支计数）的 base 同为 `17204597c33d`，两份公开工作树 `diff -rq` 无差异；比对未显示互相包含。两题修复都进入了 5.1（ea6906b0 的 `doc/changes.rst:77-88`）。
- **外部答案**：上游 5.1 changelog 和 issue 967 公开可查；预训练是否见过无法静态判断。
- **类型与用途**：小型 API 扩展，单文件 6 行修复，题面即测试。适合作开发诊断或链路冒烟探针，不宜作难度区分样本。

## 8. 未知与下一步

未知：① 候选 B、M 的实际得分（静态推断都是 1）；② 公开提示的普通 pytest 形式（addopts 与 `-n3` 生效）在 agent 身份下能否正常运行（低风险）；③ devcheck 镜像与评分镜像的配方是否一致；④ 真实模型求解、实际渲染的消息、Qwen adapter 链路；⑤ 与 `016af5f6`、`5dbbe143` 的逐行包含。

**唯一最值得先做的下一步**：用正式评分代码实跑候选 B（只改 `control.py`），确认"插件入口没修也得 1"这一漏测；同一批顺带跑 A 和 M。

---

## 附录 A：实际读取范围与暴露

- **角色与方法**：复核卡 `roles/reviewer_r2e.md` 全文。主审卡 `roles/investigator_r2e.md` 由工具一次载入全文（42 行），我只把"材料""R2E 的评分口径""第二批补充规则"三节当口径使用；其余两节（主审逐题流程、边界）也在载入内容里。另读了八方面协议、R2E 第二批环境卡、记录模板的全文；40 项清单未读。
- **PUBLIC_DIR**：`user_prompt.txt`、`environment_brief.md`、`public_bundle.json`、`worktree_manifest.json`（顶层字段与 install.sh 条目）。worktree 里读了：`coverage/config.py` 全文；`coverage/control.py` 的 180–300、355–405、640–690 行及 grep；`coverage/plugin.py:204-232`；`coverage/backunittest.py`；`coverage/version.py`；`CHANGES.rst:1-60`；`doc/config.rst` 中关于 paths 的 grep；`setup.cfg`；`tox.ini` 的 grep；`run_tests.sh`；`.gitignore`；`tests/conftest.py`；`tests/coveragetest.py:1-120` 及方法列表；`tests/plugin_config.py`；`tests/test_plugins.py:874-914`；`tests/test_api.py` 的 grep；`tests/test_config.py`（与隐藏测试做 diff）。
- **PRIVATE_DIR**：全部文件（`hidden_tests/test_1.py` 全文、`__init__.py`、`expected_output.json`、`gold.patch`、`run_tests.sh`、`revisions.json`、`grading_bundle.json`、`validation_bundle.json`、`run_refs.json`）。
- **运行原件**：`run_refs.json` 列出的 4 条账本行（均为第 8 行）和 4 份 eval 日志（全文或解析），M3 账本第 29、76 行和两份 `test_output.txt` 的汇总行。
- **devcheck**：`orig/` 的 `commands_with_preflight.json`、全部 `captures/*.out`、`prelaunch.json`、`attempt.json`、`activation_check.json`、`devcheck_stdout.json`、`bringup_artifacts/cc_version_observed.json`、`post_run_facts_root.txt`、两个 stderr 日志的末尾，以及 `stub/requests/messages_000.json` 的用户文本与 system 概况；`private_gold/private_control.json`、`stdout.log`。没有读 `harness/trajectory.jsonl`、`messages_001`–`009`、`stub_log.json`、`stub_script.json`、`stub_stdout.log`。
- **跨题**：`cross_task_gold_scan.json` 的 method 与 coveragepy 各条；同仓其它 4 题公开包的 `public_bundle.json`（标题、base）与 `coverage/version.py`；ea6906b0 工作树的 `coverage/config.py`（grep）、`tests/test_config.py:335-375`、`coverage/control.py:385-432`、`doc/changes.rst:60-95`；对 f5eb5f21 工作树做了整树 `diff -rq`。没有读任何其它题的私有包。
- **暴露**：我见过本题 gold、隐藏测试、期望映射和评分日志。没有打开 `public_read.md`，但 devcheck 的 `commands_with_preflight.json` 含公开读者建议的 7 条命令，所以间接看到了它的验证思路（同时测 `Coverage` 与 `CoverageConfig`、配置器插件、`combine()`）。`control.py:271-276` 的二选一是我在读 devcheck 之前从源码读到的，但"漏测 ①"的独立性应打一定折扣。
- **本地操作**：在 scratchpad 的 `config.py` 副本上做了 `patch --dry-run` 和 `git hash-object`；`diff -rq` 的输出曾临时写到 `/tmp` 下一个文件，随即删除。没有修改任何原件，也没有运行项目代码或容器。

## 附录 B：关键证据定位

**B1 材料一致性**
- base：题面第 1 行 `17204597c33d`，与 `public_bundle.json`、`grading_bundle.json` 的 `base_commit`、devcheck 的 `GIT_HEAD` 一致。
- 镜像：`public_bundle.json` 的 `image_manifest_digest` `sha256:802b61d5…`，与账本 `image_digest_expected`、M3 `image_digest_actual` 一致。
- 隐藏测试：`test_1.py` sha256 `acae864f…`、`__init__.py` `e3b0c442…`（空文件），与 `grading_bundle.json` 一致；树摘要 `ddfa078c…` 与评分日志第 3 行 `RH2_SETUP_HIDDEN_TESTS_TREE` 一致。
- 期望：`2388143c…`，与 `run_refs.json` 的 `expected_sha256` 一致，内容与 grading bundle 的 `expected_output_json` 相同。
- `run_tests.sh`：`8285765f…`，与评分日志的 `RH2_SETUP_ENTRY_SHA256` 一致。
- gold：`0a9c0747…`，与 validation bundle 的 `golden_patch_sha256`、账本 `candidate.patch_sha256` 一致。gold 前像 `index 78a3e86a` 等于工作树 `coverage/config.py` 的 `git hash-object`；在副本上 dry-run 可干净应用。
- manifest：`initial_diff` 为空（镜像初态 = base 跟踪文件 + 未跟踪的 `install.sh`、`run_tests.sh`）；`install.sh` 列在 `untracked_missing`。

**B2 评分运行（均为 `material=current`）**

| 组 | 候选 | 账本行 | 结果 | 日志要点 |
| --- | --- | --- | --- | --- |
| R-f 09-23 | noop | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:8` | 0.0，43/44，mismatched 只有目标键 | `…noop-c_8ee3ccfc.eval.log` 20–63 行失败栈；136 行 `1 failed, 43 passed` |
| R-f 09-23 | gold | `…/ledger_r2e_all_gold.jsonl:8` | 1.0，44/44 | `…gold-c_10174c98.eval.log` 92 行 `44 passed` |
| 环境轮 rerun2 09-24 | noop | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:8` | 0.0，43/44 | `…rer_4e5c6a85.eval.log` 29–63 行，同一失败栈 |
| 环境轮 rerun2 09-24 | gold | `…/_rerun2/ledger_gold.jsonl:8` | 1.0，44/44 | `…rer_f2cf72dd.eval.log` 汇总行 `44 passed` |
| M3 独立参考 | gold ×2 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:29,76` | passed | 两份 `test_output.txt` 第 77 行 `44 passed` |

4 份评分日志的 sha256 与 `run_refs.json` 一致。4 条账本行都是：镜像 `rh2-r2e-derived/coveragepy:97997d2cd680-r2e_derive_v1`（ID `ab9a4d0f…`），`policy.user=rh2grader`，`candidate.apply_user=agent/54321`，`candidate_test_like_paths=[]`，`derived_image_recipe=null`。

**B3 devcheck**
- orig（agent；真实 Claude Code 2.1.205 + 桩端点；镜像 `sha256:59ba6725…`；`image_is_overlay_derived_id: true`）：
  - `r2e_preflight.out`：三项都是 ok。
  - `pr1_1_cmd.out`：base 下 `Coverage` 和 `CoverageConfig` 两行都是 ERROR。
  - `pr4_2_cmd.out`：base 下配置器拿到 `Coverage`，在 `config.py:463` 抛错。
  - `pr5_3/5_4/5_5_pytest.out`：rc 4，`--failed-first` 无法识别。
  - `pr6_6_pytest.out`：43 passed。
  - `pr7_7_cmd.out`：set 抛错；`combine` 结果 `['ci/girder/g1.py']`，没有重映射。
- private_gold（root，同一镜像，gold `git apply` 干净）：
  - `pr1_1`：两个对象 before 都是 `OrderedDict()`，after 都是 `OrderedDict([('magic', ['src', 'ok'])])`。
  - `pr4_2`：配置器（拿到 `Coverage`）改动后生效。
  - `pr6_6`：43 passed。
  - `pr7_7`：`['girder/g1.py']`，别名生效。
  - `pr5_*`：同样 rc 4。
