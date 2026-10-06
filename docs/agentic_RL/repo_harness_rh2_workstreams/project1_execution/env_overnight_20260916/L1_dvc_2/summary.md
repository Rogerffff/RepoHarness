# L1_dvc_2 · 逐题静态审查小结

范围：iterative/dvc 18 题（ASSIGNMENT.json 顺序；`task_signals_swegym.json` 里这 18 题的 `in_e2` 全空、`fragile_reference_id` 全 false、stage1 `gold=RESOLVED_FULL` / `empty=RESOLVED_NO`、无 DeepSeek 候选，故按给定顺序做）。
方法：先只看 `problem_statement` + base 代码写 `public_view`，再读 `test_patch` / `fail_to_pass` / `pass_to_pass` / `golden_patch` / `hints_text`。
base 代码用裸克隆 `git show <base>:<path>` / `git grep <base>` 读取（COMMON.md 允许的只读操作），未建 worktree。全程静态：未启动 Docker、未实跑测试、未调模型 API、未连远程机器。
逐题记录：`records/<instance_id>.json`。脚本：`scripts/{extract,prescan,collide,leak,dump,rec}.py`；中间产物 `runs/env_overnight_20260916/L1_dvc_2/{mat/,prescan.json}`。

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| iterative__dvc-3677 | **题面与 F2P 之间缺一整段因果**：题面只报告 `.dvc/.gitignore` 反复多出 `/tmp`，F2P 却是 `is_tracked('dir')` 必须为 True 的目录跟踪语义；把两者接起来的那句话只在上游 commit message 与不可见 hints 里。**题面症状零覆盖**——按题面在 `_add_entry_to_gitignore` 做去重的合理修复得 0，只改 `is_tracked` 而没验证症状的修复得满分。gold 与上游 e2981d274 逐字一致。P2P 5 条全在同一个测试文件内，两个真实调用者（output/base.py:220、repo/add.py:112）零保护 | needs_repair | 盲解一次只给现题面，看是否走 `Git.ignore()` 路径（预期 F2P 0 通过）；另在 base/gold 上跑「两次 dvc add 后 .gitignore 只一行」的新端到端断言 |
| iterative__dvc-3794 | **题面与评分要的是两个不同 CLI**：题面逐字要求 `dvc remote modify <name> name <new>`，F2P 要的是新子命令 `dvc remote rename <old> <new>`；维护者否决 `name` 的整段讨论只在不可见 hints 里。F2P 本身设计好（跨 level 重名检测 + core.remote 同步），但额外锁死了退出码 254/251 与必填位置参数。gold 与上游 3f846a179 一致，自带两个瑕疵：错误消息 `.format({self.args.new})` 传了集合字面量、`args.new` 未小写化。另：status_map 28 个键里 8 个是 **dvc 自己打印的 `ERROR:` 日志行**被 parser 当成测试状态 | needs_repair | 盲解一次看是否实现 `name` 参数（预期 F2P 0/3）；另构造只打印 `PASSED <nodeid>` 的假补丁走真实 grader，验证 parser 可写面 |
| iterative__dvc-4066 | 题面质量本包最好（完整 traceback 定位到 `dvc/ignore.py:39`、最小 `.dvcignore` 复现、TL;DR），gold 一行 `if ignore is not None`，F2P 行为化不锁实现。两个缺口：(a) 交付的 F2P 只保留了维护者复现的前半段，丢掉 `monkeypatch.chdir` 后的相对路径断言，且只覆盖『空行在中间』；(b) **4066→4125→4166 是强同族**——后两题的 base 都已包含本题参考解且共用 `tests/func/test_ignore.py`，划分必须同侧。另这三个镜像下同样 3 条 test_ignore 用例长期 FAILED | ready_for_probe | 写只处理『中间空行』的窄修复跑当前 F2P（预期满分）；单跑那 3 条既有失败取 traceback |
| iterative__dvc-4124 | **判分链路本包最干净的一题**：收集集合 34 条 = F2P 6 + P2P 28，零过选零漏选，gold 34/34 全绿；P2P 有真实判别力（无条件加 `\n` 会打挂所有 plain 模式断言）。缺口：题面只提 `dvc metrics diff --show-md`，F2P 却要求 diff/metrics/params 三条命令都改（三者共用 `dvc/utils/diff.py::table`，在共享点修才全过；只改 metrics 的等价修复 2/6）。题面 389 字符且以疑问句收尾，几乎不提供验收标准 | ready_for_probe | 写只改 `dvc/command/metrics.py` 的修复跑 6 条 F2P，预期 2 过 4 挂 |
| iterative__dvc-4125 | **首次定位到仓库级依赖缺陷**：gold 下 `tests/func/test_ignore.py` 有 3 条崩在 `re.error: redefinition of group name 'ps_d'`——dvc 1.x `setup.py` 只写 `pathspec>=0.6.0` 无上界，新版 pathspec 的 `(?P<ps_d>…)` 命名组被 `dvc/ignore.py` 的 `"|".join` 拼接后重名；上游后来才 `pathspec<0.9.0`。这些坏死用例被静默排除出 P2P，其中 `test_ignore_blank_line` 正是 dvc-4066 的 F2P（同一条测试在两个镜像里一个是判分依据一个是坏死项）。题意侧：题面讲 `dvc add` 的 PermissionError，F2P 验的是 `checkout` 不恢复被忽略文件，题面症状零覆盖 | needs_repair | 在镜像里 `pip install 'pathspec<0.9.0'` 后重跑该文件，统计恢复用例数并重算双侧通过集 |
| iterative__dvc-4166 | **两个 P1**：(1) P2P 里的键 `tests/unit/test_ignore.py::test_match_ignore_from_file[` 是一对多——参数以空格开头（`" to_ignore"`），parser 按空白截断后 `patterns5-False` 与 `patterns6-True` 合成同一键，日志里 patterns6 在后，**patterns5 的结果永远被丢弃**；而这两条恰是判别『尾随空格是否生效』的相反对（与 L2 包扫描一致）。(2) 依赖未锁：pathspec 太新致 `re.error: ps_d`、networkx 太旧致 `from fractions import gcd` ImportError，3 条同族用例在 gold 下就崩并被静默移出 P2P。题意侧：题面列的 6 个失败写法按 git 语义本来就不该工作，评分实际验的是另一件事（尾斜杠目录模式），F2P 只 1 条 | needs_repair | 人为让 patterns5 失败 patterns6 通过跑真实 grader，确认总分不变；镜像里降 pathspec/升 networkx 后重跑两个测试文件 |
| iterative__dvc-4719 | **本包最危险的一题**：P2P=0，同文件另外 4 条 run-cache 正向用例在 gold 下全崩（pathspec `re.error`），`RESOLVED_FULL` 完全由一条单测决定；而该单测的 `assert get_stage_hash.not_called` 是**永远为真的空断言**（MagicMock 属性，不是 `assert_not_called()`），另一条 `restore` 抛错在 base 就成立。更关键：测试用 `mocker.Mock(spec=Repo)` 构造 `StageCache`，而 `Repo.cache` 是实例属性不在 `dir(Repo)` 里，**只做题目要求的 `save()` 守卫而不把 `cache_dir` 改成 `cached_property` 就会在构造处 AttributeError 判 0** —— gold 的第一段其实是为测试服务的结构改动 | needs_repair | `def save(self, stage): return` 的破坏性假修复跑当前 F2P+P2P，预期满分；再跑「只加 save 守卫不动 cache_dir」验证强制结构 |
| iterative__dvc-4778 | **本包最直接的奖励漏洞**：F2P 四条全是 `with pytest.raises(DvcException): dvc.add(...)`，P2P=0，gold 下同文件 55 条里 51 条 FAILED（4 条 PASSED 恰为 F2P 全集）——在 `dvc/utils/__init__.py:resolve_paths` 开头写一行 `raise DvcException` 即可 RESOLVED_FULL。方向也相反：题面要『第二次 add 能成功』，评分验的是新增的『符号链接目录一律拒绝』；唯一覆盖题面症状的 `test_add_symlink_file`（注释引用 issue #4654）因 pathspec `re.error` 在 gold 下也是红的，F2P/P2P 都进不去。empty 侧 55/55 全红，`RESOLVED_NO` 零信息 | needs_repair | 先跑 `raise DvcException` 一行假修复走真实 grader（预期满分）；再降级 pathspec 后重跑整文件重建 F2P/P2P |
| iterative__dvc-4785 | **题面写的修法会被判 0**：题面末句明说 `The simplest fix would be using res.raise_for_status()`，但 F2P 断言的是 `dvc.exceptions.HTTPError`（`DvcException` 子类），与 `requests.exceptions.HTTPError` 无继承关系——照题面做第三段必挂。另：**题面整段逐字重复两遍**（362×2，hints 同样重复），属 216 题里 6 道重复题面之一。判分链路本身很干净：收集 9 条 = F2P 1 + P2P 8，gold 全绿，无 pathspec 问题。P2P 的 `test_download_fails_on_error_code` 依赖一个 127.0.0.1 本地静态 HTTP 服务器（非外网） | needs_repair | 写 `res.raise_for_status()` 版实现跑 F2P，确认只有第三段失败 |
| iterative__dvc-4961 | **参考 ID 截断最集中的一题**：6 条 F2P 的 nodeid 都含空格（dict 字面量 `{'level': 35}`），`parse_log_pytest` 按空白切分只留首段，参考集与 status_map 恰好『同样截断』所以当前判分正确，但键已丢掉 `-outN-None` 索引，任何新增同前缀参数化都会合并（本题 6 条前缀互异，无碰撞）。其余很干净：题面含完整复现与精确错误文本、gold 与上游一致、收集 47 条 = F2P 6 + P2P 41 且全绿、P2P 的 12 条既有 `test_parse_target` 参数化对原 `:` 分隔语义有真实判别力。缺口：题面症状（`dvc repro -f` 找不到 stage）零端到端覆盖；hints 里维护者最初说『list 里放 dict 本来就不支持』，与最终修法方向相反 | ready_for_probe | 给 test_parse_target 再加一个 `build@{'level': 36}` 参数，确认与 35 那条合并成同一键 |
| iterative__dvc-5004 | 题面提出的方案（『忠实存字符串，只在输出统计时转类型』＝改 params 读取层）与 gold 的修法（改插值层 `str_interpolate` 的 `str(value)`→`to_str`）**不在同一层**；F2P 还额外要求整值插值 `${item}` 保持 Python 的 `True`/`False`、只有嵌在字符串里的才小写化，这条区分题面零依据。判分语义本身不错：`resolve_str("${enabled}") is True` 的身份断言堵住『一律转字符串』，P2P 的 `test_set[3]/[None]/[3.14…]` 堵住『所有类型都小写 str』。但 `tests/func/test_stage_resolver.py` 有 19 条因 pathspec `re.error` 在 gold 下崩溃被排除；P2P 还含一个空格截断键 `test_set[To`（无碰撞） | needs_review | 写『在 params 加载处转字符串』的实现跑 F2P+P2P，预期 `is True` 断言失败 |
| iterative__dvc-5148 | **test_patch 自己新增的两条功能级验收在 gold 下就崩**：`tests/func/test_remove.py` 整文件 6/6 FAILED（pathspec `re.error`），其中包含 `test_cmd_remove_gitignore_single_stage` / `multistage`——它们才是『`dvc remove` 后 .gitignore 被删』的直接验收，因此既进不了 F2P 也进不了 P2P，留下的 F2P 只覆盖 SCM helper 层。另：gold 的早退 `if not filtered: os.unlink(...); return` **跳过了 base 原有的 `self.track_file(relpath(gitignore))`**，删除是否需要同步 git 索引无人验证。题面 267 字符、hints 99 字符（只有认领对话），信息量本包最低。与 3677 同改 `dvc/scm/git/__init__.py` 同族 | needs_repair | 降 pathspec 后单跑 `tests/func/test_remove.py`，确认那两条在 base FAILED / gold PASSED 后纳入 F2P |
| iterative__dvc-5188 | **gold 一半的改动不被评分**：gold 把 `run()` 拆成 `_list/_get/_set`，其中 `_get` 被改成不给 level 时按 `Config.LEVELS[::-1]` 逐级查找（含 `except ConfigError: if self.args.level: raise` 的控制流），而 F2P 只有一条 `--list --show-origin` 合并输出断言，P2P 也不覆盖——整段删掉仍可满分。题面措辞与初态不符：题面说『下一步需要 --show-origin』，base 其实已有它（只是要求显式 level），真实任务是去掉这个限制。判分链路干净：收集 27 条 = F2P 1 + P2P 26 且全绿，无 pathspec 问题；P2P 含两个空格截断键（无碰撞） | ready_for_probe | 写只改 `_list`、保留 base `_get` 的实现跑 F2P+P2P，预期满分（证明 gold 一半改动不被评分） |
| iterative__dvc-5336 | 本题有三个结构性异常：(1) **base 不在 origin/main 上**——`9638dde4da`（`dvc: bump to 1.11.12`）只被 tag 1.11.12+ 含，上游是一次 **backport/cherry-pick**，本包唯一一例；(2) **test_patch 夹带无关基础设施改动** `tests/docker-compose.yml`（azurite 3.9.0→3.10.0，来自另一个 PR #5272），是『test_files 由 test_patch 全部路径生成』会带进非测试代码的具体样本；(3) **F2P 过弱**——gold 是把按 errno 精细判断改成吞掉全部 OSError 的**放宽型**修复，而唯一断言是 `assert mock_chmod.called`，`except BaseException: pass` 即可满分，P2P 只有 4 条且不覆盖 protect 的真实调用面。题面症状是 Windows+Samba，Linux 镜像里不可复现 | needs_repair | 写 `except BaseException: pass` 版 chmod 跑 F2P+P2P，预期满分 |
| iterative__dvc-5839 | gold 只有一行（`CmdMetricsShow.run` 漏传 `self.args.precision`，base 的 `_show_metrics` 早就有该形参并正确实现）。**F2P 把私有函数 `_show_metrics` 的调用签名钉死**：`mocker.patch(..., spec=_show_metrics)` + `assert_called_once_with({}, markdown=False, …, precision=8)`——好处是 `spec=` 让位置/关键字调用归一化，坏处是把 precision 传给 `repo.metrics.show()` 等同样正确的实现会判 0。而且 `_show_metrics` 被**整体 mock 成返回空串**，『--precision 8 与默认输出不同』这件事一次都没验证。题面自问的科学计数法语义（两个版本）gold 一个都没实现。判分链路干净：22/22 全绿、收集集合 = F2P 1 + P2P 21 | ready_for_probe | 写「把 precision 传进 `repo.metrics.show()`」的实现跑 F2P，预期两条 mock 断言都失败 |
| iterative__dvc-6954 | **参考 ID 截断最彻底的一题：13/13 全部被截断**——pytest 按参数文本生成 id（`UNARY_OP = -1-result9`、`SUM = 1 + 2`），必然含空格，parser 只留首 token；参考集与 status_map 同样截断，当前无碰撞（首 token 互异），但再加一个 `INT = 6` 就会和 `INT = 5` 合并。适合做 parser 回归语料。题目本身质量高：题面 6 步复现 + 精确错误文本，gold 用 `ast.literal_eval` 替掉手写 `_get_ast_value`，F2P/P2P 只断言返回值不锁实现，13/13 全绿、收集集合 = F2P 1 + P2P 12。缺口：P2P 全是本次新增（该测试文件 base 上不存在），`parse_py` 的真实调用面零覆盖；负向要求（`dict(a=1)`/`1+2` 仍须返回 `{}`）题面无依据 | ready_for_probe | 把本题 gold 日志 13 行摘要 + 期望 status_map 存成 parser 回归样例；另写 `eval` 版宽松实现验证 `SUM = 1 + 2` 会挂 |
| iterative__dvc-9212 | **题意与评分范围错位最大的一题**：题面请求 dvc 原生 `${}` 插值支持嵌套（自然落到 `dvc/parsing/`），**题面一个字都没提 hydra**；gold 却是在 `dvc/utils/hydra.py::compose_and_dump` 里加一行 `OmegaConf.resolve(cfg)`，F2P 还用了题面从未出现的相对插值语法 `${.root}`。把两者连起来的唯一依据是不可见 hints 里维护者那句『You are using the hydra integration, right?』。gold 实际做的事是统一 hydra 的 yaml 与 toml/json 两条 dump 路径（base 里 `to_yaml` 默认不解析、`to_object` 解析），并没有实现题面请求的功能。判分链路干净：55/55 全绿、收集集合 = F2P 1 + P2P 54 | needs_repair | 盲解一次只给现题面，统计候选改动落在 `dvc/parsing/` 还是 `dvc/utils/hydra.py`（预期前者、F2P 0/1）|
| iterative__dvc-9391 | **又一个可复现奖励漏洞**：gold 只有一行 `action="append"`，而 5 条 F2P 全是把 mock 断言里的 `rev="foo"` 改成 `rev=["foo"]`，**没有任何一条传两个 `--rev`**；P2P 24 条又全是 `test_experiments_init/gc/apply/branch/run/save/diff/clean` 等与 `--rev` 无关的邻居。于是 `type=lambda s: [s]`（或在各 `run()` 里把单值包成列表）即可满分，功能根本没实现。题面请求的其实是 **per-rev 的 `-n`**（`--rev main -n 5 --rev other -n 3`），gold 没有交付；判断『只改 CLI 就够』的前提（内部 API 已支持多 rev）只在不可见 hints 里。判分链路干净：29/29 全绿、收集集合 = F2P 5 + P2P 24 | needs_repair | 写 `type=lambda s: [s]` 的假修复跑 F2P+P2P，预期 RESOLVED_FULL |

## 覆盖与统计

- 覆盖 **18/18** 题，全部落盘 `records/<instance_id>.json`（均为合法 JSON，每题 18–19 项检查）。**未做清单：空**。
- 处置建议分布：`ready_for_probe` 6（4066、4124、4961、5188、5839、6954）、`needs_review` 1（5004）、`needs_repair` 11（3677、3794、4125、4166、4719、4778、4785、5148、5336、9212、9391）。
- 检查状态合计：`pass` 208、`issue` 115、`unknown` 2（4719 的 check 31 控制面、5336 的 check 2 初态）。issue 严重度：P1 17、P2 31、P3 20。
- 方法与限制：**全部静态审查**。未启动 Docker、未实跑任何测试、未调用模型 API、未连任何远程机器。base 代码用裸克隆的 `git show <base>:<path>` / `git grep <base>` / `git log` 读取（COMMON.md 允许的只读操作），未建 worktree。实跑证据一律来自既有的阶段一离线日志 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/<iid>/{gold,empty}/offline/a1/`。凡标 `pass` 的检查都附了文件行号、commit 或日志路径；未做的写 `not_checked`，证据不足写 `unknown`。
- `costs.minutes` 是**工作量估计**而非墙钟耗时（本包 18 题实际墙钟约 50 分钟，2026-09-16 本机 03:06–03:56）。
- 中间产物（都在 `runs/env_overnight_20260916/L1_dvc_2/`）：`mat/`（18 题四面材料抽取）、`prescan.json`、`smstat.json`（逐题 status_map 统计）、`upstream.json`、`deps_scan.txt` / `deps_scan2.txt`（依赖故障扫描，覆盖全部 35 道 dvc 题）、`truncated_ids.txt`（截断参考 ID 清单 + 运行时全名）、`p2p_loss.txt`（逐题收集数/F2P/P2P/gold 侧失败数）、`evalcmd_check.txt`（eval.sh 与 test_patch 路径对照）、`base_branch.txt`、`statement_quality.txt`。脚本在 `scripts/`。

## 仓库级（跨题）发现

以下六条不是单题问题。

### 1. dvc 的判分是「整文件跑」，P2P 是整文件双侧通过集的副产物

`grading_bundles_v2_v0.jsonl` 里 18 题的 `eval_cmd` 全是裸 `pytest -rA`，实际命令由 runner 追加 **test_patch 里的 `.py` 路径**（`evalcmd_check.txt`：18 题逐条核对，唯一"不等"的是 5336，因为它的 test_patch 还含一个 `tests/docker-compose.yml`，非 `.py` 不进 pytest 参数，但**仍在恢复集合里**——`git checkout <base> tests/docker-compose.yml tests/unit/remote/test_local.py`）。

这与 mypy 的 `-k` 子串过选是完全不同的机制，后果也不同：
- **没有过选/漏选问题**：18 题里有 **10 题**的收集集合与 `F2P ∪ P2P` 完全相等（3677、4124、4785、4961、5188、5336、5839、6954、9212、9391）；其余 8 题的差额**逐题精确等于**"gold 侧仍然失败的用例数"（3794 差 5、4066 差 3、4125 差 3、4166 差 3、4719 差 4、4778 差 51、5004 差 19、5148 差 6，见 `p2p_loss.txt`）。
- **代价转移到了运行成本与既有失败**：整文件跑意味着一道题要跑几十条无关用例（4166 收集 62 条、5148 收集 56 条、9212 收集 55 条），而且**同文件里 gold 下就红的用例会被静默排除出 P2P**。
- 全包合计：**收集 534 条，F2P 42，P2P 398，gold 侧仍失败 94 条（17%）**（`p2p_loss.txt`）。

### 2. 镜像依赖未按历史锁定，打掉了大量回归保护（P1）

两处独立的版本不匹配，都属于清单第 6 项"历史依赖与工具链是否可恢复"：

1. **pathspec 太新** → `re.error: redefinition of group name 'ps_d' as group 2; was group 1 at position 46`。
   dvc 1.x 的 `setup.py` 只写 `pathspec>=0.6.0`（无上界，见 `51a8c782a:setup.py:66`），而 `dvc/ignore.py` 会把多条 `.dvcignore` 模式的正则用 `"|".join(...)` 拼起来；新版 pathspec 的 `pattern_to_regex` 产生命名组 `(?P<ps_d>...)`，拼接后同名组重复，Python `re` 直接报错。上游后来先封顶（`97809661b setup: pathspec <0.9.0 (#6331)`）再适配（`2a3a93314 pathspec 0.9.0 quickfix (#6689)`）。
   影响面（`deps_scan.txt` / `deps_scan2.txt`，扫了全部 **35 道** dvc 题的 gold 日志）：**8 题命中**（4066、4125、4166、4719、4778、5004、5148，以及 L1_dvc_1 的 5822），gold 侧 169 条失败里至少 80 条是这一条原因。最极端的是 **4778（55 条里 51 条红，P2P=0）** 与 **5822（46 条红）**。
2. **networkx 太旧、与镜像的 Python 3.9 不兼容** → `ImportError: cannot import name 'gcd' from 'fractions'`（`site-packages/networkx/algorithms/dag.py:23`；`fractions.gcd` 在 Python 3.9 被移除）。**4 题命中**（3794、4066、4166、4185）。

直接后果不是"判错分"，而是**P2P 是在一个坏环境下筛出来的通过集**：凡在 gold 下崩掉的用例都不会进 P2P，于是回归保护被静默削掉。几个具体样本：
- **4719**：P2P=0，同文件 4/5 条 run-cache 正向用例全红。
- **4778**：P2P=0，且唯一覆盖题面症状的 `test_add_symlink_file` 也红着，F2P/P2P 都进不去。
- **5148**：test_patch 自己新增的两条功能级验收（`test_cmd_remove_gitignore_single_stage` / `multistage`）在 gold 下就红。
- **4125**：被排除的 `test_ignore_blank_line` 正是 **dvc-4066 的 F2P** —— 同一条测试在 4066 镜像里是判分依据，在 4125 镜像里是环境坏死项。

### 3. 参考 ID 被空白截断：1 条一对多，23 条丢失参数信息（P1/P2）

`parse_log_pytest`（`rh2/src/repoharness2/envpack/swegym_parsers.py`）对摘要行取 `line.split()[1]` 作 test id，nodeid 里只要有空格就被截断。本包 **5/18 题、23/440 条**参考 ID 被截断（`truncated_ids.txt`，每条都附了运行时全名）：

| task | 截断数 | 形态 |
| --- | --- | --- |
| dvc-6954 | **13/13（100%）** | pytest 按参数文本生成 id：`test_parse_valid_types[UNARY_OP = -1-result9]`、`test_parse_invalid_types[SUM = 1 + 2]` |
| dvc-4961 | 6/47 | dict 字面量参数 `build@{'level': 35}` |
| dvc-5188 | 2/27 | 期望错误消息里带空格 `option 'profile' doesn't exist` |
| dvc-4166 | **1/59（一对多）** | 参数以空格开头 `" to_ignore"` |
| dvc-5004 | 1/33 | 参数是 `"To set or not to set"` |

其中 **dvc-4166 是真正的判分缺陷**：P2P 的键 `tests/unit/test_ignore.py::test_match_ignore_from_file[` 同时对应 `[ to_ignore-patterns5-False]` 与 `[ to_ignore-patterns6-True]`（gold 日志第 1639/1640 行），dict 后写覆盖先写，日志里 patterns6 在后，因此 **patterns5 的结果永远被丢弃、永不参与判分**；而这两条恰是判别"尾随空格是否生效"的相反对，合并后判别力归零。与 L2_reference_ids 包独立扫描的结论一致（`truncation_collisions_summary.json` 里 `iterative__dvc-4166 collided_keys=2, reference_ids_on_collided_keys=1`）。

其余 22 条当前**不影响判分**（参考集与 status_map 同样截断，且首 token 互异无碰撞），但都很脆：只要给 6954 再加一个 `INT = 6` 参数，它就会和现有的 `INT = 5` 合并。dvc-6954 的 13 行摘要是现成的 parser 回归语料，建议并入 L2 的 `parser_samples/`。

### 4. 测试段内的 dvc 日志会写进 status_map（与阶段一的 pip 噪声不同，这条在生产路径上也成立）

阶段一离线日志**没有** `>>>>> Start/End Test Output` 标记（grep 计数 0），所以它们的 status_map 是**整份日志**解析出来的，混进了 pip 的 `ERROR: Could not find a version...`（→ 伪键 `Could`、`No`）。生产 v2 入口只取标记段且不回退（`rh2/src/repoharness2/envpack/scoring.py:189-245`），缺标记直接 `apply_ok=False`，所以这类 install 段噪声**不会**出现在生产判分里——引用阶段一 status_map 时要注明这一点。

但有一部分噪声在生产路径上同样成立：**dvc 自己在测试期间打印到 stdout 的 `ERROR: ...` 行落在测试段内**。以 3794 为例，测试阶段从第 473 行开始，其后有 9 条 `^ERROR: ` 行（如 `ERROR: configuration error - config file error: remote 'a' doesn't exists.`、`ERROR: the following arguments are required: new`），加上 pytest 捕获日志的 `ERROR    dvc:main.py:50 configuration error` 一族，产生伪键 `configuration`/`the`/`unexpected`/`dvc:main.py:50`/`dvc:main.py:74`/`dvc.cli:cli.py:92`。18 题里 6 题出现这类段内伪键。

当前这些伪键都不与真实 nodeid 冲突，判分不受影响。但它证明 parser 的唯一门槛是"行首是状态词"，**测试期间进入 stdout 的任意文本都能写进 status_map**——这就是 check 31 所说的控制面。是否存在可利用的伪造路径（例如候选新增 `tests/**/conftest.py` 打印 `PASSED <nodeid>`）我没有实跑验证，也没核对 RH2 是否另有保护，逐题记为 `unknown`。

顺带一条交叉印证：3794 的 gold 在实跑日志里打出 `Remote name '{'overlap'}' already exists.`，直接证实了我在静态审查里指出的 `.format({self.args.new})` 集合字面量 typo。

### 5. 四道题存在可复现的奖励漏洞（P1）

都可以用**一行**改动拿到 `RESOLVED_FULL`，且都有具体的下一实验：

| task | 一行假修复 | 为什么过 | P2P |
| --- | --- | --- | --- |
| **dvc-4778** | `dvc/utils/__init__.py:resolve_paths` 开头 `raise DvcException("x")` | 4 条 F2P 全是 `with pytest.raises(DvcException): dvc.add(...)` | 0（同文件 51/55 已红） |
| **dvc-9391** | `--rev` 加 `type=lambda s: [s]`（或在 5 个 `run()` 里把单值包成列表） | 5 条 F2P 只检查传给 repo API 的是 `rev=["foo"]`，**没有一条传两个 `--rev`** | 24 条全与 `--rev` 无关 |
| **dvc-4719** | `StageCache.save` 开头 `return`（彻底关掉 run-cache） | F2P 只断言 `cache.save(stage) is None`；另两条 `assert get_stage_hash.not_called` 是**永远为真的空断言**（MagicMock 属性而非 `assert_not_called()`） | 0（同文件 4/5 已红） |
| **dvc-5336** | `chmod` 改成 `except BaseException: pass` | F2P 唯一断言是 `assert mock_chmod.called` | 4 条，不覆盖 protect 的调用面 |

共同形状：**F2P 只断言"抛了某个异常 / 某个 mock 被调用 / 参数形状变了"，而不断言最终行为**；同时 P2P 要么为空、要么与被改代码无关。这四题在修好前不应进训练集。

前两条已做静态旁证：**9391** —— `ls.py:16`、`pull.py:27`、`push.py:69`、`remove.py:34` 都写 `rev=self.args.rev`，`show.py:185` 写 `revs=self.args.rev`，全部原样透传，所以在参数上加 `type=lambda s: [s]` 会让 5 个调用点同时得到 `["foo"]`；**4778** —— `dvc/utils/__init__.py:352 resolve_paths` 在 base 里只被 `dvc/repo/add.py:138` 与 `dvc/repo/imp_url.py:20` 调用（`dvc/stage/utils.py:183` 是同名但不同的函数），fixture 建 Repo 的路径不经过它，因此开头无条件 `raise DvcException` 只会影响 add/import——正好是 4 条 F2P 期待抛异常的那条路径。两条仍需真机跑一次才算证实。

### 6. 题面与评分错位是本包最普遍的题意问题（6/18）

不是环境缺陷，而是**题面与 upstream 决定之间的信息落差**，决定性依据几乎都只在**不可见的 `hints_text`** 里：

| task | 题面要的 | 评分要的 | 落差在哪 |
| --- | --- | --- | --- |
| dvc-3794 | `dvc remote modify <name> name <new>` | 新子命令 `dvc remote rename <old> <new>` | hints 里维护者否决 `name`：``"`name` is ugly. `dvc remote rename` is much better."`` |
| dvc-9212 | dvc 原生 `${}` 嵌套插值（会落到 `dvc/parsing/`） | hydra 集成的 `compose_and_dump` 调 `OmegaConf.resolve` | hints 里维护者反问 `You are using the hydra integration, right?`；题面无 hydra 字样 |
| dvc-4778 | 第二次 `dvc add` 应**成功** | 对符号链接目录应**明确报错** | 覆盖题面症状的 `test_add_symlink_file` 因依赖问题在 gold 下也红 |
| dvc-3677 | `.dvc/.gitignore` 反复多出 `/tmp` | `is_tracked('dir')` 必须为 True 的目录跟踪语义 | 因果只在上游 commit message（`doesn't work with directories, which results in ... #3561`） |
| dvc-4785 | 题面直接写 `use res.raise_for_status()` | `pytest.raises(dvc.exceptions.HTTPError)` | 两者无继承关系，照题面做必挂 |
| dvc-9391 | per-rev 的 `-n`（`--rev main -n 5 --rev other -n 3`） | 只要 `--rev` 可重复 | gold 未交付题面请求的功能 |

另有两类较轻的题面问题：**整段重复**（4785：724 字符 = 362×2 逐字相同，hints 同样重复；与 L1_mypy_1 扫出的 6 题重复题面清单一致）；**信息量过低**（5148 题面 267 字符 + hints 99 字符；4124 题面 389 字符且以疑问句收尾）。

### 7. 同族与划分约束

- **dvcignore 三连**：4066 → 4125 → 4166，后两题的 base 都已包含 4066 的参考解（`git merge-base --is-ancestor 3a469f2e9 e4dafb8552/520e01f113` 均为真），三题共用 `tests/func/test_ignore.py`，4166 的 P2P 里甚至直接含 4066 的 F2P `test_ignore_blank_line`。**必须同侧**，且 4166 不能当作对 4066 的独立泛化评测。
- **SCM 二连**：3677 与 5148 同改 `dvc/scm/git/__init__.py`、同用 `tests/unit/scm/test_git.py`，5148 的 base 含 3677 的参考解。
- **同文件邻居**：4778 与 4961 同改 `dvc/utils/__init__.py`（不同函数）；4124 与 5839 同用 `tests/unit/command/test_metrics.py`。
- **dvc-5336 的 base 不在主线**：`9638dde4daf3f338e3538712133c4457e96d23ad`（`dvc: bump to 1.11.12`）不是 `origin/main` 的祖先，只被 tag 1.11.12/13/14 包含，上游是一次 backport/cherry-pick（`bp #5335`）。本包 18 题里唯一一例（`base_branch.txt`）。做跨题时间线推理与数据划分时不能对它用主线祖先关系。

## 最值得用户裁定的 3 个问题

1. **dvc 1.x 的镜像依赖要不要重建？** 现状是 `pathspec` 与 `networkx` 都没按历史锁定，导致 8/35 道 dvc 题在 gold 下就有测试崩溃，P2P 是在坏环境里筛出来的通过集（4719、4778 直接被筛到 P2P=0）。修法是给配方补 `pathspec<0.9.0` 与能在 Python 3.9 上工作的 networkx（或改用 base 时间点的 pip freeze 快照），代价是**所有受影响题的 P2P/F2P 都要重算**，而且重算后 5148 的两条功能级验收、4778 的 `test_add_symlink_file` 有可能从"坏死"变成合格的 F2P，等于修订题目定义（清单第 37 项）。**是重建镜像并重算参考集、只对 P2P=0 的题重建、还是维持现状并接受这些题目前几乎没有回归保护？**

2. **参考 ID 的空白截断怎么修？** 本包 23/440 条被截断，其中 dvc-4166 已经是可证的一对多（一条 P2P 永久不参与判分）。两条路：(a) 改 parser——不再按 `line.split()[1]` 取 id，而是按 `<file>::<...>` 的完整行匹配；(b) 按镜像实际 nodeid 重生成参考 ID。前者改的是共享 parser，影响全部 13 个仓库（清单第 39 项"共享修复会不会破坏其他题"），且会让现有参考集与新 status_map 对不上，必须与重生成一起做；后者是逐题修订。L2_reference_ids 包在做 10 道"参考 ID 缺席"的题，而本包这 23 条属于"参考 ID 存在但已丢信息"，两者是同一个根因的不同表现。**是统一改 parser + 重生成参考集，还是只处理已证明碰撞的个案？**

3. **"F2P 只验异常/mock 而不验行为"这类题怎么处置？** 4778 / 9391 / 4719 / 5336 四题都能用一行改动拿满分，且这四题的 gold 本身没问题——问题在测试设计（源自上游作者的习惯：只补最小单测）。补测试等于修订题目定义，需要人来写新断言并在 base/gold 双侧验证；剔除则损失四道 gold 干净、题面完整的题。另外 3794/9212 这类"题面与 upstream 决定方向不一致"的题，补题面同样是修订。**是投入人力逐题补断言与题面（并把修订版与原版分开记账），还是把这些题降级为评测集/剔除？** 我的建议是：先跑第 5 节那四个一行假修复作为反例证据（成本很低、结论确定），再据此决定投入规模；但这属于数据集取舍，需要用户拍板。
