<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266：私有主审分析（读历史前）

2026-09-25 · 私有主审（静态审查）· 本稿在读任何历史调查之前保存。只做静态阅读与既有证据核对：未运行项目代码，未开容器或远端，未改原件。

路径约定：`PUBLIC_DIR` / `PRIVATE_DIR` 指本题 v3 公开 / 私有包（`runs/r2e_static_prep_20260924/v3/{public,private}/coveragepy__97997d2c…/`）；`DEVCHECK` 指 `runs/r2e_actor_20260925/devcheck/coveragepy__97997d2cd6801d0335e3fa162b71/`；其余 `runs/...` 相对仓库根目录。

## 0. 结论先行（暂定，待历史环节核对）

| 项 | 暂定判断 | 证据级别 |
|---|---|---|
| 目标 | `get_option("paths")` / `set_option("paths", v)` 能整段读写 `[paths]`；configurer 插件拿到的两种对象（`Coverage`、`CoverageConfig`）都要能用 | 公开题面 + base 源码 |
| 材料 | 题面、base、gold、隐藏测试、expected、`run_tests.sh` 对应同一上游提交；gold 与上游 diff 逐字节相同 | 哈希与 diff 核对 |
| 初态与评分 | noop 只错目标键，失败原因就是题面引用的 `No such option: 'paths'`；gold 44/44。2 次 noop、2 次 gold（RH2 派生镜像）加 2 次 gold（M3 来源镜像）结果逐键一致 | 历史真实 RH2 + 独立 runner |
| expected | 44 个键全是 PASSED，没有必须"继续失败"的键。更完整的修复不会因为把某个键翻成 PASSED 而判 0 | 期望映射 + 日志 |
| 主要问题 | 目标测试只经 `Coverage` 对象，从空起点做一次 set→get 往返。静态推断以下两种实现都会得 1：只改 `control.py` 转发层的部分修复（W1）；把值存进 `combine()` 不读的旁路属性的假修复（W2） | 静态推断（高把握），待正式评分实跑 |
| 误拒 | 没发现缺少公开依据的精确约束。复制、规范化、展开 `~` 等合理变体，静态推断都得 1 | 静态推断 |
| 题目关系 | 与 `f5eb5f21` 的初始工作树逐字节相同；本题修复和加强版目标测试已在 `ea6906b0` 的初始工作树里；本题工作树含 `016af5f6`、`5dbbe143` 的修复（后两者只有机械比对线索） | 直接比对公开工作树 + 比对文件 |
| 暂定处置 | 静态候选：`needs_review`，reason=静态候选待 actor 验证；`development_diagnostic`。附覆盖缺口说明，与同族题放在同一划分。不修订也能用于诊断 | — |
| 唯一优先下一步 | 用正式评分代码实跑 W1（只改 `coverage/control.py`），确认缺口是否真的给 1 | — |

## 1. 读取范围

- 方法：角色卡、八方面协议、R2E 第二批环境卡、记录模板、40 项清单。
- 公开包：`public_read.md` 全文。`PUBLIC_DIR` 的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`，以及 `worktree_manifest.json`（只看顶层）。
- 公开工作树：
  - `coverage/config.py` 全文；`coverage/control.py`（95–300、355–405、640–690）；`coverage/plugin.py`（70–90、200–222）；`coverage/files.py` 的 `PathAliases`。
  - `tests/coveragetest.py`（1–140、247–292、480–500）；`tests/conftest.py`、`tests/__init__.py`、`tests/plugin_config.py` 全文；`tests/test_plugins.py` 的 `ConfigurerPluginTest`。
  - `setup.cfg`、`run_tests.sh`、`.gitignore`、`requirements/pytest.pip` 全文；`tox.ini` 只看段名；`doc/config.rst`（215–250）。
  - `get_option` / `set_option` 的全仓 grep。公开 `tests/test_config.py` 与隐藏测试做了全文 diff。
- 私有包：`PRIVATE_DIR` 全部文件，`hidden_tests/test_1.py` 读了全文。
- 运行原件：
  - `run_refs.json` 四个 current 行对应的账本第 8 行，以及 4 份 `.eval.log` 全文。
  - M3 的两行账本、两份 `test_output.txt`、`git_gold.diff` / `gold.diff`。
  - `_rerun2` 下两份 `.diagnostics.json` 只被 grep 命中一行（`install_failed_commands: []`）。
- devcheck：
  - 全文或全部：`commands_with_preflight.json`、`captures/*.out`、`prelaunch.json`、`activation_check.json`、`devcheck_stdout.json`、`private_gold/` 下两个文件。
  - 部分：`attempt.json`（元数据）；`post_run_facts_root.txt`（开头）；`stub/requests/messages_000.json`（只看首条 user 消息、system 中的 gitStatus 段和工具名）。
- 同仓其它题的公开包：
  - 5 道 coveragepy 题的标题、base、`version.py`。
  - 4 道同仓题（`f5eb5f21`、`016af5f6`、`5dbbe143`、`ea6906b0`）的工作树分别与本题做 `diff -rq`。
  - `ea6906b0` 的 `coverage/config.py`（415–475）、`tests/test_config.py`（325–375）、`doc/changes.rst`（60–92）。
- 跨题比对：`cross_task_gold_scan.json` 里涉及 coveragepy 的 8 行。
- 没有读：其它题的私有包、任何审查产物、`history/`、`docs/.../r2e_env_repair_20260924/`、本批 README 与 `assignments.json`。

## 2. 材料与初态（方面 2；清单 1、2、27）

| 核对 | 结果 |
|---|---|
| gold | `gold.patch` 与 M3 从上游提交取出的 `git_gold.diff` 逐字节相同。只改 `coverage/config.py`：`set_option`、`get_option` 开头各加一个 `"paths"` 特判。上游提交另外改了 `tests/test_config.py`，已作为测试剔除（M3 `gold_meta`） |
| 隐藏测试 | `hidden_tests/test_1.py` = 公开 `tests/test_config.py` + `from collections import OrderedDict` + 新测试 `test_tweaks_paths_after_constructor`（test_1.py:344–353）。其余 43 个测试逐字相同 |
| 哈希 | 以下都与 `grading_bundle.json` / `validation_bundle.json` 一致：`test_1.py`（`acae864f…`）、空 `__init__.py`、`run_tests.sh`（`8285765f…`）、gold（`0a9c0747…`）。本地 `expected_output.json` 与 bundle 内字符串解析结果相同（sha `2388143c…`）。4 份 eval log 的哈希与 `run_refs.json` 一致 |
| 初始工作树 | `initial_diff` 为 0 字节；未跟踪文件只有 `install.sh`、`run_tests.sh`，与 devcheck 的 `git status` 一致 |
| noop 失败位置 | 调用链：`r2e_tests/test_1.py:346` 的 `cov.get_option("paths")` → `coverage/control.py:375` 转发 → `coverage/config.py:463`。在最后一处抛出 `coverage.misc.CoverageException: No such option: 'paths'`（R-f noop log 第 23–63 行），与题面引用的异常逐字相同 |
| 修订 | `revisions.json` 为 `[]`；`env_recipe`、`resource_recipe` 都是 null |

清单 1、2、27：pass。

## 3. 隐藏测试展开（方面 3；清单 18–20、25、32）

### 3.1 目标键（只有一个）

`ConfigTest.test_tweaks_paths_after_constructor`：noop 为 FAILED，gold 为 PASSED，两轮 RH2 一致。

1. `cov = coverage.Coverage()`：
   - `CoverageTest` 通过 `TempDirMixin` 在新建的临时目录里运行。那里没有 `.coveragerc`、`setup.cfg`、`tox.ini`、`pyproject.toml`，也没有设置 `COVERAGE_RCFILE`。
   - 所以 `config.paths` 就是 `read_coverage_config` 末尾重建出的空 `OrderedDict`（config.py:542–545）。
   - 构造时不调用 `_init()`，不会进入 `int(time.time()) % 2` 的插件分支。
2. `assertEqual(cov.get_option("paths"), OrderedDict())`：只比较 `==`，空的普通 `dict` 也相等。
3. `set_option("paths", new_paths)`，其中 `new_paths` 是只有一个键 `magic: ['src', 'ok']` 的 `OrderedDict`。
4. `assertEqual(cov.get_option("paths"), new_paths)`：只比较 `==`。单键，无从检查顺序；也不检查是不是同一个对象。

这条测试就是题面示例本身：值、步骤、注释都与 `user_prompt.txt:15–23` 一一对应。它只调用 `Coverage.get_option/set_option`，没有检查：

- 直接对 `CoverageConfig` 调用；
- 插件 `configure` 路径；
- `combine()` 是否用上新值；
- 起点非空时是替换还是合并；
- 从配置文件读入的 `[paths]` 能否经 `get_option` 取回。

### 3.2 回归键（43 个）

全部是公开 `tests/test_config.py` 的原有测试，解题者能看到也能运行（devcheck `pr6_6`：agent 身份下 43 passed）。以下 5 项与本题接口相关，逐条读过：

- `test_tweaks_after_constructor`（331–342）：`run:timid` 等 `section:option` 形式的 set/get，保住 K1。
- `test_tweak_error_checking`（355–365）：`run:xyzzy`、`xyzzy:foo` 的 set/get 仍抛 `No such option: '…'`，保住 K2。不含不带冒号的名字。
- `test_tweak_plugin_options`（367–379）：插件选项的读写，以及 `no_such.plugin:foo` 报错，保住 K3。
- `test_tilde_in_config`（262–297）：读入 `[paths] mapping` 并展开 `~`，断言 `cov.config.paths == {...}`。
- `ConfigFileTest.*`：`LOTSA_SETTINGS`（486–491）含 `[paths] source/other`，断言在 559–562。
  - 保住 K4：`[paths]` 的条目名可以任意，不触发 "Unrecognized option"，并能正确读入。
  - 如果实现把 `paths` 放进 `CONFIG_FILE_OPTIONS`，这些键会失败，属于正确拒绝。

其余 38 个回归键（构造参数、环境变量、TOML、解析错误、未装 toml 时的行为等）只通读确认与 get/set/paths 无交集，没有逐条写评语。

公开 `tests/test_plugins.py::ConfigurerPluginTest`（K5）和 `tests/test_api.py::test_ordered_combine`（K6）不在隐藏测试里，不参与评分。

### 3.3 依赖

- 隐藏测试 `from tests.coveragetest import CoverageTest, UsingModulesMixin`，用的是候选工作树里 base 版的测试辅助，评分时不重置。它又依赖 `tests/helpers.py`，以及第三方包 `unittest_mixins`、`mock`。
- `UsingModulesMixin` 按 `tests/coveragetest.py` 所在目录定位 `tests/modules` 和 `tests/moremodules`。用的是绝对路径，搬迁后仍然有效。
- 原目录 `tests/conftest.py` 的 autouse fixture（`set_warnings`、`reset_sys_path`、`fix_xdist_sys_path`）对 `r2e_tests/` 不生效，属于搬迁伪影。但 4 次 gold 都是 44/44、2 次 noop 都是 43/44，没看到影响。
- 只有一个隐藏测试文件，44 个键互不重复，不会跨文件撞键。

## 4. 双向映射（核心表）

| 公开要求 / 合理旧行为 | 依据 | 测试 ID / 决定性断言 | 覆盖 | 运行证据 / 下一验证 |
|---|---|---|---|---|
| R1 `get_option("paths")` 不报错，默认返回空 `OrderedDict` | `user_prompt.txt:16–17,27`；config.py:231,542–545 | 目标键 test_1.py:346–347 | 覆盖（只经 `Coverage`；返回 `{}` 也能过） | noop 在 346 行失败；gold 通过 |
| R2 set 之后 get 返回新值 | `user_prompt.txt:19–23,27` | 目标键 349–353 | 覆盖（单键，只比 `==`） | 同上 |
| R3 选项名就是 `"paths"` | 题面示例 | 目标键 | 覆盖 | — |
| R4 替换，不与旧值合并 | 示例注释 "Expected to output the new_paths OrderedDict"；其它选项的 set 都是 `setattr` | 无（起点为空） | **缺失**（题面 "containing the new paths" 按合并理解也说得通，属于规格歧义） | 候选 M；上游后来的目标测试从非空起点出发，能区分两者（见 §10） |
| R5 插件拿到 `CoverageConfig` 时同样可用 | 标题 "via Plugins"；control.py:271–276（`[self, self.config][int(time.time()) % 2]`）；plugin.py:207–219 | 无（只测 `Coverage` 对象） | **缺失** | 候选 W1；devcheck pr1_1 的 CoverageConfig 那一行能区分：noop 报错，gold 成功 |
| R6 设置的值会被 `combine()` 使用 | control.py:673–678；doc/config.rst 的 `[paths]` 一节 | 无 | **缺失** | 候选 W2；devcheck pr7_7：noop 输出 `['ci/girder/g1.py']`，gold 输出 `['girder/g1.py']` |
| R7 配置文件读入的 `[paths]` 能经 get 取回 | 题面 "retrieve the current paths configuration" | 无（回归键只检查 `cov.config.paths` 属性） | 缺失 | gold 自然满足；上游后来的目标测试覆盖了这一点 |
| K1 `section:option` 读写 | 公开旧测试 test_config.py | `test_tweaks_after_constructor` | 覆盖 | 43 个回归键 noop、gold 都通过 |
| K2 未知选项的报错格式 | 同上 | `test_tweak_error_checking`、`test_tweak_plugin_options` | 覆盖（不含无冒号的名字） | 同上 |
| K3 插件选项 | 同上 | `test_tweak_plugin_options` | 覆盖 | 同上 |
| K4 `[paths]` 条目名任意，不报 Unrecognized | config.py:290–310 | `ConfigFileTest.*`、`test_tilde_in_config` | 覆盖 | 同上 |
| K5 configurer 插件的既有流程 | tests/test_plugins.py:874–886 | 不在隐藏测试里 | 缺失（gold 没碰这条路径） | 公开可跑；devcheck 没跑成（见 §8） |
| K6 `[paths]` 的顺序决定 combine 结果 | tests/test_api.py:470–511 | 不在隐藏测试里 | 缺失（gold 没碰） | 同上 |

反查：隐藏测试的每条断言都能追到公开依据。目标键就是题面示例，其余 43 个键是公开旧测试原样。没有只出现在隐藏材料里的约束。

## 5. R2E 专项

- **(a) 非 PASSED 键**：没有，44 个键全是 PASSED。因此不存在"更完整的修复把 FAILED 键翻成 PASSED 而判 0"的风险。能让回归键失败的只有真正破坏旧行为的实现，属于正确拒绝，例如：
  - 改掉错误消息格式；
  - 把 `paths` 放进 `CONFIG_FILE_OPTIONS`；
  - 改掉 `config.paths` 这个属性名。
- **(b) 报错是否一致**：noop 目标键的失败原因就是 `coverage.misc.CoverageException: No such option: 'paths'`（log 第 61 行）。
  - 小偏差：题面说异常在 set 时抛出，实际最先失败的是 get（test_1.py:346，对应示例第 16 行）。
  - base 上 get 和 set 抛的是同一条消息，这个偏差不影响开发。
- **(c) 是否泄漏修法**：题面没有给出实现位置。但示例就是隐藏目标测试的原文（值和步骤一一对应），等于测试完全公开。"`paths` option is not recognized" 指向选项查找逻辑，属于正常强度的提示。
- **(d) 是否依赖 base 版测试辅助**：是（§3.3）。
  - `tests/coveragetest.py` 和 `setup.cfg` 都在候选可改范围内，评分时不重置；评分时 pytest 会读 `setup.cfg` 的 `addopts`。
  - 公开提示禁止改测试文件，但并不强制执行。
  - 这是 R2E 共享控制面的问题（清单 31），不是本题特有，这里只记适用。
- **(e) 时间、随机、资源敏感的键**：未发现。
  - 目标键和回归键都不会触发 `_init()` 里的时间分支。
  - xdist `-n3` 的调度顺序两轮不同，逐键结果不变。
  - 内存峰值 281.84 MB（R-f noop 账本 `resource.mem_peak_mb`），测试阶段约 2–3 s。
  - 时间分支只影响解题者自己做的插件端到端自测（D3）。devcheck 两次跑 D3，拿到的都是 `Coverage`。
- **(f) 材料修订**：无。

## 6. gold 检查（方面 5；清单 26、27）

- **公开要求**：R1–R7 都满足。
  - R1、R3、R7：`get_option` 返回 `self.paths`，默认值和配置文件读入的值都能取回。
  - R2、R4：`set_option` 直接赋值 `self.paths = value`，是替换语义。
  - R5：改在 `CoverageConfig`，`Coverage` 经转发自动受益。
  - R6：新值写回 `self.paths`，`combine()` 读的是同一个属性。
- **执行证据**（devcheck `private_gold`，root 身份、一次性容器）：
  - pr1_1：两种对象都返回 `OrderedDict([('magic', ['src', 'ok'])])`。
  - pr4_2：插件路径成功（这次拿到的是 `Coverage`）。
  - pr7_7：输出 `['girder/g1.py']`，别名生效。
- **回归**：只在 set/get 开头加特判，其它名字的查找和报错不变；43 个回归键 gold 全部通过。
- **未测但可以接受的行为**：
  - set 存的是调用者对象的引用，与其它选项一致。
  - 不校验类型。
  - 不对 set 进来的值展开 `~`；`PathAliases.add` 也不展开（files.py:349–383）。
  - 没有更新 docstring、`doc/config.rst`、`CHANGES.rst`。上游 5.1 changelog 的对应条目出现在后来的版本里（见 §10），不算本题 gold 的缺陷。
- 没有无关改动。清单 26、27：pass。

## 7. 候选（写成可直接改成补丁的形式，供协调者用正式评分实跑）

| ID | 类型 | 改法 | 预期得分 | 与公开要求不符之处 |
|---|---|---|---|---|
| W1 | 可能蒙混的部分实现（最可能自然出现） | 只改 `coverage/control.py`，`coverage/config.py` 不动。`Coverage.get_option` 开头加 `if option_name == "paths": return self.config.paths`；`Coverage.set_option` 开头加 `if option_name == "paths": self.config.paths = value; return` | 1（44/44） | 当前秒为奇数时，插件拿到 `CoverageConfig`，`config.get_option("paths")` 仍抛 `No such option: 'paths'`（违反 R5）；公开读者 D2 命令的 CoverageConfig 那一行也仍报错 |
| W2 | 假修复（旁路存储） | 只改 `coverage/config.py`。`set_option` 开头加 `if option_name == "paths": self._paths_override = value; return`；`get_option` 开头加 `if option_name == "paths": return getattr(self, "_paths_override", self.paths)` | 1（44/44） | `combine()` 仍读 `self.paths`，设置的别名不生效（违反 R6）；D5（pr7_7）会输出 `['ci/girder/g1.py']` |
| A1 | 合理替代解 | 只改 `coverage/config.py`。`set_option` 开头加 `if option_name == "paths": self.paths = collections.OrderedDict((k, [os.path.expanduser(p) for p in v]) for k, v in value.items()); return`；`get_option` 开头加 `if option_name == "paths": return collections.OrderedDict(self.paths)`（返回副本） | 1（44/44） | 无。用来确认测试不要求返回同一个活对象，也不排斥规范化 |
| M（可选） | 规格歧义候选 | 与 gold 相同，只是 set 改成 `self.paths.update(value)` | 1（44/44） | 起点非空时结果会多出旧条目，与示例注释的替换读法不符。上游后来的目标测试会拒绝它，但本题题面的措辞两种读法都说得通，所以不作为反例 |

以上"预期 1"都是静态推断：目标键只经 `Coverage` 对象做一次往返，其余 43 个键不涉及 `paths` 的 get/set。

## 8. 开发需求（方面 6；清单 6–15）

| 项 | 需求与事实 | 证据 | 级别 |
|---|---|---|---|
| 解释器 / 导入 | `python` 是 `/testbed/.venv/bin/python`（3.7.9）。`coverage` 从 `/testbed/coverage/__init__.py` 导入，`cd /` 后也是，说明是开发式安装，改源码立即生效。这解决了公开读者 D1 的疑问 | devcheck `env.out`（uid 54321）；grader 账本 `RH2_OBS_IMPORT_PATH` | devcheck 实测 |
| 测试依赖 | pytest 4.6.6；插件 xdist 1.30.0、flaky 3.6.1、hypothesis 4.41.2、forked 1.6.0。`mock`、`unittest_mixins`、`toml` 都可用：`tests/test_config.py` 含 TOML 用例，43 个全部通过 | `pr6_6_pytest.out` | devcheck 实测 |
| pip / 网络 | pip 20.0.2 存在；外部 DNS 和直连都被拒绝；本题任何阶段都不需要网络 | `env.out`；`prelaunch.json` | 实测 |
| 资产 | 不需要外部资产；`/tmp`（1 GiB）和 home（256 MiB）可写 | `prelaunch.json` | 实测 |
| 权限 | agent 可写 `/testbed`（属主 54321）；激活文件不可写 | `prelaunch.json`、`env.out` | 实测 |
| 构建 | 纯 Python 改动，不需要构建；C tracer 是否已编译未知，与本题无关 | 静态 | — |
| 复现 | 公开读者的 D2（pr1_1）、D3（pr4_2）、D5（pr7_7）在 agent 身份下能区分修复前后：noop 报 `No such option: 'paths'` 或不应用别名，gold 对照成功 | devcheck `orig/captures` 对比 `private_gold` | devcheck 实测（gold 对照为 root 身份） |
| 公开回归测试 | 见表后说明 | `pr5_*`、`pr6_6`；eval log | 部分实测；原命令 actor 待验 |
| 其它公开测试 | `test_plugins.py -k ConfigurerPluginTest`、`test_api.py -k test_ordered_combine` 因同一原因没跑成 | `pr5_4`、`pr5_5` | actor 待验 |
| 提交边界 | 修改 `coverage/config.py`（或 `control.py`）。gold 的投影为 `included_paths=["coverage/config.py"]`、`ignored_paths=[]`。`.pytest_cache`、`.hypothesis`、`.coverage*` 都在 `.gitignore` 里，自测残留不会进补丁 | grader 账本；`.gitignore` | grader 实测 |
| 真实模型 | 实际渲染的消息、工具交互、求解成本 | — | actor 待验 |

公开回归测试的具体情况：

- 已实测：`python -m pytest -o addopts="" tests/test_config.py` 在 agent 身份下 43 passed。
- 公开读者的原命令（带 `setup.cfg` 默认 addopts）没有在 agent 身份下跑过：
  - devcheck 把它改写成了带 `-p no:cacheprovider` 的版本。
  - addopts 里的 `--failed-first` 由 cacheprovider 插件注册，禁用该插件后报 "unrecognized arguments"，rc=4。noop 与 gold 结果相同。
  - 这是核对命令被改写造成的伪影，不是镜像缺陷。
- 评分侧以 uid 54322 跑同一组 addopts 是成功的（xdist 起了 3 个节点），所以原命令大概率可用，仍记 actor 待验。

## 9. 交付与评分边界（方面 7；清单 4、16–17、21–22、29–31）

- **4 / 16 / 17**：合法修复只涉及 `coverage/` 下的源码，不会被投影忽略，也不会被官方恢复覆盖（grader 只替换 `r2e_tests/`）。pass。
- **21**：四次 RH2 运行都没有执行失败，`segment_completed=true`，44 个键都在段内解析。pass。
- **22**：M3 独立 runner 在来源镜像上跑两次 gold，都是 44 passed，与 RH2 派生镜像的结果一致。pass。
- **29**：本题范围 pass；共享机制引用其它审查。
  - devcheck 的 git 清理结果：`HEAD_AFTER=17204597…`；refs、remotes、reflog 都是 0；不可达对象 0；HEAD 没有子提交。
  - system 提示里的 gitStatus 只列到 base（`17204597 One clarification` 及更早的提交）。
- **30**：环境不联网。但这个修复从 coverage 5.1 起就公开了（`ea6906b0` 工作树的 `doc/changes.rst:75–88`，issue 967），模型预训练是否见过未知。
- **31**：见 §5(d)。属于共享控制面问题，本题只记适用：隐藏测试导入 `tests/coveragetest.py`，评分时 pytest 读 `setup.cfg`。gold 与 noop 的 `candidate_test_like_paths` 都为空。
- **观察（共享，不针对本题）**：devcheck 中 Claude Code 实际提供的工具是 `Bash`、`Edit`、`NotebookEdit`、`Read`、`Write`，而 `public_bundle.json` 的 `allowed_tools` 只写了 `bash`、`edit`。

## 10. 题目关系与用途（方面 8；清单 5、29–30、37–40）

同仓 5 道题按版本排序：

1. `016af5f6`、`5dbbe143`：5.0.2a1。
2. 本题、`f5eb5f21`：5.0.5a0，base 同为 `17204597`。
3. `ea6906b0`：6.1.0a0。

| 关系 | 核对 | 结论 |
|---|---|---|
| 与 `f5eb5f21` 同 base | 两个公开工作树 `diff -rq` 无差异，两者的 `initial_diff` 都是 0 字节 | 初态完全相同，修复不同。`f5eb5f21` 修的是 JSON 报告缺少分支计数，推断对应上游 5.1 changelog 第 78 行的条目。同族，需放在同一划分 |
| 本题修复出现在 `ea6906b0` 的初态中 | 比对文件：4/4 行命中。直接读 `ea6906b0` 的公开包：`coverage/config.py:428,459` 有相同的特判；`tests/test_config.py:339–361` 有加强版目标测试，先从非空 `[paths]` 读入并断言，再替换 | 确认。`ea6906b0` 的解题者能看到本题答案和更强的测试。如果一题用于训练、另一题用于评测，存在答案暴露 |
| 本题初态含 `016af5f6`（3/3）、`5dbbe143`（7/7）的修复 | 只有机械比对和版本顺序支持；没读它们的 gold（私有） | 线索，未独立核实 |

用途：小型 API 缺陷修复（给一个配置选项加特判）；题面示例就是隐藏目标测试。静态阅读不推断基座成功率或学习价值。

## 11. 八方面覆盖与 40 项初判（稀疏）

| 方面 | 已查 | 未查 / 未知 | 初判 |
|---|---|---|---|
| 公开需求 | 题面、base 源码、调用者、公开旧测试、文档 | 模型实际收到的完整消息：devcheck 的首条 user 消息是核对指令，不是题面 | 3 unknown；23 pass（歧义 A1–A6 不妨碍开发） |
| 材料与初态 | 哈希、diff、noop 失败位置 | — | 1、2、27 pass |
| 测试是否测到要求 | 目标键全链、5 个相关回归键逐条、其余通读 | — | 18、19、20 pass；25 issue；32 并入 25 |
| 误拒 | 精确断言逐条对照公开依据；候选 A1 | 未实跑 | 24 pass（静态）；28 not_applicable |
| 回归与 gold | gold 逐项对照 R1–R7、K1–K6；private gold 对照 | K5、K6 不参与评分 | 26、27 pass |
| 开发条件 | devcheck 全部命令与预检 | 默认 addopts 的原命令、另外两条公开测试、真实模型 | 6、7、8、9、11、13 pass；10 pass（`-o addopts=""` 已实测，原命令待验）；12 not_applicable；14 pass（6 次运行一致）；15 not_checked |
| 交付与评分边界 | 投影、段内解析、独立 runner、git 清理 | 共享控制面不重复审计 | 4、16、17、21、22、29 pass；30 pass（附：预训练是否见过未知）；31 unknown（共享机制） |
| 题目关系与用途 | 跨题比对，并直接读了公开包 | `016af5f6`、`5dbbe143` 方向未独立核实 | 5 issue；33–36 not_checked；37–40 not_applicable |

## 12. 缺口、未知与建议队列

1. **（优先）实跑 W1**：只改 `coverage/control.py` 的补丁，静态预期正式评分得 1。如果确认，记为"目标测试放过部分修复"（清单 25），证据升级为当前 CPU。同一批可以顺带跑 W2、A1，预期都是 1。
2. **检查通过的真实解**：对通过的真实解补丁做一次低成本检查，看修改是否落在 `CoverageConfig`，即是否属于 W1 型（清单 35）。
3. **补跑 devcheck**：以 agent 身份、不加 `-p no:cacheprovider`，重跑公开读者的三条 pytest 命令，确认默认 addopts 可用。风险低。
4. **可选修订（改测试标准，需用户决定）**：如果希望本题的 reward 能区分插件路径：
   - 在目标测试里加对 `cov.config` 的 get/set 断言。依据 R5：标题和 control.py:271–276。
   - 改用上游后来版本的写法，从非空 `[paths]` 起步。依据 R4、R7，这是上游自己测试的演进。
   - 不建议把 `combine()` 断言作为强制项，除非另有公开依据。
   - 不修订也能作为诊断题使用。
5. **划分**：本题与 `f5eb5f21`、`ea6906b0`（以及线索中的 `016af5f6`、`5dbbe143`）归为同族，训练与评测不要跨族划分。
6. **未知**：模型实际收到的消息；真实模型的求解表现和成本（清单 33–36）。

## 附录 A：证据索引

| 证据 | 位置 | 要点 |
|---|---|---|
| R-f noop | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:8`；log `…/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-c_8ee3ccfc.eval.log`（sha256 `290d88a6…`） | reward 0，43/44，只错目标键；`RH2_TEST_RC=1` |
| R-f gold | `…/ledger_r2e_all_gold.jsonl:8`；log `…c_10174c98.eval.log`（`8bcbaa11…`） | reward 1，44/44；`included_paths=["coverage/config.py"]` |
| 环境轮复跑 noop / gold | `runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:8`；log `…rer_4e5c6a85`（`5ac5d933…`）/ `…rer_f2cf72dd`（`3a0f3e74…`） | 与 R-f 逐键一致，只有 xdist 顺序和耗时不同 |
| 派生镜像 | 评分侧：`rh2-r2e-derived/coveragepy:97997d2cd680-r2e_derive_v1`，ID `sha256:ab9a4d0f…`。devcheck：同一 ref 和 recipe 重建，ID `sha256:59ba6725…`。来源镜像 digest `sha256:802b61d5…` | 同一配方的不同构建，镜像 ID 不同属预期 |
| M3 独立 runner | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:29,76`；logs `…/coveragepy/97997d2cd680/gold/a{1,2}/test_output.txt`（`85ed1439…`、`a262dd54…`） | 来源镜像上 gold 两次都是 44 passed |
| devcheck（agent） | `DEVCHECK/orig/`：`captures/*.out`、`prelaunch.json`、`attempt.json` | 预检三项都是 ok；详见 §8 |
| devcheck gold 对照（root） | `DEVCHECK/private_gold/private_control.json` | pr1_1、pr4_2、pr7_7 成功；pr5_* 同样 rc=4 |

## 附录 B：devcheck 命令的 noop / gold 对照

| 命令 | 来源 | noop（agent） | gold（root，一次性容器） |
|---|---|---|---|
| pr1_1（D2） | 公开读者 | 两种对象都报 `No such option: 'paths'` | 两种对象都从 `OrderedDict()` 变为 `OrderedDict([('magic', ['src', 'ok'])])` |
| pr4_2（D3） | 公开读者 | 打印 `configure() got: Coverage` 后，`cov.start()` 抛同一异常，rc=1 | `paths after start: OrderedDict([('magic', ['src', 'ok'])])` |
| pr5_3/4/5（D4） | 公开读者命令，外加 devcheck 插入的 `-p no:cacheprovider` | rc=4，`unrecognized arguments: --failed-first` | 同左 |
| pr6_6（D4 的退路） | 带 `-o addopts=""` | 43 passed | 43 passed |
| pr7_7（D5） | 公开读者 | 打印 `set_option ERROR`，输出 `['ci/girder/g1.py']` | `['girder/g1.py']` |
