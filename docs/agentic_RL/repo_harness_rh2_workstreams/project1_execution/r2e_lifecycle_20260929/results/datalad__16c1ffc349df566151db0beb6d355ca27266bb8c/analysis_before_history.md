# datalad `16c1ffc3`：私有主审读历史前初判

- 题目：`datalad__16c1ffc349df566151db0beb6d355ca27266bb8c`（base `fddce1e754d3`，datalad 0.5.1.dev1，2017 年春）。无材料修订（`P:revisions.json` 为 `[]`）。
- 角色与时点：R2E 私有主审（单题闭环试行 2026-09-29），干净上下文。本文件在打开任何历史调查与 devcheck 结果之前封存。
- 路径约定：
  - `W:` = `PUBLIC_DIR/worktree/`（解题者看到的 `/testbed`）；`PUB:` = `PUBLIC_DIR/`；`P:` = `PRIVATE_DIR/`；
  - `runs/...` 相对仓库根；
  - 同仓其它题公开工作树：`58ba5165:` = `runs/r2e_static_prep_20260924/v3/public/datalad__58ba5165234cb16de0e8463ee75097362099835f/worktree/`，`19f5b450:`、`9ba5de09:`、`6b6fa389:` 同理。
- 证据标记：〔读〕静态阅读与源码推断；〔史跑〕已有 RH2 正式评分或 M3 独立 runner 的原始日志；〔待跑〕需协调者实跑。
- 阅读范围：
  - 方法：角色卡、统一标准 v1、八方面协议、R2E 环境卡、记录模板、40 项清单；
  - 本题：`public_read.md`、`commands.json`、`PUBLIC_DIR` 全部（工作树按需）、`PRIVATE_DIR` 全部；`run_refs.json` 所列 4 份 RH2 eval 日志、M3 账本第 3/51 行与两份 `test_output.txt`；两份跨题扫描；
  - 同仓 4 题的公开包：题面，以及相关源码与测试。
- 没读：history、各审查目录、devcheck 结果、同仓其它题私有包。
- 没运行项目代码；只在 scratchpad 里对候选与修订补丁做了 `git apply --check` 和 `py_compile`（语法检查）。

## 0. 结论摘要（暂定）

1. **键的构成。**
   - 目标键只有 `test_result_filter`：noop FAILED、gold PASSED，两轮一致。
   - `test_eval_results_plus_build_doc`、`test_interface_prep` 是活的回归键。
   - 其余 5 个期望 FAILED 的键是**死键**：R2E `conftest.py` 的 `path` fixture 与 datalad 的 `@with_tempfile` / `@with_tree` 装饰器冲突，报 `TypeError: ... got multiple values for argument 'path'`，测试体从不执行。只改库代码的候选（包括更完整的修复）都翻转不了它们。
2. **第 2 步：示例拟合。** 核心断言就是题面示例原样：隐藏测试的 `greatfilter` 对应题面 `custom_filter`，同一调用 `Test_Utils().__call__(4, dataset='awesome', ...)`，同一检查 `'dataset' in kwargs`。→ S1（T2c）〔读〕。
3. **第 3 步：退化探测。** 核心断言写在 filter 回调里，外层不检查返回结果。退化候选 D 把 `except ValueError` 改成 `except Exception`，吞掉 filter 的错误，预计得 1。→ S1（T2b）〔待跑〕。
4. **第 4 步：常见错误修法。** 最自然的"半对"修法 N 无条件执行 `result_filter(res, **_kwargs)`，预计得 1〔待跑〕。但它会让以下调用全部 `TypeError`：
   - `ds.create()`：Create 的类级默认 filter 是 Constraint；
   - `clean(dataset=ds, result_filter=lambda x: ...)`、`ds.save(result_filter=is_ok_dataset)`；
   - CLI 的 `--report-status/--report-type`。

   → S1。原本能兜住这类回归的 `test_dirty` 等，恰好是那 5 个死键。
5. **可能误拒合理解（T1，conditional）。** `sadfilter` 要求"没传 `dataset` 时 kwargs 里不能有这个键"，题面没有规定这一点。上游后来改成连默认值也传入：同仓题 `58ba5165`（0.17.9）的公开工作树里，同一测试改成了 `kwargs.get('dataset', 'bob') == None`。按这种语义写的合理解 C2 预计判 0〔待跑〕。
6. **题目关系（X1）。**
   - `58ba5165`、`19f5b450` 的初态含本题修复的重构版，以及更新后的 `greatfilter`/`sadfilter`；
   - 本题初态含 `9ba5de09` 的修复（反向包含）；
   - 两份机械扫描都漏报了这些关系（原因见 §9）。
7. **暂定处置与用途。** S1，走 R-c：新增两个隐藏测试，加两个 expected 键。R-b（放宽 `sadfilter`）只能与 R-c 同批，待 C2 实跑和复核后决定。用途：
   - 问题定位 yes；
   - 能力比较 conditional；
   - 训练候选 no（现版本；R-c 验收后重评）；
   - 留出 no。
8. **唯一最值得先做：** 按正式评分（1200 s 时限）同批实跑 D 与 N（附录 A），然后跑 C2。

## 1. 公开读者没有捕获的条件（第 1 步）

公开读者记录的需求 R1–R9、歧义 A1–A3 和兼容性分析，我都对照源码核过，结论一致。它是静态阅读，以下条件它没有、也无法捕获：

- **实际消息**：渲染后的系统提示、CC 版本与工具定义没有捕获（`public_read.md` §5 已声明）。
- **`.venv` 包**：评分侧日志显示有 pytest 7.4.4（带 cov 插件）、nose 和 mock。
  - 依据：noop 日志 `:16-18`、`:135-147`；`P:hidden_tests/test_1.py:17-25` 导入 nose 与 `datalad.tests.utils`，后者在 `W:datalad/tests/utils.py:27` 导入 mock。
  - 解题与评分用同一镜像，但 actor 侧仍待 devcheck 确认。
- **装饰器测试在 pytest 下会 ERROR**〔读〕：
  - `W:datalad/interface/tests/test_utils.py:71-72,106,169,218,267` 的 `@with_tempfile` / `@with_tree` 测试，经 `functools.wraps`（`W:datalad/tests/utils.py:423,561`）向 pytest 暴露了 `path` 参数；
  - 解题环境没有 R2E 的 conftest，pytest 会报 fixture 'path' not found；
  - 公开读者的 `public_tests_narrow` 只选了不带装饰器的测试，避开了这一点。解题者如果整文件运行 `test_utils.py`，会看到 5 个与本题无关的错误。
- **git-annex**：是否在 PATH 未知，`env_imports` 会打印。
- **评分边界**：评分侧只替换 `r2e_tests/`，仓库测试辅助 `datalad/tests/utils.py` 不会重置，见 §4(d)。
- **`install.sh`**：镜像里有这个未跟踪文件，公开工作树没有（`PUB:worktree_manifest.json` 的 `untracked_missing`）。评分不执行它（日志 `RH2_INSTALL_SKIPPED=1`）。

## 2. 隐藏测试展开（第 2 步）

`P:hidden_tests/` 含 `__init__.py`、`conftest.py`、`test_1.py`。`test_1.py` 与公开的 `W:datalad/interface/tests/test_utils.py` 只有两处差异：
- 相对导入改成了绝对导入（`test_1.py:36-44`）；
- `test_result_filter` 末尾新增了 `greatfilter`/`sadfilter` 一段（`:423-434`）。

| 键（expected） | noop / gold（两轮一致） | 性质 | 测什么 |
| --- | --- | --- | --- |
| `test_result_filter`（PASSED） | FAILED / PASSED | **目标键** | 见下 |
| `test_eval_results_plus_build_doc`（PASSED） | PASSED / PASSED | 活回归键 | 文档含 `result_filter`、`dictionary is passed` 等子串；`eval_results` 能确定所属类；返回条数；`getargspec` 签名 |
| `test_interface_prep`（PASSED） | PASSED / PASSED | 活回归键，与本题无关 | `Save._prep(path=[], dataset=None)` |
| `test_dirty`、`test_paths_by_dataset`、`test_save_hierarchy`、`test_get_dataset_directories`、`test_filter_unmodified`（FAILED） | FAILED / FAILED | **死键** | 测试体从不执行，见 §4(a) |

目标键 `test_result_filter`（`test_1.py:400-434`）逐段看：

- **`:402-422`**：无 filter 时得 `[0,1,2,3]`；`EnsureKeyChoice('somekey',(0,2))` 与等价 lambda 都得 `[0,2]`，末条是完整 dict。
  - 这几次调用都不带其它关键字参数。`eval_results` 先把 eval 参数 pop 掉（`W:datalad/interface/utils.py:979-983`），`generator_func(*_args, **_kwargs)`（`:986`）收到的 `_kwargs` 为 `{}`。
  - 所以不管 filter 收不收 kwargs，这几段结果都一样。它们是回归检查，与 base 公开测试相同。
- **`:426-429` `greatfilter(res, **kwargs)`**：在回调里执行 `assert_in('dataset', kwargs)`。外层调用 `Test_Utils().__call__(4, dataset='awesome', result_filter=greatfilter)` 只要求不抛异常，**不检查返回值**。
  - base 在 `utils.py:1030` 只执行 `result_filter(res)`；`AssertionError` 不是 `ValueError`，不会被 `:1032` 捕获；
  - 默认 list 模式下，异常在 `list(results)`（`:1070`）处抛出。
- **`:431-434` `sadfilter`**：在回调里执行 `assert_not_in('dataset', kwargs)`，调用时不带 dataset。
  - noop 下 kwargs 恒为 `{}`，这段必过；
  - 它只约束实现不要多传。
- **fixture 与 helper**：
  - `Test_Utils` 定义在本文件（`:327-352`），`__call__(number, dataset=None)` 产出 4 条含 `path`、`status`、`somekey` 的结果；
  - `assert_in`/`assert_not_in` 来自 base 版 `datalad.tests.utils`（`W:datalad/tests/utils.py:38-41` 转出 nose.tools）；
  - conftest 的 autouse fixture 只改 HOME、写 git 身份（`P:hidden_tests/conftest.py:12-21`），与目标无关。
- **公开依据**：`greatfilter` 与题面示例（`PUB:user_prompt.txt:12-17`）逐字对应；`sadfilter` 在题面里没有对应语句，见 §3、§8。

回归阅读范围：8 个测试体和 2 个 fixture 全部读过。受影响接口 `eval_results` 的其它调用者，在隐藏测试里都没有活的覆盖（§3）：Create 默认 filter、CLI、Dataset 方法绑定、`is_ok_dataset`。死键所测函数（如 `handle_dirty_dataset`）的实现没有读：这些测试不执行，也与本题无关。

## 3. 双向映射（第 3 步）

**公开要求 / 合理旧行为 → 断言：**

| # | 要求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 证据 / 下一步 |
| --- | --- | --- | --- | --- | --- |
| R1 | 带 `**kwargs` 的 filter 收到 API 调用的关键字参数（示例：`dataset`） | `PUB:user_prompt.txt:5-21` | `greatfilter`（`test_1.py:426-429`） | 覆盖，但**只用示例字面值**；断言在回调里，外层不看结果 | 〔史跑〕noop 失败信息与题面一致；D〔待跑〕 |
| R1' | 一般情形：不只 `dataset`（如以关键字给出的 `number`）；generator 模式；Dataset 方法调用 | 题面标题与描述是一般表述（"does not receive `kwargs`"、"additional keyword arguments from the API call"）；两种返回模式共用 `generator_func`（`W:.../utils.py:1063-1082`）；Dataset 方法把全部参数转成关键字（`W:datalad/distribution/dataset.py:441-451`） | 无 | **缺失** | R-c |
| R3 | 过滤语义：返回假值或抛 `ValueError` 才排除，其它异常照常抛出 | 文档只列这两种排除条件（`W:.../utils.py:864-867`）；代码只捕获 `ValueError`（`:1032`） | Constraint / lambda 两段只验证了排除；"其它异常抛出"没有断言。`greatfilter` 在 noop 下失败靠异常传播，但测试通过时没有任何外层断言 | 部分 | D〔待跑〕 |
| R4 | 调用带关键字参数时，Constraint 作 filter 仍可用 | Create 的类级默认 filter（`W:datalad/distribution/create.py:89-91`）；Dataset 方法把 `dataset` 作为关键字传入（`dataset.py:444`）；CLI（`W:datalad/interface/base.py:316-338`）；`Constraint.__call__(self, value)`（`W:datalad/support/constraints.py:54,290,420`） | 活键里没有。死键 `test_dirty` 等会调用 `ds.create()`，但不执行 | **缺失** | N〔待跑〕；R-c |
| R5 | 调用带关键字参数时，单参数函数 / lambda 作 filter 仍可用 | `W:datalad/interface/results.py:66-67`；公开测试 `W:datalad/interface/tests/test_save.py:119`、`test_clean.py:39-40`、`W:datalad/distribution/tests/test_get.py:244,405,409`、`test_uninstall.py:158` | 无 | **缺失** | N〔待跑〕；R-c |
| R6 | 公开 `test_result_filter` 的原有断言 | `W:datalad/interface/tests/test_utils.py:400-422` | `test_1.py:400-422` | 覆盖 | 〔史跑〕 |
| R7 | 生成的文档含指定子串 | `W:.../tests/test_utils.py:373-379` | `test_eval_results_plus_build_doc` | 覆盖。`dictionary is passed` 也出现在 `result_xfm` 文档（`W:.../utils.py:871`），改写 `result_filter` 文档不会误伤 | 〔史跑〕 |
| A2 | 没传 `dataset` 时，filter 看不到它 | 题面无。base 渲染器先例 `result_renderer(res, **_kwargs)`（`W:.../utils.py:1048,1050`）只传显式给出的关键字 | `sadfilter`（`test_1.py:431-434`）要求键不存在 | **可能误拒**：连默认值一起传入（`dataset=None`）的实现判 0 | C2〔待跑〕 |
| A3 | 值原样传递 | 题面无 | 无 | 未测 | — |

**关键断言 → 公开依据：**
- `greatfilter`：题面示例原样。
- `sadfilter`：题面没有直接依据。间接依据只有两条：渲染器先例，以及 Python 里 "kwargs" 的字面含义。上游后来又改成了相反的写法（§8）。
- Constraint / lambda 两段、`test_eval_results_plus_build_doc`、`test_interface_prep`：base 公开测试原样。
- 5 个死键：base 公开测试原样，但不执行。

**不同于 gold 的合理实现，与可能蒙混的实现**（全文见附录 A，预期得分见 §10）：
- 合理 C1：用 `inspect.signature` 判断 filter 是否有 VAR_KEYWORD 参数，有才传 `_kwargs`；拿不到签名时回退旧调用。
- 合理 C2：判断方式同 C1，但像上游后来那样传"全部参数"：位置参数映射成名字，并补上默认值。
- 蒙混 N：无条件执行 `result_filter(res, **_kwargs)`。另有一个变体：只给 Constraint 的 `__call__` 加 `**kwargs`、再无条件转发。它同样能过现有隐藏测试，但单参数 lambda 仍会 `TypeError`。
- 退化 D：`except ValueError` → `except Exception`。

## 4. R2E 专项

**(a) 非 PASSED 键的原因。**
- 机制：`P:hidden_tests/conftest.py:6-9` 的 `path` fixture 被 pytest 作为关键字参数注入（pytest 沿 `functools.wraps` 留下的 `__wrapped__` 读取签名）；装饰器又把临时路径作为位置参数追加（`W:datalad/tests/utils.py:429,564`）。结果是 `TypeError: test_dirty() got multiple values for argument 'path'`。
- 证据〔史跑〕：4 份 RH2 日志与 2 份 M3 日志一致，例如 noop 日志 `:24-91`、`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/datalad/16c1ffc349df/gold/a1/test_output.txt:19-77`。
- 影响：
  - 只改库代码的候选，包括更完整的修复，都翻转不了这些键；只有改 `datalad/tests/utils.py` 的装饰器才可能改变，而题面提示禁止改测试文件。
  - 它们是无效断言（T5），对判分无害；
  - 但它们让本应保护 `ds.create()` 等主路径的 5 个回归测试失效，这正是 N 能蒙混的原因。

**(b) 题面报错是否出现在 noop 目标键里。** 是。noop 日志 `:120-145`：`greatfilter` 在 `utils.py:1030 generator_func` 处报 `AssertionError: 'dataset' not found in {}`，与 `PUB:user_prompt.txt:24` 逐字一致。有一处小出入（P4，公开读者已指出，不影响理解）：题面示例写的是裸 `assert`，而报错文本是 `assert_in`（unittest `assertIn`）的格式。

**(c) 题面是否泄漏修法。** 不泄漏。
- 题面只有用法与期望，没有实现；标题和示例明确指向调用 filter 的位置。
- 示例几乎就是隐藏测试的 `greatfilter`。这是 R2E 题面生成方式带来的，与第 2 步的示例拟合问题相关，但不属于 P1。

**(d) 是否依赖 base 版测试辅助、搬迁伪影或撞键。**
- **依赖测试辅助。** `assert_in`、`assert_not_in`、`ok_`、`with_tempfile`、`with_tree` 都来自 `datalad.tests.utils`（`test_1.py:18-25`），评分时不重置。
  - 候选若把 `datalad/tests/utils.py` 的 `assert_in` 改成空函数，未修复的代码也能通过 `greatfilter`。
  - 这是通用的控制面改写通道（E3 / 清单 31），不是本题特有，交 A 线处理。
  - 本题的事后审计应标出改动了 `datalad/tests/` 的得 1 补丁。
- **搬迁伪影**：见 (a)。
- **跨文件撞键**：只有一个测试文件，没有。
- **模块名**：`eval_results` 按 `__qualname__` 找类（`W:.../utils.py:975-976`），模块名变成 `r2e_tests.test_1` 不受影响；日志里有 `Determined class ... r2e_tests.test_1.Test_Utils`。

**(e) 时间 / 随机 / 资源。**
- 活键都是确定性的纯 Python 调用。测试段耗时：RH2 1.00–1.38 s，M3 2.64–3.00 s。
- 协调者提到的 1200 s 评分时限来自控制面的 `chown -R`，属于 E3 链路问题，不是题目的时序问题。

**(f) 材料修订。** 无。

## 5. gold 检查与运行原件（第 5 步）

- **改动范围。** gold（`P:gold.patch`）只改 `datalad/interface/utils.py`：
  - Constraint 实例先取其 `__call__`；
  - 再用 `getfullargspec(...).varkw` 判断，只给带 `**kwargs` 的 filter 包一层，传入 `**_kwargs`；
  - 更新参数文档。
- **原例与旧用法。** 原例已修好（〔史跑〕gold 两轮 8/8）。Constraint 与单参数 filter 仍按旧方式调用〔读〕。
- **未测回归〔读，未实跑〕。** `getfullargspec` 对拿不到签名的可调用对象会抛 `TypeError('unsupported callable')`。因此 `result_filter=bool`、`operator.itemgetter('status')` 这类在 base 能用的 filter，在 gold 下会让整个命令报错。这是罕见路径，登记为 G1 → T3。C1 用 `try/except` 回退，没有这个问题。
- **范围。** 只有声明了 `**kwargs` 的 filter 才收到参数；写成 `def f(res, dataset=None)` 的收不到。这与上游后来的 `get_result_filter`（`58ba5165:datalad/interface/utils.py:233-240`）一致，题面示例也用 `**kwargs`。登记为 T3，不建议为此加断言。
- **无关改动。** 无。
- **运行原件。**
  - 4 份 current 日志都满足：`RH2_SETUP_APPLY_RC=0`、`RESTORED=3`、`TEST_FILES=4`、`collected 8 items`、pytest 7.4.4、Python 3.7.9。
  - gold 日志里 `utils.py` 的行号整体后移：debug 行 977→980（gold 日志 `:99`），filter 行 1031→1046（`:113`）。这说明评分加载的是候选改过的文件〔史跑〕。
  - noop 的 0 来自目标键的 `AssertionError`，不是补丁应用失败或解析到零个键。

## 6. 开发需求（第 6 步）

| 项 | 需求 | 依据 | 状态 |
| --- | --- | --- | --- |
| 导入 | `python` 指向 `/testbed/.venv/bin/python`（3.7.9）；`import datalad` 会调用 git | `PUB:environment_brief.md:10`；公开读者 §4 | 解释器：镜像层面实测。actor 侧导入：待验（devcheck `env_imports`） |
| 依赖 | 目标调用链：`wrapt`、`six`、标准库 `inspect`；复现还需 `nose`、`mock` | 评分日志 | 评分侧实测；解题与评分同镜像，actor 待验 |
| 资产 / 构建 | 无，纯 Python | — | 不适用 |
| 网络 | 准备、解题、安装、测试四个阶段都不需要 | `PUB:environment_brief.md:11` | 不适用 |
| 权限 | agent（uid 54321）可写 `/testbed`；最小核对不需要 git 身份 | `PUB:environment_brief.md:12-13` | 镜像层面实测 |
| 最小验证 | 公开读者的 5 条命令足够：复现、兼容性、kwargs 探针、窄公开测试。装饰器测试在 pytest 下会 ERROR（§1） | `commands.json` | actor 待验；墙钟时间待 devcheck |
| 提交边界 | `datalad/interface/utils.py`；替代解也可能改 `datalad/support/constraints.py`。都是普通文件，按字节差异导出 | 环境卡 §6 | 不涉及构建产物 |
| 评分侧 | 本机需要 1200 s 评分时限（`chown -R`，E3） | 协调者说明 | 链路问题，单独记账 |

## 7. 八方面覆盖与未查项

| 方面 | 已查 | 未查 / 缺口 |
| --- | --- | --- |
| 公开需求 | 题面、提示、`eval_results` 与各调用者；公开读者的 R1–R9、A1–A3 | 模型实际收到的消息 |
| 材料与初始问题 | 公开工作树即 base（`initial_diff` 0 字节）；gold 可应用；noop 失败位置与题面一致；隐藏测试树 sha 与账本一致 | — |
| 测试是否测到要求 | 8 个键全读：示例拟合、断言在回调内、缺回归覆盖 | — |
| 是否误拒合理解 | `sadfilter` 的"键不存在"约束 | C2 实跑 |
| 回归与 gold 完整性 | Create 默认 filter、CLI、Dataset 方法、`is_ok_dataset`、公开测试里的 lambda 用法；gold 对内建可调用对象的回归 | gold 回归只有静态推断 |
| 开发条件 | 环境说明、评分日志、公开读者命令 | devcheck 结果（协调者第二步给出） |
| 交付与评分边界 | 单文件交付；评分只替换 `r2e_tests/`；测试辅助可被候选改写（E3） | 通用控制面问题交 A 线 |
| 题目关系 | 两份扫描，加手工核对同仓 4 题公开包 | 同仓其它题私有包按规定不读 |

## 8. v1 §4 严重度判定（初判）

**核心要求**：带 `**kwargs` 的 `result_filter` 收到 API 调用的关键字参数。依据是题面标题与期望行为，按一般表述理解，不限于 `dataset`。

1. **核心要求有没有直接断言？** 有（`greatfilter`），不命中。
2. **核心断言是否只用示例字面值？** 是 → **S1（T2c）**〔读〕。
   - 同一命令、同一 `number=4`、同一 `dataset='awesome'`、同一检查 `'dataset' in kwargs`。
   - `sadfilter` 是反方向的约束，noop 必过，不算核心要求的非示例实例。
   - 例：只转发 `dataset` 的实现也能过，但它违反"收到调用的 kwargs"，例如以关键字给出的 `number` 就收不到。
3. **退化探测：** D 预计得 1 → **S1（T2b）**〔待跑〕。D 违反的公开要求：
   - 题面期望行为是"filter 应收到 `dataset`"。D 下 filter 从未收到，它的 `AssertionError` 被吞掉，4 条结果被静默丢弃：题面原例会返回 `[]`，而不是 4 条。
   - base 文档规定只有"返回假值或抛 `ValueError`"才排除结果（`W:.../utils.py:864-867`），D 把任意异常都变成了静默排除。
4. **已有候选：** N 预计得 1〔待跑〕，但破坏了有文档、常用的公开行为 → **S1**（T2，第 4 步）。
   - `ds.create()` 走 Create 的类级默认 Constraint filter，会 `TypeError`；
   - 公开用法 `clean(dataset=ds, result_filter=lambda ...)`、`ds.save(result_filter=is_ok_dataset)` 同样 `TypeError`。
5. 不适用（已判 S1）。

结论：S1。第 2 步已由阅读确定；第 3、4 步各待 1 次正式评分。

**另：`sadfilter` 与合理解 C2 冲突，记 T1（误拒；由 P3 引出），单列 conditional。** 它不属于 §4 那类"错误解得分"的严重度。依据：
- 题面没有规定：没传的参数，是否出现在 kwargs 里。
- base 的渲染器先例支持"不出现"（`W:.../utils.py:1048,1050`）。
- 上游后来改成连默认值也传入：
  - 实现：`58ba5165:datalad/interface/utils.py:372-379,391,469,475` 用 `get_allargs_as_kwargs`（`58ba5165:datalad/interface/base.py:608-634`），注释写明 "all args incl. defaults"；
  - 测试：`58ba5165:datalad/interface/tests/test_utils.py:330-338` 改成 `assert_equal(kwargs.get('dataset', 'bob'), None)`。在那一版测试下，本题 gold 式的实现反而会失败。
- 两版上游测试互相排斥，说明两种读法都是合理设计。

我倾向把它看作接口细节，而不是 P5 的任务目标分歧：两种读法都完成了任务目标，差别只在"没给参数"怎么表示。复核若认定为 P5，就按 v1 交用户决定。

## 9. 题目关系（X1）

**机械扫描。** `runs/r2e_static_prep_20260924/cross_task_gold_scan.json` 与 `cross_task_test_scan.json` 都没有本题条目，对本题是结构性漏报：
- gold 扫描做的是逐字比对，而上游后来重构了这段代码；
- 测试扫描只看"本题公开工作树里没有的测试函数名"，而本题隐藏测试没有新增函数，只在 `test_result_filter` 里加了一段。

**手工核对同仓公开包：**
- **`58ba5165`（0.17.9，2022）与 `19f5b450`（1.1.3，2024）**：初态含本题修复的重构版，语义已改为传入默认值（§8）。
  - 修复：`get_result_filter`（`58ba5165:datalad/interface/utils.py:233-240`；`19f5b450:datalad/interface/utils.py:210-217`，调用处 `19f5b450:datalad/interface/base.py:824`）；
  - 测试：更新后的 `greatfilter`/`sadfilter`（`58ba5165:datalad/interface/tests/test_utils.py:330-338`；`19f5b450:datalad/interface/tests/test_utils.py:332-340`）。
- **`9ba5de09`（0.4.1.dev1，2016）**：修的是 `eval_results` 返回 `FunctionWrapper`，它的初态只有原型 `eval_results(switch)`（`9ba5de09:datalad/interface/utils.py:769-787`）。本题初态的完整 `eval_results` 已包含那一修复。这是反向包含，涉及同一函数，也用同样的 `fake_command` 测试写法。
- **`6b6fa389`（0.2.dev1）**：修 SSH URL 解析，与本题无关。

**处置。** 登记 X1。训练时控制同族题的重复采样。按 D3 的仓库划分，datalad 各题都在同一侧，不会跨训练集与留出集泄漏。

## 10. 候选与需要协调者实跑的内容

候选补丁全文见附录 A。它们都对 base 的 `datalad/interface/utils.py`（blob `7c35619`，与 gold 的 index 前缀一致）通过了 `git apply --check`，改后的文件通过了 `py_compile`。

| 候选 | 改法（`datalad/interface/utils.py`，`eval_results` 内的 `generator_func`） | 语义判断 | 预期得分（现材料） | 预期不符的键 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| D（退化，第 3 步） | filter 调用处 `except ValueError as e:` → `except Exception as e:` | 错：违反题面期望行为与文档里的过滤语义（§8 第 3 步） | 1 | 无（8/8） | 必跑 |
| N（蒙混，第 4 步） | `if not result_filter(res):` → `if not result_filter(res, **_kwargs):` | 错：调用带关键字参数时，Constraint 与单参数 filter 会 `TypeError`（如 `ds.create()`） | 1 | 无（8/8） | 必跑 |
| C2（合理替代，读法 ii） | 签名有 VAR_KEYWORD 的 filter 收到"全部参数"：位置参数映射成名字、补默认值，再并入 `_kwargs`；其它 filter 仍只收 `res` | 满足题面与 R4/R5；与上游后来的语义一致 | 0 | `test_result_filter`：`sadfilter` 收到 `{'number': 4, 'dataset': None}`，`assert_not_in` 失败 | 高 |
| C1（合理替代，读法 i） | 判断方式同 C2，但只传 `_kwargs`；拿不到签名时回退 | 满足全部公开要求；遇到内建可调用对象比 gold 稳 | 1 | 无 | 低（非 gold 的正对照；R-c 验收也要用） |

**请协调者实跑：**
1. **正式评分**（本机 1200 s 时限，单独记账），依次跑 D、N、C2、C1。每次核对三点：`RH2_SETUP_APPLY_RC=0`；`collected 8 items` 且目标键确实执行；`utils.py` 行号随补丁变化，即候选确已加载。
2. **可选的行为对照**（公开命令，解题身份即可）。源码推导已足以说明违例，这一步不影响判定：
   - N 应用后跑公开读者的 `filters_backcompat`：预期 `TypeError ... unexpected keyword argument 'dataset'`，非零退出；
   - D 应用后跑 `repro_issue_example`：预期打印 `RESULT []` 并以 0 退出，而正确修复会打印 4 条；
   - C2 应用后跑 `filter_kwargs_probe`：预期 `no_dataset` 一行含 `dataset`。
3. **devcheck**（协调者第二步给出）需要回答：
   - `env_imports` 里 nose、mock、pytest 的版本，以及 git-annex 是否在 PATH；
   - `repro_issue_example` 在 base 上是否以非零退出、报 `AssertionError`；
   - `public_tests_narrow` 是否 18 passed；
   - 各条命令的墙钟时间。

## 11. 修订建议（v1 §5）

### R-c：针对第 2、3、4 步的 S1，一轮完成

改动：在 `P:hidden_tests/test_1.py` 末尾新增两个测试（附录 B 的 `rev_rc.patch`），并在 `P:expected_output.json` 加两个 PASSED 键（`rev_expected.patch`）。两个测试都只用现有的 `Test_Utils` 和 `Dataset('/does/not/matter')`，不需要 git-annex。

**`test_result_filter_gets_call_kwargs`（新目标键）**
- 做法：一个带 `**kwargs` 的 filter 记录每次收到的参数，并按 `somekey in (1, 3)` 决定去留。三种调用下都断言：结果为 `[1, 3]`；每次记录的参数里 `number == 4`，`dataset` 等于调用时给出的值。
  - 显式关键字，list 模式；
  - 显式关键字，generator 模式；
  - Dataset 方法 `ds.fake_command(4, ...)`，此时要求 `dataset is ds`。
- 公开依据：
  - 题面标题与描述的一般表述；
  - 两种返回模式共用 `generator_func`（`W:.../utils.py:1063-1082`）；
  - Dataset 方法把所有参数都转成关键字（`W:.../dataset.py:441-451`）。
- 刻意不断言的内容：调用次数，以及 kwargs 之外的任何东西，以免约束实现方式。

**`test_result_filter_plain_callables_with_call_kwargs`（新回归键）**
- 做法：`EnsureKeyChoice`、`&` 组合、单参数 lambda 三种 filter，分别在"直接调用并传 `dataset='awesome'`"和"Dataset 方法调用"两种情况下都得 `[0, 2]`。
- 公开依据：`W:datalad/distribution/create.py:89-91`、`W:datalad/interface/base.py:325-338`、`W:datalad/interface/results.py:66-67`，以及公开测试 `test_clean.py:39-40`、`test_save.py:119`。
- 它也能挡住 N 的变体：只给 Constraint 加 `**kwargs`、再无条件转发。

**修订后仍受保护的公开要求：** R1、R1'、R3（filter 的去留决定是否被遵守）、R4、R5、R6、R7。

**预期结果**（静态推断，待验收实跑）：

| 候选 | `test_result_filter` | `..._gets_call_kwargs` | `..._plain_callables_with_call_kwargs` | 得分 |
| --- | --- | --- | --- | --- |
| noop | FAILED | FAILED | PASSED | 0 |
| gold | PASSED | PASSED | PASSED | 1 |
| D | PASSED | FAILED（`number` 缺失） | PASSED | 0 |
| N | PASSED | PASSED | FAILED（`TypeError`） | 0 |
| C1 | PASSED | PASSED | PASSED | 1 |
| C2（不带 R-b） | FAILED | PASSED | PASSED | 0 |

### R-b：针对 T1，conditional

- **改动**：把 `sadfilter` 里的 `assert_not_in('dataset', kwargs)` 改成 `assert_equal(kwargs.get('dataset'), None)`（附录 B 的 `rev_rb.patch`）。意思是只要求"没给 dataset 时，filter 不会拿到一个非空的 dataset"。
- **触发条件**：C2 实跑确实为 0，且复核同意 C2 满足全部公开要求。
- **不能单独上。** 单独放宽后，"对所有 `**kwargs` filter 固定传 `{'dataset': None}`"这种与输入无关的退化实现就能通过 `test_result_filter`，因为 `greatfilter` 只查键在不在。R-c 新测试里的取值断言能挡住它。
- **与 R-c 同批时**：预期 C2 = 1，其余候选同上表。
- **撤回条件**：复核若认定这是 P5，就撤回 R-b，交用户决定。

### R-a：可选，不必做

5 个死键已确认是无效断言（测试体从不执行），但对判分无害。如果在同一轮修订里顺手清理，必须同时删掉测试和对应的 expected 键。不清理也不影响结论：它们本该提供的回归覆盖，改由 R-c 的第二个测试承担，而且不依赖 git-annex。

### 验收计划（v1 §5）

- 正对照：gold = 1；C1 = 1，作为独立替代解。
- noop = 0。
- 已知错误候选 D、N 都为 0。
- C2：带 R-b 时为 1，不带时为 0。
- 保存新旧版本、理由和触发反例（D、N、C2），交 Codex 复核。

## 12. 问题登记（v1 编号）

| 编号 | 问题 | 证据层次 | 去向 |
| --- | --- | --- | --- |
| T2（第 2 步，T2c） | 核心断言只用题面示例的字面值 | 〔读〕，已确定 | R-c |
| T2（第 3 步，T2b） | 断言在回调里、外层不看结果；吞掉错误的 D 预计得 1 | 〔读〕；D〔待跑〕 | R-c |
| T2（第 4 步） | 没有回归断言保护"调用带 kwargs 时，Constraint 与单参数 filter 仍可用"；N 预计得 1 | 〔读〕；N〔待跑〕 | R-c |
| T1（由 P3 引出） | `sadfilter` 要求没传的参数不出现在 kwargs 里，拒绝上游后来的读法 C2 | 〔读〕+ 同仓公开包；C2〔待跑〕 | R-b（与 R-c 同批），或交用户 |
| T5 | 5 个期望 FAILED 的死键（fixture 与装饰器冲突） | 〔史跑〕RH2 4 份、M3 2 份 | 登记；可选 R-a |
| G1 → T3 | gold 遇到无签名的可调用对象（`bool`、`itemgetter`）会报错；只给声明了 `**kwargs` 的 filter 传参 | 〔读〕 | 登记 |
| T3 | 按位置传 `dataset`（A2）、值是否转换（A3）都未测 | 〔读〕 | 登记 |
| P4 | 报错文本是 `assert_in` 的格式，示例却写裸 `assert`；题面没说 `Test_Utils` 定义在哪 | 〔读〕 | 登记；公开材料能消解 |
| E3 | 本机评分需 1200 s（`chown -R`）；隐藏测试用的断言函数来自可被候选改写的 `datalad/tests/utils.py` | 协调者说明；〔读〕 | 交 A 线；本题事后审计标出改动 `datalad/tests/`、`.venv` 的得 1 补丁 |
| X1 | 与 `58ba5165`、`19f5b450` 相关（两者初态含本题修复的重构版）；与 `9ba5de09` 相关（本题初态含其修复）；两份扫描结构性漏报 | 〔读〕公开包 | 登记 |

没有发现 P1、P2、P5（见 §8 的说明）、P6、D1、E1、E2、E4、E5、X2。

## 13. 暂定处置与用途（读历史前）

- `disposition`：`needs_repair`（测试层 R-c；R-b 待定），`scope=static_review`。
- `usage.v1`：
  - `problem_localization`：yes。
  - `capability_comparison`：conditional。还差：
    - devcheck 确认解题侧开发路径可用；
    - 把 1200 s 评分时限写进有效运行条件；
    - 预登记事后审计：得 1 的补丁要检查是否属于 N 型（无条件传 kwargs）、D 型（吞掉 filter 异常），或改动了测试辅助；
    - `sadfilter` 争议单列：只因 C2 型读法而失败的尝试记为争议，原始 reward 保留。
  - `training_candidate`：no。现版本有未处理的 S1；R-c（与可能的 R-b）验收后重评。
  - `heldout_candidate`：no。

## 14. 缺口、未知与唯一下一步

- **未知**：
  - D、N、C2、C1 的正式评分结果；
  - devcheck：actor 侧导入、原例复现、窄公开测试、墙钟时间、git-annex 是否存在；
  - `sadfilter` 争议的复核结论。
- **只有静态推断**：gold 对内建可调用对象的回归。
- **唯一最值得先做**：按正式评分（1200 s 时限）同批实跑 D 与 N，它们决定 S1 的执行证据；随后跑 C2，决定是否上 R-b。

## 附录 A：候选补丁（在 base 工作树根目录 `git apply`）

### A.1 D（退化候选，第 3 步）— `cand_D.patch`

```diff
diff --git a/datalad/interface/utils.py b/datalad/interface/utils.py
index 7c35619..83a7ad7 100644
--- a/datalad/interface/utils.py
+++ b/datalad/interface/utils.py
@@ -1029,7 +1029,7 @@ def eval_results(func):
                     try:
                         if not result_filter(res):
                             raise ValueError('excluded by filter')
-                    except ValueError as e:
+                    except Exception as e:
                         lgr.debug('not reporting result (%s)', exc_str(e))
                         continue
                 ## output rendering
```

### A.2 N（蒙混候选，第 4 步）— `cand_N.patch`

```diff
diff --git a/datalad/interface/utils.py b/datalad/interface/utils.py
index 7c35619..1ade648 100644
--- a/datalad/interface/utils.py
+++ b/datalad/interface/utils.py
@@ -1027,7 +1027,7 @@ def eval_results(func):
                         break
                 if result_filter:
                     try:
-                        if not result_filter(res):
+                        if not result_filter(res, **_kwargs):
                             raise ValueError('excluded by filter')
                     except ValueError as e:
                         lgr.debug('not reporting result (%s)', exc_str(e))
```

### A.3 C1（合理替代，读法 i）— `cand_C1.patch`

```diff
diff --git a/datalad/interface/utils.py b/datalad/interface/utils.py
index 7c35619..49cc4b8 100644
--- a/datalad/interface/utils.py
+++ b/datalad/interface/utils.py
@@ -991,6 +991,22 @@ def eval_results(func):
             incomplete_results = []
             # inspect and render
             result_filter = common_params['result_filter']
+            # filters that accept **kwargs additionally get the keyword
+            # arguments of the API call; all other filters (Constraints,
+            # plain one-argument callables) keep being called with the
+            # result only
+            _result_filter = result_filter
+            if result_filter:
+                try:
+                    _filter_takes_kwargs = any(
+                        p.kind == inspect.Parameter.VAR_KEYWORD
+                        for p in inspect.signature(result_filter).parameters.values())
+                except (TypeError, ValueError):
+                    # no introspectable signature (e.g. some builtins)
+                    _filter_takes_kwargs = False
+                if _filter_takes_kwargs:
+                    def _result_filter(res):
+                        return result_filter(res, **_kwargs)
             result_renderer = common_params['result_renderer']
             result_xfm = common_params['result_xfm']
             if result_xfm in known_result_xfms:
@@ -1025,9 +1041,9 @@ def eval_results(func):
                         # first fail -> that's it
                         # raise will happen after the loop
                         break
-                if result_filter:
+                if _result_filter:
                     try:
-                        if not result_filter(res):
+                        if not _result_filter(res):
                             raise ValueError('excluded by filter')
                     except ValueError as e:
                         lgr.debug('not reporting result (%s)', exc_str(e))
```

### A.4 C2（合理替代，读法 ii，仿上游后来的 `get_allargs_as_kwargs`）— `cand_C2.patch`

```diff
diff --git a/datalad/interface/utils.py b/datalad/interface/utils.py
index 7c35619..42e5f48 100644
--- a/datalad/interface/utils.py
+++ b/datalad/interface/utils.py
@@ -991,6 +991,29 @@ def eval_results(func):
             incomplete_results = []
             # inspect and render
             result_filter = common_params['result_filter']
+            # filters that accept **kwargs additionally get all arguments of
+            # the API call (positional ones mapped to their names, defaults
+            # filled in); all other filters (Constraints, plain one-argument
+            # callables) keep being called with the result only
+            _result_filter = result_filter
+            if result_filter:
+                try:
+                    _filter_takes_kwargs = any(
+                        p.kind == inspect.Parameter.VAR_KEYWORD
+                        for p in inspect.signature(result_filter).parameters.values())
+                except (TypeError, ValueError):
+                    # no introspectable signature (e.g. some builtins)
+                    _filter_takes_kwargs = False
+                if _filter_takes_kwargs:
+                    _spec = inspect.getfullargspec(wrapped)
+                    _defaults = _spec.defaults or ()
+                    _call_kwargs = dict(zip(_spec.args, _args))
+                    for _k, _v in zip(_spec.args[-len(_defaults):], _defaults):
+                        _call_kwargs.setdefault(_k, _v)
+                    _call_kwargs.update(_kwargs)
+
+                    def _result_filter(res):
+                        return result_filter(res, **_call_kwargs)
             result_renderer = common_params['result_renderer']
             result_xfm = common_params['result_xfm']
             if result_xfm in known_result_xfms:
@@ -1025,9 +1048,9 @@ def eval_results(func):
                         # first fail -> that's it
                         # raise will happen after the loop
                         break
-                if result_filter:
+                if _result_filter:
                     try:
-                        if not result_filter(res):
+                        if not _result_filter(res):
                             raise ValueError('excluded by filter')
                     except ValueError as e:
                         lgr.debug('not reporting result (%s)', exc_str(e))
```

## 附录 B：修订补丁（路径相对 `PRIVATE_DIR`，即材料树根）

`rev_rc.patch` 与 `rev_rb.patch` 可以各自单独应用，也可以按任意顺序先后应用（已用 `git apply --check` 核过四种组合）。修订后的 `test_1.py` 通过了 `py_compile`。

### B.1 R-c 新增测试 — `rev_rc.patch`

```diff
diff --git a/hidden_tests/test_1.py b/hidden_tests/test_1.py
index b961d0d..70dc79e 100644
--- a/hidden_tests/test_1.py
+++ b/hidden_tests/test_1.py
@@ -433,2 +433,56 @@ def test_result_filter():
         return True
     Test_Utils().__call__(4, result_filter=sadfilter)
+
+
+def test_result_filter_gets_call_kwargs():
+    # a filter that accepts **kwargs gets the keyword arguments of the API
+    # call -- not only `dataset` -- also in generator mode and when the
+    # command is called as a Dataset method (all arguments become keyword
+    # arguments); the filter's decision is honored
+    seen = []
+
+    def kwfilter(res, **kwargs):
+        seen.append(kwargs)
+        return res['somekey'] in (1, 3)
+
+    for rtype in ('list', 'generator'):
+        del seen[:]
+        assert_equal(
+            [r['somekey'] for r in Test_Utils().__call__(
+                number=4, dataset='awesome', return_type=rtype,
+                result_filter=kwfilter)],
+            [1, 3])
+        ok_(seen)
+        for kw in seen:
+            assert_equal(kw.get('number'), 4)
+            assert_equal(kw.get('dataset'), 'awesome')
+
+    del seen[:]
+    ds = Dataset('/does/not/matter')
+    assert_equal(
+        [r['somekey'] for r in ds.fake_command(4, result_filter=kwfilter)],
+        [1, 3])
+    ok_(seen)
+    for kw in seen:
+        assert_equal(kw.get('number'), 4)
+        ok_(kw.get('dataset') is ds)
+
+
+def test_result_filter_plain_callables_with_call_kwargs():
+    # filters that do not accept **kwargs -- Constraints (as used for the
+    # class-level default filter of `create` and for the --report-status /
+    # --report-type command line options) and plain one-argument callables
+    # (e.g. datalad.interface.results.is_ok_dataset) -- keep working when
+    # the API call has keyword arguments
+    ds = Dataset('/does/not/matter')
+    for filt in (
+            EnsureKeyChoice('somekey', (0, 2)),
+            EnsureKeyChoice('status', ('ok',)) & EnsureKeyChoice('somekey', (0, 2)),
+            lambda x: x['somekey'] in (0, 2)):
+        assert_equal(
+            [r['somekey'] for r in Test_Utils().__call__(
+                4, dataset='awesome', result_filter=filt)],
+            [0, 2])
+        assert_equal(
+            [r['somekey'] for r in ds.fake_command(4, result_filter=filt)],
+            [0, 2])
```

### B.2 R-b 放宽 `sadfilter`（只与 B.1 同批）— `rev_rb.patch`

```diff
diff --git a/hidden_tests/test_1.py b/hidden_tests/test_1.py
index b961d0d..a7f5afc 100644
--- a/hidden_tests/test_1.py
+++ b/hidden_tests/test_1.py
@@ -431,3 +431,5 @@ def test_result_filter():
     def sadfilter(res, **kwargs):
-        assert_not_in('dataset', kwargs)
+        # no dataset was given in the call: the filter must not be handed
+        # one (the argument may be absent or None)
+        assert_equal(kwargs.get('dataset'), None)
         return True
```

### B.3 expected 增键（随 B.1）— `rev_expected.patch`

```diff
diff --git a/expected_output.json b/expected_output.json
index 325e99f..107caf0 100644
--- a/expected_output.json
+++ b/expected_output.json
@@ -6,5 +6,7 @@
     "test_paths_by_dataset": "FAILED",
     "test_save_hierarchy": "FAILED",
     "test_get_dataset_directories": "FAILED",
-    "test_filter_unmodified": "FAILED"
+    "test_filter_unmodified": "FAILED",
+    "test_result_filter_gets_call_kwargs": "PASSED",
+    "test_result_filter_plain_callables_with_call_kwargs": "PASSED"
 }
\ No newline at end of file
```

## 附录 C：原始证据索引

- **noop（09-23 R-f 全池）**：`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-d_ff9ede96.eval.log`，账本 `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl` 第 11 行。
  - `:5-12`：setup，`APPLY_RC=0`，`INSTALL_SKIPPED=1`；
  - `:16-19`：pytest 7.4.4，collected 8；
  - `:24-91`：5 个死键的 `TypeError`；
  - `:120-145`：`greatfilter` 的 `AssertionError: 'dataset' not found in {}`，调用栈经 `utils.py:1082 → 1070 → 1030`；
  - `:188-197`：摘要，6 failed、2 passed。
- **gold（09-23）**：`.../evallog_replay-r2e-rf-all-gold-d_dff48178.eval.log`，账本第 11 行。
  - `:1`：` M datalad/interface/utils.py`；
  - `:99`：`utils.py:980`；
  - `:113`：`generator_func:1046`；
  - `:136-145`：5 failed、3 passed。
- **09-24 环境轮复跑**：`runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_dcc2c830.eval.log`（noop）与 `..._a280b0c2.eval.log`（gold）。与 09-23 两份逐行对比，只有临时路径、时间戳和耗时不同。
- **M3 独立 runner（来源镜像）**：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 3、51 行，gold 两次都通过。`logs_r2e/datalad/16c1ffc349df/gold/a1/test_output.txt:19-77,122-130` 显示同样的 5 个死键。
