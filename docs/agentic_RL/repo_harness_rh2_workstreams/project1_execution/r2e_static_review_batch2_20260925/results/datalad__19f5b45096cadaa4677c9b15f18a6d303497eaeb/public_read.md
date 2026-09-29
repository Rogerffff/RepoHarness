# datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb：公开读者报告

- 角色：公开读者，只做静态审查，不解题。只读了角色卡和 PUBLIC_DIR 下的文件；没有运行项目代码，没有联网，没有读任何私有材料。
- 路径约定：`worktree/` 内的文件写相对路径，等同于容器里的 `/testbed/<路径>`；PUBLIC_DIR 顶层文件直接写文件名。行号以本次读到的工作树为准。
- 标注含义："明示"表示题面直接写出；"可推知"表示能从公开仓库的代码、文档或测试合理推出；"多解"表示公开材料不足以确定。§4 的命令一律是**建议，未执行**。

**题意概括**：从命令行调用 `datalad run` 时，如果被执行的 shell 命令以非零码 N 退出，datalad 进程现在统一以 1 退出。题面要求改为以 N 退出。

## 1. 需求表

### 1.1 base 行为链（从源码读出，未运行）

1. `datalad/core/local/run.py:693-709` 的 `_execute_command` 捕获 `CommandError`，返回 `(e.code, e)`；`run.py:1013-1015` 把退出码写进 `run_info['exit']`。
2. `run.py:1061-1082`：非 rerun 且退出码非零时产生 `status="error"` 的结果记录，记录里有 `exit_code=cmd_exitcode` 和 `exception=exc`（原始 `CommandError`）。
3. `Run.on_failure = 'stop'`（`run.py:210`）。`datalad/interface/utils.py:390-396` 把失败记录放进 `incomplete_results` 并中断循环，随后 `datalad/interface/base.py:939-942` 抛出 `IncompleteResultsError(failed=...)`。
4. `datalad/cli/main.py:199-220`：先设 `exit_code = 1`（201 行）。`IncompleteResultsError` 分支只调用 `lgr.debug`（207-210 行），最后 `sys.exit(1)`。只有直接抛到这里的 `CommandError` 才会经 `_communicate_commanderror` 转发 `exc.code`（211-212、223-235 行），而 run 的 `CommandError` 被包在结果记录里，走不到这个分支。

所以，按源码推断，在 base 上 CLI 执行 `datalad run 'exit 3'` 会以 1 退出，与题面的 Actual Behavior 一致。

### 1.2 需求

| 编号 | 需求 | 性质 | 依据 |
|---|---|---|---|
| R1 | 在 no-annex 数据集中，`datalad run --explicit 'exit 3'`（默认 `on_failure=stop`）应以 3 退出。示例经 `run_main` 调用进程内 `main()`，并断言 `SystemExit.code == 3` | 明示 | `user_prompt.txt:15-18, 21-25` |
| R2 | 推广到一般情况：run 执行的命令以任意非零码 N 退出时都转发 N，不限于 3，也不限于 `--explicit` | 可推知 | `user_prompt.txt:22`（"the same non-zero exit code … that the underlying command returns"）；`Run` docstring `run.py:105-106`；`docs/source/design/cli.rst:65-71` |
| R3 | 命令成功（退出码 0）时仍退出 0，成功路径的保存行为不变 | 保留（代码） | `cli/main.py:171-172`；`run.py:1099-1113` |
| R4 | 失败原因不是命令退出码时（输入缺失 `run.py:490-496`、数据集有未保存改动 `run.py:887-895`、占位符错误 `run.py:925-933, 963-970`），仍按"结果不完整"退出 1 | 可推知 | `cli.rst:61-63`；`cli/main.py:201, 207-210`；这些失败记录没有 `exit_code` 字段 |
| R5 | 其它 CLI 退出码不变：参数不足退出 2，子命令带未知参数退出 1，`-c` 配置覆盖格式错误退出 3，KeyboardInterrupt 退出 3 | 保留（公开测试和代码） | `datalad/cli/tests/test_main.py:198-211, 237-256, 347-351`；`cli/main.py:101-108, 202-206, 213-216`；`datalad/cli/helpers.py:271` |
| R6 | Python API 行为保留：默认 stop 时抛 `IncompleteResultsError`，不是 `CommandError`；`on_failure='ignore'` 时不抛异常，返回 `status='error'` 的 run 记录且 `run_info['exit'] > 0`；失败时不保存；非 `--explicit` 时写 `COMMIT_EDITMSG` 并给出保存提示 | 保留（公开测试） | `datalad/core/local/tests/test_run.py:103-109, 149-158, 160-173`；`datalad/local/tests/test_rerun.py:314-323, 344-348`；`datalad/interface/common_opts.py:354-362` |
| R7 | CLI 下 `--on-failure ignore` 时，失败不应产生非零退出码 | 可推知（文档）；题面未涉及 | `datalad/cli/common_args.py:95-99`；`docs/source/design/result_records.rst:78-86` |
| R8 | 以下情况是否也转发退出码，公开材料没有约定：`--on-failure continue`；一次调用里有多个失败且退出码不同；rerun 的退出码与记录不符（`run.py:1061-1062`）；`run-procedure`（`datalad/local/run_procedure.py:463-473` 内部先用 `ignore` 调 Run，再由自身的 on_failure 处理）；`--dbg/--idbg` 调试路径 | 多解 | 题面只给出默认 stop 下单个失败的情形 |
| R9 | 失败时是否在 stderr 打印类似 `CommandError: 'exit 3' failed with exitcode 3 under …` 的说明 | 多解。如果判分沿用示例中的 `run_main`，它的默认参数 `expect_stderr=False` 要求 Python 层的 `sys.stderr` 为空（见 §2） | `test_main.py:77-79, 86-87`；`cli/main.py:223-235` 使用 `os.write(2, …)`；`cli.rst:68-71` |
| R10 | 只对 `run` 生效，还是对所有失败记录带 `exit_code` 的命令都转发。`get_status_dict` 遇到 `CommandError` 时会自动加 `exit_code`（`datalad/interface/results.py:132-133`） | 多解 | 题面标题和正文只提到 `datalad run` |

## 2. 合理实现范围

需要满足的可观察约定见 R1–R7。以下几类实现差异都应被接受：

- **在哪一层把命令退出码传到进程退出码，公开材料没有限定。** 可以在 CLI 异常处理器里读取 `IncompleteResultsError.failed` 中失败记录的 `exit_code`，或记录里 `exception` 字段所存 `CommandError` 的 `.code`；可以在结果汇总或异常对象上附带退出码，再由 CLI 读取；也可以只对 `action == 'run'` 的记录生效。所需信息在 base 里已经存在：`CHANGELOG.md:1191` 写明原始 `CommandError` 保留在结果记录的 `exception` 字段中，该记录可经 `IncompleteResultsError.failed` 取得。
- **多个失败时取哪个退出码**：第一个、最后一个，或只在唯一且一致时转发，公开材料都没有约定，应视为都可接受。
- **是否额外输出错误说明、是否更新 `Run` docstring 或 changelog 片段**：都不是必需的。
- **是否把转发扩展到其它命令（R10）**：题面没有要求也没有禁止。这会扩大行为范围，公开测试没有覆盖。
- **命名**：不需要新增公共接口，公开材料也没有约定新名字。

以下做法不合理，或有明确风险：

- **把 Python API 的默认异常改成 `CommandError`**，或让 stop 模式在 Python 下不再抛 `IncompleteResultsError`。这与 `test_run.py:149-158`、`test_rerun.py:314-315, 346-348` 以及 `common_opts.py:359-362` 的文档冲突。
- **在 `--on-failure ignore` 下也强制非零退出。** 这与 CLI 帮助文案 `common_args.py:95-99` 冲突。
- **对缺字段的失败记录处理不当导致崩溃。** 输入缺失产生的 `action="run"` 错误记录没有 `exit_code` 和 `run_info`（`run.py:493-496`）；`CommandError.code` 默认为 `None`（`datalad/runner/exception.py:31-44`）。实现需要能回退到 1；如果异常处理器本身再抛异常，退出行为会失控。
- **通过 Python 层 `sys.stderr` 输出信息（推断的约束，题面未明示）。** 判分如果像示例那样使用 `run_main`（`test_main.py:53-98`），它会 patch `sys.stdout` 和 `sys.stderr`，默认 `expect_stderr=False` 要求被 patch 的 `sys.stderr` 为空。经 `os.write(2, …)` 输出（现有 `_communicate_commanderror` 的做法）或经日志输出都不受影响：日志 handler 在导入时已绑定原始 stderr（`datalad/log.py:634, 689`）。但 `print(..., file=sys.stderr)` 或 `sys.stderr.write` 会让这种断言失败。
- **为了让示例原样可运行而补导入路径**，即把 `run_main` 加进 `datalad.api`、把 `create` 加进 `datalad.utils`、把 `chpwd` 加进 `datalad.support.gitrepo`。这不是题目需求。尤其是把测试辅助函数引入 `datalad.api`，会让生产 API 依赖 tests 模块和 pytest。
- **修改测试文件。** public_hints 禁止修改测试文件；`run_main` 位于测试文件 `datalad/cli/tests/test_main.py`，只能调用，不能改。
- **使用 Python 3.10+ 语法。** 解释器是 Python 3.9.21（`environment_brief.md:10`）。
- **在测试中触发 datalad 自身的弃用警告。** `tox.ini:69-71` 的 `[pytest]` 配置含 `error::DeprecationWarning:^datalad`，这类警告会让测试报错。例如不要导入已弃用的 `datalad.interface.utils.eval_results`（`interface/utils.py:220-226`）或 `datalad.cmdline.main`（`datalad/cmdline/main.py:14-17`）。

## 3. 题面质量与初态线索

### 3.1 题面是否给出或暗示修法

- 题面没有给出修复代码或修复位置，也没有提到 `IncompleteResultsError`、`exit_code` 字段或 `datalad/cli/main.py`。
- 示例写成测试的形态（`run_main([...], exit_code=3)`），暗示判分很可能调用进程内 `main()` 并断言 `SystemExit.code`。这是关于测试形态的线索，不是修法泄露。

### 3.2 题面描述的行为能否从 base 读出

- 能，推理链见 §1.1。
- **这个行为是 0.16.0 有意引入的。** `CHANGELOG.md:1191`（位于 0.16.0 的 "Deprecations and removals" 小节，标题分别在 1121 和 1172 行）和 `docs/source/changelog.rst:2422-2436` 明确写着：`run` 不再抛 `CommandError`，CLI 退出码不再转发底层命令的退出码，但失败时仍然非零；Python API 的异常从 `CommandError` 改为 `IncompleteResultsError`。题面把退出 1 当作 bug，实际是要求恢复转发。
- **仓库文档自相矛盾。** `Run` docstring（`run.py:105-109`）仍说失败时会抛出"带相同退出码的 `CommandError`"；CLI 设计文档 `cli.rst:54-78` 把"内部 shell 命令失败"列为转发退出码的一类，但 run 的失败实际落在"结果不完整（退出 1）"一类。题面的要求与 docstring 和 cli.rst 一致，与 0.16.0 changelog 相反。题面没有交代这段历史，也没有说明 Python API 是否要改回 `CommandError`；现有公开测试要求不改（R6）。

### 3.3 示例在 base 接口下是否说得通

示例不能原样运行，三处导入在 base 里都不存在：

- `from datalad.api import run_main`：`datalad/api.py:11-12` 只执行 `from datalad.coreapi import *` 并动态加入扩展命令，没有 `run_main`。`run_main` 是测试辅助函数，定义在 `datalad/cli/tests/test_main.py:53`。
- `from datalad.utils import create`：`datalad/utils.py` 里没有 `create`。`create` 来自 `datalad.api`（见 `test_main.py:20-23`）。
- `from datalad.support.gitrepo import chpwd`：`datalad/support/gitrepo.py:97-110` 从 `datalad.utils` 导入的名字里没有 `chpwd`。`chpwd` 定义在 `datalad/utils.py:1743`，`test_main.py:47` 正是从这里导入。

其它问题：

- `execute_run_command()` 定义了但没有被调用。
- 固定路径 `/tmp/test_dataset` 在重复执行时，`create` 会因目标已经是数据集而失败。
- `annex=False` 让复现不依赖 git-annex，与 `test_main.py:310` 的用法一致。

示例的意图可以恢复：改成 `from datalad.api import create`、`from datalad.utils import chpwd`、`from datalad.cli.tests.test_main import run_main`，就是一个合理的复现（§4 的 C2）。

### 3.4 复现与调查入口

- `grep -rn run_main` 可以直接找到 `test_main.py:53`。相关代码位置：
  - CLI 退出码映射集中在 `datalad/cli/main.py:184-235`；
  - run 的失败记录在 `run.py:1061-1082`；
  - 失败汇总和抛出异常在 `interface/utils.py:390-396` 与 `interface/base.py:939-942`；
  - `IncompleteResultsError` 定义在 `datalad/support/exceptions.py:499-526`。

  正常读代码即可定位，不需要额外信息。
- **注意入口**：`datalad/__main__.py` 不是 CLI 入口，它是 `-m datalad` 的 FUSE 式辅助程序。CLI 入口是 console script `datalad=datalad.cli.main:main`（`setup.py:127-129`）。用 `python -m datalad run …` 复现会走错入口。

### 3.5 初态

- `worktree_manifest.json` 中 `initial_diff.bytes = 0`，即镜像初态相对 base 没有改动。未跟踪文件中 `run_tests.sh` 已包含，`install.sh` 缺失。
- `run_tests.sh` 执行 `.venv/bin/python -W ignore -m pytest -rA r2e_tests`。`r2e_tests/` 不在工作树中（manifest 标注隐藏测试未包含），解题者直接运行它大概率会报路径不存在，不能用来验证。
- `r2e_tests/` 位于仓库根，不在 `datalad/` 下。`datalad/conftest.py` 的会话夹具（临时 HOME 或 `GIT_CONFIG_GLOBAL` 加 git 身份，`conftest.py:86-136`）是否作用于隐藏测试，公开材料看不出来。

### 3.6 缺失信息的影响

真正可能阻碍开发的：

1. **git 提交身份**：在 pytest 之外独立复现时需要 git 身份。brief 已说明 HOME 里没有身份，而 `create` 需要提交。
2. **git-annex**：brief 没说明是否安装。多数公开 run 测试使用默认的 `Dataset(path).create()`，会建 annex 仓库，因此受影响；`annex=False` 的核心复现不受影响。
3. **datalad 安装方式与 console script**：`.venv` 里 datalad 是否以 editable 方式安装、`datalad` console script 是否存在，都没有说明。只影响子进程式复现，以及 `test_main.py` 里调用外部 `datalad` 的测试（`test_script_shims` 259-285 行、`test_cfg_override` 288-344 行）。

只需正常读代码即可解决的：失败记录的字段、on_failure 流程、CLI 异常处理器中各分支的顺序。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | environment_brief.md 支持到哪一层 | 缺口 | 命令 |
|---|---|---|---|---|
| Python 解释器与已装依赖（只做纯 Python 修改，不需要新包） | public_hints；`requirements.txt` | 明示：`python` 指向 `/testbed/.venv/bin/python`（3.9.21），没有 pip/uv，不能出网（brief 第 10-11 行） | datalad 是否 editable 安装；`install.sh` 缺失 | C0 |
| git 可执行文件 | `conftest.py:125`；所有数据集操作 | 隐含（brief 第 13 行提到 git 身份） | 未显式确认 git 存在及版本 | C0 |
| git 提交身份 | `create` 需要提交；`datalad/config.py:1155-1167` 缺身份时只发警告 | 明示：HOME 没有 user.name/email，需在命令里临时指定（brief 第 13 行） | pytest 下由 `datalad/conftest.py:86-136` 提供；独立脚本需要设置 `GIT_AUTHOR_*` / `GIT_COMMITTER_*` 环境变量 | C1、C2、C5 |
| git-annex | 公开 run 测试默认建 annex 数据集；`CONTRIBUTING.md:139, 159` | 未说明 | 是否可用未知 | C0、C4 |
| `datalad` console script | `setup.py:127-129`；`test_main.py:259-285, 288-344`；`CONTRIBUTING.md:255-268`（需 develop 安装才生成入口脚本） | 未说明 | 是否在 PATH 上、是否指向 `/testbed` 源码，都未知 | C0、C5 |
| 进程内 CLI 复现（主判别手段） | 题面示例；`cli/main.py:61-143`；`test_main.py:53-98` | 足够（只需纯 Python 和 git） | 需要 git 身份 | C1、C2 |
| 公开回归测试 | `test_main.py`、`test_run.py`、`test_rerun.py`；`tox.ini:69-71` 的 `[pytest]` 配置 | 支持 `python -m pytest`（public_hints） | 部分测试依赖 git-annex 或 console script；建议改动前先跑一次基线 | C3、C4 |
| 资源 | — | 2 CPU / 4 GiB，`/tmp` 1 GiB（brief 第 12 行） | 临时数据集放在 `/tmp`，体积很小 | — |

### 命令（全部为建议，未执行；在 `/testbed` 下原样运行）

**C0 环境核对**

```bash
cd /testbed && python -c "import sys, datalad; print(sys.executable); print(datalad.__file__)"; (cd / && python -c "import datalad; print('import outside /testbed ->', datalad.__file__)"); git --version; command -v git-annex || echo "no git-annex on PATH"; command -v datalad || echo "no datalad console script on PATH"
```

预期输出，逐项解读：

1. 解释器路径为 `/testbed/.venv/bin/python`，模块路径为 `/testbed/datalad/__init__.py`。
2. 在 `/testbed` 之外导入时：
   - 仍显示 `/testbed/datalad/__init__.py`：datalad 是 editable 安装，console script 会用到改动。
   - 显示 site-packages 路径：子进程和 console script 不会用到改动。
   - 报 ImportError：venv 里没有安装 datalad。
3. 输出 git 版本号。
4. 输出 git-annex 的路径，或提示不存在。
5. 输出 `datalad` console script 的路径，或提示不存在。

**C1 进程内 CLI 复现（主判别命令，同时覆盖 R2/R4/R7）**

```bash
cd /testbed && GIT_AUTHOR_NAME=tester GIT_AUTHOR_EMAIL=tester@example.com GIT_COMMITTER_NAME=tester GIT_COMMITTER_EMAIL=tester@example.com python - <<'EOF'
import sys, tempfile
sys.path.insert(0, "/testbed")
from datalad.api import create
from datalad.cli.main import main
d = tempfile.mkdtemp(prefix="dl-exit-")
create(dataset=d, annex=False, result_renderer="disabled")
cases = [
    ["run", "--explicit", "exit 3"],
    ["run", "exit 3"],
    ["run", "--explicit", "exit 0"],
    ["run", "--explicit", "-i", "does-not-exist", "exit 3"],
    ["--on-failure", "ignore", "run", "--explicit", "exit 3"],
]
for args in cases:
    try:
        main(["datalad", "-C", d] + args)
    except SystemExit as e:
        print("ARGS", args, "EXIT", e.code, flush=True)
EOF
```

各用例在修复前后的预期 `EXIT`（中间会夹有 `run(error): … [exit 3]` 之类的结果行）：

| 用例 | 修复前 | 修复后 | 依据 |
|---|---|---|---|
| `run --explicit 'exit 3'` | 1 | 3 | 明示 |
| `run 'exit 3'` | 1 | 3 | 可推知 |
| `run --explicit 'exit 0'` | 0 | 0 | 保留 |
| `run --explicit -i does-not-exist 'exit 3'` | 1 | 1 | 推断：输入缺失时 stop 模式不执行命令，失败记录没有 `exit_code` |
| `--on-failure ignore run --explicit 'exit 3'` | 0 | 0 | 推断：依据 `--on-failure` 的帮助文案；题面未涉及 |

**C2 与题面示例一致的复现（可选；同时检查 Python 层 stderr 为空）**

```bash
cd /testbed && GIT_AUTHOR_NAME=tester GIT_AUTHOR_EMAIL=tester@example.com GIT_COMMITTER_NAME=tester GIT_COMMITTER_EMAIL=tester@example.com python - <<'EOF'
import sys, tempfile
sys.path.insert(0, "/testbed")
from datalad.api import create
from datalad.utils import chpwd
from datalad.cli.tests.test_main import run_main
d = tempfile.mkdtemp(prefix="dl-exit-")
create(dataset=d, annex=False, result_renderer="disabled")
with chpwd(d):
    run_main(["run", "--explicit", "exit 3"], exit_code=3)
print("run_main(exit_code=3) passed")
EOF
```

- 修复前：`test_main.py:83` 的 `assert_equal(cm.value.code, exit_code)` 失败，AssertionError（1 != 3）。
- 修复后：输出 `run_main(exit_code=3) passed`。
- 如果修复后改为在 stderr 比较处失败，说明实现经 Python 层 `sys.stderr` 写了内容。
- 如果在 pytest 之外无法导入测试模块，以 C1 为准。

**C3 CLI 既有退出码回归（不需要 git-annex）**

```bash
cd /testbed && python -m pytest -q datalad/cli/tests/test_main.py -k "usage_on_insufficient_args or subcmd_usage_on_unknown_args or incorrect_cfg_override or incorrect_option"
```

预期共 7 项（`test_incorrect_option` 有 4 个参数化用例），修复前后都应全部通过。

**C4 Python API 行为保留（需要 git-annex）**

```bash
cd /testbed && python -m pytest -q datalad/core/local/tests/test_run.py -k "test_basics or test_run_cmdline_disambiguation"; python -m pytest -q datalad/local/tests/test_rerun.py -k "test_run_failure"
```

- 修复前后都应通过：默认 stop 时仍抛 `IncompleteResultsError`，`on_failure="ignore"` 时返回 error 记录，CLI 参数消歧义仍经 `SystemExit` 结束。
- 如果没有 git-annex，这些测试在修复前后都会在 `Dataset(path).create()` 处报错。这属于环境缺口，不是回归，所以建议改动前先跑一次记录基线。

**C5 console script 子进程路径（可选；仅当 C0 显示脚本存在且指向 `/testbed` 源码时才有意义）**

```bash
cd /testbed && d=$(mktemp -d) && GIT_AUTHOR_NAME=tester GIT_AUTHOR_EMAIL=tester@example.com GIT_COMMITTER_NAME=tester GIT_COMMITTER_EMAIL=tester@example.com datalad create --no-annex "$d" && datalad -C "$d" run --explicit 'exit 3'; echo "exit=$?"
```

- 修复前预期输出 `exit=1`，修复后 `exit=3`。
- 如果 `datalad create` 失败，`$?` 是 create 的退出码，不能用来判断修复。

以上命令会在 `/tmp` 留下小的临时数据集（`/tmp/dl-exit-*`、`/tmp/tmp.*`），可以手动删除。

## 5. 阅读范围

实际打开的文件：

- **角色卡**：`public_reader_r2e.md`。
- **PUBLIC_DIR 顶层**：
  - `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`：全文。
  - `worktree_manifest.json`：只看了开头、结尾和键列表，没有打开其中指向 PUBLIC_DIR 以外的路径（`initial_diff.source`、`untracked_included.*.origin`）。
- **worktree 全文**：
  - `run_tests.sh`
  - `datalad/cli/main.py`
  - `datalad/cli/exec.py`
  - `datalad/cli/tests/test_main.py`
  - `datalad/core/local/run.py`
  - `datalad/core/local/tests/test_run.py`
  - `datalad/runner/exception.py`
  - `datalad/api.py`
  - `docs/source/design/cli.rst`
  - `datalad/cmdline/main.py`
  - `tox.ini`、`pyproject.toml`、`setup.cfg`
  - `changelog.d/pr-7645.md`、`changelog.d/pr-7649.md`
- **worktree 片段或 grep**：
  - 接口层：`datalad/interface/base.py:660-960`、`datalad/interface/utils.py:1-460`、`datalad/interface/results.py:1-150`、`datalad/interface/common_opts.py:340-377`
  - 异常与执行器：`datalad/support/exceptions.py`（grep 及 499-536 行）、`datalad/runner/runner.py:90-250`
  - CLI 其它模块：`datalad/cli/common_args.py:70-110`、`datalad/cli/parser.py`（grep 及 560-606 行）、`datalad/cli/helpers.py`（grep）
  - 测试：`datalad/local/tests/test_rerun.py`（grep 及 300-349 行）、`datalad/tests/test_cmd.py:160-215`、`datalad/support/tests/test_sshrun.py:30-50`、`datalad/cli/tests/test_exec.py` / `test_utils.py` / `test_helpers.py`（grep）
  - run 相关命令：`datalad/local/rerun.py:500-560`、`datalad/local/run_procedure.py:450-490`、`datalad/core/local/create.py`（grep）
  - 工具与配置：`datalad/utils.py`（grep）、`datalad/support/gitrepo.py:1-135`（导入部分）、`datalad/log.py`（grep 及 600-660 行）、`datalad/config.py:1140-1175`、`datalad/conftest.py:1-200`、`datalad/tests/utils_pytest.py`（导入部分及 grep）
  - 入口与安装：`datalad/__main__.py`（开头部分）、`setup.py`（entry points）
  - 文档：`CHANGELOG.md`（grep、版本标题、1191 行）、`docs/source/changelog.rst:2154, 2418-2436`、`docs/source/design/result_records.rst:60-110`、`docs/source/design/provenance_capture.rst:30-70`、`CONTRIBUTING.md`（grep 及 130-165、255-275 行）

只用本地只读命令（ls/grep/sed/cat）查看了公开包，另用系统 `python3` 解析过 manifest 的 JSON 键。

没有查看的范围：

- 隐藏测试（`r2e_tests/`）和 `install.sh`，二者都不在包内；
- `.venv` 及其中已安装的包，`.git`；
- 其它命令（get/push 等）失败路径的细节，`datalad/ui/*` 的内部实现，扩展入口；
- 其它题的公开包，以及任何私有材料、gold 补丁、旧审查结论。

两个限制需要保留：

- `user_prompt.txt` 只是 `render_user_prompt` 的静态渲染，不是捕获到的实际模型消息；
- `worktree/` 不是完整的运行容器。

因此本报告没有验证模型实际收到的消息、运行资源、git/git-annex/console script 是否可用，也没有验证任何开发条件。§4 的预期结果都来自静态推断。

**关键未知项**：

1. 隐藏测试的形态：是进程内 `main()`/`run_main` 还是子进程；是否断言 stderr；位于 `r2e_tests/` 时是否有 git 身份夹具。
2. 多失败、`--on-failure continue`、rerun 等情形下的退出码语义（R8、R10）。
3. 镜像里是否有 git-annex 和 `datalad` console script，datalad 是否 editable 安装。
