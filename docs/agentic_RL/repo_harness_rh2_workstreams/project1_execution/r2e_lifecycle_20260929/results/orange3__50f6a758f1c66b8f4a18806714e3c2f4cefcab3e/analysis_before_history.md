# orange3__50f6a758 私有主审：读历史前分析

- 角色：R2E 私有主审（单题闭环试行，按统一标准 v1 给结论）。起草时间 2026-09-29 07:50 +08。
- 状态：**读历史前封存稿**。本题的历史调查、history 包、各审查目录、本批 README / board / assignments 都没有打开；devcheck 结果与定点评分还没拿到。
- 路径缩写（均相对仓库根）：`PUB/` = `runs/r2e_static_prep_20260924/v3/public/orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e/`；`PRIV/` = `runs/r2e_static_prep_20260924/v3/private/orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e/`；`OUT/` = 本目录。`owcolor.py` 未注明时指 `PUB/worktree/Orange/widgets/data/owcolor.py`（base 版）；`test_owcolor.py` 指同目录 `tests/test_owcolor.py`（公开版）；`test_1.py` 指 `PRIV/hidden_tests/test_1.py`。
- 证据级别：〔源〕源码推断；〔日志〕已有 RH2 / M3 运行原件；〔待跑〕需要协调者实跑。

## 0. 结论速览

1. **题目**：`OWColor._parse_var_defs` 读取配色定义文件时，对"文件里定义了、数据里没有"的变量要给出警告。base 在 `owcolor.py:700-703` 直接 `continue`，不留任何提示。gold 在同处收集这些名字，拼成一条消息，插到已有的 "Invalid definitions" 警告正文最前面（`PRIV/gold.patch`）。
2. **键**：唯一目标键是 `TestOWColor.test_load_ignore_warning`（noop FAILED、gold PASSED，09-23 与 09-24 两次 RH2 运行一致）。其余 47 个回归键里，46 个与公开测试文件逐字相同；`test_parse_var_defs_no_rename` 删掉了与新需求冲突的 "var not" 断言块（公开 `test_owcolor.py:885-888`）。
3. **T1（误拒合理解，最主要的问题）**：目标键用子串精确匹配名字列表的写法。n=6、7 时要求 `'foo', 'bar', 'baz', 'qux' and 2 other` 这种"超过 5 个只列前 4 个，再写 and N other"的截断格式（`test_1.py:813-820`）。题面只要求"指出 'foo' 和 'bar' 已定义、但数据里没有用到"（`PUB/user_prompt.txt:22`）；仓库里各处列表截断的写法互不一致（§2.2）。候选 K1 满足全部公开要求，只是把名字全部列出，按源码推断会被判 0〔源，待跑〕。去向 R-b。
4. **T2（核心判据缺口，暂定 S1）**：目标键的 7 个实例全部沿用题面示例的输入形态：定义都在 `categorical` 段，`numeric` 为空，没有加载数据，文件里的变量全部未用。按源码推断，下面三个候选都能拿到 48/48〔待跑〕：K2"加载了数据就不警告"（退化候选）、K3"只要有一条定义匹配上就不警告"、K4"只检查 categorical 段"。v1 第 2 步按严格版，在输入形态这一维度命中（T2c）；第 3 步 K2 预计命中 T2b。去向 R-c：补一个"已加载数据、混合文件、两段都有未用变量"的实例。
5. **其它登记项**：
   - P4：题面 "Actual Behavior" 写的 `TypeError`，其实是测试在 mock 从未被调用时自己抛出的，不是应用行为，noop 日志可以证实。
   - P6：公开旧测试的 "var not" 段与正确修复冲突，隐藏版已删掉这一段。
   - X1：本题 gold 与目标测试逐字出现在同仓 `c3fb72ba`、`f5026689` 两题的公开初态里。
   - G1：gold 没有实质问题。
6. **暂定处置**：`needs_review`，原因是题意 / 测试有争议且核心判据有缺口，要等 R-b、R-c 修订和 actor 验证。v1 用途：问题定位 yes；能力比较、训练候选、留出评测都是 conditional（条件见 §9）。
7. **最关键的未知项**：K2（退化候选）和 K1（合理替代）的正式评分结果；actor 侧 devcheck（Qt 前缀、公开命令的墙钟时间）。

## 1. 八方面覆盖

| 方面（清单编号） | 已查 | 未查 / 待验 |
| --- | --- | --- |
| 公开需求（3、23） | `PUB/user_prompt.txt` 全文；`PUB/public_bundle.json:15`（提示）；`PUB/environment_brief.md`；公开读者的 `OUT/public_read.md` 与 `OUT/commands.json`；base `owcolor.py` 第 1–240、470–804 行；在全仓 grep 列表截断写法（§2.2） | 模型实际收到的消息（手里只有静态渲染） |
| 材料与初始问题（1、2、27） | 公开测试与隐藏测试逐行 diff（只差两处，见 §3(d)）；在 base 副本上 gold 能用 `patch -p1` 干净应用，补丁体与 `validation_bundle` 一致；`grading_bundle` 与 `run_refs` 的哈希一致；4 份 RH2 日志与 2 份 M3 日志的 sha256 与 run_refs 一致；读了 noop 的失败位置 | 新机派生镜像上的 noop / gold 基线（由协调者跑） |
| 测试是否测到要求（18–20、25、32） | 目标键逐行追到输入、mock、断言；47 个回归键按类读完（§2.1） | 退化 / 部分候选的实跑（§8） |
| 是否误拒合理解（24、28） | 每条关键断言都反查了公开依据（§2.2）；构造了 K1 | K1 实跑 |
| 回归与 gold 完整性（26、27） | `_parse_var_defs` 唯一的调用者是 `load()`（`owcolor.py:642-659`）；受影响行为 R4–R7 对应到测试；gold 逐行检查（§4） | gold 在公开冲突测试上的实际失败（等 devcheck 的私有 gold 对照） |
| agent 开发条件（6–15） | 环境卡、`environment_brief.md`、评分侧观测（导入路径、版本、pytest 7.4.4、测试段 4–7 s） | actor 侧全部（devcheck 在跑） |
| 交付与评分边界（4、16–17、21–22、29–31） | 修复只涉及一个非测试文件，gold 投影的 `included_paths` 就是这个文件；隐藏测试只有一个文件，不依赖 conftest 或相对路径资源；键没有碰撞 | 通用控制面问题只引用 A 线结论，不逐题审（例如候选改 `Orange/widgets/tests/base.py` 这类不会被重置的测试辅助） |
| 题目关系与用途（5、29–30、37–40） | 两份跨题比对逐条核对，并用 grep 核实（§3、§7 X1） | 反向包含只核实到测试名：对方私有 gold 按规则不读 |

## 2. 需求—断言双向表

### 2.1 公开要求 / 合理旧行为 → 隐藏断言

| # | 要求 / 旧行为 | 公开依据 | 隐藏测试 ID / 决定性断言 | 覆盖 | 证据 / 下一步 |
| --- | --- | --- | --- | --- | --- |
| R1 | 文件含数据里不存在的变量定义时，显示警告 | `user_prompt.txt:6-7, 21-22` | `TestOWColor.test_load_ignore_warning`（`test_1.py:796-820`），1–7 个名字 | **部分**：只覆盖示例的输入形态 | noop FAILED、gold PASSED〔日志〕；K2 / K3 / K4〔待跑〕 |
| R1a | 警告要指出是哪些变量 | `:22` | 同一个键，`assertIn(message, msg_box.call_args[0][2])` 精确子串 | **冲突（过严）**：列表格式和 n≥6 的截断无公开依据（T1） | K1〔待跑〕 |
| R1b | 已加载数据、只有部分定义匹配（混合文件）时，也要对未用的那些警告 | `:6-7` 的一般表述；与公开旧测试 `test_owcolor.py:885-888` 冲突（P6） | 无。上游删掉了唯一一条混合文件断言 | **缺失** | K3〔待跑〕 |
| R1c | `numeric` 段里的未用变量同样要警告 | `:22` 的一般表述；文件分两段的格式见 `owcolor.py:662, 695-697, 628-640` | 无 | **缺失** | K4〔待跑〕 |
| R2 | 过程中不报错 | `:22` | 隐式：抛异常时该键为 ERROR / FAILED | 覆盖 | gold PASSED〔日志〕 |
| R3 | 警告走 `QMessageBox.warning(parent, 标题, 正文)` | 同一函数里两处 `owcolor.py:683-686, 714-715`；公开测试 `test_owcolor.py:860, 870, 877`；题面的 TypeError `:25` | `@patch(...QMessageBox.warning)`，并用 `call_args[0][2]` 取正文 | 覆盖，有代码惯例作依据（残余风险见 §7） | — |
| R4 | 匹配上的定义照常生效，未用的被忽略 | `owcolor.py:698-712`；`test_owcolor.py:804-834` | `test_parse_var_defs`（文件里的定义全部匹配） | 部分：没有混合文件 | — |
| R5 | 非法文件照旧抛 `InvalidFileFormat`，抛之前不弹框 | `owcolor.py:662-677, 691-692`；`test_owcolor.py:836-851` | `test_parse_var_defs_invalid` | 覆盖；但不含"有未用变量、同时某条已用定义非法"时的先后顺序 | gold PASSED |
| R6 | 已有两类警告不变（改名后重名、值改名后重名） | `owcolor.py:150-157, 678-689, 713-715` | `test_parse_var_defs_shows_warnings`；`test_parse_var_defs_no_rename` 前三段 | 覆盖 | gold PASSED |
| R7 | 未用变量的 `rename` 不参与重名检查 | `owcolor.py:678-681`；公开旧测试 `test_owcolor.py:885-888` | 无（隐藏版把这一段删了） | **缺失**（T3，边缘） | 可以随 R-c 顺带补回 |
| R8 | 空文件、或全部定义都匹配时，不弹警告 | base 行为；题面只对未用变量要求警告 | `test_load_ignore_warning` 开头的 `assert_not_called`（`test_1.py:797-799`）；`test_parse_var_defs_no_rename` 第三段 | 覆盖 | gold PASSED |
| R9 | 没有加载数据时也要警告 | 题面示例没有数据准备步骤（`:12-18`） | `test_load_ignore_warning` 的全部实例 | 覆盖 | gold PASSED |

### 2.2 关键断言 → 公开依据（反查）

| 断言（`test_1.py` 行号） | 公开依据 | 判断 |
| --- | --- | --- |
| 797-799：空文件不调用 `warning` | 题面只对未用变量要求警告；base 行为 | 有依据 |
| 803-804：n=1，正文含 `'foo'` | 题面把 `'foo'` 连同单引号写在代码格式里（`:22`） | 弱依据（只关乎引号） |
| 805-806：n=2，含 `'foo' and 'bar'` | 题面散文 "the variables `'foo'` and `'bar'` are defined but not used" | 弱依据：读起来像在描述含义，不像在约定格式 |
| 807-812：n=3–5，逗号分隔、最后一个前用 " and "、无牛津逗号 | 从 n=2 外推；仓库惯例有 `Orange/widgets/data/owaggregatecolumns.py:123-128`（`'a', 'b' and 'c'`）和 `Orange/widgets/data/owrandomize.py:111` | 弱依据 |
| 813-816：n=6、7，前 4 个名字加 `and N other` | **无**。仓库里的截断写法各不相同：`Orange/widgets/utils/__init__.py:144-153`（`... and {} others`，按 max_shown）；`Orange/widgets/utils/state_summary.py:187-195`（超过 3 个时列前 2 个，再加 `and {n-2} others`）；`Orange/widgets/data/owgroupby.py:201`（前 3 个，再加 `and N more`）；`owaggregatecolumns.py:125-126`（超过 30 个才截断，写 `and N others`）。控件文档 `doc/.../color.md` 不讲加载与保存（公开读者已查） | **无依据**，是 T1 的核心 |
| 820：`call_args[0][2]`，即最后一次调用的第 3 个位置参数 | 同函数惯例、公开测试写法、题面 TypeError | 有依据（中等） |
| 796-820：全部实例都不加载数据 | 题面示例 | 有依据 |

## 3. R2E 专项

- **(a) 期望里的非 PASSED 键**：没有。48 个键全是 PASSED（`PRIV/expected_output.json`），所以更完整的修复不会因为"期望 FAILED 的键被翻转"而判 0。会被判 0 的是"消息格式不同"的合理解（T1）。
- **(b) 题面报错是否出现在 noop 目标键里**：`TypeError: 'NoneType' object is not subscriptable` 确实出现了，但抛出位置是测试自身 `r2e_tests/test_1.py:820` 的 `msg_box.call_args[0][2]`：mock 从未被调用，`call_args` 是 None，取下标就报这个错。它不是应用代码抛的〔日志：`runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_df1485a0.eval.log:54-57`；09-23 的 noop 日志相同〕。按源码推演，base 应用对题面示例既不报错也不警告（`owcolor.py:662-719`；我复核后与公开读者 §3.1(b) 一致）→ P4。
- **(c) 题面是否泄漏修法**：没给修法代码。题面点名了私有方法 `_parse_var_defs`，这只是定位提示；TypeError 那句间接暴露了"测试会检查 mock 的 `call_args` 下标"，属于弱的测试机制提示，不构成答案泄漏，不算 P1。
- **(d) 测试辅助、搬迁伪影、撞键**：
  - 隐藏测试只有 `test_1.py` 和一个空的 `__init__.py`。它 = 公开 `test_owcolor.py` + 新增的 `test_load_ignore_warning` − `test_parse_var_defs_no_rename` 末尾的 "var not" 段（逐行 diff，只有这两处差异）。
  - 依赖：`Orange.widgets.tests.base.WidgetTest`（仓库自己的测试辅助，base 版，评分时不会重置）；`orangewidget.tests.base.GuiTest`（已装包）；数据集 iris、heart_disease、zoo（`Orange/datasets/` 下的跟踪文件）。不依赖 conftest，也不依赖相对路径资源。
  - 撞键：48 个键都带类名，互不重复，只有一个文件，不存在跨文件撞键。日志里还有 3 个 SKIPPED（`orangewidget/tests/base.py:238/244/250` ".widget was not set"），推断来自模块命名空间里导入的 `WidgetTest` 类本身；SKIPPED 不成键〔日志 :111-113〕。
- **(e) 时间、随机、资源敏感的键**：
  - 没有时间或随机敏感的键。`test_minimum_size`、`test_image_export` 依赖 Qt 渲染，但 4 次 gold 运行（RH2 ×2、M3 ×2）与 2 次 noop 运行结果一致。测试段 4–7 s（ledger `install.test_seconds` 为 4.4–5.6）。
  - 评分的 `grader_trusted_setup` 在旧机上是 160–190 s（ledger `phases`）。协调者说在新机上要把控制面保护时限放宽到 1200 s；这属于成本与资源档位，不是题目质量问题。
- **(f) 材料修订**：没有。`PRIV/revisions.json` 为 `[]`，run_refs 的 `material_revisions: []`、`env_recipe: null`。

## 4. gold 检查

- **原例**：对题面示例（未加载数据，foo、bar），gold 调用一次 `QMessageBox.warning(self, "Invalid definitions", ...)`，正文是 "Definitions for variables 'foo' and 'bar', which do not appear in the data, were ignored."〔源〕。目标键 n=2 那一轮 PASSED〔日志〕。
- **范围**：两段都收集，与是否加载数据无关，混合文件也警告〔源〕。满足 R1、R1b、R1c、R9。
- **时机**：所有 `from_dict` 执行完才生成消息，赋值之后才弹框；非法文件不会先弹警告再报错（R5）〔源〕。
- **回归**：
  - 会让公开旧测试 `test_parse_var_defs_no_rename` 的 "var not" 段失败（P6；上游已改测试）〔源；等 devcheck 私有 gold 对照〕。
  - 其余公开测试预计不受影响，因为没打补丁的测试都不含未用变量〔源〕。
- **小瑕疵**（不影响处置）：
  - 只有未用变量时，对话框标题仍是 "Invalid definitions"。
  - 变量是按段查找的：变量其实在数据里、只是写在了另一段时，消息仍说"不在数据里"（R11，边缘情况，没有公开要求）。
  - 消息末尾自带 `\n`，再经 `"\n".join` 拼接，会多出一个空行。
- **无关改动**：没有，只改了一个函数。
- **结论**：没有 G1 问题。gold 是合理实现之一，但不是唯一答案（K1 同样合理）。

## 5. 开发需求（逐题）

| 阶段 / 项 | 需求 | 依据 | 证据级别 |
| --- | --- | --- | --- |
| 准备 | 派生镜像 `rh2-r2e-derived/orange3:50f6a758f1c6-r2e_derive_v1`（旧机 image ID `sha256:9fa2177f…`；新机已重建，ID 可能不同）；没有配方修订 | run_refs；ledger `overlay.*` | 评分侧实测（旧机）；新机待协调者跑 |
| 导入 | `python` 指向 `/testbed/.venv/bin/python`（3.7.9）；Orange 从 `/testbed/Orange/__init__.py` 导入，版本 3.32.0.dev；编译扩展和 `Orange/version.py` 已在镜像里 | `environment_brief.md:10`；ledger `observations.RH2_OBS_IMPORT_PATH / RH2_OBS_PKG_VERSION` | 评分侧实测；actor 待验（devcheck `env_import`） |
| 依赖 | PyQt5、AnyQt、orangewidget、pytest 7.4.4 都已装；不用装包，也不用联网 | 评分日志 `Python 3.7.9, pytest-7.4.4` | 评分侧实测；actor 用同一张镜像（代码配置），待验 |
| 资产 | iris、heart_disease、zoo 在 `Orange/datasets/`（跟踪文件） | `PUB/worktree/Orange/datasets/` | 静态核对 |
| Qt | widget 测试要加前缀 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum`。公开提示没写；从 `PUB/worktree/run_tests.sh:1` 和 `CONTRIBUTING.md:111-112` 可以推知 | `environment_brief.md:13` | brief 称环境阶段已实测；actor 待验；不带前缀会怎样，未知 |
| 权限 | agent（uid 54321）可写 `/testbed` 和 HOME。widget 测试可能写 Qt / Orange 设置（如 `test_reuse_old_settings`），这一点是推断 | `environment_brief.md:12` | actor 待验 |
| 网络 | 各阶段都不需要 | — | 静态 |
| 构建 | 不需要编译，修复是纯 Python | gold 只改 `owcolor.py` | 静态 |
| 提交边界 | 只需改跟踪文件 `Orange/widgets/data/owcolor.py`；正式导出按文件字节差异 | gold ledger `projection.included_paths` | 评分侧实测 |
| 公开测试 | 修好后，公开的 `test_parse_var_defs_no_rename` 必然失败（P6），其余应全过。公开读者的命令 3、4 已把这一条单独列出 | `test_owcolor.py:885-888` | 源码推断；等 devcheck 私有 gold 对照 |
| 墙钟 | 评分侧测试段 4–7 s（51 项，含 3 个 skip） | ledger | 评分侧实测；actor 侧等 devcheck |

**公开读者的命令是否够用**：四条命令覆盖了导入、题面复现（无数据直接调用，以及加载数据后经 `load()` 调用两种）、相关公开测试和冲突测试，足够 actor 自查。不足有两点：混合文件那一例只打印、不断言（因为公开材料在这一点上确实有歧义）；没有复现 `numeric` 段的未用变量。这两点属于题目本身的规格缺口，不要求公开命令来补。

## 6. v1 §4 五步（暂定）

1. **第 1 步**：核心要求有直接断言（`test_load_ignore_warning` 断言了警告内容），不命中。
2. **第 2 步**：名字和个数有非示例的实例（1–7 个名字），但全部实例都沿用示例的输入形态：categorical 段、numeric 为空、未加载数据、全部未用。按严格版（D1），在"输入形态"这一维度命中 T2c。若复核认为名字和个数的变化已经算非示例实例，第 2 步就不命中，S1 改由第 3 步决定。
3. **第 3 步**：唯一指定的退化候选是 K2（加载了数据就关掉检查）。
   - 违反的公开要求：`user_prompt.txt:6-7, 21-22`，"文件含数据里没用到的变量定义时要警告"。
   - 看出违例的输入：加载 iris 后读题面示例文件，K2 不警告。公开读者 `repro_unused_vars_warning` 的例 2 就能测出来。
   - 预计 48/48、reward 1，命中 T2b〔待跑〕。
4. **第 4 步**：构造候选 K3（混合文件不警告）和 K4（`numeric` 段不警告）预计也都得 1。它们违反的是同一核心要求的其它实例，其中混合文件是最常见的真实场景（加载为另一份数据保存的配色文件），不是罕见路径，因此判 S1〔待跑〕。
5. **暂定**：S1。第 2 步已静态命中，第 3、4 步待实跑。另有 T1，它不属于这五步，按 R-b 处理。

## 7. 问题清单

| 编号 | 问题 | 证据级别 | 去向 |
| --- | --- | --- | --- |
| T1 | 目标键精确匹配名字列表的格式，n≥6 的截断规则没有公开依据；合理解 K1 预计判 0 | 源码推断（确定性高），K1 待跑 | R-b |
| T2（T2c / T2b） | 核心断言只覆盖示例的输入形态；K2、K3、K4 预计得 1 | 源码推断 + 待跑 | R-c |
| T3 | R7，以及"未用变量 + 某条已用定义非法"时的先后顺序，都没有断言 | 源码推断 | 登记；R7 可随 R-c 顺带补回 |
| P4 | 题面 Actual Behavior 里的 TypeError 是测试伪影；标题 "Error Occurs…" 与描述 "fails to handle the warnings properly" 把"缺少的功能"说成了"已有的处理出错" | noop 日志 + 源码 | 登记；R-f 可选（§9） |
| P6 | 公开旧测试 "var not" 段写死了"不警告"的旧行为，与正确修复冲突；隐藏版已删 | 公开 / 隐藏测试 diff | 登记。探针分析按 P6 解读：这条公开测试失败不算模型改错。它与 T2 叠加有训练风险：为保住这条公开测试而写出 K3 式特例的解会拿满分 |
| X1 | 本题 gold（14/14 条非平凡新增行）和目标测试名，出现在 `c3fb72ba`（base 419b1882）、`f5026689`（base 3dd6d9c9）的公开工作树里（`owcolor.py:695-724`、`test_owcolor.py:817`，已 grep 核实）。反向：本题工作树含 `4014f248`、`9b5494e2`、`f237f968` 的新测试名（`Orange/tests/test_discretize.py:47`、`Orange/tests/test_logistic_regression.py:135`、`Orange/widgets/data/tests/test_owselectrows.py:345`，已核实），以及扫描报告的 `22e98f8f` gold 行（未能复核，需要对方私有 gold）。这些都与 owcolor 无关 | 机械扫描 + grep | 登记；训练时控制重复采样；留出按仓库划分，同仓全部同侧 |
| 残余风险 | 只用控件消息栏（`self.Warning`）显示、不调 `QMessageBox.warning` 的候选会判 0。依据是同函数惯例和题面 TypeError 的暗示，所以不算 T1，只登记 | 源码推断 | 登记 |

## 8. 候选与请协调者实跑的内容

### 8.1 候选

补丁全文见附录 A。四个补丁都已在 base 副本上用 `patch -p1` 干净应用，Python 语法解析通过；没有运行项目代码。

- **K1：合理替代（T1 探针）**
  - 改法：沿用 gold，但 2 个名字以上时一律全部列出（`'a', 'b', … and 'z'`），删掉"超过 5 个只列前 4 个，再写 and N other"那个分支。
  - 公开要求：满足全部（两段都查、有无数据都查、混合文件也查、每个名字都点到、不报错、其它警告不变）。
  - 预计：`TestOWColor.test_load_ignore_warning` FAILED，失败在 n=6 那一轮的 `test_1.py:820`，因为找不到 `'foo', 'bar', 'baz', 'qux' and 2 other`；其余 47 键 PASSED。reward 0。
- **K2：退化候选（v1 第 3 步，本题唯一指定的退化候选）**
  - 改法：gold 的 `if unused_vars:` 改成 `if unused_vars and self.data is None:`，即加载了数据就关掉检查。
  - 违反：题面要求对"定义了、但数据里没用到"的变量警告；加载 iris 后读题面示例文件，K2 不会警告。
  - 预计：48/48，reward 1，命中 T2b。
- **K3：部分实现，遵循冲突的公开测试**
  - 改法：`if unused_vars and not any(both_descs):`，只要文件里有任一定义匹配上数据就不警告。解题者为了让公开旧测试 "var not" 段继续通过，很可能写出这种特例。
  - 违反：混合文件里的未用变量不警告。
  - 预计：reward 1。
- **K4：部分实现，按段漏检**
  - 改法：只在 categorical 段收集未用名字。
  - 违反：`numeric` 段的未用变量不警告。
  - 预计：reward 1。隐藏测试里的未用变量都在 categorical 段，所以结果可以静态确定。K4 主要留作修订验收时的已知错误候选，可以不先跑。

### 8.2 正式评分（第一优先）

- 条件：当前材料（无修订）；新机派生镜像；控制面保护时限放宽到 1200 s，只放宽时限。
- 优先顺序：K2 > K1 > K3 > K4。
- 每次需核对：`RH2_SETUP_APPLY_RC=0`；`projection.included_paths` 为 `["Orange/widgets/data/owcolor.py"]`；日志的 short summary 有 48 个键和 3 个 SKIPPED；逐键列出 mismatched / missing / unexpected。
- K1 另外核对失败断言：应在 `test_1.py:820`、n=6 那一轮。
- 若新机还没复跑 noop / gold，请各跑 1 次作基线。

### 8.3 私有行为对照（可选，成本低）

在派生镜像里分别应用 gold、K1、K2、K3、K4 和 noop，然后跑附录 B 的探针。用 root 或 agent 跑都可以，这里不涉及权限归因。这个探针只作私有对照，不要写进解题者的环境说明。预计结果：

| 探针例 | gold | K1 | K2 | K3 | K4 | noop |
| --- | --- | --- | --- | --- | --- | --- |
| a：加载 iris + 题面示例文件 | 过 | 过 | **挂** | 过 | 过 | 挂 |
| b：加载 iris + 混合文件（iris 改名，categorical 未用 foo，numeric 未用 bar） | 过 | 过 | **挂** | **挂** | **挂**（缺 bar） | 挂 |
| c：无数据 + 只在 numeric 段有未用 foo | 过 | 过 | 过 | 过 | **挂** | 挂 |
| d：加载 iris + 定义全部匹配（回归保护，不应弹框） | 过 | 过 | 过 | 过 | 过 | 过 |

它能证明两件事：K2、K3、K4 的违例输入确实被执行到，而且运行的是候选代码；K1 在这些输入上行为正确。

### 8.4 请 devcheck 给出的观测

- 公开读者四条命令在 noop 上的输出与墙钟时间。预计：
  - `repro_unused_vars_warning` 退出码 1，例 1、例 2 报 `AssertionError: False is not true : []`，**不是** TypeError；
  - 另外三条退出码 0。
- 私有 gold 对照：
  - `repro_unused_vars_warning`：3 passed；
  - `public_no_rename_conflict`：在第 888 行失败（P6 的执行证据）；
  - `public_owcolor_tests_except_conflict`：全过。
- 可选：不带 Qt 前缀跑一个 widget 测试，看会发生什么，用来判断公开提示只写 `python -m pytest` 是否够用。命令：`cd /testbed && timeout 300 python -m pytest -p no:cacheprovider -q Orange/widgets/data/tests/test_owcolor.py -k test_parse_var_defs_shows_warnings; echo rc=$?`（预期未知）。

## 9. 暂定处置、用途与修订方向

- **disposition（暂定）**：scope 为 `static_review`；state 为 `needs_review`。reason：题意 / 测试有争议（T1），核心判据有缺口（T2，待 K2 实跑），修订后再复评；静态结论还需 actor 验证。
- **usage.v1（暂定）**：
  - `problem_localization`：yes。
  - `capability_comparison`：conditional。缺：
    - R-b 验收。按现状，得分基本取决于能否猜中截断格式，合理解会被判 0；
    - actor devcheck；
    - 新机 noop / gold 基线。
  - `training_candidate`：conditional。缺：
    - R-b + R-c 一轮修订与验收（gold 1、K1 1、noop 0、K2 / K3 / K4 0）；
    - Codex 复核；
    - actor 条件。
    X1 已登记。
  - `heldout_candidate`：conditional。修订后只能作"标明版本的自建评测"；按仓库划分，与 `c3fb72ba`、`f5026689` 放在同侧；审查暴露已记录。
- **修订方向**（按 v1 §5；具体测试代码写进 card，由协调者实施与实测）：
  - **R-b（针对 T1）**，改 `PRIV/hidden_tests/test_1.py` 的 `test_load_ignore_warning`：
    - 保留：空文件不警告；`QMessageBox.warning` 第 3 个位置参数这一通道。
    - 每轮先 `reset_mock()`，解析后 `assert_called()`。
    - n≤2 时，要求每个名字都出现在正文里。
    - n≥3 时，每个名字要么出现在正文里，要么正文写出了没列出的名字有几个。
    - 删掉关于逗号、" and "、截断的精确子串。
    - 公开依据：题面 `:22`（要指出是哪些变量）；删掉的只是格式细节。
    - 验收：gold 1；K1 从 0 变 1；noop 0；不点名的错误候选（例如正文只写 "Some definitions were ignored"）仍为 0。
    - n≥3 的阈值属于设计选择，修订时由协调者与 Codex 复核确认。
  - **R-c（针对 T2）**，在同一文件加一个有数据的实例：
    - 用 `send_signal(iris)` 加载数据，再读混合文件：`iris` 改名，categorical 有未用的 `foo`，numeric 有未用的 `bar`。
    - 断言警告正文含 foo 和 bar，并且输出里的 `class_var` 已改名。
    - 可选：再加一个"反转的 var not"实例，即 `_create_descs()` + `{"categorical": {"varA": {"rename": "X"}}, "numeric": {"var not": {"rename": "X"}}}`，断言警告提到 `var not`、且不出现 "duplicated names"。这样可以顺带补回 R7。
    - 新增测试函数时，要同时在 `expected_output.json` 里加 PASSED 键；也可以并入现有目标测试，保持键集不变。
    - 注意：只用 `_create_descs()`、不 `send_signal` 杀不掉 K2，因为那时 `self.data` 仍是 None。
    - 公开依据：题面的一般表述；文件分两段的格式；base 已有的"匹配上的定义照常生效"。
    - 验收：gold 1、K1 1（与 R-b 同一轮）、noop 0、K2 / K3 / K4 均为 0。
  - **R-f（针对 P4，可选）**：
    - 做法：把 "Actual Behavior" 改成在 base 上核实过的症状：不显示警告，未用变量的定义被静默忽略。
    - 代价：题面里对 `QMessageBox` mock 通道的间接提示也会随之消失；不过这个通道仍有同函数惯例和公开测试写法作依据。
    - 做不做由协调者按成本定。

## 10. 缺口与唯一下一步

- **未知**：
  - K1–K4 的正式评分结果；
  - 新机的 noop / gold 基线；
  - actor devcheck；
  - orangewidget 的测试基类会不会拦截模态框。这只影响"在没打补丁的测试里也会弹框"的候选，K1–K4 都不涉及；
  - 真实模型候选：目前没有。
- **判断会怎样改变**：
  - 若 K2 实跑得 0：先核对补丁是否交付、测试是否执行；如果运行有效，T2b 不成立，S1 只剩第 2 步的严格版依据，改记 conditional，交复核。
  - 若 K1 实跑得 1：T1 被推翻，要回头核对日志。
- **唯一最值得先做的下一步**：用正式评分给 K2（第 3 步退化候选）和 K1（误拒探针）各跑 1 次。K2 的结果决定 T2b / S1 是否成立，K1 给出 T1 的执行证据；两者合起来决定修订范围（R-b + R-c）。

## 附录 A：候选补丁全文（相对 base，git apply 可用）

K1（合理替代：名字全列，不截断）：

```diff
diff --git a/Orange/widgets/data/owcolor.py b/Orange/widgets/data/owcolor.py
--- a/Orange/widgets/data/owcolor.py
+++ b/Orange/widgets/data/owcolor.py
@@ -690,6 +690,7 @@
 
         # First, construct all descriptions; assign later, after we know
         # there won't be exceptions due to invalid file format
+        unused_vars = []
         both_descs = []
         warnings = []
         for old_desc, repo, desc_type in (
@@ -700,11 +701,22 @@
             for var_name, var_data in js[repo].items():
                 var = var_by_name.get(var_name)
                 if var is None:
+                    unused_vars.append(var_name)
                     continue
                 # This can throw InvalidFileFormat
                 new_descs[var_name], warn = desc_type.from_dict(var, var_data)
                 warnings += warn
             both_descs.append(new_descs)
+        if unused_vars:
+            names = [f"'{name}'" for name in unused_vars]
+            if len(unused_vars) == 1:
+                warn = f'Definition for variable {names[0]}, which does not ' \
+                       f'appear in the data, was ignored.\n'
+            else:
+                warn = 'Definitions for variables ' \
+                       f'{", ".join(names[:-1])} and {names[-1]}'
+                warn += ", which do not appear in the data, were ignored.\n"
+            warnings.insert(0, warn)
 
         self.disc_descs = [both_descs[0].get(desc.var.name, desc)
                            for desc in self.disc_descs]
```

K2（退化候选：有数据时关掉检查），与 `PRIV/gold.patch` 只差一行：gold 的 `+        if unused_vars:` 改成下面的样子。

```diff
diff --git a/Orange/widgets/data/owcolor.py b/Orange/widgets/data/owcolor.py
--- a/Orange/widgets/data/owcolor.py
+++ b/Orange/widgets/data/owcolor.py
@@ -690,6 +690,7 @@
 
         # First, construct all descriptions; assign later, after we know
         # there won't be exceptions due to invalid file format
+        unused_vars = []
         both_descs = []
         warnings = []
         for old_desc, repo, desc_type in (
@@ -700,11 +701,26 @@
             for var_name, var_data in js[repo].items():
                 var = var_by_name.get(var_name)
                 if var is None:
+                    unused_vars.append(var_name)
                     continue
                 # This can throw InvalidFileFormat
                 new_descs[var_name], warn = desc_type.from_dict(var, var_data)
                 warnings += warn
             both_descs.append(new_descs)
+        if unused_vars and self.data is None:
+            names = [f"'{name}'" for name in unused_vars]
+            if len(unused_vars) == 1:
+                warn = f'Definition for variable {names[0]}, which does not ' \
+                       f'appear in the data, was ignored.\n'
+            else:
+                if len(unused_vars) <= 5:
+                    warn = 'Definitions for variables ' \
+                           f'{", ".join(names[:-1])} and {names[-1]}'
+                else:
+                    warn = f'Definitions for {", ".join(names[:4])} ' \
+                           f'and {len(names) - 4} other variables'
+                warn += ", which do not appear in the data, were ignored.\n"
+            warnings.insert(0, warn)
 
         self.disc_descs = [both_descs[0].get(desc.var.name, desc)
                            for desc in self.disc_descs]
```

K3（混合文件不警告）：与 K2 完全相同，只把条件行换成

```diff
+        if unused_vars and not any(both_descs):
```

K4（只查 categorical 段）：与 gold 相同，只把收集那一行换成两行（第二个 hunk 变为 `@@ -700,11 +701,27 @@`）：

```diff
                 if var is None:
+                    if repo == "categorical":
+                        unused_vars.append(var_name)
                     continue
```

K3、K4 的完整补丁由 gold 同法替换即可得到；我在本地临时目录生成并校验过（能应用到 base、得到预期文件）。四个补丁的 sha256 如下，文件头部带 `diff --git`：K1 `e0b92f37…d907`、K2 `928a4b12…5c`、K3 `f924b3cf…d4`、K4 `2aa27974…82`。

## 附录 B：私有行为探针（只作私有对照，不进解题者环境说明）

在 `/testbed` 下运行，要求已应用候选补丁：

```bash
cd /testbed || exit 2
cat > /tmp/test_r2e_owcolor_priv.py <<'PY'
import json
from unittest.mock import patch

from Orange.data import Table
from Orange.widgets.data import owcolor
from Orange.widgets.tests import base as wbase

EXAMPLE = {"categorical": {"foo": {"renamed_values": {}},
                           "bar": {"renamed_values": {}}},
           "numeric": {}}


def texts(mock):
    return [" | ".join(str(a) for a in list(c[0][1:]) + list(c[1].values()))
            for c in mock.call_args_list]


class TestPrivUnused(wbase.WidgetTest):
    def setUp(self):
        self.widget = self.create_widget(owcolor.OWColor)

    def _parse(self, js):
        with patch.object(owcolor.QMessageBox, "warning") as warn, \
                patch.object(owcolor.QMessageBox, "critical") as crit:
            self.widget._parse_var_defs(js)
        return texts(warn), texts(crit)

    def test_priv_a_example_with_data(self):
        # statement example while iris is loaded: foo/bar are not in the data
        self.send_signal(self.widget.Inputs.data, Table("iris"))
        warns, crits = self._parse(json.loads(json.dumps(EXAMPLE)))
        print("A warning calls:", warns, "| critical:", crits)
        self.assertEqual(crits, [])
        self.assertTrue(any("foo" in t and "bar" in t for t in warns), warns)

    def test_priv_b_mixed_with_data(self):
        # used definition (iris -> species) plus unused foo (categorical)
        # and unused bar (numeric)
        self.send_signal(self.widget.Inputs.data, Table("iris"))
        js = {"categorical": {"iris": {"rename": "species"},
                              "foo": {"renamed_values": {}}},
              "numeric": {"bar": {"colors": "linear_viridis"}}}
        warns, crits = self._parse(js)
        print("B warning calls:", warns, "| critical:", crits)
        self.assertEqual(crits, [])
        joined = "\n".join(warns)
        self.assertIn("foo", joined)
        self.assertIn("bar", joined)
        out = self.get_output(self.widget.Outputs.data)
        self.assertEqual(out.domain.class_var.name, "species")

    def test_priv_c_numeric_only_no_data(self):
        warns, crits = self._parse({"categorical": {}, "numeric": {"foo": {}}})
        print("C warning calls:", warns, "| critical:", crits)
        self.assertEqual(crits, [])
        self.assertIn("foo", "\n".join(warns))

    def test_priv_d_all_used_no_warning(self):
        # regression guard: every definition matches the data -> no dialog
        self.send_signal(self.widget.Inputs.data, Table("iris"))
        warns, crits = self._parse(
            {"categorical": {"iris": {"rename": "species"}},
             "numeric": {"petal length": {"colors": "linear_viridis"}}})
        print("D warning calls:", warns, "| critical:", crits)
        self.assertEqual(warns, [])
        self.assertEqual(crits, [])
PY
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -p no:cacheprovider -q -rA -k test_priv /tmp/test_r2e_owcolor_priv.py
```

建议 `timeout_s` 为 300。`-k test_priv` 只选这 4 例，不会选中 `WidgetTest` 继承来的通用测试。本地只做了 `bash -n` 与 Python 语法解析，没有运行。

## 附录 C：证据索引与阅读范围

- **题面与公开材料**：`PUB/user_prompt.txt:4, 6-7, 12-18, 22, 25`；`PUB/public_bundle.json:15`；`PUB/environment_brief.md:10-13`；`PUB/worktree_manifest.json` 只看了顶层字段（`initial_diff` 为 0 字节；未跟踪文件 `datasets`、`install.sh`、`run_tests.sh`）。
- **base 源码**：`owcolor.py:64-74, 139-175, 223-231`（`from_dict` 返回 `(desc, warnings)`）、`:586-606`（`set_data`）、`:642-659`（`load`）、`:661-719`（`_parse_var_defs`）。
- **隐藏测试与期望**：`test_1.py:796-820`（目标）、`:888-909`（no_rename 隐藏版）；`PRIV/expected_output.json`（48 键，全部 PASSED）；公开 `test_owcolor.py:853-888`。
- **运行原件**（均为 current 材料，配方 `r2e_derive_v1`，旧机派生镜像 `sha256:9fa2177f…`）：
  - noop：`runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:25`，reward 0，47/48，mismatched 只有目标键；`runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:25`，同上；日志 `…/evallog_replay-r2e-envrepair-rer_df1485a0.eval.log:25-57, 114-119`。
  - gold：两份 ledger 的 `:25`，48/48，reward 1；日志 `…rer_83d64336.eval.log`，48 passed、3 skipped。
  - 独立参考：M3 在来源镜像上跑 gold 两次都通过，`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:24, 74`。
- **跨题比对**：`runs/r2e_static_prep_20260924/cross_task_gold_scan.json` 与 `cross_task_test_scan.json` 里 orange3 的各条；同仓公开包：各题 `user_prompt.txt` 首行与标题、`public_bundle.json` 的 base_commit，以及对 `owcolor.py` / `test_owcolor.py` 的 grep。
- **方法文档**：角色卡、八方面协议、R2E 环境卡、记录模板、40 项清单、统一标准 v1。
- **没有读**：本题历史与 history 包；各审查目录；本批 README / board / assignments / status_table / morning_summary / probe_chain_check / codex_reviews；其它题的私有包；`.venv` 里的已装包源码（包括 orangewidget 的测试基类）。
- **暴露说明**：本会话自动载入了项目说明与本机私有说明（机器与镜像清单、统一标准的决定摘要），其中没有本题的历史结论。
