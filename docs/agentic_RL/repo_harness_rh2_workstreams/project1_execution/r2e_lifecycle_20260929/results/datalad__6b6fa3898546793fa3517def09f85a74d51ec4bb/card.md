# datalad `6b6fa389` 题卡（R2E，单题闭环试行）

## 版本与引用约定

- 作者：私有主审；2026-09-29。
- 材料：`expected_v0`，本题没有修订；v3–v11 材料对本题相同。
- 镜像：`rh2-r2e-derived/datalad:6b6fa3898546-r2e_derive_v1s`，ID `sha256:2ec5e89b…`，配方 `r2e_derive_v1+sysconfig_v1`。
- 评分：`r2e-gym-subset@e8b9fcbc+parser:prime-envs@c4d04dfe`；代码 `code_v9`。
- 引用缩写：
  - `HT` = `PRIV/hidden_tests/test_1.py`，`NET` = `PUB/worktree/datalad/support/network.py`；`PUB`、`PRIV`、`RD` 的含义同 `analysis_before_history.md`；
  - `DC/` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/<本题>/`；
  - `INV/` = `runs/r2e_lifecycle_20260929/inv/datalad_6b6f/`；
  - `BV/` = `runs/r2e_lifecycle_20260929/budget_v5/`；
  - `EV/` = `runs/r2e_lifecycle_20260929/env_verify/`。

## 结论

**处置：`needs_repair`，修订必做。** 材料缺陷都已由实跑坐实：
- 满足全部公开要求的替代解 C-A 判 0（T1）；
- 不修解析器、只改 `URL.__eq__` 的错误补丁 D-eq 判 1，而题面原例照旧失败（S1，v1 §4 第 4 步）；
- 核心要求只有示例字面值这一条断言（S1，T2c）。

按 v1 §5 的预授权做 **R-b + R-c**（附录 A），一轮修订一轮验收（附录 B），Codex 复核后再评用途。修订前只作问题定位。另有链路条件：本机评分必须把控制面保护时限放宽到 1200 s。

| v1 用途 | 结论 | 差什么（证据） |
|---|---|---|
| 问题定位 | yes | — |
| 能力比较 | conditional | 修订版按附录 B 验收通过并经 Codex 复核；评分用 1200 s 时限，超时不计入分母。原版不进分母，因为它把 C-A 判 0（`INV/ledger_CA_budget1200.jsonl:1`）、把 D-eq 判 1（`INV/ledger_Deq_budget1200.jsonl:1`） |
| 训练候选 | conditional | 上一条之外，还要在修订版上复核 §4 第 2–4 步（D-hard、D-eq、D-eq-minus 都为 0）；X1 重复采样控制写进训练计划；S2 缺口已登记（§4） |
| 留出评测候选 | no | 原版不满足训练候选的质量条件；修订后只能作标明版本的自建题；与另外 4 道 datalad 题互相包含（X1），按 D3 须整仓同划分 |

## 1. 题目目标

`URL('weired_url:/')` 在 base 上被解析成 `file:implicit`，要求改成 `ssh:implicit` / `weired_url` / `/`。

- 根因：`urlparse` 不把含 `_` 的前缀当 scheme，于是落进 `NET:491-499` 的 file 分支。
- 改动面：只有 `network.py` 一个文件。
- 评分：17 个键，唯一的目标键是 `test_url_samples`；`test_get_local_file_url_linux` 期望 FAILED。

## 2. 关键映射（完整表见 `analysis_before_history.md` §3）

| 需求或旧行为 | 公开依据 | 决定性断言 | 覆盖 | 执行证据 / 下一步 |
|---|---|---|---|---|
| 题面示例的三个字段 | `PUB/user_prompt.txt:10-22` | `HT:206` 经 `_check_url` 的 115 行（字段比较）与 118 行（往返） | 覆盖，但字段比较走候选可改的 `URL.__eq__` | noop 在 206 行失败（`BV/ledger_noop.jsonl:4`；`DC/orig/captures/repro_issue_example.out`）。D-eq 得 1.0，原例仍失败（`INV/pcheck_repro_Deq.json`） |
| 一般情形：非示例主机名加冒号加路径 | `PUB/user_prompt.txt:7`；`NET:281-283` | 无 | **缺失 → T2c** | base 上 `weired_url:path` 为 file（`DC/orig/captures/edge_case_survey.out:4`）。R-c 补 |
| 冒号前有 `/` 的本地路径保持 file（base 行为） | base（`DC/…/edge_case_survey.out:9-10`）；上游后来也这样做（`PUB19/…/support/tests/test_network.py:340,367`） | `HT:216-217` 要求判为 ssh，且主机名带 `/` | **冲突 → T1** | C-A 判 0.0，失败在 217 行经 115 行（`INV/logs_CA/…df7c9247.eval.log:98-115`） |
| 由解析字段重建原串 | `NET:278-279,526-531,600-608`；base 对这类输入能原样重建 | 118 行；216-217 行把它和无依据的分类要求绑在一起 | 部分 | C-B 判 0.0，失败在 217 行经 118 行（`INV/logs_CB/…458282dd.eval.log:98-113`）。R-b 只保留重建要求 |
| 已有 URL 形式、转义冒号、`weired://` 告警 | `PT` 同名测试 | `HT` 同名函数，207-210、226-234 行 | 覆盖 | gold 与 C-A 都通过 |
| `~` 编码 | `PT:280`（过时） | `HT:291`，期望 FAILED | 不属本题（T5） | 所有日志都失败在 291 行；上游后来把期望改成了 `file:///a~` |

## 3. 八方面：已查与未查

| 方面 | 已查 | 未查 / 缺项 |
|---|---|---|
| 公开需求 | 题面、公开读者稿、`NET` 全文、调用者 | 模型实际收到的消息。devcheck 发给模型的是 devcheck 指令，不是题面 |
| 材料与初态 | 初态 diff 为 0 字节；noop 在示例处失败；216-217 的同类输入在 base 上是 file（执行证据） | — |
| 测试是否测到要求 | `HT` 全文 | 核心断言经 `URL.__eq__`；缺非示例实例 |
| 误拒 | C-A 实跑判 0 → T1 | — |
| 回归与 gold | gold 的 K7 / K8 / A2 边缘回归（执行证据），测试都不保护 | — |
| 开发条件 | devcheck 13 项全真；无 pip、无网络；pytest 7.4.4；公开读者的 5 条命令加协调者的 2 条标准命令，经真实 CC 共约 20 s | — |
| 交付与评分 | 单文件交付，投影正确；本机需要放宽时限 | 测试辅助（`datalad/tests/utils.py`）与 `/testbed/.venv` 候选可写，属共享机制，没有逐题测 |
| 题目关系 | X1：另外 4 道 datalad 题的初态含本修复；机械扫描漏报 | 其它来源是否重复 |

## 4. 问题与证据层次

| 编号 | 问题 | 严重度 | 证据层次 |
|---|---|---|---|
| T1（根因 P3） | `HT:216-217` 要求把 `example.com/path/sp1:fname` 判为 ssh、主机名带 `/`，并能原样往返。题面没有这个要求，它还与 base 行为、git 约定和上游后续实现相反 | 修订前必修 | 当前 CPU 实跑：C-A 判 0.0；C-A 与 gold 在 4 条公开命令上退出码相同；上游后续实现（跨题公开包） |
| T2c（第 2 步） | 有依据的核心目标断言只有示例字面值 | S1 | 静态判断，加实跑旁证：D-hard 与 D-eq-minus 都通过了示例，只被 216-217 挡住 |
| T2（第 4 步） | 核心判据经候选可改的 `URL.__eq__` | S1 | 当前 CPU 实跑：D-eq 判 1.0，原例仍失败 |
| T3 / G1 | gold 的边缘回归：`/some/dir:x` 被当成 ssh 且 `is_url` 为 True；query 含冒号的模板抛 `ValueError` | S2，登记 | 当前 CPU 行为对照（base / gold / C-A） |
| T5 | `~` 键期望 FAILED（Python 3.7 的 `quote` 不再转义 `~`） | 登记 | 执行证据 + 上游后续 |
| E3（链路） | 默认 300 s 时限下 noop 与 gold 都报 `infra_failure`；trusted setup 实测 155–324 s | 链路条件 | `EV/ledger_l2_{noop,gold}.jsonl:3`；`BV/*:4`；`INV/*` 账本 |
| X1 | 本修复出现在 `16c1ffc3`、`9ba5de09`（判断式逐字相同）与 `19f5b450`、`58ba5165`（演化后的规则）的初态里 | 登记 | 跨题公开包 |
| P4 | 题面把缺陷说得比实际宽；"hostname undefined"实为空串 | 登记 | 静态 |

## 5. 建议、复核与下一步

**建议**：R-b + R-c（附录 A）。验收用附录 B 的 7 个候选。修订后的题只作标明版本的自建题。

**与复核初判的关系**：
- 一致：T1、T2c、采用 R-b + R-c；复核的退化候选 D1 就是 D-hard。
- 增补：因为 D-eq 实跑得 1，R-c 必须加不经 `__eq__` 的字段直查断言。
- C-B 的归属：修订版上应为 0。C-B 会让 base 能原样重建的输入重建成另一台主机的地址，属于对旧行为的回归，不是误拒。若改用 R-a 备选，C-B 会得 1。

**唯一最值得先做的下一步**：实施附录 A 的修订，按附录 B 实跑。

## 6. 剩余事项

- **链路条件**：本机正式评分要用 `replay_grade_budget.py --env-reset-timeout 1200`。探针与训练的评分入口，要么同样放宽，要么由 A 线把默认值或 trusted setup 的耗时修好。超时记 `failed_to_grade`，不计 0 分。
- 修订后要重建派生镜像（配方加 `+material_vN`），镜像 ID 会变，需在新 ID 上复跑 `r2e_preflight`、`import_env` 和附录 B。
- 模型实际收到的消息（清单第 3 项）与真实模型求解（第 33–36 项）都未做。
- 复核终稿待出；修订由 Codex 复核。

## 7. 探针就绪差距

本批 README §3 我按规则没有读，下表按 v1 §2 与协调者转述的要求写，请协调者对照 §3 调整。

| 条件 | 状态 | 谁来补 |
|---|---|---|
| 评分依据可信：没有未处理的 S1，误拒已纠正 | **未满足**（T1 + 两处 S1） | 协调者实施附录 A、实跑附录 B；Codex 复核 |
| noop 0 / gold 1，注明材料与环境版本 | 原版在 1200 s 时限下已满足（`BV/*:4`）；修订版待跑 | 协调者 |
| 评分链路能在本机跑完 | 有条件满足：须放宽到 1200 s | A 线修默认值；在此之前由协调者按 1200 s 跑 |
| actor 开发条件 | 已满足：v9 任务面 devcheck 13 项全真，真实 CC 2.1.205，agent 身份。修订后需在新镜像 ID 上复核预检 | 协调者 |
| 模型实际收到的消息 | 未核 | A 线探针链路 |
| 独立复核 | 初判已出，终稿待出 | 复核者 |
| 题目关系与暴露登记 | X1 已登记 | 协调者汇总 |
| 探针后检清单 | 已列（附录 C 末） | 探针分析 |

## 附录 A：修订草案（可直接实施；只改 `PRIV/hidden_tests/test_1.py`，期望映射不变）

每条都是"原文里恰好一处替换"。行号是修订前的行号。

**A1｜R-c：字段直查，不经 `__eq__`。**
- 位置：`_check_url`，`HT:114-115`。
- 依据：题面示例读的正是解析结果的 `.scheme` / `.hostname` / `.path`，这些是公开属性（`NET:591-592`）。
- 原文：
  ```python
      url_ = URL(**fields)
      eq_(URL(url), url_)
  ```
- 替换为：
  ```python
      url_ = URL(**fields)
      parsed = URL(url)
      for f in URL._FIELDS:
          eq_(getattr(parsed, f), getattr(url_, f))
      eq_(URL(url), url_)
  ```

**A2｜R-c：非示例实例。**
- 位置：`HT:206` 之后。
- 依据：题面的一般表述 "hostname followed by a colon and a path"；类说明里 ssh 的隐式形式写作 `host:path`（`NET:281-283`）。
- 原文：
  ```python
      _check_url('weired_url:/', scheme='ssh:implicit', hostname='weired_url', path='/')
  ```
- 替换为：
  ```python
      _check_url('weired_url:/', scheme='ssh:implicit', hostname='weired_url', path='/')
      _check_url('my_host:path/sp1', scheme='ssh:implicit', hostname='my_host', path='path/sp1')
      _check_url('data_server.example.org:/srv/ds',
                 scheme='ssh:implicit', hostname='data_server.example.org', path='/srv/ds')
  ```

**A3｜R-b：去掉无依据的分类要求，保留有依据的重建要求。**
- 位置：替换 `HT:211-217`。
- 依据：`NET:278-279,526-531,600-608`；base 对该输入能原样重建。
- 原文：
  ```python
      # ssh is as stupid as us, so we will stay "Consistently" dumb
      """
      $> ssh example.com/path/sp1:fname
      ssh: Could not resolve hostname example.com/path/sp1:fname: Name or service not known
      """
      _check_url('example.com/path/sp1:fname',
                 scheme='ssh:implicit', hostname='example.com/path/sp1', path='fname')
  ```
- 替换为：
  ```python
      # 'host/with/slash:path' is not pinned to one classification (local path or
      # ssh-like host); whatever it parses to, its fields must rebuild the string
      _u = URL('example.com/path/sp1:fname')
      eq_(str(URL(**_u.fields)), 'example.com/path/sp1:fname')
  ```
- 注意：不能写成 `str(URL(url)) == url`。构造时会存下原串（`NET:524`），那样写恒为真。

**A4｜R-c（可选）：下游 API。**
- 位置：`test_is_url`。
- 依据：`is_url` 的文档说明它包括 git 能理解的 ssh 地址（`NET:613-617`）；题面提到 "downstream operations"。
- 原文：
  ```python
      nok_(is_url('relative'))
  ```
- 替换为：
  ```python
      ok_(is_url('weired_url:/'))
      ok_(is_url('my_host:path/sp1'))
      nok_(is_url('relative'))
  ```

**R-a 备选**：不做 A3，直接删掉 211–217 行，A1、A2、A4 照做。代价是冒号前带 `/` 的输入完全不受约束，C-B 会得 1。v1 R-b 规定"有依据的行为要求必须保留"，所以推荐 A3。

## 附录 B：验收矩阵

修订版上正式评分用 1200 s 时限。gold 与 noop 各跑 2 次，其余候选各 1 次。候选补丁见 `RD/cands/`。

| 候选 | 原版（已实跑） | 修订版应得 | 修订版预计的失败点 |
|---|---|---|---|
| gold | 1.0（`BV/ledger_gold.jsonl:4`） | 1 | — |
| noop | 0.0（`BV/ledger_noop.jsonl:4`） | 0 | 206 行的字段直查 |
| C-A（git 规则替代解） | 0.0（`INV/…CA…:1`） | **1** | —（本次要纠正的误判） |
| C-B（gold 式分类，不改 `__str_ssh__`） | 0.0（`INV/…CB…:1`） | 0 | A3 重建断言，得到 `'example.com:path/sp1/fname'` |
| D-eq（改 `__eq__` 加 gold 的 `__str_ssh__`） | **1.0**（`INV/…Deq…:1`） | **0** | A1 字段直查，206 行 scheme 为 file |
| D-eq-minus（只改 `__eq__`） | 0.0（`INV/…Deqminus…:1`） | 0 | 同上 |
| D-hard（写死示例，第 3 步退化候选） | 0.0（`INV/…Dhard…:1`） | 0 | A2 的 `my_host:path/sp1` 为 file |

另须核对：
- 键集仍为 17 个；`test_get_local_file_url_linux` 仍为 FAILED；XFAIL 不成键；
- 每行都确认补丁已交付（`included_paths` 含 `network.py`）且 `test_url_samples` 确已执行；
- 保存新版本、父版本（隐藏测试树 `8af0fcf7…`）、理由与触发反例：父版本上 C-A 为 0、D-eq 为 1。

## 附录 C：证据索引与探针后检

**评分**：
- 原版 noop / gold：`BV/ledger_{noop,gold}.jsonl:4`；
- 默认时限超时：`EV/ledger_l2_{noop,gold}.jsonl:3`；
- 候选：`INV/ledger_{CA,CB,Deq,Deqminus,Dhard}_budget1200.jsonl:1`，日志在 `INV/logs_*/`，补丁与日志的 sha256 都与账本一致。

**公开命令**：
- base：`DC/orig/captures/*.out`；
- gold：`DC/private_control.json`（root）、`INV/pcheck_public4_gold.json`（agent）；
- C-A：`INV/pcheck_public4_CA.json`；
- D-eq 与 noop：`INV/pcheck_repro_{Deq,none}.json`。

**旧机与独立 runner 对照**：`PRIV/run_refs.json` 的 current 行，以及 M3 两次 gold。

**探针后检**：按公开需求读补丁，重点看这些：
- 是否改了 `URL.__eq__` / `__ne__`、`datalad/tests/utils.py` 或 `/testbed/.venv` 里的文件；
- 是否改了 `get_local_file_url`（越界，T5）；
- 冒号前带 `/` 的输入与 query 含冒号的输入的行为（S2 缺口）；
- 公开命令 `repro_issue_example` 必须通过。
