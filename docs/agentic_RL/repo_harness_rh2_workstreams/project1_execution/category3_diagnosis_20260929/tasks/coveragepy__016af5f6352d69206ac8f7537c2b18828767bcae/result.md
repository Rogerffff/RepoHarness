# R2E coveragepy__016af5f6：第3类质量调查结果

2026-09-29 / Claude（云端，第3类负责人）。原分类：第3类“题目质量调查未完成”。R2E 线的公开读者稿已经保存（[public_read.md](../../../r2e_lifecycle_20260929/results/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/public_read.md)），但文中提到的 `commands.json` 缺失，主审和独立复核都还没做。

**结论（主审）：问题和修法已明确，建议转第2类。** 共三项：

- **P4，已实跑确认**：题面原例照抄在 base 上不崩溃。
- **两个 S1**：
  - 只修行覆盖路径的候选能得 1，但在分支覆盖模式下仍会崩溃；
  - 跳过所有非 ASCII 文件名的候选能得 1，但会丢掉可编码的 `café.py`。
- **修法**：R-f 修正示例；R-c 在原测试函数内补三处检查。gold 仍作正对照。

公开读者担心的“隐藏测试只接受跳过或转换中的一种”已消除：两类做法都能通过。独立复核待做。

## 1．公开要求与既有证据

题面要求：文件名不能按 UTF-8 编码时，`Coverage.save()` 不应抛 `UnicodeEncodeError`，“either by skipping them or handling the encoding error internally”。

环境记录：09-24 T0-1 修订 `r2e-mr-001` 把一个因来源宿主机缺 mock 而误记为 FAILED 的键改为 PASSED，状态为 `qualified_with_revision`，gold 15/15。gold 在 `inorout.check_include_omit_etc` 中返回“不跟踪”，理由是 `non-encodable filename`。

## 2．私有实测

- 源镜像：`namanjain12/coveragepy_final@sha256:71895ed4…5a39`，与冻结摘要一致。
- 方式：root、断网、一次性容器。隐藏测试取自镜像 `/r2e_tests`（`test_1.py` 的 sha256 为 `72b69833…`，与评分包一致）。
- **私有评分**：复制到 `/testbed/r2e_tests`，运行评分包里的 `run_tests.sh`，按 `pytest -rA` 结果逐键对照评分包的期望映射（15 键，含 `r2e-mr-001`）。这是按同一命令和期望映射做的**私有模拟**，不是 R2E 正式评分链。

| 版本 | 题面原例照抄 | 修正后复现：行覆盖／分支覆盖 | 可编码的 `café.py` 是否保留 | 原隐藏测试（私有评分） | 公开测试（175 项） |
| --- | --- | --- | --- | --- | --- |
| base | **不崩溃**，只测到脚本本身 | 两种模式都崩溃 | — | 0（仅目标键 FAILED） | 全过 |
| gold（在跟踪决策处跳过） | 不崩溃 | 都正常 | 保留 | **1** | 全过 |
| `skip_write`（写数据时跳过） | 不崩溃 | 都正常 | 保留 | **1** | 全过 |
| `convert`（转义后存储，文件名保留在数据中） | 不崩溃 | 都正常 | 保留 | **1** | 全过 |
| `lines_only`（只在 `add_lines` 跳过） | 不崩溃 | 行正常，**分支崩溃** | 保留 | **1** | 全过 |
| `ascii_only`（跳过所有非 ASCII 名） | 不崩溃 | 都正常 | **丢失** | **1** | 全过 |
| `catch_save`（在 `save()` 外层吞异常） | 不崩溃 | `get_data()` 仍崩溃 | — | 0 | 全过 |

说明：
- 公开测试为 `tests/test_data.py`、`test_api.py`、`test_oddball.py::ExecTest`、`test_files.py`，使用 `-o addopts=''`。第一次按 `-n 0` 运行时，因 `setup.cfg` 的 addopts 冲突而未执行，这是命令问题，不是题目问题，已按 R2E 线的已验写法重跑。
- 隐藏的 `test_unencodable_filename` 只断言两点：`save()` 不崩溃；执行 exec 的 `bug891.py` 仍被记录。它**不检查** `\udcff.py` 是否留在数据里，所以跳过和转换两类实现都被接受。

## 3．判定（v1 §3–§4）

- **P4（已实跑确认）**：示例的 `exec(compile(..., "\udcff.py", ...))` 在 `cov.start()` 之前执行；测量期间只有文件名为 `<string>` 的代码，这类代码不被跟踪，所以照抄不会崩溃。这是题面对 base 行为的错误陈述，按用户对普通探针的口径（参照 mypy15184 已转第2类的处理），应中性修正，不能留给模型自己发现。
- **§4 第 4 步（S1），两例**：
  - `lines_only` 得 1，但在分支覆盖模式（公开的常用模式 `--branch`）下 `save()` 仍崩溃，违反了同一核心要求的另一个实例；
  - `ascii_only` 得 1，但丢掉可编码的非 ASCII 文件名的测量数据。题面只允许跳过“无法编码”的文件，这属于常用行为回归。
- **§4 第 2 步（D1 严格版）**：原断言只用了题面示例的文件名 `\udcff.py`，属于示例字面值，需要补一个非示例实例。
- **误拒风险（公开读者 A1）已消除**：两类合理做法都通过。

## 4．修法（交第2类，走 R2E 已有的材料修订机制）

**R-c：`hidden_test_text_replace`**

- 修订后文件为 [`hidden_test_1_revised_v1.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/cov016/hidden_test_1_revised_v1.py)，sha256 `c7f272d5…`，原文件 `72b69833…`。
- 在原 `test_unencodable_filename` 末尾追加一段：以 `branch=True` 运行一个 exec 了 `caf\xe9.py` 和 `\udc80\udc81_other.py` 的模块，保存后断言模块本身和 `café.py` 都在数据中。
- 键集不变，期望映射不用改。

私有复验（同一方式）：

| 候选 | 修订版 |
| --- | --- |
| base | 0 |
| gold（正对照） | **1** |
| `skip_write` | **1** |
| `convert` | **1** |
| `lines_only` | 0（分支模式 `UnicodeEncodeError`） |
| `ascii_only` | 0（`café.py` 不在数据中） |
| `catch_save` | 0 |

**R-f：`statement_text_replace`**

- 修订题面为 [`revised_statement_v1.txt`](../../../../../../../rh2/experiments/category3_cloud_20260929/cov016/revised_statement_v1.txt)。父版本 sha256 `67c1899b…d410`，与 public bundle 一致；修订后 `e654fab9…e1e1`。
- 改动只在示例代码块：补 `import coverage`，把 exec 移到 `start()` 与 `stop()` 之间，并删去“Create a file…”这句不准确的注释。
- 已实跑确认：修订后的示例在 base 上抛 `UnicodeEncodeError`，在 gold 下正常保存。
- 新句没有隐藏测试细节。修正后示例崩溃位置随工作目录变化，题面 Error Message 中的“position 80”未改动，它只是示意。

**交接给第2类：**
1. 在 R2E 材料修订单中登记上述两项，并构建派生镜像；
2. 正式评分：noop 0，gold、`skip_write`、`convert` 为 1，`lines_only`、`ascii_only`、`catch_save` 为 0；
3. 由一位新公开读者验收修订题面；
4. Codex 复核。

## 5．当前用途与未做

- **用途**：原版只作问题定位；能力比较和训练在修订落地并验收前为 no。
- **未做**：
  - R2E 正式评分链与派生镜像没有在云端重建，本页评分是私有模拟；
  - 真实解题身份（UID 54321）的开发条件（R2E devcheck）未验；
  - 公开读者稿缺失的 `commands.json` 未重建。其中已给出全文的复现命令和公开测试命令，已按等价方式在 root 私有容器中执行；
  - 独立复核待做。
- **已登记的非本题问题**（公开读者 A3–A5）：`source=` 未执行文件发现路径、直接调用 `CoverageData` API、不可编码的上下文名。这些都超出题面范围，不作要求。
