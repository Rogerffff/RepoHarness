# python__mypy-16869 — 独立 reviewer 初稿（解封前）

- 日期：2026-09-21；角色：B4 fresh 独立 reviewer，非主审。
- 权威根：`${REPO_ROOT}`；base：`8c2ef9dde8aa803e04038427ad84f09664d9d93f`。
- 建议：`disposition.state=needs_review`，`disposition.scope=static_review`，`usage.intended_use=development_diagnostic`。这是有条件的静态诊断候选，不是 actor 条件已验或正式训练/评测批准。
- 暴露：已读公开原件、完整 test/gold patch、完整 2 F2P/4 P2P 清单、本题环境记录及选定原日志；**不是 result-blind**。未读公开读稿、主审分析/卡片/结构化记录/delta/review、history/refs 或其他题质量结论。环境记录自带历史结果和原日志内 `git show` 不构成独立盲测。
- 本轮仅文本/JSON/hash/tar 成员只读检查；未导入项目、运行 pytest/项目代码、安装、联网、执行容器或修改原题。仅写本文件；保存后冻结，待明确解封才写 `review.md`。

以下证据简称：`P=runs/swegym_quality_batch04_20260921_v1/public/python__mypy-16869`；`V=.../private/python__mypy-16869`；`S=P/base`；`E=runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16869`。所有路径相对上述权威根。

## 独立结论

公开目标清楚：在 Python 3.12、默认 `stubgen test.py` 下，`TypeVarTuple("_Ts")` 用作 `Generic[*_Ts]` 不应使 stubgen 崩溃。base 的 `AliasPrinter` 没有处理 `StarExpr`，继承的 no-op 返回 None，再进入元组字符串 join；源码调用链和历史 noop 的实际失败位置相合。gold 添加递归星号打印，直指这个原因；历史 gold 确实通过所选六项，而不是仅解析了“成功”日志。

尚无足够证据判原题必须拒绝或 gold 引入回归。需要保留两点质量边界：验收不是题面原样输入，且精确文本比公开的“不崩溃”目标更具体。默认 `_Ts` 声明省略的静态证据真实存在，但这是旧有私有名规则，公开文档也明确只生成待人工修订的草稿，不能把它直接升级成“gold 没修崩溃”。本题适合诊断这一小型 AST 打印缺陷；不得由六项通过推断完整 stub 正确性或全部合理解都被接受。

## 需求—测试双向映射

所有测试 ID 的共同前缀为 `mypy/test/teststubgen.py::StubgenPythonSuite::stubgen.test::`。

| 公开要求 / 合理旧行为 | 依据 | 验收与决定性断言 | 判断与证据限度 |
| --- | --- | --- | --- |
| `Generic[*_Ts]` 不崩溃，并保留泛型形状 | `P/user_prompt.txt` 原例/traceback；`S/mypy/stubgen.py:749–758,308–323` | F2P `testGenericClassTypeVarTuplePy311`：改用公开名 `Ts`，期望完整 import、TypeVarTuple 定义和 `class D(Generic[*Ts]): ...` | 核心星号路径覆盖；原样 `_Ts` 未覆盖。历史 noop 对应 NoneType join 崩溃，gold 通过。 |
| 同一星号路径经过语义分析也能打印 | 默认语义分析见 `S/docs/source/stubgen.rst:113–118` | F2P `testGenericClassTypeVarTuplePy311_semanal`，同样精确输出 | 覆盖；测试名后缀启用语义分析。两项均设置 Python 3.11 语法。 |
| 既有显式 `Unpack[Ts]` 保持可用 | 公开已有索引表达式递归打印；新增 test patch 给定样例 | P2P `testGenericClassTypeVarTuple` 与 `_semanal`：typing_extensions 的 TypeVarTuple/Unpack、完整定义/基类输出 | 这两项是 test patch 新增但 base 已通过的测试，不是假设它们原先就在 base；两种分析模式实际参与评分。 |
| `object` 和导入别名 `b.object` 仍被省去 | `S/test-data/unit/stubgen.test:1214–1223`；`get_base_types:754–756` | P2P `testObjectBaseClass`、`testObjectBaseClassWithImport` 均期望 `class A: ...` | 覆盖；后者由 `-k testObjectBaseClass` 子串选中，原日志确认执行。 |
| 题面原样 `_Ts` 默认调用的输出；私有名选项 | `stubgen.py:826–834,1114–1126`；`stubutil.py:767–780`；文档 `:165–168` | 六项均无 `_Ts`，无 `--include-private`，无默认导入模式 | 缺失。静态推断 gold 默认仍输出 `Generic[*_Ts]` 但省略 `_Ts` 赋值；`--include-private` 应保留。未执行，且不是 gold 新增的省略规则。 |
| 常规 Generic、TypeVar-like 定义、非 Generic 调用者不退化 | 公开旧 `testGenericClass[_semanal]`（1198–1212）、`testTypeVarPreserved`（1349–1360）；AliasPrinter 调用者 | 这些公开旧用例不在六个参考项。命名元组/TypedDict/类型别名/类关键字也会调用同一打印器 | 回归保护有限；已追调用点，未穷举所有输入。gold 只补此前无实现分支，没发现具体已支持输入的新回归。 |

测试 helper 已读 `S/mypy/test/teststubgen.py:655–767`：默认写临时 main.py；非 `_import` 一律 `no_import=True`，非 `_semanal` 一律 `parse_only=True`；调用 `generate_stubs` 并读取实际 `.pyi` 内容，再用 `assert_string_arrays_equal` 比较。`helpers.py:107–139,217–233` 仅做路径/行尾清理后比较，未做类型语义等价归一化。不是只看退出码、文件存在或 Mock。test patch 新增版本不足时 skip；实际历史 Python 3.12.4 下六项均执行，无 skipped，故此处 skip 没造成伪通过。

## 合法替代解、漏测及误拒

1. **与 gold 不同、仍可满足精确输出的路线**：在索引/元组打印路径中识别 StarExpr，递归打印其 operand，并按现有 import tracker 记录名字；无需新添 gold 同名方法即可生成同一文本。验收没有内省方法名、调用次数或内部实现顺序，未见强制复制 gold 的证据。
2. **可能误拒的具体范围**：将星号规范化为语义等价的 `Generic[Unpack[Ts]]`，并正确补 `Unpack` 导入、保持 TypeVarTuple 定义，是可讨论的合法输出路线。公开目标没有要求保留星号拼写，现有 AliasPrinter 还会将 Union/Optional 转为 `|`（308–315），故“源码拼写必须原封不动”不是通则；但当前 F2P 的精确输出必然拒绝这种文本。本轮没有实现/运行该候选或验证全输出语义，故记为**静态误拒疑点**，不宣称已证实 false reject。
3. **漏测限度**：所有星号 F2P 使用相同名字 `Ts` 和单个泛型参数，未测混合 TypeVar、member operand、原例 `_Ts` 或实际默认导入入口。只对 `Ts` 作特殊处理的不足修复可能过关；这是从输入范围推断，未做评分反例，不能写成当前已复现攻击。
4. **gold 原例边界**：gold 的递归 `o.expr.accept(self)` 对 `_Ts` 与 `Ts` 使用相同 NameExpr 路径，因此静态支持“不再发生该 join 崩溃”。`_Ts` 赋值在访问基类前已被私有名过滤，之后 `require_name` 只管理 import，不会追补本地赋值。公开文档 `stubgen.rst:50–53` 的 draft/manual-update 定位和默认省略私有定义说明降低了把这个现象判为本次必修要求的依据。需区分输出完整性限制与核心 crash 修复。

## 八方面覆盖及未查项

| 方面 | 已查 / 结论 | 未查或不能外推 |
| --- | --- | --- |
| 公开需求（23）与消息（3） | 原例、版本、默认命令、public_hints、相关公开文档；最小目标明确 | `user_prompt.txt` 是静态渲染，真实 solver rendered 消息未见；3=unknown，不能用题意清楚代替它。 |
| 材料 / 初始问题 | base 身份字段、patch 内容一致性、源码故障路径、noop 真实 trace | 未重新重放，不用 gold diff 单独证明初态。 |
| 测试覆盖 | 完整 test patch，全部 2 F2P/4 P2P 及 helper | 原样 `_Ts`/默认导入/扩展参数组合缺口，未检查全仓测试。 |
| 合法替代解（24） | 可生成同样输出的另一实现；Unpack 归一化疑点 | 24 保留 unknown，未证明所有合理解均接受。 |
| gold / 回归 | 完整 gold，调用链、公开 Generic/TypeVar-like 用例、私有名规则 | 不宣称完整生成语义正确，也未证实额外回归。 |
| 开发条件 | 公开开发入口、依赖和最小命令可定位；既有 grader 成功明确 | actor 解释器、资产权限、安装消费和 CLI 交互未验。 |
| 交付 / 评分 / 资产（29） | test patch 只改测试/helper；gold 修改的普通源码实际被投影；官方恢复两个测试路径 | 当前真实 actor 镜像可见资产/历史/答案泄漏未知，29=unknown；完整安全与 parser 审计未重做。 |
| 关系 / 用途 | 源码局部 AST 崩溃修复；题面暴露 traceback/入口但没给补丁 | 未读其他题，关联/重复簇未检查；33–36 真实 solver 能力/成本未知。见过 gold 的本稿不可给 solver。 |

## 开发条件、交付及原运行证据

| 操作 / 资产 | 公开依据 | 已有证据、缺口与最小验证路径（未执行） |
| --- | --- | --- |
| 使用当前工作区 Python/stubgen | `CONTRIBUTING.md:39–44`；公开 issue | 在实际 agent/54321 shell 记录 `id`、`pwd`、`python -V`、解释器及 `mypy.stubgen.__file__`，确认候选源码生效；随后运行原样公开 `stubgen test.py`。历史 grader 的导入成功不能代填 actor。 |
| 依赖与可编辑安装 | CONTRIBUTING 的 requirements、`pip install -e .`；pyproject build-system | 需要现有 pytest/xdist、mypy-extensions、typing-extensions、打包依赖、typeshed（base 已含）；本题复现不需要数据集、外部服务或 GPU。准备依赖可能需联网下载，准备完成后运行不需要公网。系统前缀可写性及是否必须重装待 actor 验证。 |
| 公开窄测试 | CONTRIBUTING:74；`S/mypy/test/teststubgen.py` | 建议 `pytest -n0 mypy/test/teststubgen.py -k 'testGenericClass or testTypeVarPreserved or testObjectBaseClass'`；未将隐藏测试作为 solver 开发前提。原配置 `-nauto`，历史实际生成 11 workers；窄测试可用公开推荐 `-n0`，不假设 actor 资源实测。 |
| 交付源文件 | `mypy/stubgen.py` 为普通源码 | gold ledger projection included_paths 只有该文件，ignored_paths 空。历史 setup 恢复 `mypy/test/teststubgen.py` 与 `test-data/unit/stubgen.test`，再应用 test patch；相关修复路径不被恢复。public_hints 的笼统“所有测试修改不计分”是待核真实输入的共享声明，但本题合理源代码修复无需依赖改测试。 |

原件复读范围及定位：

- `E/noop/ledger.jsonl:1`：reward 0，F2P 0/2、P2P 0 fail/4、安装 rc 0、测试 rc 1、stage_error null、cleanup.removed=true。`E/noop/eval_logs/evallog_replay-er19-iw1-python___fd19ff5b.eval.log:422–541` 显示六项实际执行，两个 F2P 均在 `AliasPrinter.visit_tuple_expr` 的 join 因 NoneType 失败。
- `E/gold/ledger.jsonl:1`：补丁 SHA 与本题 gold 一致，reward 1，F2P 2/2、P2P 0 fail/4，安装和测试 rc 均 0，cleanup.removed=true。`E/gold/eval_logs/evallog_replay-er19-iw1-python___13fbae98.eval.log:194–239,411–472`：两个官方测试文件恢复/应用成功，可编辑构建和安装完成，六项 PASSED，18.26s。这里的“full test”仅是派生 `-k` 命令六项，不是全仓回归。
- 两行均为历史 RH2 grader 条件：`rh2grader/54322`，2 CPU/4 GiB、deny_all；候选应用用户 agent/54321 不等于运行真实 solver。派生镜像 `sha256:5cb7a943ddd7b212706e5413fedc61c8e8cccf3edc8f73e583c06e967b4f2ce1`，recipe `install-wave1:python__mypy-16869`，scripts digest `sha256:f3e13f2518ab8a2ae6396c156ad5805fd2f106d818b1d9db76991b78d11615df`。记录峰值 gold 880.328 MB / noop 912.902 MB，只适用于当时 grader。
- `runs/env_recipe_repair_20260919/install_wave1/run_install_wave1.py:24–65` 复读：只 COPY 离线 wheels，设置 PIP_NO_INDEX/PIP_FIND_LINKS，原 replay CLI 用 noop/gold-dir 和派生镜像；本题 inventory entry 没有 recipe/materials/bindings 覆写。未读其他题 entry。inventory 声明当前本地缺构建 context，原 summary 是历史 `/work` 路径，目标镜像存在性/可达 summary 未验，不能直接视作可运行配方。
- 对 `frozen_sources/baseline.tar.gz` 只用 `tarfile.extractfile` 读取并校验 inventory 中四个成员 hash；未解包/执行。重点读 `scripts/replay_grade.py:49–95`、`.../replay_grade.py:691–704`、`.../prepared_task_face.py:128–156,194–228` 及 `spec_vendor.py` mypy selector。它们支持“历史重放候选评分”及“官方路径恢复”，不支持真实 actor 消息/工具成功。

一致性检查：`V/test.patch` SHA256=`6d6d9ce5ba34022d813f91f0bb31e454e6940201dda69d9b9e4166f02b38e144`，与 grading.test_patch 逐字一致；gold SHA256=`c48adbd28c5b5542afb4875ef6be5109a2907ab95cbbae216d8be9e8b879d421`，与 validation 和 ledger 一致。两份原日志 hash 分别为 noop `44113d4526300b34bba9b09012a74dff713f1fd70f0f5031b3e7c3f001438a2c`、gold `7b6f37747435fb991f2bfe225e9bf873fbad77a6351158523282927eff56a1ce`，均与环境记录一致。这是本轮文件核验，不是本轮测试结果。

## 唯一优先下一步

在配方和实际 agent 身份已准备可用的条件下，做一次**题面原样 `_Ts` 的 base/gold 定点 CPU 对照**：记录真实 shell/解释器/源码路径，分别运行默认 `stubgen test.py` 与 `--include-private`，同时保存退出码和生成 stub。它直接区分“gold 消除原例崩溃，仅保留已有私有名省略”与“原样默认入口仍有不同故障”，并验证 actor 是否能执行最小公开复现。若前者成立，应限定本题结论为 crash 修复，不因草稿完整性限制宣判拒绝；若后者成立，再定位为语义缺口或 actor 配方缺口。当前不执行，也不要求为了数量同时制造两个对抗候选。
