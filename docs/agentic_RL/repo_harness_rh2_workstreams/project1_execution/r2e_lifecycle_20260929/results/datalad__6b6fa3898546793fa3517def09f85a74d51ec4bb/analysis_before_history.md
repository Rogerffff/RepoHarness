# 私有主审：读历史前的分析（datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb）

- 角色与时间：R2E 私有主审（单题闭环试行，干净上下文），2026-09-29 07:50 +08 起。按 `roles/investigator_r2e.md` 第 1–7 步，读历史之前封存。
- 性质：静态阅读加既有原始日志与账本核对。没有运行项目代码，没有开容器或远端，没有改任何原件。文中"预计"都是源码推断，等协调者实跑。
- 引用约定（都相对仓库根目录）：
  - `PUB/` = `runs/r2e_static_prep_20260924/v3/public/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb/`
  - `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb/`
  - `RD/` = 本题结果目录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb/`
  - `NET` = `PUB/worktree/datalad/support/network.py`（base 版）；`HT` = `PRIV/hidden_tests/test_1.py`；`PT` = `PUB/worktree/datalad/tests/test_network.py`（公开旧测试）
  - 同仓其它题的公开包写作 `PUB16/`、`PUB9b/`、`PUB19/`、`PUB58/`，分别指 `runs/r2e_static_prep_20260924/v3/public/datalad__16c1ffc3…/`、`…/datalad__9ba5de09…/`、`…/datalad__19f5b450…/`、`…/datalad__58ba5165…/`。

## 0. 摘要与暂定处置

**题目**：`URL('weired_url:/')` 在 base 上被解析成 `scheme='file:implicit'`、`hostname=''`、`path='weired_url:/'`，要求改为 `ssh:implicit` / `weired_url` / `/`。根因是标准库 `urlparse` 不把含 `_` 的前缀当 scheme，于是落进 `NET:491-499` 的 file 分支。

**核心发现（按影响排序）**：

1. **T1 误拒合理解（根因 P3：测试要求超出题面）**。隐藏测试在同一个键 `test_url_samples` 里新增 `HT:216-217`：`_check_url('example.com/path/sp1:fname', scheme='ssh:implicit', hostname='example.com/path/sp1', path='fname')`。它要求两件题面没提的事：
   - 冒号前含 `/` 的字符串也要当 ssh，主机名里带 `/`；
   - 由字段拼回字符串时要能原样往返，这需要改 `__str_ssh__`（gold 第一个 hunk）。

   这与 base 对该输入的行为相反：base 得到 `file:implicit`，因为 `/` 不是 scheme 字符，也没有 `@`（`NET:491-499`）。它也与 git 的 scp 式地址约定相反（冒号前有 `/` 就是本地路径；这是外部常识，不是仓库证据），而且上游 datalad 后来自己推翻了这个行为：
   - `PUB19/worktree/datalad/support/network.py:379-382` 与 `PUB58/…/network.py:379-382` 把 `/`、`\`、`#` 排除在主机名之外；
   - `PUB19/worktree/datalad/support/tests/test_network.py:340,362-367` 断言 `f/s:1`、`e.com/p/sp:f` 是 `PathRI`，并附 yoh 2019-05-16 的注释"this looks like a perfectly valid path"。

   因此，按 git 规则实现的合理修复 C-A，以及 gold 式但不改 `__str_ssh__` 的最小修复 C-B，预计都判 0。公开读者独立推出的保留项 K7 也正是"冒号前有 `/` 仍为 file"（`RD/public_read.md` §1.2 K7）。
2. **S1（第 2 步，T2c 示例拟合）**。按题面一般读法（"hostname followed by a colon and a path"），核心要求的直接断言只有示例字面值 `weired_url:/`（`HT:206`）。唯一的非示例目标实例是上面那条无依据的 `/` 主机名断言。现在退化候选之所以得 0，靠的恰恰是这条应删的断言，所以删它时必须同时补非示例实例（R-c）。
3. **核心判据经候选可改的 `URL.__eq__`**。`_check_url` 用 `eq_(URL(url), url_)` 比较解析结果（`HT:115`），走的是 `URL.__eq__`（`NET:537-540`），而这个方法候选可以修改。把 `__eq__` 改成比较字符串、再带上 gold 的 `__str_ssh__` hunk、完全不修解析器的候选 D-eq，预计 17/17 得 1，而题面示例的症状原样保留。若实跑证实，按第 4 步是 S1。目前要绕过还需要那个无依据的 `__str_ssh__` 行为，所以实际风险偏低；但 T1 那条断言删掉以后，只改 `__eq__` 就能得 1。修订时必须加不经 `__eq__` 的字段断言。
4. **其它登记项**：
   - G1→T3：gold 的未测回归，都是边缘路径。其一，`/some/dir:x`、`rel_dir/sub:x` 这类本地路径变成 ssh，`is_url` 返回 True，`install` 会把它们当 URL（`PUB/worktree/datalad/distribution/install.py:292-321`）；其二，query 里含冒号的爬虫模板会抛 `ValueError`（`PUB/worktree/datalad/crawler/pipeline.py:465-469,487`）。
   - T5：期望 FAILED 的键 `test_get_local_file_url_linux` 由 Python 3.7 的 `quote` 行为造成，无需修订。
   - X1：本题修复以演化后的形式出现在另外 4 道 datalad 题的初态里，机械扫描漏报。
   - P4：题面把缺陷说得比实际宽；"hostname undefined"实为空串。

**暂定处置**：`needs_review`，理由是"题意/测试争议（T1）加 S1（T2c，D-eq 待证）"。建议一轮修订：先用 R-a 删 `HT:211-217`，再用 R-c 补非示例实例和不经 `__eq__` 的字段断言（§9）。v1 用途暂定：

| 用途 | 暂定 |
|---|---|
| 问题定位 | yes |
| 能力比较 | conditional（差 T1 修订验收与 actor devcheck；在此之前只作问题定位） |
| 训练候选 | conditional（差 R-a + R-c 验收、D-eq / D-hard 在修订版为 0、Codex 复核） |
| 留出评测候选 | no（当前材料） |

**最关键未知**：C-A 与 D-eq 的正式评分结果，以及 actor 侧 devcheck。**唯一最值得先做的下一步**：用正式评分跑 C-A（§8），它直接决定 T1 是否成立。

## 1. 公开读者没有捕获的条件（第 1 步）

- 没有捕获模型实际收到的消息：`PUB/user_prompt.txt` 只是静态渲染；`public_hints` 写进容器的 `/rh2/public_task_bundle.json`，不注入系统提示（`r2e_environment_card.md` §2）。
- 容器条件公开读者全是推断。目前只有**评分侧**实测：
  - Python 3.7.9、pytest 7.4.4、pluggy 1.2.0、pytest-cov 4.1.0；
  - nose 装在 `.venv` 里（`eq_` 来自 `.venv/lib/python3.7/site-packages/nose/tools/trivial.py:29`，见 noop 日志 104 行）；
  - `datalad` 从 `/testbed/datalad/__init__.py` 导入，版本 `0.2.dev1`（账本 `observations`）。

  以下都要等协调者的 devcheck，以 agent（uid 54321）身份核对：mock / GitPython / patool 能否导入、`git` 可执行文件是否在、HOME 可写、`.git` 里修复提交是否已清掉。
- 公开读者的 5 条命令与预计结果我复核过，推断与源码一致；需要 devcheck 给出的具体观测见 §8.1。

## 2. 隐藏测试展开（第 2 步）

**材料**：`HT` 是修复提交后的 `datalad/tests/test_network.py`，相对导入改成了绝对导入（`diff PT HT` 只差导入、`_check_url` 新增一行、`test_url_samples` 新增 207-217 行）。另外两份：
- `PRIV/hidden_tests/conftest.py`：`path` fixture，以及把 HOME 换成临时目录、执行 `git config --global` 的 autouse fixture，与本题无关；
- 空的 `__init__.py`。

期望映射共 17 键（`PRIV/expected_output.json`）：16 个 PASSED，`test_get_local_file_url_linux` 为 FAILED。`test_get_url_straight_filename` 是 yield 测试，pytest 7.4.4 下为 XFAIL [NOTRUN]，不成键（noop 日志 145 行）。

**目标键**：`test_url_samples`，这是唯一的 noop/gold 差异键。依据是 `run_refs.json` 的 current 行：两次 noop 的 mismatched 都是 `[test_url_samples]`，两次 gold 都是 17/17。

| 断言（`HT` 行） | 调用路径与输入 | 最终断言 | base | gold | 公开依据 |
|---|---|---|---|---|---|
| 206 `weired_url:/` | `_check_url`（112-122）：`URL(url)` 走 `_set_from_str`；`url_ = URL(**fields)` | 115 行 `URL(url) == url_`（经 `URL.__eq__` 比较 `_fields`）；116 行 `str(URL(url)) == url`（恒真，`_str` 存原串，`NET:524`）；117 行同 115；118 行 `url == str(url_)`（经 `_as_str`→`__str_ssh__` 往返）；121-122 行 `url_` 的字段（恒真） | 在 115 行失败，日志与题面症状一致 | 通过 | 题面示例 |
| 207 `example.com:/`、208 `example.com:path/sp1` | `urlparse` 把 `example.com` 识别为 scheme（字母与 `.`），走 `NET:483-489` | 同上 | 推断通过 | 通过 | base 已有行为（回归） |
| 209-210 `example.com/path/sp1\:fname` → `file:implicit` | 转义冒号，`_split_colon` 不切 | 同上 | 推断通过 | 通过 | `_split_colon` 约定（`NET:595-597`、`PT:99-104`） |
| **216-217** `example.com/path/sp1:fname` → ssh，`hostname='example.com/path/sp1'`、`path='fname'` | 冒号前含 `/` | 115 行要求解析成 ssh；118 行要求 `str(URL(scheme='ssh:implicit', hostname='example.com/path/sp1', path='fname')) == 'example.com/path/sp1:fname'`。base 的 `__str_ssh__` 会把 hostname 里的第一个 `/` 换掉，得到 `example.com:path/sp1/fname` | 推断失败（file） | 通过（靠两个 hunk） | **无**（P3；与 base 行为、git 约定、上游后续实现相反） |
| 226-234 `weired://` 告警 | `swallow_logs` 加正则 | 精确告警文本 | 通过 | 通过 | base 行为（`PT:215-223`） |

- noop 日志在 206 行即中止（`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-d_df2e5fa5.eval.log:86-102`），所以 207-234 行在 base 上**没有执行证据**，上表 base 列是源码推断。gold 下整段执行并 PASSED（gold 日志 62 行）。
- **回归键**（15 个 PASSED 键）：与公开测试逐函数相同，只有导入不同。我通读了 `HT` 全文，受影响接口是 `URL._set_from_str`、`__str_ssh__`、`is_url`、`parse_url_opts`：
  - 覆盖到的：http、ssh、file、datalad、dl+archive、hg+https、git 各形式，`is_url` 的否定例，`parse_url_opts` 的 http / s3 例子；
  - 没覆盖的：冒号前有 `/` 的本地路径应保持 file（K7）、query 里带冒号的模板（K8）、`host1:22`、大写主机名、`install` 等调用者。

## 3. 需求—断言双向表（第 3 步）

### 3.1 公开要求 / 合理旧行为 → 断言

| 要求（编号沿用 `RD/public_read.md`） | 公开依据 | 断言 | 覆盖 | 证据 / 下一步 |
|---|---|---|---|---|
| C1 示例三字段 | `PUB/user_prompt.txt:10-22` | `HT:206`（115 / 118 行） | 覆盖，但经 `URL.__eq__` 间接比较 | noop 在 206 行失败，gold 通过。D-eq 待跑 |
| C2 其余字段为空串 | `PT:112-121` 比较全部 `_fields` | `HT:206`（115 行） | 覆盖（同上） | 同上 |
| C3 往返 | `PT:117-118` | `HT:206`（118 行） | 覆盖；base 的 `__str_ssh__` 本来就满足 | — |
| C4 一般情形：任意"主机名:路径"，主机名含 `urlparse` 不认的字符 | `PUB/user_prompt.txt:7`；类文档 `NET:281-283` | 无非示例实例（216-217 行的主机名含 `/`，按一般读法不是 hostname） | **缺失 → T2c** | R-c（§9） |
| C5 `is_url('weired_url:/')` 为 True（题面所说的 "downstream"） | `NET:613-624` 文档 "includes ssh urls which git understands" | 无 | 缺失（C1 成立后自动满足） | R-c 可选 |
| K1–K6 已有形式与 `_split_colon` 约定 | `PT` 相应行 | `HT` 同名函数及 207-210 行 | 覆盖 | gold 日志全部 PASSED |
| **K7 冒号前有 `/` 的本地路径保持 file** | base 行为（`NET:491-499`）；git 约定（外部）；上游后续（`PUB19/…/support/tests/test_network.py:340,367`） | `HT:216-217` 要求相反 | **冲突 → T1** | C-A、C-B 实跑 |
| K8 query 含冒号的爬虫模板不抛错 | `PUB/worktree/datalad/crawler/pipeline.py:465-469,487` | 无 | 缺失；gold 在此回归 | 登记 T3 |
| `get_local_file_url('/a~') == 'file:///a%7E'` | `PT:280`（过时，见 §4a） | `HT:291`，期望 FAILED | 不是本题要求 | T5 登记 |

### 3.2 关键断言 → 公开依据（反查）

- `HT:206`：有依据（题面示例）。
- `HT:207-210`：base 已有行为与转义约定，属于合理回归检查。
- `HT:116`：恒真，因为 `_str` 存原串。
- `HT:226-234`：base 已有告警文本，公开测试里有同样断言。
- **`HT:216-217`：没有公开依据**。
  - 题面只说 "hostname followed by a colon and a path"；`example.com/path/sp1` 不是主机名。
  - base 公开测试、文档、类说明都没有"主机名可含 `/`"。
  - 测试注释引 ssh 为据（`HT:211-215`），但 ssh 本身根本不按冒号切，会把整串 `example.com/path/sp1:fname` 当作主机名。这条理由也不支持"在冒号处切开、前半当主机名"。
- `HT:291` FAILED：环境造成，不对应任何本题要求（§4a）。

### 3.3 替代实现与部分实现（有具体疑点才提）

- 合理替代解 C-A：沿用 git 规则。它满足 C1–C5，保留 K1–K8；和 gold 只在"冒号前有 `/`"一处不同。疑点正是 216-217 行。
- gold 式最小修复 C-B：只改解析、不改 `__str_ssh__`，是最像真实模型会写的修法。它在 216-217 行的往返断言（118 行）上失败。
- 可能蒙混的错误实现 D-eq：绕过比较器，疑点是 115 行依赖候选可改的 `__eq__`。
- 退化候选 D-hard：只把示例写死。

四个候选的补丁描述见 §8。

## 4. R2E 专项（第 4 步）

**(a) 非 PASSED 键**：只有 `test_get_local_file_url_linux` 期望 FAILED。

- 原因：`HT:291` 的 `get_local_file_url('/a~')` 在 Python 3.7 下得到 `file:///a~`，因为 3.7 起 `urllib.parse.quote` 不再转义 `~`；测试期望 `%7E`。
- 执行证据：noop / gold 日志的失败点相同（noop 日志 105-124 行，gold 日志 25-44 行），M3 独立 runner 也相同。
- 本题的正确修复（包括更完整的修复）不碰 `get_local_file_url`，不会把它翻成 PASSED。只有越界"顺手修"公开失败测试、把 `~` 编码成 `%7E` 的候选会被翻转而判 0。
- 这种顺手修并不更正确：上游后来把期望改成了 `('/a~', 'file:///a~')`（`PUB58/worktree/datalad/support/tests/test_network.py:477-487`）。
- 结论：T5 登记，状态有固定来源解释，不需要 R-a。探针分析时，模型改 `get_local_file_url` 按越界处理。公开测试在 base 上本来就有这 1 个失败，不算模型改错，类似 P6。

**(b) 题面症状是否出现在 noop 目标键的失败原因里**：是。noop 在 `HT:206` 报 `AssertionError: URL(path='weired_url:/', scheme='file:implicit') != URL(hostname='weired_url', path='/', scheme='ssh:implicit')`，与题面 "Actual Behavior" 一致（noop 日志 86-102 行；环境轮复跑逐字相同，只差时间戳）。

**(c) 题面是否泄漏修法**：没有。题面只写症状。公开旧测试 `PT:204-205` 的注释点出了根因（scheme 字符限制），这是 base 公开材料，只是定位线索，不是 P1。

**(d) 测试辅助、搬迁伪影、撞键**：

- `HT` 依赖 base 版 `datalad.tests.utils`：`eq_`、`neq_`、`ok_`、`nok_`、`assert_raises` 转自 nose；`skip_if_on_windows`、`assert_re_in`、`get_most_obscure_supported_name` 定义在 `PUB/worktree/datalad/tests/utils.py`；`swallow_logs` 来自 `datalad/utils.py:543`。候选可以改这些文件，评分不重置。这是通用的控制面风险（40 项清单第 31 项），公开提示禁止改测试文件，按共享机制引用 A 线审查，逐题不另报。
- 更值得注意的是本题特有的**非测试源码比较器** `URL.__eq__`（D-eq），见 §7。
- 搬迁伪影：只有相对导入改绝对导入；base 没有 conftest 或 pytest 配置；只有一个隐藏文件，不会跨文件撞键。

**(e) 时间 / 随机 / 资源敏感**：

- `test_rfc2822_to_epoch` 用固定时区偏移；`get_most_obscure_supported_name` 在临时目录建文件，Linux 文件系统下结果确定；全程不联网。
- 测试段约 1–2 s，内存峰值约 560 MB（账本 `resource`）。
- current 材料下 noop ×2、gold ×2 逐键一致，M3 独立 gold ×2 也一致。未见 E5。

**(f) 材料修订**：`PRIV/revisions.json` 为 `[]`，没有已批准的修订。

## 5. gold 检查（第 5 步）

- **原例修到**：是（执行证据：gold 日志 62 行 `test_url_samples` PASSED；M3 独立 runner 在来源镜像上也 PASSED）。
- **改动**：`PRIV/gold.patch` 有三个 hunk。
  - hunk 1（5-23 行）：`__str_ssh__` 改为只替换主机名之后的第一个 `/`，注释写明"尽量像 ssh 一样笨，主机名里可以有 `/`"；
  - hunk 2：删了一个空行；
  - hunk 3（34-46 行）：在"无 scheme、无主机名"分支加 `len(_split_colon(url)) > 1` 即判为 ssh。它对整串（含 query）找未转义冒号，也不排除 `/`。
- **超出题面**：hunk 1 和 hunk 3 对 `/` 的处理实现的是题面没要求的行为（216-217 行），上游后来推翻了它（见 §0 第 1 条的出处）。
- **未测回归（G1→T3）**，都是源码推断，devcheck 的私有 gold 对照若跑了 `edge_case_survey` 可以直接证实：
  1. `/some/dir:x`、`rel_dir/sub:x` 由 file 变成 ssh（主机名分别是 `/some/dir`、`rel_dir/sub`），`is_url` 变为 True。`install` 用 `is_url` 判定目标路径（`PUB/worktree/datalad/distribution/install.py:292-299,309,321`），含冒号的本地路径会被当 URL。
  2. `openfmri_s3?_url=s3://b/k` 这类 query 含冒号的模板被判为 ssh，然后在 `NET:505-511` 抛 `ValueError`，经 `parse_url_opts` 让 `load_pipeline_from_config` 失败。这是 `pipeline.py:465-469` 文档允许的写法，但仓库里的标准配置按 `_k=v` 分行写（`initiate_pipeline_config`），所以属于罕见路径。
  3. `weired_url:/p?x=1` 抛 `ValueError`；base 上是 file 加 query，公开读者把它列为有歧义的边界 A2。
  4. 用户名加含 `/` 的主机名往返错误：`URL(scheme='ssh:implicit', username='user', hostname='a/b', path='c')` 会得到 `user@a:b/c`，因为 hunk 1 用 `len(hostname)` 在带 `user@` 的串上切，位置错了。

  四项都是边缘输入或罕见路径，按 §4 第 4 步是 S2（T3），不单独作为处置依据。
- **判定理由**：不是"与 gold 不同"。gold 满足题面，但把一个题面没有、且上游后来推翻的设计选择写进了评分，并带来上述未测回归。

## 6. 开发需求（第 6 步；环境卡 + `PUB/environment_brief.md`）

| 项 | 内容 | 证据级别 |
|---|---|---|
| 解释器与导入 | `/testbed/.venv/bin/python` 3.7.9；导入链需要 `six`、`requests`、`appdirs`；导入的必须是 `/testbed/datalad` | 评分侧实测（账本 `RH2_OBS_IMPORT_PATH`）；**actor 待验**（devcheck `import_env`） |
| 测试依赖 | 公开测试和 `_check_url` 需要 nose、mock、GitPython（加 `git`）、patool；pytest 7.4.4 | 评分侧实测（gold 通过即说明能导入）；actor 待验（`repro_check_url_helper`、`public_test_network`） |
| 资产 | 无 | 源码推断 |
| 权限 | 写 `/testbed/datalad/support/network.py`；`import datalad` 会在 HOME 下建配置目录 | brief 说 agent 可写 `/testbed` 与 home；actor 待验 |
| 网络 | 准备、解题、安装、测试四个阶段都不需要 | 源码推断；评分 `network=deny_all` 下通过 |
| 构建 | 纯 Python，无编译 | 源码推断 |
| 提交边界 | 只改一个非测试源文件；gold 的投影 `included_paths=['datalad/support/network.py']` | 评分侧实测（gold 账本 line 14 `projection`） |
| 公开验证路径 | 题面示例可用 `python -c` 复现；可以不改测试文件、直接调用 `_check_url`；公开测试文件预计 16 passed / 1 failed（`~`）/ 1 xfailed，不能区分修复前后 | 源码推断；actor 待验 |
| 最小验证墙钟 | 测试段约 2 s | 评分侧实测 |
| 目标调用链版本一致性（E1） | 目标行为只依赖标准库 `urllib.parse`（3.7 特有的"冒号后全是数字当端口"判断）；actor 与 grader 用同一张派生镜像 | 环境卡 §2（代码配置）；本题无 E1 疑点 |

- 评分侧环境身份（旧机器）：镜像 `rh2-r2e-derived/datalad:6b6fa3898546-r2e_derive_v1`，ID `sha256:acb73dcd…`，配方 `r2e_derive_v1`（`sha256:0da821a1…`），无 env / 资源配方（`PRIV/run_refs.json` `current_material`）。
- 新机器上重建的镜像 ID 会不同，以协调者新跑的记录为准。

## 7. 严重度（v1 §4）与问题编号

| 步 | 判断 | 证据 |
|---|---|---|
| 1 核心要求有直接断言 | 有。`HT:206` 的字段加往返断言，但字段比较经候选可改的 `URL.__eq__`，见第 4 步 | §2 |
| 2 只用示例字面值 | **命中（T2c，S1）**。按题面一般读法，核心要求的目标实例只有 `weired_url:/`。唯一的非示例目标实例 216-217 行不是一般读法下的主机名，且本身是 T1 | §3.1 C4 |
| 3 退化探测 | 候选 D-hard（写死示例），预计 0，**未命中**；但只因为有 216-217 行这条无依据断言。删掉它而不补 R-c 的话，预计得 1 | §8.2，待实跑 |
| 4 已有 / 构造候选 | **预计命中**：D-eq 预计得 1，而题面示例本身仍是 `file:implicit`，比"违反其它实例"更严重，也破坏了 `URL` 按字段判等这一公开行为（`NET:537-540`、`PT:108-109`）。gold 自身的回归只涉及边缘路径 → S2（T3） | §8.2，待实跑 |
| 5 | 不适用：已有 S1 | — |

**问题清单**：

| 编号 | 问题 | 证据层次 |
|---|---|---|
| T1（根因 P3） | `HT:216-217` 与隐含的 `__str_ssh__` 要求 | 静态推断；上游后续行为是跨题公开包证据；C-A / C-B 实跑待做 |
| T2（T2c） | 核心要求只有示例字面值 | 静态 |
| T2（第 4 步） | 核心判据经候选可改的 `URL.__eq__` | 静态；D-eq 实跑待做 |
| T3 / G1 | gold 的未测回归 K7、K8、A2 与用户名往返 | 静态；devcheck gold 对照可证 |
| T5 | 期望 FAILED 的 `~` 键，环境造成 | 执行证据加上游后续证据 |
| P4 | 题面把缺陷说宽；"undefined" 实为 `''`；标题的 "Parsing Failures" 在 base 上并不抛错 | 静态；公开材料能消解 |
| X1 | 题目关系，见 §10 | 跨题公开包 |

E1–E5、D1、P1、P2、P5、X2、H1 都没发现。

关于 P5 的判断：216-217 行这件事**不按 P5（两种读法都有依据）处理**。测试采用的读法没有 base 时点的公开依据，另一种读法有 base 行为与外部约定支撑，所以走 P3→T1，也不适用 R-f（R-f 不得新增无依据的要求）。若复核认为 base 里 `@` 分支对 `user@a/b:c` 的"笨"处理（`NET:492-494,513-520`）构成依据，就改按 P5 交用户决定。我认为不构成：那只是 `@` 形式下未加检查，base 的 `__str_ssh__` 也不支持含 `/` 的主机名往返。

## 8. 需要协调者实跑的内容

### 8.1 devcheck（协调者正在跑）里需要取出的观测

1. `import_env`：3.7.9，导入路径为 `/testbed/datalad/__init__.py`。
2. `repro_issue_example`：base 上以 `AssertionError: ('file:implicit', '', 'weired_url:/')` 退出，用来确认原例在解题侧复现。
3. `repro_check_url_helper`：base 失败的是 `AssertionError`，不是 `ImportError`，用来确认 agent 能导入测试辅助。
4. `edge_case_survey`：
   - base 上 `/some/dir:x`、`rel_dir/sub:x` 为 file，作为 T1 论证的执行证据；
   - 私有 gold 对照若跑了同一命令，看 `/some/dir:x` 是否变 ssh、`openfmri_s3?_url=s3://b/k` 与 `weired_url:/p?x=1` 是否报 `EXC ValueError`，作为 T3 的执行证据；
   - 3.7.9 下 `host1:22` 的结果。
5. `public_test_network`：16 / 1 / 1，且失败的只是 `~` 那一项。

### 8.2 定点正式评分（本题控制面保护时限放宽到 1200 s，评分语义不变）

每个候选都要核对三点：投影 `included_paths` 含 `datalad/support/network.py`（补丁确已交付）；日志里 `test_url_samples` 确已执行，并看失败行号；给出完整的逐键映射。

**C-A｜合理替代解（git / scp 规则）——判 T1。优先级 1。**

- 文件与函数：`datalad/support/network.py` 的 `URL._set_from_str`，改 `NET:491-499`，其余不动（`__str_ssh__` 保持 base）。
  ```python
          if not fields['scheme'] and not fields['hostname']:
              parts = _split_colon(url)
              if fields['path'] and '@' in fields['path']:
                  # user@host:path/sp1
                  fields['scheme'] = 'ssh:implicit'
              elif len(parts) > 1 and not set(parts[0]).intersection('/\\#?'):
                  # host_name:path -- scp-like, only if no '/', '\', '#', '?' before the colon
                  fields['scheme'] = 'ssh:implicit'
              elif url.startswith('//'):
                  # e.g. // or ///path
                  fields['scheme'] = 'datalad:implicit'
              else:
                  fields['scheme'] = 'file:implicit'
  ```
- 为什么合理：
  - 满足 C1–C5；
  - 保留 K1–K8，包括 base 对 `/some/dir:x` 的 file 行为，以及模板 query 不被误判；
  - 与上游后来的规则（`PUB19/…/network.py:379-382`）基本一致，只多排除了 `?`。
- 预计：只有 `test_url_samples` 不符，失败在 `HT:216` 经 `_check_url` 的 115 行，报 `URL(path='example.com/path/sp1:fname', scheme='file:implicit') != URL(hostname='example.com/path/sp1', path='fname', scheme='ssh:implicit')`。其余 16 键与期望相同，reward 0。
- 正对照核实：v1 §5 要求正对照先核实确实满足公开要求。建议协调者在私有对照里对 C-A 的工作区跑 §8.1 的 2–5 条公开命令：示例通过；`weired:/`、`user@weired_url:/`、`like@sshlogin`、`weired://` 不变；带 `/` 的两项与模板保持 file；公开测试 16 / 1 / 1。

**D-eq｜可能蒙混的错误实现（绕过比较器）——判第 4 步 S1 与 R-c 设计。优先级 2。**

- 文件与函数：`datalad/support/network.py`，改两处。
  1. `URL.__str_ssh__`（`NET:345-355`）：原样套用 gold 第一个 hunk（`PRIV/gold.patch:5-23`）；
  2. `URL.__eq__`（`NET:537-540`）改为：
     ```python
         def __eq__(self, other):
             if not isinstance(other, URL):
                 other = URL(other)
             return str(other) == str(self)
     ```
  `_set_from_str` 不动。
- 违反的公开要求：题面示例本身。`URL('weired_url:/')` 仍是 `scheme='file:implicit'`、`hostname=''`、`path='weired_url:/'`，`is_url('weired_url:/')` 仍为 False；URL 判等也不再比较字段。用公开命令 `repro_issue_example` 在该候选的工作区里跑，预计仍然 `AssertionError`，可作后检。
- 预计：17/17，reward 1。推理：
  - `_check_url` 115 与 117 行变成比较 `str(URL(url))`（即原串）和 `str(url_)`，等价于 118 行本来就要求的往返；
  - `url_` 的往返靠 gold 的 `__str_ssh__` 成立；
  - `test_url_eq` / `test_url_base` 里 `URL()` 与 `URL(hostname='x')` 的字符串是 `''` 与 `'//x'`，`neq_` 仍然成立；
  - 其它键不经 `__eq__`。
- 若得 1：按第 4 步是 S1，R-c 必须加不经 `__eq__` 的字段断言。另可补跑 D-eq-minus（只改 `__eq__`、不带 gold hunk），当前材料下预计 0，失败在 216-217 行的 118 行往返。它主要用于修订验收。

**D-hard｜第 3 步退化候选（只有这一个）：与输入无关的固定结果，改在 gold 的修改位置。优先级 3。**

- 文件与函数：`datalad/support/network.py` 的 `URL._set_from_str`，`NET:492` 改为 `if fields['path'] and '@' in fields['path'] or url == 'weired_url:/':`，其余不动。
- 违反的公开要求：题面的一般表述 "hostname followed by a colon and a path"。`URL('my_host:path/sp1')`、`URL('weired_url:path')` 仍为 `file:implicit`。
- 预计：`test_url_samples` 在 `HT:216` 失败，reward 0，第 3 步未命中。要注明挡住它的是 T1 那条无依据断言，修订后必须仍为 0（§9 的验收）。

**C-B｜gold 式最小修复（无 `__str_ssh__` 改动）——可选，用来量化 T1 的波及面。优先级 4。**

- 只应用 `PRIV/gold.patch` 的第 3 个 hunk（`_set_from_str` 加 `parts = _split_colon(url)` 与 `or len(parts) > 1`），不应用第 1 个。
- 预计：`test_url_samples` 在 `HT:216` 经 118 行失败，报 `'example.com/path/sp1:fname' != 'example.com:path/sp1/fname'`，reward 0。
- 它说明：沿用 base `@` 分支风格、最自然的修法也被判 0，因为题面没要求含 `/` 主机名的往返。

**不需要跑的**：gold 再加上把 `get_local_file_url` 的 `~` 编码成 `%7E`，按判分规则必然 0（键翻成 PASSED），见 §4a。

## 9. 修订建议草案（v1 §5；待协调者实施与实测、Codex 复核）

**R-a，删无公开依据的断言（键集不变）**

- 改动：删 `HT:211-217`，即 `# ssh is as stupid as us…` 注释、212-215 行的 docstring、216-217 行的 `_check_url('example.com/path/sp1:fname', …)`。保留 207-210 行。
- 依据：
  - 题面没有这项要求；
  - base 对该输入是 file（合理旧行为）；
  - 上游后来推翻了它（`PUB19/…/support/tests/test_network.py:362-367`）。
- 删掉后，冒号前带 `/` 的输入两种结果都接受，不另加反向断言。反向断言会让 gold 失败，也会新增题面没有的要求；若要按上游后续行为收紧，属于模板外，需要用户决定。

**R-c，补有依据的断言（与 R-a 同一轮完成，分别列依据）**

1. 非示例实例（依据：题面一般表述与类文档 `NET:281-283`）。在 `HT:206` 之后加：
   ```python
       _check_url('my_host:path/sp1', scheme='ssh:implicit', hostname='my_host', path='path/sp1')
       _check_url('data_server.example.org:/srv/ds', scheme='ssh:implicit', hostname='data_server.example.org', path='/srv/ds')
   ```
   主机名与示例不同，一个相对路径、一个绝对路径。静态推算：gold、C-A、C-B 都通过；base 与 D-hard 失败。
2. 不经 `__eq__` 的字段断言（依据：题面示例读的就是解析结果的 `.scheme` / `.hostname` / `.path`，这些是公开属性，`NET:591-592`）。在 `_check_url` 的 `url_ = URL(**fields)`（`HT:114`）之后加：
   ```python
       parsed = URL(url)
       for f in URL._FIELDS:
           eq_(getattr(parsed, f), getattr(url_, f))
   ```
   现有所有输入在 gold 下都满足（gold 原本就满足 `_fields` 相等）；D-eq 与 D-eq-minus 会在 206 行失败。
3. 可选：在 `test_is_url`（`HT:273-285`）加 `ok_(is_url('weired_url:/'))` 与 `ok_(is_url('my_host:path/sp1'))`。依据是 `is_url` 的文档（包括 git 能理解的 ssh 地址）与题面所说的 "downstream"。

**验收计划**：

| 候选 | 修订版应得 |
|---|---|
| gold | 1 |
| noop | 0（失败在 206 行） |
| C-A | 1（本次要纠正的误判） |
| C-B | 1（可选） |
| D-hard、D-eq、D-eq-minus | 0 |

另外核对：键集仍为 17 个、`test_get_local_file_url_linux` 仍为 FAILED、XFAIL 不成键。保存新版本、父版本、理由与触发反例（父版本上 C-A 为 0、D-eq 为 1）。修订后的题只作标明版本的自建题。

**待用户决定**：无，除非复核把 216-217 行改判为 P5（见 §7 末段）。

## 10. 题目关系（第 8 方面）

- 机械扫描：`runs/r2e_static_prep_20260924/cross_task_gold_scan.json` 与 `cross_task_test_scan.json` 都没有涉及本题的记录。
  - test 扫描按设计本来就看不到本题：隐藏测试没有新的测试函数名，改动都在已有函数内部；
  - gold 扫描**漏报**：gold 的 `__str_ssh__` 行后来被重构，逐字命中不到 80%。
- 人工核对（只读同仓其它题的公开包）：
  - **本题修复包含在另外 4 题的初态里**：
    - `PUB16/worktree/datalad/support/network.py:301-305` 与 `PUB9b/` 同位置，逐字含 gold 的判断式 `if fields['path'] and '@' in fields['path'] or len(parts) > 1:` 与注释 "or host_name: (hence parts check)"；
    - 两题的公开测试 `support/tests/test_network.py:266,271-276` 含本题两条目标断言的 RI 版本（`weired_url:/`→SSHRI、`example.com/path/sp1:fname`→SSHRI）；
    - `PUB19/` 与 `PUB58/` 含后来演化、排除了 `/` 的规则（`network.py:379-382`）。
  - 反方向：本题 base（`2753d472`，`network.py` 663 行，RI 重构之前）是这 5 道 datalad 题里最早的，没发现其它题的修复出现在本题初态。
  - 上游后续推翻了本题的 `/` 主机名行为：`PUB19/…/support/tests/test_network.py:340,362-367`，`PUB58/…:314,335-340`。
- 用途含义：
  - 训练时控制与这 4 题的重复采样：它们的初态里就有本题答案和测试；
  - 留出按 D3 按仓库划分，datalad 5 题同进同出；
  - 审查暴露：本主审已读 gold、隐藏测试和同仓其它题的公开包。
- 任务类型：小型解析缺陷修复，改一个文件。题面不给修法。外部答案可达性（上游仓库）按正式 profile 断网处理，未另核。

## 11. 八方面覆盖与未查项

| 方面 | 已查 | 未查 / 缺项 |
|---|---|---|
| 公开需求 | 题面、公开读者稿、`NET` 全文、`PT` 全文、调用者（install、crawler、archives） | 模型实际收到的消息 |
| 材料与初态 | base / 来源提交 / gold / 隐藏测试 / 期望映射对应；初态 diff 为 0 字节（`PUB/worktree_manifest.json` `initial_diff`）；noop 失败位置 | 216-217 行在 base 上的执行证据（noop 在 206 行中止） |
| 测试是否测到要求 | `HT` 全文；目标键逐断言；回归键按接口抽查 | — |
| 误拒 | C-A / C-B 的静态推算 | 正式评分实跑 |
| 回归与 gold | gold 三个 hunk；K7、K8、A2 与用户名往返的推算 | gold 对照的 `edge_case_survey` 执行证据 |
| 开发条件 | 评分侧实测事实；公开命令复核 | actor 侧 devcheck 全部待给 |
| 交付与评分边界 | 投影路径、测试辅助依赖、`__eq__` 比较器 | 候选改测试辅助的通用风险按 A 线审查引用，逐题未另测 |
| 题目关系 | 两份扫描加 4 题公开包人工核对 | 其它来源（非 R2E）是否重复：未查 |

**卡片阶段仍要补的**：本批 README §3 的探针就绪标准。通用规则不允许我现在读 README，需要协调者在第二步提供。

## 附录：实际阅读范围

- 方法：角色卡；八方面协议；R2E 环境卡；记录模板；40 项清单；统一标准 v1。
- 本题公开：`RD/public_read.md`、`RD/commands.json`；`PUB/` 下的 `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`，以及 `worktree_manifest.json` 的顶层字段；`NET` 全文；`PT` 全文；以下文件的片段：
  - `worktree/datalad/distribution/install.py`（100-145、280-340）
  - `worktree/datalad/crawler/pipeline.py`（450-500 与 `initiate_pipeline_config`）
  - `worktree/datalad/interface/crawl.py`（40-100）
  - `worktree/datalad/tests/utils.py`（1-60、895-930）、`worktree/datalad/tests/__init__.py`、`worktree/datalad/utils.py`（540-600）
  - `docs/examples` 与 README 中 ssh 的 grep 结果
- 本题私有：`PRIV/` 下全部文件（`gold.patch`、`expected_output.json`、`run_tests.sh`、`revisions.json`、`run_refs.json`、`grading_bundle.json`、`validation_bundle.json`、`hidden_tests/*`）。
- 原始运行证据：`run_refs.json` 列出的 4 份 current 日志（核过 sha256）与 4 份账本的第 14 行；M3 独立参考 a1 日志（尾部）与账本第 27 行。
- 同仓其它题的公开包（只读公开部分）：4 题的 `public_bundle.json` 题面首行、`network.py` 相关片段、`support/tests/test_network.py` 的 grep 结果与片段。
- 两份跨题扫描 JSON。
- 没读：任何 history、审查目录、本批 README / board / assignments、其它题的私有包、`runs/` 下的分析汇总文件。
