# orange3 公开需求独立阅读

整理日期：2026-09-29。结论：**公开题面足以推导一般输入的正确结果，核心需求自洽；公开源码及已有测试支持这一理解。题面没有给出修复算法或补丁。** 现有公开 helper 测试有覆盖盲点，单独通过它不足以证明修复完成。本报告仅作静态阅读，不是容器验收、实际消息核对或运行通过证明。

## 阅读边界与输入身份

只访问指定公开包 `runs/category2_repair_20260929/r2e/orange3_22e98_public_v1/`，另读获准的角色说明 `r2e/orange3_22e98_public_reader_prompt.md:1–7`。未读取其它题卡、历史审查、修订草案、gold、hidden tests 或其它运行记录；未联网、SSH、启动容器、执行项目代码或修改输入。

包的 `manifest.json` SHA256 为 `fcbeb310d0ba3f7ef683404ad5ee43681720ed9009ecc7af9192d79995ed630e`，与委托值一致。报告末尾列出的 13 个包内内容文件均通过该 manifest 的逐文件 SHA256 核对；没有声称逐项核验全包。题面正文摘要为 `f8701d3a4322270fde2618cc7cfc094460c9a5f1ec874e400c5bfaeef9ec7199`（公开元数据值），与带外壳的 `user_prompt.txt` 文件摘要不是同一个概念。

边界披露：`worktree_manifest.json:31–34` 自带 `run_tests.sh` 来自 `grading_bundle` 的来源文字。我看到了这段公开元数据，未打开该脚本，也未接触其评分内容或包外来源。没有误读私有材料。

## 公开任务要求什么

修复 `Orange.widgets.data.owcreateclass.unique_in_order_mapping` 的映射。对于通常的一维、元素可比较的输入序列 `a`，返回 `U, M`：

- `U` 每种值只保留一次，排列顺序取决于该值在 `a` 中第一次出现的位置。
- `M` 与 `a` 等长；每个 `M[i]` 是 `a[i]` 在 `U` 中的零起始索引。因此每个有效位置都必须满足 `U[M[i]] == a[i]`，重复值必须使用同一个索引。
- 输入全不相同时，`U` 保持原顺序，`M` 就是从零开始的连续索引。不能只处理题面给出的那组数值。

这些关系来自 `user_prompt.txt:8–21`，并得到函数自身说明 `owcreateclass.py:150–154` 的支持。

以下是我独立构造的例子；方括号只表达序列内容，并不要求把既有 NumPy 返回值改成 Python `list`。

| 输入 `a` | 唯一值 `U` | 映射 `M` |
| --- | --- | --- |
| `[8, 4, 6, 8, 4]` | `[8, 4, 6]` | `[0, 1, 2, 0, 1]` |
| `["zebra", "apple", "zebra", "mint", "apple"]` | `["zebra", "apple", "mint"]` | `[0, 1, 0, 2, 1]` |
| `[7, 7, 7]` | `[7]` | `[0, 0, 0]` |
| `[]` | `[]` | `[]` |

首例中，位置 3 的值是 `8`，而 `8` 是 `U` 的第 0 项，所以 `M[3]` 必须为 0。源码调用处用字符串类别名作为输入，故字符串例子也有直接使用场景（`owcreateclass.py:531–550`）；空输入和重复值由公开测试明确支持（`test_owcreateclass.py:75–91`）。

## 明确要求与未规定内容

**明确：** 保留首次出现顺序、去重、原序列逐位置映射到返回唯一值序列、零起始索引、重复值共用索引。公开开发提示另规定只改非测试源码、不要改仓库测试、在 `/testbed` 使用 `python -m pytest` 做窄范围验证（`public_task.json:12`）。这些是开发约束，不是我本次只读任务的执行授权。

**应保持兼容，但题面没有另行规定：** 源码返回 NumPy 数组，题面实际输出也写成 `array(...)`。因此“list of unique elements”合理理解为有序集合内容，不能据此要求更换返回容器。现有调用处还会把两项转换成 tuple（`owcreateclass.py:538–539`）。

**未规定：** 多维输入的轴或展平方式、生成器、自定义对象、异质且不可比较的元素、`NaN` 的相等规则、具体数组 dtype、异常类型、输入原地修改要求、复杂度或性能目标。无需为这些未规定边界扩写需求。该缺省不妨碍普通数字及字符串序列的修复。

题面给出的预期值是外部可观察行为，不是实现答案。它没有指定 NumPy 操作组合、内部变量修改、源代码行替换或补丁。题面描述、示例预期和现有函数说明相互一致；没有发现妨碍开发的核心矛盾。

## 源码与公开测试提供的证据

`owcreateclass.py:155–158` 用 `np.unique` 得到唯一值、首次位置和逆映射，然后重排唯一值及映射。对我构造的首例进行纸面代入，当前公式给出的映射内容为 `[1, 2, 0, 1, 2]`，无法满足 `U[M[i]] == a[i]`。这独立支持“唯一值顺序可正确而映射错误”的问题描述；这是静态推演，未运行复现。

`_create_variable` 用该 helper 合并同名类别，再将映射传给转换器（`owcreateclass.py:523–550`）；`map_by_substring` 按规则位置读取映射值（同文件 `:21–50`）。这说明映射必须与原规则位置对应，否则会输出错误类别索引。

公开 helper 测试检查空输入、单元素、全重复值，以及两种非平凡排列（`test_owcreateclass.py:75–91`）。它们支持上述契约，但这两种排列的重排恰好与其逆置换相同，当前公式在这些例子上也可成立。题面三元素排列和我构造的首例不具备这一性质。因此，应加入临时断言覆盖这类重排及重复值，而不能把“旧 helper 测试通过”当作充分证据。这里不建议修改仓库测试文件，也没有提供修复代码。

## 最小公开开发验证路径与条件

以下仅是对获准开发者的建议命令，**本次均未执行**。实际环境须先确认工作目录确为 `/testbed`，`python` 指向任务虚拟环境，pytest、NumPy、Orange 及其已编译组件、AnyQt/Qt 与 widget 依赖可导入，且 Qt 无显示器运行条件成立。即使只调用 helper，也会导入 widget 模块及测试基础设施，不能当成只有 NumPy 的独立文件（`owcreateclass.py:5–18`；`test_owcreateclass.py:8–13`；`Orange/widgets/tests/base.py:10–40`）。

在确认这些条件后，从 `/testbed` 运行：

```bash
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q Orange/widgets/data/tests/test_owcreateclass.py::TestHelpers::test_unique_in_order_mapping
```

随后在同样 Qt 启动条件下，通过一次性 Python 调用断言本报告的数字重复例和字符串例，并检查 `U[M]` 能逐项还原输入；无需落盘修改测试。helper 通过后，运行同一个公开测试文件作为调用处的窄范围回归：

```bash
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q Orange/widgets/data/tests/test_owcreateclass.py
```

`environment_brief.md:9` 只记录历史 Python 3.7.9、任务虚拟环境、2 CPU/4 GiB、离线及上述 Qt 启动前缀；它没有证明当前容器具备这些条件。`public_task.json:12` 中关于已激活环境、pip 的文字同样只是静态来源提示。公开工作树缺少 `.venv`、编译产物、`datasets` 与 `install.sh`（`worktree_manifest.json:26–41`），所以不能把本包直接视为可运行环境。若依赖缺失，须先报告环境缺口；不应依据通用开发文档临时联网安装或把导入失败记作功能失败。

## 已读文件与行号

以下路径均相对公开包；`worktree/` 下的行号以复制文件为准。目录清单与 `rg unique_in_order_mapping` 检索也严格限制在本包。初始长输出有截断，下面将重点证据与扫描范围分开说明。

| 文件 | 阅读范围／用途 |
| --- | --- |
| `user_prompt.txt` | 1–30，全题面 |
| `environment_brief.md` | 1–11，材料性质与历史环境 |
| `public_task.json` | 1–16，公开字段及开发提示 |
| `manifest.json` | 文件清单扫描（长输出截断），重点 1–9；摘要核对 |
| `worktree_manifest.json` | 1–100 扫描，重点复读 1–45，快照与缺失项 |
| `worktree/Orange/widgets/data/owcreateclass.py` | 1–250 初读；重点复读 1–75、145–158、500–570 |
| `worktree/Orange/widgets/data/tests/test_owcreateclass.py` | 1–280、445–485；其余仅关键词匹配行，核心 75–91 |
| `worktree/README-dev.md` | 1–69，构建前提；其通用安装流程未执行 |
| `worktree/tox.ini` | 1–78，项目测试依赖与运行方式 |
| `worktree/requirements.txt` | 1–3 |
| `worktree/requirements-core.txt` | 1–26 |
| `worktree/requirements-gui.txt` | 1–9 |
| `worktree/Orange/widgets/__init__.py` | 1–32 |
| `worktree/Orange/widgets/tests/base.py` | 1–90，测试导入依赖 |

读取结束后仅创建本报告；未写修复代码。剩余不确定性限于上列未规定输入边界，以及真实开发环境和运行结果，本次静态阅读不能消除它们。
