# coveragepy `ea6906b0` 修订方案（R-c）

2026-09-29 · 修订执行者（Claude，单题闭环试行，统一标准 v1 §5 预授权模板）。

**状态：修订草案已在新派生镜像上试跑，验收全部符合预期；待 Codex 复核。** 正式修订单、pins 与派生镜像材料步骤由协调者落地。试跑工具不是正式评分，差别见 §6。

路径约定（均相对仓库根）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/`，其中 `PUB/worktree/` 就是解题者的 `/testbed`；
- `PRIV` = 同题的 `v3/private/` 目录；
- `CANDS` = `runs/r2e_actor_20260925/grader_cands/`；
- `trials/` = 本目录下的试跑结果。

## 0. 结论

- **模板与范围**：R-c，一轮修订。新增一个隐藏测试文件 `r2e_tests/test_2.py`（修订类别 `hidden_test_file_add`），`test_1.py` 不动。期望映射由 46 键变为 48 键，新增的两个键如下：
  1. `HtmlGitignoreTest.test_html_report_is_ignored_by_git`：生成报告后，用真实 git 判断报告文件是否都被忽略。用来关住 C-B（只写一个空 `.gitignore`）。
  2. `ReportingTest.test_no_data_to_report_on_html`：从公开旧测试 `tests/test_coverage.py:1843-1848` 原样搬入。用来关住 RE（没有数据时也提前建出输出目录）。
- **试跑结果**：
  - 新派生镜像 `sha256:ac0f9340…`，配方 `r2e_derive_v1+sysconfig_v1`。当前材料下 noop 为 mismatch、gold 为 match，环境正常。
  - 修订后：gold 得 1；合理替代解 C-A 得 1；noop 得 0。
  - C-B、RE 在当前材料下都得 1，修订后都得 0，而且各自只在对应的新键上失败。
  - C-C（公开可见的替身约束对照）仍然是 0，失败的正是原来那 7 个键。
- **新增的评分依赖**：评分时需要能执行 `git`。试跑中评分用户能用 git，正式评分环境仍需确认，见 §6。

## 1. 缺口与公开依据

| # | 缺口 | 触发反例（09-25，当前材料，正式评分） | v1 §4 | 公开依据 |
|---|---|---|---|---|
| H1 | 目标断言只检查 `htmlcov/.gitignore` 是否存在（`PRIV/hidden_tests/test_1.py:147`，经 `tests/coveragetest.py:276-279` 的 `os.path.exists`），不检查它是否真的让 git 忽略了报告 | C-B 只写一个空的 `.gitignore`，得 1，46/46（`runs/r2e_actor_20260925/grader/ledger_cea69_CB_empty_gitignore.jsonl`）。09-25 的语义对照显示：`.gitignore` 为 0 字节，`htmlcov/` 下有 9 个文件未被忽略 | 第 3 步：写出空产物的退化候选得 1（v1 §10 第一行就是这个例子） | 题面期望行为（`PUB/user_prompt.txt:26`）："The HTML output directory should contain a `.gitignore` file that ignores all its contents, preventing Git from tracking the generated static files." |
| H2 | "没有数据时不建输出目录"这一公开旧行为不在隐藏集里 | RE 在 `report()` 开头执行 `ensure_dir` 并写 `.gitignore`，得 1（`ledger_cea69_RE_gitignore_before_data_check.jsonl`）。09-25 的对照显示：命令报 `No data to report.`、rc=1，但 `htmlcov/` 已经建出来了；公开旧测试在 RE 下 FAILED（`runs/r2e_actor_20260925/grader/private_public_b2/cea69_pt_*.json`） | 第 4 步：破坏了有公开测试的常用旧行为 | 公开旧测试 `PUB/worktree/tests/test_coverage.py:1843-1848`。注释写 "Reporting with no data produces a nice message and no output directory."，断言是 `assert_doesnt_exist("htmlcov")` |

## 2. 具体改动

- **新文件** `r2e_tests/test_2.py`。按草案生成的文件 sha256 为 `f29c0497…`。
- **不改** `r2e_tests/test_1.py`，sha256 仍是 `e590d036…`。
- **全文如下**（精确内容见 `revision_draft.json`）：

```python
# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""R2E revision tests (2026-09-29) for the .gitignore in the HTML report directory.

HtmlGitignoreTest: the generated .gitignore really makes git ignore the report files.
ReportingTest.test_no_data_to_report_on_html: copied unchanged from the public
tests/test_coverage.py (no data: a nice message, and no output directory).
"""

import os
import subprocess

import pytest

import coverage
from coverage.exceptions import CoverageException

from tests.coveragetest import CoverageTest


def run_git(*args):
    """Run git in the current directory, isolated from user and system config."""
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["HOME"] = os.getcwd()
    for name in ("XDG_CONFIG_HOME", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    return subprocess.run(
        ["git"] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, env=env,
    )


class HtmlGitignoreTest(CoverageTest):
    """The .gitignore in the HTML output directory makes git ignore the report."""

    def test_html_report_is_ignored_by_git(self):
        init = run_git("init", "-q", ".")
        assert init.returncode == 0, init.stderr
        self.make_file("main_file.py", """\
            import helper1
            helper1.func1(12)
            """)
        self.make_file("helper1.py", """\
            def func1(x):
                if x % 2:
                    print("odd")
            """)
        cov = coverage.Coverage()
        self.start_import_stop(cov, "main_file")
        cov.html_report(directory="report_out")

        report_files = [f for f in os.listdir("report_out") if f != ".gitignore"]
        assert "index.html" in report_files
        status = run_git("status", "--porcelain", "--untracked-files=all", "--", "report_out")
        assert status.returncode == 0, status.stderr
        not_ignored = sorted(
            line[3:] for line in status.stdout.splitlines()
            if line[3:] != "report_out/.gitignore"
        )
        assert not_ignored == []


class ReportingTest(CoverageTest):
    """Tests of some reporting behavior."""

    def test_no_data_to_report_on_html(self):
        # Reporting with no data produces a nice message and no output
        # directory.
        with pytest.raises(CoverageException, match="No data to report."):
            self.command_line("html -d htmlcov")
        self.assert_doesnt_exist("htmlcov")
```

**设计说明**

- **判定方式用真实 git 的行为**：在临时仓库里执行 `git init`，再用 `git status --porcelain --untracked-files=all -- report_out` 看哪些文件仍会被跟踪。这与题面 "preventing Git from tracking" 的说法一致。
- **不规定 `.gitignore` 的具体内容**：`*`、`/*`、`**`、带注释的写法都能通过。
- **不检查 `.gitignore` 自身是否被忽略**，所以 `*` 加 `!.gitignore` 的写法也能通过。题面没有规定这个细节，不在这里下判断。
- **输出目录用非默认的 `report_out`**：题面说的是 "The HTML output directory"，示例里的 `htmlcov` 只是一个例子。写死 `htmlcov` 的实现会在这里失败。这是同一要求的非示例实例（与 v1 §4 第 2 步的做法一致），不是新增要求。
- **git 调用与用户、系统配置隔离**：设 `GIT_CONFIG_NOSYSTEM=1`，让 `HOME` 指向测试临时目录，并去掉 `XDG_CONFIG_HOME`、`GIT_DIR` 等变量，避免全局 excludes 文件影响判定。仓库建在 `CoverageTest` 的临时目录里，属主就是运行测试的评分用户，不会触发 `safe.directory` 检查。
- **不引入新的实现约束**：新测试不经过 `HtmlDeltaTest` 的 `coverage.html.open` 替身（`test_1.py:99-137`）。已有的 `open(..., encoding=...)` 约束（即 C-C）不变。
- **类名**：以 `Test` 结尾，符合 `PUB/worktree/setup.cfg:6` 的 `python_classes = *Test`。与 `test_1.py` 的类名（HtmlDeltaTest、HtmlTitleTest、HtmlWithUnparsableFilesTest、HtmlTest、HtmlGoldTest、HtmlWithContextsTest）不重名。
- **第二个测试逐字取自公开测试**：类名、docstring、注释与断言都相同。只搬了这一个方法，没有搬同一个类里 annotate 和 xml 的两个方法（与本题无关）。

## 3. 期望映射的逐键变化

| 键 | 修订前 | 修订后 |
|---|---|---|
| `HtmlGitignoreTest.test_html_report_is_ignored_by_git` | 无 | PASSED（新增） |
| `ReportingTest.test_no_data_to_report_on_html` | 无 | PASSED（新增） |
| 其余 46 键 | PASSED | 不变 |

修订后的完整映射见 `revision_draft.json` 的 `expected_after`。父版本 `PRIV/expected_output.json` 的 sha256 为 `7ab45968…`。

## 4. 验收计划与试跑结果

**运行条件**：
- 镜像 `sha256:ac0f93404ee941081735bff14e9e89ae99a64bb2061a8fe5f4ed3d326caae9e1`，配方 `r2e_derive_v1+sysconfig_v1`；
- 以评分用户 uid 54322 运行，不联网，`HOME=/tmp`；
- 每个候选跑 1 次，测试段约 5–8 秒。

| 候选 | 补丁 | 应得分 | 应失败的键 | 试跑结果 | 文件 |
|---|---|---|---|---|---|
| 环境确认：noop（当前材料） | — | 0 | 6 个目标键 | mismatch，正是这 6 个键；原因是 `File 'htmlcov/.gitignore' should exist` | `trials/env_noop_current.json` |
| 环境确认：gold（当前材料） | `PRIV/gold.patch` | 1 | — | match，46/46 | `trials/env_gold_current.json` |
| gold（正对照） | `PRIV/gold.patch` | 1 | — | match，48/48 | `trials/rev_gold.json` |
| noop | — | 0 | 6 个目标键加 git 键；无数据键应通过（base 本来就不建目录） | mismatch，正是这 7 个键。git 键的失败原因是 `assert [...] == []`，列出 9 个未被忽略的文件，第一个是 `report_out/coverage_html.js` | `trials/rev_noop.json` |
| C-A：合理替代（只在原本为空的目录里写入 `*`） | `CANDS/coveragepy_ea69_CA_only_if_dir_was_empty.patch` | 1 | — | match，48/48 | `trials/rev_CA.json` |
| C-B：空 `.gitignore`（原先得 1） | `CANDS/coveragepy_ea69_CB_empty_gitignore.patch` | 0 | git 键 | mismatch，只有 git 键 | `trials/rev_CB.json` |
| RE：数据检查前就写入（原先得 1） | `CANDS/coveragepy_ea69_RE_gitignore_before_data_check.patch` | 0 | 无数据键 | mismatch，只有无数据键；原因是 `AssertionError`，即预期的异常已抛出，但目录已经存在 | `trials/rev_RE.json` |
| C-C：gold 加 `encoding=`（原先得 0，公开替身约束对照） | `CANDS/coveragepy_ea69_CC_gold_with_encoding.patch` | 0 | 与 09-25 相同的 7 个 `HtmlDeltaTest` 键 | mismatch，正是这 7 个键（`TypeError: open() got an unexpected keyword argument 'encoding'`），两个新键都通过 | `trials/rev_CC.json` |

**C-B 失败原因的证据级别**：
- 试跑结果只保留了日志末尾 8000 字符，其中只有 `FAILED r2e_tests/test_2.py::HtmlGitignoreTest::test_html_report_is_ignored_by_git` 这一行，没有断言详情。
- "失败在 `not_ignored == []` 这一断言"属于推断，依据有三：
  - 同一镜像、同一身份下，gold 和 C-A 都通过了同一个测试，说明 git 本身可用；
  - C-B 与 gold 唯一的差别是 `.gitignore` 为空；
  - 09-25 的语义对照显示，C-B 下有 9 个文件未被忽略。
- 如需直接证据，正式评分时保留完整日志即可。

**对照 v1 §5 的 R-c 验收**：
- 正对照为 1、noop 为 0：满足。
- 本次要纠正的误判已被纠正：C-B、RE 由 1 变为 0，而且各自只在对应的新键上失败。
- 已知相关的错误候选仍为 0：C-B、RE、C-C 都是 0。
- 合理替代解没有被误拒：C-A 得 1。
- 公开核心要求有直接断言：见 §5。
- 新版本、父版本、理由与触发反例：见本文与 `revision_draft.json`。
- Codex 复核：待做。

## 5. 修订后仍受保护的公开要求

| 公开要求 | 断言 |
|---|---|
| 输出目录里有 `.gitignore` | 6 个 `HtmlDeltaTest` 目标键（未改） |
| `.gitignore` 让 git 忽略全部报告文件 | 新增的 git 键 |
| 没有数据时报错，且不建输出目录 | 新增的无数据键；报错文字另有 `HtmlWithUnparsableFilesTest.test_dothtml_not_python` 覆盖 |
| 原有页面、静态文件、增量写入、返回值 | 原 40 个回归键（未改） |

## 6. 与正式评分的差别、风险与未做

- **git 依赖**：
  - 试跑用的是 `docker exec -u 54322:54322 -e HOME=/tmp`，PATH 继承镜像的默认值。
  - 正式评分给评分用户的环境与 PATH 也必须能找到 `git`。定稿后跑正式 gold 即可确认。
  - 如果找不到，gold 会在 git 键上失败，问题会被暴露出来，不会静默放过。
  - 按 v1 §6，这类"只在评分侧使用的工具"记录在案即可。
- **试跑工具与正式评分的差别**（见 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py` 文件头）：
  - 不做基线重建比对；
  - 不核对隐藏测试树与入口摘要；
  - 权限布置经过简化。

  所以定稿后要按正式材料重跑正式评分的 gold 和 noop，并至少再跑 C-B、RE 中的一个。
- **仍未覆盖、不属于本次修订的已登记项**：
  - gold 会无条件覆盖用户已有的 `.gitignore`（低，见 09-25 审查卡 §4）；
  - CLI 路径 `coverage html -d`；
  - 成功时 stdout 不应多出消息（公开 `tests/test_process.py`、`tests/test_plugins.py` 中有相应测试）。
- **稳定性**：每个候选只跑了 1 次。git 判定是确定性的；新测试不依赖时间或网络。

## 7. 边界自查

- **没有扩大需求**：两处新断言分别来自题面第 26 行和一条公开旧测试，没有要求任何具体的 `.gitignore` 内容或写入位置。
- **没有为保住 gold 而放宽**：没有删改任何原有断言。
- **没有复制 gold 的输出当期望**：`.gitignore` 的内容没有被钉成 gold 写的 `"# Created by coverage.py\n*\n"`。
- **没有越界改动**：没有改题面，没有改生产代码，也没有写 `s2_r2e` 下的正式修订单和 pins。
