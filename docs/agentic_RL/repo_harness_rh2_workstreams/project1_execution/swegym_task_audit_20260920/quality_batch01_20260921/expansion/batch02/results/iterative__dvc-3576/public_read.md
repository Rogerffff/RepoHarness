# iterative__dvc-3576 公开阅读记录

审查日期：2026-09-21。角色：独立公开读者，仅做静态阅读；未修复、未运行项目或测试。

材料根目录：`runs/swegym_quality_batch02_20260921_v2/public/iterative__dvc-3576/`。下文路径均相对此目录；`base/` 是源码导出。未使用继承 cwd 中的 worktree。

公开材料足以定位实现入口并设计本地复现。一个重要初态差异是：所给源码和旧功能测试已经支持单侧缺失指标，但表格仍输出 `diff not supported`，无变化提示仍走 STDOUT。因此，不能把题面中的 `unexpected error - 'HEAD^'` 当成本 base 上已复现的事实。需要真实 actor 后续验证，但不需要先补外部业务数据。

## 1. 输入层次与证据限制

| 层次 | 实际可见内容 | 本次处理 |
| --- | --- | --- |
| Issue 需求 | `user_prompt.txt:3–36`；`public_bundle.json:1` 的 `problem_statement` 重复同一文本 | 作为行为目标；复选框已打勾不能代替实现或运行证据。 |
| Harness 操作指令 | `public_bundle.json:1` 的 `public_hints` 要求修改 NON-TEST 源码、禁止改测试、窄范围验证、完成后简短总结；公开工具为 bash/edit，工作目录 `/testbed` | 这是解题工作流指令，与 issue 行为要求分开。本审查角色更窄，仅静态读写报告。 |
| 环境声明 | 同字段称 conda `testbed` 已激活；公开 bundle 有镜像标识与摘要 | 未运行容器或 actor shell，不能据此断言解释器、安装包、身份或资源可用。 |
| 当前说明 | `environment_brief.md:3–16,20–26` | 题面是静态渲染，未捕获实际模型请求；bundle 会写入解题容器公开路径，字段未渲染进用户消息不代表不可见。实际消息、shell、权限及预装资产待验证。 |
| 导出身份 | `base_identity.json:3–12` 记录指定 commit、349 个 materialized blobs、无 gitlinks/LFS 指针、未导出 Git 元数据 | 这是材料附带记录，不是本读者重新校验 commit 或 blob 的结果。没有据此读取历史、共享镜像或其他目录。 |

旧提示的“测试修改全部恢复、永不计分”不能当作已核实的当前机制。当前说明明确：已取消按测试文件名统一排除，仍可能恢复具体官方文件；逐文件限制不在本角色范围内。原“禁止改测试”是否应用于真实求解仍须核对，审查不授权忽略它（`environment_brief.md:20–26`）。

## 2. 需求表

| 行为 | 明示、合理推知或歧义 | 公开依据与应保留的约定 |
| --- | --- | --- |
| 旧版本没有指标文件，新版本有指标时仍能比较 | 明示 | 应显示新指标及其值，缺失的数值变化用示例中的 `-`，不因缺少旧值整体崩溃；`user_prompt.txt:4–20,33`。这个情况应是可成功处理的比较。 |
| JSON 支持缺失旧值 | 明示目标；表示法可由仓库推知 | Issue 仅说“no old values”，没有 JSON 示例（`user_prompt.txt:22,34`）。现有接口和旧测试明确使用 `{"old": None, "new": value}`，没有可计算差值时省略 `diff`；序列化对应 `old: null`，不是必须删除 `old` 键。见 `base/dvc/repo/metrics/diff.py:20–34,47–75`、`base/tests/func/test_metrics.py:978–989`、`base/dvc/command/metrics.py:147–150`。 |
| 提供有含义的诊断 | 明示目的；触发条件不完全明确 | `user_prompt.txt:24,35` 用“something like”给出错误文案，不要求逐字匹配。“单侧缺失应成功”与同场景“应报 old version not found”有语义张力。合理处理是正常比较不再出现裸引用键异常；真正不能比较时说明原因，而不是为了匹配示例额外制造失败。 |
| STDOUT 只放结果，状态和诊断走 STDERR | 明示 | 最后总结明确 STDERR（`user_prompt.txt:36`），覆盖前文写成 STDIN 的笔误（第 26 行）。文本结果为表格；`--show-json` 当然应输出 JSON，不能机械解释成 JSON 也禁止出现在 STDOUT。无变化提示不得污染结果流。 |
| 表格列名与含义 | 明示及既有接口 | 保留 `Path / Metric / Value / Change`，Value 是新值，数值 Change 为 `new - old`；`user_prompt.txt:15–20`、`base/dvc/command/metrics.py:120–129`、`base/dvc/repo/metrics/diff.py:31–34`。没有要求列出旧值列。 |
| 默认比较方向与选项 | 由公开接口、旧测试合理推知，应保留 | `a_rev` 默认 HEAD，`b_rev` 默认工作区；两 revision、`--targets`、类型、xpath、recursive、`--show-json` 已约定。见 `base/dvc/command/metrics.py:135–158,284–328`、`base/tests/unit/command/test_metrics.py:5–38`。 |
| 正常 diff 与空结果 | 由旧测试合理推知，应保留 | 未变化指标省略；嵌套 JSON 使用点分路径；数字计算差值；原始字符串允许 old/new 而不伪造数值差；两侧均无指标返回 `{}`。见 `base/tests/func/test_metrics.py:882–975`。不能把所有空结果统一改成“旧文件找不到”错误。 |
| 删除指标及坏 JSON | 由旧测试合理推知，应保留 | 删除时 `new: None`，坏 JSON 在现有比较中可呈现 `unable to parse`；`base/tests/func/test_metrics.py:955–970,992–1007`。Issue 的重点是缺少旧值，不自动授权重定义这些数据语义。 |
| 无效 Git revision 与有效 revision 上缺少文件 | 现有接口区分，应保留 | 无效引用应继续报告 revision 错误；`base/dvc/scm/git/__init__.py:348–377`、`base/dvc/scm/base.py:8–24`。不能通过吞掉全部异常，把不存在的 HEAD 父提交或拼错的引用当成“无旧指标”。 |
| 表格次序、空格与非数值 Change 文案 | 部分已有测试约定，任务扩展仍有选择 | 题面没要求排序；源码用集合遍历路径和指标，不能从示例行序推导必须完全同序（`base/dvc/repo/metrics/diff.py:53–55,92–97`）。旧单元测试精确断言空格和 `diff not supported`（见下一节），但新增指标的这一旧文案被题面 `-` 直接涉及。只对缺失侧改为 `-`，或把所有无法计算的 Change 统一为 `-`，是不同的合理展示范围，后者需要说明对原始字符串展示的影响。 |

## 3. 静态调用链与合理实现范围

调用入口明确：`CmdMetricsDiff.run` 将选项交给 `repo.metrics.diff`；`Metrics.diff` 转发到 `dvc/repo/metrics/diff.py`；该实现分别读取两个版本，再合并文件路径并逐指标比较（`base/dvc/command/metrics.py:135–158`、`base/dvc/repo/metrics/__init__.py:25–28`、`base/dvc/repo/metrics/diff.py:78–100`）。

目前 `_get_metrics` 已使用 `metrics.get(rev or "", {})`，且捕获 `NoMetricsError` 返回空映射；文件层面也使用 `old.get(path)`、`new.get(path)`。对有效引用上缺少旧文件的常见路径，这些源码不再直接按 `'HEAD^'` 索引缺失结果。旧功能测试已覆盖新增、删除及完全无指标。因此，本次不能确认题面异常的精确根因，更不能宣称已经复现；应先验证当前 base 的实际表现，保留已有容错而不要凭旧日志大改数据层。

读取层对缺失文件记 WARNING 后跳过；无任何指标时可能抛 `NoMetricsError`。`brancher` 还会遍历工作区和指定引用，因此不能把 `metrics.show` 返回的整个映射当成某个引用结果（`base/dvc/repo/metrics/show.py:208–257,278–313`、`base/dvc/repo/brancher.py:23–50`）。这属于正常源码调查，不是题面缺陷。

两处明确的展示差异：

- `_show_diff({})` 返回 `No changes.`，随后与表格共用 `logger.info`；INFO handler 指向 STDOUT（`base/dvc/command/metrics.py:108–112,150–152`、`base/dvc/logger.py:164–183`）。
- 没有 `diff` 的变化条目被渲染成 `diff not supported`，而非示例中的 `-`（`base/dvc/command/metrics.py:123–129`）。缺失旧值的 JSON 结构已经有公开功能测试支持。

合理路线不唯一，可以调整展示辅助函数和命令调用者，也可以在命令层区别“结果数据”和“状态消息”，通过局部日志分流或显式结果输出完成。私有函数名、分支排列、新 helper 名字并非用户需求。不需要强制重写 `_diff`、引入新依赖，或把整个 DVC 的所有 INFO 输出统一改流。若采用直接输出，应保留既有 quiet/verbose 行为的合理性（`base/dvc/main.py:43–47`）。

对于 metrics diff 的其他可达诊断，还应检查 DEBUG handler 仍指向 STDOUT、失败后 `main` 通过 INFO 输出支持页脚这两条路径（`base/dvc/logger.py:171–176`、`base/dvc/main.py:62–88`）。只验证默认无变化场景，不能证明“所有其他消息走 STDERR”这一表述已完整满足；也不应由此擅自扩大到重设计其他子命令。

**旧测试与指令的具体张力：**`base/tests/unit/command/test_metrics.py:70–76` 对新增指标精确期待 `diff not supported`，直接对应需要改变的场景；第 50–63、79–85 行还固定了原始字符串和删除指标的旧展示；第 66–67 行固定辅助函数空结果返回字符串。直接让辅助函数输出新展示后，部分这些旧断言预计会失败，不能一律当作行为回退。

- 若禁止改测试指令适用：合理源码修复仍有实现空间，也可把 CLI 的新展示策略与辅助函数现有调用约定分开；应如实解释与已过时断言的冲突，而不是修改测试或为了旧断言放弃用户要求。保持旧私有 helper 默认值、在 CLI 明确选择新策略只是一个可行方向，不是必须采用的答案。
- 若实际求解不适用该禁令：可以更新受需求改变影响的展示断言，并增加对流向和 JSON 的回归检查；是否有具体官方文件会被恢复仍待协调者按当前机制核对。

本报告不以“所有测试修改永不计分”作结论，也不据此判定题目不可用。

## 4. 初态疑义与真正缺口

| 项目 | 现有证据 | 影响及后续所需 |
| --- | --- | --- |
| Issue 异常与 base 状态不完全一致 | `.get`/`NoMetricsError` 容错与新增指标旧测试已经存在 | 缺少原始完整 traceback、当时 DVC 状态和指标仓库；这些会帮助精确还原原报告，但不阻止验证并修复当前展示/流向问题。不需要先访问历史或未来提交。 |
| 缺少“旧版本”是有效 revision 中缺文件，还是 revision 本身不存在 | 题面说文件刚创建且示例是文件 WARNING；源码有独立 revision 错误 | 以有效 Git revision 上缺文件为核心。最小复现必须创建真实父提交，避免把单提交仓库的 `HEAD^` 错误当作本 bug。 |
| JSON 缺值表示 | Issue 无 JSON 样例，旧测试有 `old: None` 且无 `diff` | 当前公开接口足以支持 `null` 方案；没有理由强行要求删除 `old` 键。若验收要求不同精确 schema，需要明确公开约定。 |
| 缺失旧文件时还要不要 WARNING/ERROR | Issue 同时要求成功表格和更好的错误文案 | 不制造致命错误是较合理解释；允许保留有意义的 STDERR 缺文件警告。具体日志级别、前缀、逐字措辞未被题面锁定。 |
| JSON null、空内容、新指标值为 null 等边界 | 当前比较把缺值表示成 None，`_read_metrics` 跳过假值结果（`base/dvc/repo/metrics/show.py:252–255`） | Issue 未要求区分显式 JSON null 和不存在的键。可作为额外边界调查，不能臆造为本次全部必须重定义的行为。 |
| 外部安装/贡献指南 | `base/README.rst:91–153` 与 `base/CONTRIBUTING.md:1` 指向外部网站 | 本包不含外链正文；未访问。源码、setup 与旧测试足够推导本题最小流程，当前没有必须补齐的外链/附件。若实际安装受阻，再请求所缺依赖的离线包或相应公开说明。 |
| 实际执行条件 | 环境说明明确未做 actor CPU 验证 | 解释器、依赖版本、Git、临时目录写权限、测试导入和资源限额仍需验证；属于共享运行条件未知，不是公开 issue 逻辑不可定位。 |

## 5. 开发需求表

本节所有命令都是**建议，未执行**，用于后续真实 actor 的 `/testbed`。本次没有安装依赖、启动容器、运行项目、测试、构建或访问网络。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小命令及预计现象（均为建议，未执行） |
| --- | --- | --- | --- | --- |
| Python 与当前源码导入 | `base/setup.py:49–85,162–174`；`base/dvc/__main__.py:1–7` | 仅声明预激活 conda `testbed`、bash/edit、`/testbed` | 实际 Python 版本、解释器路径、安装来源和兼容性未验。setup 声明 >=3.5、列出 3.5–3.8；不能推导现代 Python 一定兼容 | `python -V`；下方导入命令。应解析到 `/testbed/dvc` 并成功导入；缺包或兼容异常是环境障碍。 |
| Python 运行依赖 | `base/setup.py:49–85` 包括 GitPython、jsonpath-ng、flatten_json、texttable、YAML 等，部分为旧版本范围 | 不保证实际镜像满足；不假定公网可下载 | 必须核对预装依赖；若缺失请求离线资产。README 的“安装最新开发版”不是固定 base 的合适补救 | `python -m pip check`；导入 `dvc.repo.metrics.diff` 与命令模块。应无依赖错误；命令不替代功能测试。 |
| pytest 和收集期依赖 | `base/setup.py:110–133`；`base/tests/conftest.py:3–8` 顶层导入 mockssh、HTTP helper；后者导入 RangeHTTPServer（`base/tests/utils/httpd.py:1–6`） | 只说应另做 actor 验证 | 即使只跑指标测试，也可能在收集期因 mockssh/RangeHTTPServer/pytest-mock 缺失而失败；这些不是本题需要真实 SSH/HTTP 服务的证明 | `python -m pytest --collect-only -q tests/unit/command/test_metrics.py tests/func/test_metrics.py -k metrics_diff`。应能收集目标测试。 |
| 本地 Git、临时可写目录与小型 DVC 仓库 | `base/tests/dir_helpers.py:89–107,217–255`；新增/删除指标旧测试 | profile 声明 agent/54321、工作区/home 可写、默认 2 CPU/4 GiB/PID512；均未实测 | Git 可执行、提交身份、实际写权限和进程限制待验；源码导出自身无 .git，但可新建隔离复现仓库 | `id`、`git --version`；下方临时仓库脚本。应建立两个以上提交并解析 HEAD^；缺 Git、写入失败与版本比较错误要区分。 |
| 测试进程资源 | `base/tests/__init__.py:30–36` 在非 Windows 上设置 NOFILE/NPROC 限额 | 说明不保证实际资源 | actor 的硬限制可能影响测试导入；不能只因资源声明看似足够就保证成功 | 上述 pytest 收集命令也覆盖这段导入；若在 setrlimit 失败，应记录为运行条件问题。 |
| JSON、stage 元数据、Git 对象及可选本地缓存 | `base/dvc/repo/metrics/show.py:225–234` 区分缓存和 Git/工作区读取；旧测试就地生成指标 | 无需外部训练集；所需数据可生成 | 原用户两份指标文件未提供，但不是本地最小复现的必要资产。缓存分支可由旧测试验证 | 下方脚本采用 `-M` 自包含 JSON；功能测试的 raw/JSON 分支也使用本地缓存。预计不需要网络、GPU、模型或云凭证。 |
| 独立 stdout/stderr 捕获 | `base/dvc/logger.py:164–183`；题面输出要求 | bash 可表达重定向；实际流向未捕获 | 旧指标单元测试主要检查返回字符串，不足以证明 CLI 流向 | 下方 `1>`/`2>` 捕获；修复后结果文件只有表格/JSON，无变化时 stdout 空、stderr 有状态。 |
| 构建或安装入口 | `base/setup.py:138–177` 定义 Python 包与 console script | 不保证包写权限、构建工具及离线依赖 | 本题无需独立二进制构建；优先用 `PYTHONPATH=/testbed python -m dvc`，可避免为验证修改解释器环境 | 若确需可编辑安装且依赖已齐，`python -m pip install --no-deps --no-build-isolation -e .`；仅作有条件建议，未执行、不承诺离线一定成功。 |

### 最小导入与旧测试命令（建议，未执行）

```sh
# 建议，未执行；在真实 actor 的 /testbed 中执行。
cd /testbed
python -V
git --version
DVC_TEST=true PYTHONPATH=/testbed python -c 'import sys, dvc; from dvc.repo.metrics.diff import _diff; from dvc.command.metrics import _show_diff; print(sys.executable); print(dvc.__file__)'
python -m pip check
DVC_TEST=true PYTHONPATH=/testbed python -m pytest --collect-only -q tests/unit/command/test_metrics.py tests/func/test_metrics.py -k metrics_diff
DVC_TEST=true PYTHONPATH=/testbed python -m pytest -q tests/func/test_metrics.py -k metrics_diff
DVC_TEST=true PYTHONPATH=/testbed python -m pytest -q tests/unit/command/test_metrics.py
```

预期：在兼容环境下，现有功能测试对新增/删除/空指标以及普通比较的断言应可通过；这不证明题面全部目标已满足。命令层旧测试预计认可旧 `diff not supported` 展示，直接更新 formatter 后可能因过时展示断言而失败。测试收集失败不能冒充原 bug 失败。若改动涉及共享 logger，再建议单独运行 `python -m pytest -q tests/unit/test_logger.py`（建议，未执行），无需自动扩大到全仓测试。

`DVC_TEST=true` 沿用 `base/tests/conftest.py:11–14`，用于阻止 updater/analytics 后台活动；源码条件见 `base/dvc/analytics.py:53–55`、`base/dvc/updater.py:50–52`。它不是网络或资源验证结果。

### 可复现两种“缺旧指标”及无变化的最小场景（建议，未执行）

下面只在新临时目录构造本地数据，不修改 `/testbed` 源码或测试。`-M` 与无 command 的 stage 声明由 `base/dvc/command/run.py:16–42,123–139` 及旧测试使用方式支持。

```sh
# 建议，未执行；应由后续 actor 在确认解释器与导入正常后执行。
export DVC_TEST=true
export PYTHONPATH=/testbed
dvc3576_scratch=$(mktemp -d /tmp/dvc3576-public.XXXXXX)
cd "$dvc3576_scratch"
git init
git config user.name 'Public repro'
git config user.email 'public-repro@example.invalid'
python -m dvc init
git add .dvc
git commit -m 'init dvc'
printf '%s\n' '{"accuracy": 0.897}' > metrics.json
python -m dvc run -M metrics.json -f metric.dvc
git add metric.dvc
git commit -m 'declare metric before its Git file'
git add metrics.json
git commit -m 'add metric file'

# 建议，未执行：HEAD^ 有 stage，但没有 Git 跟踪的指标文件。
python -m dvc metrics diff HEAD^ > old-missing.out 2> old-missing.err
python -m dvc metrics diff HEAD^ --show-json > old-missing.json 2> old-missing-json.err

# 建议，未执行：HEAD~2 连 metric stage 都还没有。
python -m dvc metrics diff HEAD~2 > no-old-stage.out 2> no-old-stage.err

# 建议，未执行：新旧完全相同；分别检查文本和 JSON 模式。
python -m dvc metrics diff HEAD > unchanged.out 2> unchanged.err
python -m dvc metrics diff HEAD --show-json > unchanged.json 2> unchanged-json.err
```

应分别记录每条 diff 命令退出码，并静态查看捕获文件（如 `cat old-missing.out old-missing.err unchanged.out unchanged.err`，建议，未执行）。依据源码推断，此 base 常见表现应是新增指标已能成功比较、JSON 含 `old: null`，但文本 Change 为 `diff not supported`，无变化时 `No changes.` 在 stdout；不是保证重现题面旧 `KeyError`。

修复目标：缺旧文件/旧 stage 时仍显示 accuracy=0.897、Change=`-`，结果 JSON 可解析且无可计算差值；无变化文本模式 stdout 空、stderr 有状态，JSON 模式 stdout 保持 `{}` 而不混入 `No changes.`。允许有意义的缺旧文件诊断留在 stderr。用已有 `test_metrics_diff_json` 验证数值 `new - old`，用 deleted/raw/broken_json 测试验证相关既有语义。

可额外建议 `python -m dvc metrics diff definitely-not-a-public-revision > invalid.out 2> invalid.err`（建议，未执行）：应得到清楚的 revision 诊断和非零退出码，不能伪装成缺指标成功。当前源码的失败页脚可能污染 stdout，需对照任务的输出流要求检查，不能预报此项已经正确。

## 6. 实际阅读与暴露记录

本轮先读指定角色卡 `roles/public_reader.md`，随后按顺序读 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。角色卡的完整授权路径来自协调者；没有读取角色目录父级调查材料。随后仅在本题公开目录静态检索和展开文件。

**全文显示到上下文的材料：**

- 包根：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`。
- 源码：`base/dvc/repo/metrics/diff.py`、`base/dvc/repo/metrics/show.py`、`base/dvc/repo/metrics/__init__.py`、`base/dvc/command/metrics.py`、`base/dvc/repo/brancher.py`、`base/dvc/logger.py`、`base/dvc/main.py`、`base/dvc/__init__.py`、`base/dvc/__main__.py`、`base/dvc/version.py`、`base/dvc/command/init.py`。
- 旧测试与配置：`base/tests/unit/command/test_metrics.py`、`base/tests/unit/test_logger.py`、`base/tests/conftest.py`、`base/tests/__init__.py`、`base/setup.py`、`base/setup.cfg`、`base/pyproject.toml`、`base/CONTRIBUTING.md`。

**按行段显示到上下文的材料：**

| 文件 | 展开行段 |
| --- | --- |
| `base/README.rst` | 85–155；另有安装关键词命中行 |
| `base/tests/func/test_metrics.py` | 1–35、620–675、735–1007；另有指标关键词命中行 |
| `base/dvc/exceptions.py` | 1–50、160–205 |
| `base/tests/dir_helpers.py` | 73–112、217–257；另有 import/fixture/Git 等命中行 |
| `base/tests/utils/httpd.py` | 1–55 |
| `base/dvc/command/run.py` | 1–75、115–144、196–210；另有选项命中行 |
| `base/dvc/analytics.py` | 45–65 |
| `base/dvc/updater.py` | 40–65 |
| `base/dvc/scm/git/__init__.py` | 1–48、338–379；另有 revision 关键词命中行 |
| `base/dvc/scm/base.py` | 1–35 |
| `base/tests/basic_env.py` | 1–110 |
| `base/dvc/remote/ssh/connection.py` | 1–50 |

**检索与元数据操作：**对本题公开根和 base 顶层做目录列表；用 `rg --files` 查 README、安装配置、指标测试、conftest/logger/scm 等路径；用 `rg -n` 在 `base/dvc`、`base/tests` 查 `metrics.diff`、`_diff_vals`、`_get_metrics`、`NoMetricsError`、`No changes.` 等，工具扫描这些树，模型看到命中行。由此还看到 `base/dvc/command/checkout.py:34`、`base/tests/unit/command/test_checkout.py:50`、`base/dvc/repo/diff.py:10`、`base/dvc/config.py:116` 及 `base/dvc/scm/git/tree.py:95` 的少量命中；这些文件没有完整展开。`base/dvc/scm/__init__.py` 参加 revision 关键词搜索但无命中。曾把 Git 模块猜为 `base/dvc/scm/git.py`，只得到“文件不存在”；随后在本题 base 内定位到 `dvc/scm/git/__init__.py`。`wc -l` 仅用于估算部分源文件长度。

未打开其余业务代码、其余完整测试、外链、Git 历史、容器、批次 manifest、私有评分/gold、其他题或任何其他角色产物。顶层列表显示的文件名不代表读取其内容。本轮未发现私有材料误读；这只是本轮协作阅读记录，不能称为文件权限隔离或预训练无污染证明。

实际操作仅有静态文本/元数据读取和本报告写入；没有项目导入、测试、安装、构建、网络检索或模型代理请求。`user_prompt.txt` 只是静态渲染，base 只是源码导出；实际模型消息、运行资源、依赖可用性、原 bug 可复现性及开发条件均未验证。保留的关键未知是当前 actor 环境、题面错误与 base 的初态差异，以及旧展示断言/原禁改测试指令在真实求解中的适用方式。
