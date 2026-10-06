# 50f6a758：公开材料静态阅读

整理日期：2026-10-03。仅据指定公开包判断；这是**静态公开材料阅读，不是 actor 交付验收**。未读 gold、隐藏测试、候选、私有调查或包外来源；未安装依赖、运行目标代码／测试、连接 SSH、调用模型或实施修复。

## 结论与公开行为

修订题面与公开 base 的静态行为相符，旧测试存在一处已被 Development Note 明示的目标冲突，读者不需要猜隐藏规则。题面例子以 `foo`、`bar` 不在当前数据中为前提；源码对未匹配到变量的定义直接跳过，且该例不触发格式／重名校验异常（`worktree/Orange/widgets/data/owcolor.py:661–715`）。这是源码推断，不是复现结果。

- **要改变：**载入包含当前数据没有的变量定义时，显示能说明这些变量已定义但未用于当前数据的警告；例子应指出 `foo` 与 `bar`，处理过程不应因此报错（`user_prompt.txt:5–23`）。描述针对变量定义，未限定只支持 categorical；公开载入器同时处理 categorical 和 numeric（源码 `:695–707`）。
- **须保留：**已有变量的合法更名、类别值更名和配色继续生效；没有新定义的变量继续保留（公开测试 `worktree/Orange/widgets/data/tests/test_owcolor.py:804–834`）。格式错误仍按既有规则报错，类别值重名仍警告（`:836–860`）。重复变量更名仍被拒绝并警告，合法变量名称互换仍无警告（`:866–883`；源码 `:678–689`）。缺失变量的更名定义不能让已有变量的合法更名变成重名冲突（`:885–888`）。类别值映射中多余的值不等同于本题的“多余变量”，其旧行为有独立无警告断言（`:153–165`）。
- **未规定：**新警告的逐字文本、标题、名称顺序、逐项或合并展示均未指定。不要据此增设消息格式要求；也不将“此例不应报错”扩大为所有畸形输入都不报错。

## Development Note 是否足够

足够。`user_prompt.txt:25–26` 准确点名 `TestOWColor.test_parse_var_defs_no_rename` 最后的未知变量断言。公开测试 `:885–888` 确实对 `var not` 要求不警告；这条要求与新增目标相反，而前面的两种重名检查和名称互换检查仍有效。因此原测试原封不动运行时，修复后可能因最后一条旧断言失败，不能把整项失败直接等同于修复错误，也不能通过跳过整项来宣称更名回归已验证。

该注释只解释预期行为与旧断言的冲突，没有给出补丁、算法或新警告文案，也没有引入超出公开 issue 的行为要求。`public_task.json:5` 的来源提示要求不修改仓库测试；“validate”可以通过仓库外临时公开探针完成，不需要把 Development Note 解读为允许修改仓库测试。例子未给出 widget／数据初始化代码，但正文已说明变量缺失条件，公开测试的 `_create_descs` 提供可用夹具（`:796–802`）；这不是阻断理解的歧义。

## 最小开发验证建议（全部未执行）

`public_commands.json` 给出两条待执行命令：

1. `public_existing_regressions`：只运行正常解析、格式错误、类别值重名警告、文件载入和多余类别值的五个已有公开测试。
2. `public_issue_and_rename_contract`：在临时目录创建公开探针，检查题面例子及 numeric 缺失变量；保留旧测试前段的两种重复更名和合法名称互换，并将末尾“已有变量合法更名＋未知变量定义”按新目标检查。探针不改仓库测试，结束删除临时目录；警告正文自动检查对应变量名，仍需人工核对其含义确实为“定义未用于当前数据”，不锁死逐字文案。

前提是后续实际 actor 中存在完整 `/testbed` 工作树、指向该工作树的已备妥 Python 环境、pytest、Orange 及其编译扩展／数据资源、AnyQt／Qt 和 orangewidget 等依赖，以及 `xvfb-run` 所需运行条件。公开夹具依赖 `iris`（测试 `:619–623`），测试基类导入 Qt 与其他 Orange 模块（`worktree/Orange/widgets/tests/base.py:7–40`）。公开说明记载历史 Python 3.7 和无头 Qt 前缀，但不能据此认定当前环境已满足（`environment_brief.md:3–8`；`worktree/run_tests.sh:1`）。本次不运行该脚本的 `r2e_tests` 目标。依赖缺失或收集失败应作为环境问题记录；上述命令的预期不是已验证通过结果。

## 本次实际读取与完整性

读取范围：本目录 `public_reader_prompt.md`；公开包内 `user_prompt.txt`、`public_task.json`、`manifest.json`、`environment_brief.md`；以及 `worktree/Orange/widgets/data/owcolor.py`、`worktree/Orange/widgets/data/tests/test_owcolor.py`、`worktree/Orange/widgets/tests/base.py`（相关代码／测试与依赖段）、`worktree/doc/visual-programming/source/widgets/data/color.md`、`worktree/README-dev.md`、`worktree/tox.ini`、`worktree/run_tests.sh`。仅将 manifest 的包外路径视为来源标识，未跟随读取。

静态 SHA256 核对：manifest 列出的 10 个文件全部吻合；`public_task.json` 的 problem_statement 与 `user_prompt.txt` 逐字一致。

- 题面 `user_prompt.txt`：`8d7ddab841c89504b41268db2e13aed59a67ac13aaa791f8c32c70a1a3a321ef`
- `manifest.json`：`9c061b4e18446d2ca27ce321ee56088dff2d521bbcbcc40f1c935325fa32b07d`
- `public_task.json`：`dd1188ec36b0e945cd2fe630214b4548187cbda31cc50f9f99b69db764531dd5`

包内声明 base commit 为 `30c5657673a46e452162b1cb4fc6415baada5784`（`public_task.json:4`）；本次未访问 Git 或实际 actor 核验该声明，不作评分或用途准入结论。
