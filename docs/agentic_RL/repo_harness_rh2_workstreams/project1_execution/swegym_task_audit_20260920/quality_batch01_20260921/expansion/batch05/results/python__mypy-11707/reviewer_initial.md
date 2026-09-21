# python__mypy-11707 — reviewer independent initial

审查范围：`static_review`；建议状态：`needs_review`。用途限 `development_diagnostic`。本稿在读取主审、公开读者、本题旧质量报告或其他题结论前独立完成，等待协调者明确 release 后才交叉复核。没有运行、导入、安装任何项目，没有网络、Docker、SSH、模型或候选实验；本轮仅阅读原件、标准库解析/哈希与 frozen archive 的 `tarfile.extractfile`。未改题、测试、gold、评分或环境材料。

路径约定（均在唯一权威 workspace）：

- ROOT=`.`
- P=`runs/swegym_quality_batch05_20260921_v1/public/python__mypy-11707`
- V=`runs/swegym_quality_batch05_20260921_v1/private/python__mypy-11707`
- ENV=`runs/env_recipe_repair_20260919/install_wave1`
- FROZEN=`runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`

## 独立判断

这是“同名子模块存在时，非模块对象的导出可见性错误”修复。base 中 `process_imported_symbol` 只因 `fullname in self.modules` 就放开非公开导入，未确认实际符号是模块，导致包中的同名类可通过改名导入继续被导出。gold 为该例外增加 `isinstance(node.node, MypyFile)`，与 base 文档和旧 stub 测试一致。历史真实 RH2 的 noop/gold 确实区分了这个 bug，不能据此认为题面期望或全部相关回归已满足。

两项需要保留的问题：

1. **公开目标方向冲突。** 题面明确希望 `from a import Y as W` 与 `from a import X as W` 在 `--strict --no-implicit-reexport` 下都成功；gold 静态效果则是把原来偶然成功的 X 路线也变为拒绝。指定 base 的公开命令行文档已经明确“改名 from-as 不导出”，旧 stub 测试也支持该规则，因此 solver 可从公开材料识别报告人的误解，而不是只能从隐藏答案猜规则。但公开材料有两种方向，不能直接把 gold 称为实现了题面的明示 Expected Behavior。建议先明确按既有导出规则修一致性，并保留原 issue 的错误预期来源；不把这项冲突简化成隐藏测试无依据或题目必然不可解。
2. **有具体静态漏测候选。** 若把目标行粗改为 `module_hidden = not module_public`，新增 F2P 和唯一 P2P 按源码推断都能满足，但会破坏公开 `testReExportChildStubs` 的真实子模块导入。真实子模块例外正是 gold 保留的边界，当前评分没有选择保护它的旧用例。此结论是待 CPU 验证的候选，不是已实测 reward 漏洞。

未发现 gold 在所读路径中新增错误回归；也未证明所有合法实现都会接受。原版暂不作为需求无歧义、评分已充分校准的模型探针。若保留为带说明的开发诊断，需显式携带上述限制，并另验 actor 开发条件。

## 公开视角先行得到的目标与歧义

方法卡与 inventory 的 common/本题条目定位后，先读 P 的 `user_prompt.txt`、`public_bundle.json`、`base_identity.json`、`environment_brief.md`，再读指定 base 文档、语义代码、相关旧测试，随后才读 V 的测试和 gold。

题面四文件 MWE 中 `a/__init__.py` 导入同名类 X 并令 `Y = X`；c 将 X 或 Y 改名为 W；d 再导入 W。字面请求是两种路径都成功。标题的 `--no-explicit-reexport` 是笔误，实际命令和 base CLI 都是 `--no-implicit-reexport`，不妨碍定位。原报告版本 0.910/Python 3.10，指定 base 和评分版本是 0.920/Python 3.9；代码路径与原症状吻合，版本差异本身不是错题证据。

P/base/docs/source/command_line.rst:556–576 明确写 `from foo import bar as bang` 不导出，而 `bar as bar` 或 `__all__` 导出；config_file.rst:592–610 解释默认 True、stub 永远关闭隐式导出。P/base/mypy/main.py:670–673 将该开关纳入 strict。P/base/test-data/unit/check-modules.test:1819–1840 已要求 stub 的 `C as D` 不导出，`C as C` 可导出。故应区分“修一致性”与“把所有 as 都视为显式导出”；公开证据支持前者，但不消除题面文字的反向期望。

公开合理实现范围：可以在导入符号处理处检查实际节点种类，也可重构导入分支，保证真正的子模块例外保留、同名类/别名不意外获得可见性、同名显式导出与 `__all__` 继续有效。没有理由要求必须使用 gold 的单行表达式或 helper 位置。

## 需求—断言双向核对

全部新增/修改测试只有 V/test.patch 的 18 行新 case；无生产源码或 helper 混入。评分全量清单为 F2P 1 个、P2P 1 个，均已读完。以下简称 F=`mypy/test/testcheck.py::TypeCheckSuite::check-modules.test::testReExportChildStubs3`，P2=`mypy/test/testcheck.py::TypeCheckSuite::check-modules.test::testNoReExportChildStubs`。

| 要求/回归与依据 | 测试与决定性断言 | 判断与证据层次 |
| --- | --- | --- |
| 同名显式导出仍为类，不应变成模块或 Any；公开旧 `C as C` 规则 | F：package/__init__.pyi `from .mod import mod as mod`；util.pyi 同名导入；main `reveal_type(mod)` 必须为 `def () -> package.mod.mod` | 覆盖；noop 已有正确 reveal，gold 保持。精确类型输出沿用公开测试形式。 |
| 同名子模块存在不能令改名类导入自动导出；base 文档/旧 stub 规则 | F：util.pyi `from package import mod as internal_detail`；main 导入 internal_detail 必须报 `Module "util" has no attribute "internal_detail"` | 覆盖；noop 原日志明确仅缺该错误，gold 通过。名字只是 fixture 数据，没有规定 solver 新 API。 |
| 非公开 C 被 from-import 和属性访问拒绝，显式 D 可实例化并保留 str 属性 | P2：`from mod import C,D` 报 C 缺失；`mod.C` 报错；`mod.x` 为 `mod.submod.C`；`mod.D().a` 为 str | 全部断言已读，历史两角色均通过。其 C 名称没有与子模块 fullname 碰撞，不能替代真实子模块例外保护。 |
| 题面 `.py` 原例 X/Y 两种路径都接受 | F 是 `.pyi`、无 flags，也无 `Y = X`、strict 或目录 CLI；gold 使 X 路线也隐藏 | 缺失且与字面期望方向冲突；原例未有本轮/所引历史实际运行。静态预期 base 为 Y 拒绝/X 接受，gold 为两者拒绝。 |
| 真正子模块仍可 `from mod import submod`，或 `import mod.submod` | 公开旧 `testReExportChildStubs`/`testReExportChildStubs2`（check-modules.test:1879–1911） | 未参与本题评分；gold 显式保留此边界。粗改候选静态预计破坏前者但仍过 F/P2。 |
| 普通 `.py` 默认隐式导出、禁用时规则、`__all__`、星号与 `__getattr__` | 已读 check-flags.test:1541–1648 的各 NoImplicitReexport case；gold 不改变 module_public 或 adjust_public_exports | 未被所引运行选择；静态看规则未变，不填运行 pass。 |
| 多轮导入/缓存和别的符号种类 | 已读 check-incremental.test:5589–5612 的导入环；nodes.py 的 visibility 序列化；Placeholder 分支 | F/P2 是冷运行，默认 cache=/dev/null；TypeAlias、函数/变量碰撞、增量更新未覆盖；未断言 gold 必坏。 |

F 没有 `# flags:`，`Options.implicit_reexport` 默认 True（options.py:173），依靠 `.pyi` 关闭隐式导出。其错误文本没有 `implicit reexport disabled` 后缀，是 report_missing_module_attribute 按当前 options 选择旧有消息的结果（semanal.py:1939–1955），不说明它测过 `.py` 开关。

测试 helper 已追到：testcheck.py:115–227 解析 options 后调用 `build.build` 并完整比较诊断数组；data.py:31–81/168–184 将 `[file]` 和 builtins fixture 加入 case，:269–315 在临时目录建文件并清理，:379–487 解析 case/续行及 E/N 注释；helpers.py:46–120 精确数组比较（仅 can't/cannot 归一），:301–307 归一路径，:365–397 解析 flags；fixtures/module.pyi 全文已读。F/P2 没有 mock、宽异常吞掉、无操作式断言或 testpatch helper 修改。历史 noop 的断言栈也到 testcheck.py:227，证明相关测试体确实执行。

## 根因、gold 与候选边界

P/base/mypy/semanal.py:1817–1885 取 `module.names[id]`，并以 `use_implicit_reexport or id == as_id` 决定 module_public。:1887–1925 原版只看 fullname 是否存在于模块表，导致取到 TypeInfo 类时也被误当成子模块例外。:4702–4713 将 module_public/module_hidden 附在新的导入引用上；下一模块的 from-import 在 :1870 检查 hidden，模块属性/限定名则在 :4334–4418 检查。nodes.py:3128–3144 清楚区分 module_public（星号导入）与 module_hidden（完全不导出），不能混成同一位。

对原例静态追踪：a.Y 不在模块表，c 的 `Y as W` 被隐藏；a.X 对应已加载子模块但取到实际类，旧代码错误地令 c.W 不隐藏；gold 增加实际节点为 MypyFile 的必要条件，所以 c 的 `X as W` 也隐藏。该改动修正例外类型，未令字面 Expected Behavior 成立。与 gold 不同的合法实现可以显式分支计算可见性、保持真正模块例外与原来的导出规则；F/P2 没有限定内部写法。

粗改候选 `module_hidden = not module_public` 不含特定测试名称或硬编码，代表常见的过度简化：F 的同名类仍公开、internal_detail 被隐藏；P2 的 C/D 规则不变；但 `testReExportChildStubs` 中 mod/__init__.pyi 的 `from . import submod` 被隐藏，主文件 `from mod import submod` 将报错。这是具体、可区分的错误修复路线，需要新 CPU 结果确认得分与回归，不能只凭公式称已经攻击成功。

## 八方面覆盖、材料与环境

| 方面 | 本轮已核/限制 |
| --- | --- |
| 公开需求 | 已核完整题面、提示、base 文档、旧测试与 CLI；目标冲突如上。公开包是静态渲染，未捕获真实 CC 消息。 |
| 材料/初态 | commit=`5d71f58b9dc5a89862253fef3d82356a7370bf8e`，tree=`880d3d6572dfa456a5a96e752e1e0e49431da4ca`；base_identity 记录 1747 个 blob 验证、无 gitlink/LFS/软链接、无 .git。patch 上下文和原日志对应；没有遍历未来 Git 历史。 |
| 测到要求 | 全部 test_patch、F2P/P2P、fixture/helper 与运行选择已核；两个用例检出实际 bug，但题面 `.py` 与真实模块回归缺失。 |
| 误拒合理解 | 不将常规精确诊断直接判过严；未发现内部结构绑定。未实测替代正确实现；字面需求与既有规范冲突单列，不能把 solver 遵从任一方向都预先定为错。 |
| gold/回归 | 已核 gold 全部、导入/visibility 消费者、显式导出、all/星号、别名与缓存相关路径及旧用例。未穷举全仓、未运行回归；没有新发现 gold 的具体错误回归。 |
| 开发条件 | 入口与最小测试可定位；依赖与离线 wheel 历史成功只属于指定 replay/grader。agent/54321 的实际激活、源码载入、依赖和写权限待验。 |
| 交付/评分 | gold 仅改 mypy/semanal.py；官方恢复仅 test-data/unit/check-modules.test。无修复必须落在被恢复文件的冲突；helper/配置整体防护不在本题重新审计。 |
| 关系/用途 | 未读其他题，不能推断近重复/跨题答案关系。题面给 MWE，没有给目标 helper/补丁；审查者已暴露 gold、隐藏测试和历史运行，不能充当未污染 solver。真实镜像资产/公开 Git 历史答案泄漏未检查，静态包无 .git 不是镜像无泄漏证明。 |

材料绑定已用标准库核对：V/test.patch 与 grading.test_patch 完全相等，SHA256=`bf4a36a7169cbbf57420bd8e3d8626ebfcbdeb62816261fefeb900afc559bb9c`；gold 与 validation.golden_patch 相等，SHA256=`1d25e148e9ab3295d29619c8941012b9186059c405a204d5dccceb941e89267c`，也等于历史 gold ledger candidate hash。`runs/full216_rh2_diagnostic_20260919/remote/replay/private/host_grading_views.jsonl` 仅选读本题第 193 行，grading 与本包相等；行去掉结尾换行的 SHA256=`cd08fb59d9cecc3a4c71ee969bb55765890db68a2bca4f4adb08cebb6a98baa3`，符合 inventory。install_wave1/plan.json 仅选 index 53，canonical hash=`7a8bd1773676e876f92b61416f451d124f1805dae9b39e4df4a7ff1ecc68e7e6`。

## 原始运行证据与适用范围

ENV/tasks/python__mypy-11707 下的 gold、noop ledger 各第 1 行、driver.log、diagnostics 和 eval.log 已核。日志 SHA 与 run_refs 一致：

- gold `gold/eval_logs/evallog_replay-er19-iw1-python___bab5562a.eval.log`：`e4aeeba767741438779a16c3ca753049183bd412e2dfa822374bf771098603c0`。:651 明确执行 `pytest -n0 -rA -k 'testReExportChildStubs3 or testNoReExportChildStubs'`；:656 只选 2 项；:662–668 两项 PASSED、test_rc=0。ledger reward=1、F2P 1/1、P2P fail 0/1。
- noop `noop/eval_logs/evallog_replay-er19-iw1-python___521f6047.eval.log`：`231d81906905f1f462e655a8b9f534153b9ecd1ca0c66611b17a14fc11ab37e1`。:633 相同命令；:643–655 明确缺失 internal_detail 错误、reveal 相同；:659–665 P2P PASS、F2P FAIL、test_rc=1。ledger reward=0。
- 两者无 reference missing/skipped、num_parsed_tests=2、无段外解析；安装成功日志、测试完成标记与 cleanup removed=true / driver 无 cleanup failure 对应。不是只依赖 environment_record 的汇总布尔。

这是 2026-09-19 真实 RH2 补丁 replay 到 grader 的历史证据，不是本轮重跑、原 issue CLI 复现或真实模型 actor 轨迹。应用候选用 agent/54321，安装/测试用 rh2grader/54322，后者可写 conda testbed 前缀；不能把两者身份混用。历史 grader 为 deny_all、2 CPU/4GiB、PID512、shm64MiB、tmp1GiB，选定两项测试约 4.2 秒，峰值内存约 127–132MiB，不能据此估算完整求解资源。

ENV/tasks/python__mypy-11707/image.json记录 base manifest `sha256:b3f866b27cdaaa85800026ad13c38cf762c2f6ebcf03fb24a7d7c351e844969e`；派生 image=`sha256:e3e933e4d2db3fb698b543dc0b878dbcb24beace775bc9ad3eb25e7a873eab1f`，recipe=`install-wave1:python__mypy-11707`，保留基镜像 layers，只 COPY 离线 wheels 并设置 PIP_NO_INDEX/PIP_FIND_LINKS。pins 为 setuptools69.5.1、wheel0.43.0、packaging24.1。本题 status.json 的命令和 run_install_wave1.py:24–66 对应此来源；未使用原 analysis_149 质量汇总。inventory 明确原 wheel context 在权威宿主已缺失、目标镜像可用性未查，image.json 不能当可复建 payload。

重要初态区分：noop log:140 起的 `git show` 显示的是基线提交自带的 typeshed 修改，不是未提交环境差异。实际 `git diff <base>` 在 noop:356–365 只有 test-requirements.txt 添加 `types-typing-extensions==3.7.3`；gold:357–383 再加 gold 的 semanal 改动。noop projection included_paths=[]，gold 仅 [`mypy/semanal.py`]，所以这个依赖 pin 属于历史镜像初态，不是 solver 修复。gold:384–391 与 noop:366–374 证明官方 .test 被恢复并 clean apply。

FROZEN 只以 extractfile 读 inventory 指定四成员，哈希均一致：scripts/replay_grade.py=`6115714639d677a7a2b116738507d8adf8fc9f5a4f4059ff7f792360359a0311`；adapters/slime/replay_grade.py=`b8f1fbe2f37032e52b496f2eb9296c8a647a3072af2b7def600809544c9999fb`；prepared_task_face.py=`3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27`；spec_vendor.py=`8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`。未解包、未执行。spec_vendor.py:183–197 从整个 test_patch 中的 case 名生成 -k，解释为何 P2P 由上下文被选择，而附近真实子模块旧例未被选择。prepared_task_face.py:179–228 与 :298–351 区分受信测试恢复、候选测试、公开 rollout 镜像，且 test_globs=()；replay_grade.py:293–374 区分 candidate 容器的应用/导出与后续 grader。没有把这个 replay 应用补丁阶段冒称真实 Claude Code 开发链验收。

## 开发需求与最小后续实验

| 操作/资产 | 公开依据 | 现有证据/剩余缺口 | 后续最小验证（本轮未执行） |
| --- | --- | --- | --- |
| 使用工作区 mypy 入口并令 source edit 生效 | CONTRIBUTING.md:20–49；semanal.py；setup.py 默认 USE_MYPYC=False | 历史 import probe `/testbed/mypy/__init__.py`、editable install 与 gold/noop 分化；真实 actor 的解释器及 semanal 是否加载本地源码未知 | agent 实际工具 shell 记录 UID/HOME/cwd/PATH、`python -c 'import sys,mypy,mypy.semanal; print(sys.executable,mypy.__file__,mypy.semanal.__file__)'`，预期源码均来自 /testbed。 |
| 本地复现和窄测试依赖 | mypy-requirements.txt、test-requirements.txt、pyproject.toml；pytest.ini 默认 -nauto | 核心 typing_extensions/mypy_extensions/tomli、pytest6/xdist1 等历史已装；安装所需 build wheels 被派生镜像提供；actor 是否消费该镜像未知 | 公开旧测试入口 `python -m pytest -n0 mypy/test/testcheck.py -k 'testReExportChildStubs or testNoReExportChildStubs or testNoImplicitReexport'`；`-n0` 覆盖默认并行。 |
| 公开四文件 MWE、builtins/typeshed 和临时写目录 | user_prompt、data.py、fixtures/module.pyi；base identity 无子模块缺口 | 都是仓库/本地文本，无运行期服务、权重、GPU或公网需求；准备时固定依赖即可；actor tmp 权限待验 | 在可写临时目录逐一放置原例 X/Y 版本，以该工作区 mypy 跑 `--strict --no-implicit-reexport`，区分依赖故障和预期诊断。 |
| 交付源码 | public_hints NON-TEST、gold 和投影记录 | 合理修复仅需 semanal.py；无需把系统包/测试修改作为交付。公开“所有测试改动永不计分”的解释不代表当前统一路径规则，但本题修复不受其阻碍 | 核改动确实只进入候选源码、官方恢复只覆盖指定 .test；环境准备无需由 solver 写系统前缀。 |

**唯一优先实验：**经后续授权，在固定本题派生条件下做 base/gold/上述粗改三方定点对照，同时跑官方 F/P2、公开 `testReExportChildStubs` 与原 issue 的 X/Y `.py` 版本。静态预计：base F fail/P2 pass、X 接受/Y 拒绝；gold F/P2 pass、真正模块旧例 pass、X/Y 都拒绝；粗改 F/P2 pass、真正模块旧例 fail。每项单独保留退出码/诊断/score，先验证公开期望冲突与漏测候选，再据既有文档决定中性澄清和回归补测；不得为保 gold 默默改变题意。此实验同时不能替代 actor 实际入口、镜像/依赖消费与模型消息验证。

暴露记录：本稿阅读了方法/角色/环境卡，P 原件与所列相关 base 文件，V 中 test.patch、gold.patch、grading.json、validation.json、environment_record.json、run_refs.json，本批 inventory 仅 common 与精确本题 entry，指定原始安装脚本、index53、status/image、两角色原始日志/本题 ledger、host_grading_views 精确本题行及指定 frozen 四成员。未读 O 下任何主审/公开审查/旧结论/card/screening 文件，未读 own history refs、其他题或质量汇总/handoff。未启动 subagent。封存后停止，等待 release。
