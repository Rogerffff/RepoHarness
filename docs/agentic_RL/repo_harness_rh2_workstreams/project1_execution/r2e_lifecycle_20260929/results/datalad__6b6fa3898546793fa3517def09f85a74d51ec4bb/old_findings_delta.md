# 旧结论核对与主审改判（datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb）

- 角色与时间：R2E 私有主审，2026-09-29，在封存 `analysis_before_history.md` 之后写。
- 历史来源：`runs/r2e_static_prep_20260924/v3/history/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb/refs.json` 列出的文件。它们是 09-23/24 环境审查 P2 包（B 线子代理）的产物：
  - 本题的 `findings.md`、`screening_record.json`、`facts.json` 与复现脚本，都在 `docs/.../r2e_env_repair_20260924/tasks/<本题>/`、`repros/<本题>.py` 下；
  - `known_issues.json` 的两族（无 pip；期望含非 PASSED 键）；
  - `decisions.md`、`results_20260924.md`、`packages/p2/README.md` 中与本题有关的行。
- 本次新证据：协调者今晚在新 CPU 机上的实跑，全部在 `runs/r2e_lifecycle_20260929/` 下。
  - **正式复验**：`env_verify/ledger_l2_{noop,gold}.jsonl` 第 3 行；`budget_v5/ledger_{noop,gold}.jsonl` 第 4 行。
  - **devcheck**：`devcheck_rev/unrev/<本题>/`，下文简称 `DC/`。
  - **候选评分与公开命令对照**：`inv/datalad_6b6f/`，下文简称 `INV/`。候选补丁在 `RD/cands/`，与 `INV/` 里的同名文件逐字相同，sha256 与各账本的 `patch_sha256` 一致；日志 sha256 也与账本一致（我逐个核过）。
- 历史材料的性质：只做了**环境侧**审查（评分能否复现、解题条件），没有做需求—断言语义审查，所以对 T1、S1 没有任何主张可以核对。

## 1. 旧主张逐条核对

| 旧主张（出处） | 判定 | 新的决定性证据 |
|---|---|---|
| noop 16/17，只差目标键 `test_url_samples`，原因行与题面一致（findings.md 第 6 行；record `R02`、`R16`） | **确认** | 新机 `budget_v5/ledger_noop.jsonl:4` 为 16/17，mismatched 为 `[test_url_samples]`。`DC/orig/captures/repro_issue_example.out` 在 agent 身份下报 `AssertionError: ('file:implicit', '', 'weired_url:/')` |
| gold 17/17、reward 1（record `R01`、`R08`、`R15`） | **确认** | `budget_v5/ledger_gold.jsonl:4` 为 17/17、reward 1.0 |
| `R16`："目标键 `test_url_samples` 对应题面的 ssh:implicit 解析"，pass | **部分推翻** | 该键里除了题面示例（`HT:206`），还有一条无依据的断言 `HT:216-217`：<br>• 满足全部公开要求的替代解 C-A 因此判 0（`INV/ledger_CA_budget1200.jsonl:1`，16/17；日志 `INV/logs_CA/…df7c9247.eval.log:98-115` 失败在 `test_1.py:217`，经 `_check_url` 的 115 行）。<br>• 该键的核心判据还能被改 `URL.__eq__` 绕过：D-eq 得 1（`INV/ledger_Deq_budget1200.jsonl:1`，17/17），而题面原例仍然失败（`INV/pcheck_repro_Deq.json` 与 `pcheck_repro_none.json` 输出相同）。<br>旧检查只核了 noop 的失败行，没有核该键的全部断言 |
| 期望 FAILED 键 `test_get_local_file_url_linux`：Python ≥ 3.7 的 `quote` 不转义 `~`，上游用例在该解释器下本就失败；若解答把 `~` 转义成 `%7E` 反而判 0，风险低（findings.md 第 9、14 行；`R06`；known_issues 第 7 族） | **确认，并补证** | 所有新日志的失败点都在 `test_1.py:291`（例如 `INV/logs_Deq/…664c1700.eval.log:25-42`）。补证：上游后来把期望改成了 `('/a~', 'file:///a~')`（`PUB58/worktree/datalad/support/tests/test_network.py:477-487`），所以把 `~` 转义并不是"更完整的修复"。维持 T5 登记，不修订 |
| 解题侧条件：`.venv` Python 3.7.9、pytest 7.4.4、无 pip、无网络、HEAD 无子提交、私有目录不可读（`R05`、`R07`、`R10`、`R17`） | **确认**（新镜像） | `DC/orig/captures/env.out`：uid 54321，pytest 7.4.4，`No module named pip`，`RH2_BASHENV_WRITE=DENIED`，初态只有两个未跟踪文件。`DC/orig/captures/r2e_preflight.out`：解释器、隐藏测试、git 历史三项都是 ok。`DC/devcheck.log` 的 13 项检查全为真 |
| 公开 `datalad/tests/test_network.py` 为 16 passed / 1 failed / 1 xfailed（`R09`） | **确认** | `DC/orig/captures/public_test_network.out` 末行；gold 下相同（`DC/private_control.json`、`INV/pcheck_public4_gold.json`） |
| editable 安装，在 `/tmp` 下也能导入 `/testbed/datalad`（`R05`） | **未核实**（本轮没测，沿用） | devcheck 只从 `/testbed` 运行；导入路径为 `/testbed/datalad/__init__.py`（`DC/orig/captures/import_env.out`） |
| 资源：setup 52 s、test 1 s、峰值 559 MB（`R12`） | **过时**（机器变了） | 新机的评分 `grader_trusted_setup` 为 155–324 s（`budget_v5` 第 4 行 229–230 s；`INV/*` 账本 155–324 s）。默认 300 s 的控制面保护时限下，noop 与 gold 都记 `infra_failure: grading_control_surface_protect_timeout_after_300s`（`env_verify/ledger_l2_{noop,gold}.jsonl:3`）。test 段 3–5 s，峰值约 566–574 MB |
| 两次运行逐键一致（`R13`） | **确认并扩充** | 旧机 noop 与 gold 各 2 次；新机在 1200 s 时限下 noop 与 gold 各 1 次，另有 5 个候选各 1 次，结果全部可按补丁内容解释，没有不稳定迹象 |
| 公开提示写的是 conda（`R03` 注） | **过时** | v3 起公开提示改为 `.venv` 措辞（`PUB/public_bundle.json` 的 `public_hints`） |
| agent HOME 没有 git 身份（issue，solver_condition，open） | **确认，与本题无关** | 本题复现与测试都不涉及 git 操作 |
| 分类 `solver_condition`，处置 `environment_qualified`（record `disposition`；`results_20260924.md:25`） | **过时（用途口径）** | 它只说明旧镜像 `r2e_derive_v1`（`acb73dcd…`）上的环境侧可复现，按 v1 §2 不构成能力比较或训练资格。当前镜像是 `r2e_derive_v1+sysconfig_v1`（`2ec5e89b…`）：环境侧由 devcheck 与 `budget_v5` 重新证实，但评分需要放宽时限。语义上还有 T1 与 S1，见 §2 |
| gold 只触碰 `datalad/support/network.py`（`R04`） | **确认** | 所有候选与 gold 行的 `projection.included_paths` 都是 `['datalad/support/network.py']` |

## 2. 主审自己的初判：核对与改判

| 初判（`analysis_before_history.md`） | 结果 | 依据 |
|---|---|---|
| C-A 判 0，失败在 216-217 行经 115 行 | **实跑证实** | `INV/logs_CA/…df7c9247.eval.log:98-115`：`URL(path='example.com/path/sp1:fname', scheme='file:implicit') != URL(hostname='example.com/path/sp1', …)`。206-210 行都已通过（pytest 在第一处失败停下）。C-A 满足公开要求也有执行证据：`INV/pcheck_public4_CA.json` 与 gold 在 4 条公开命令上的退出码相同（0/0/0/1，1 是 `~` 那条） |
| D-eq 得 1，第 4 步命中 S1 | **实跑证实** | `INV/ledger_Deq_budget1200.jsonl:1` 为 17/17；日志 `INV/logs_Deq/…664c1700.eval.log:46-48,62` 显示 `test_url_samples` 确已执行并 PASSED。告警行号为 `network.py:537`，说明加载的是打过补丁的文件（base 是 531）。原例仍失败，见 `INV/pcheck_repro_Deq.json` |
| D-hard 判 0，但只是被无依据的 216-217 挡住 | **实跑证实** | `INV/logs_Dhard/…db01a871.eval.log:98-115`，失败在 217 行经 115 行 |
| C-B 判 0，失败在 216-217 行的往返断言（118 行） | **实跑证实** | `INV/logs_CB/…458282dd.eval.log:98-113` 报 `'example.com/path/sp1:fname' != 'example.com:path/sp1/fname'`；解析时还连续告警 "Parsed version of url … differs"（117-123 行） |
| D-eq-minus 在当前材料下判 0，但删掉 216-217 后就会得 1 | **实跑证实前半，并补强后半** | `INV/logs_Deqminus/…e0a5a3a6.eval.log:98-115` 失败在 217 行，说明它**已经通过了 206 行的题面示例**：只改 `__eq__`、不修解析器，就过了核心断言。这是"删掉 216-217 而不补 R-c 就会得 1"的直接执行证据 |
| gold 的未测回归 K7、K8、A2（源码推断） | **升级为执行证据** | 同一 `edge_case_survey` 在三处的输出：base 见 `DC/orig/captures/edge_case_survey.out:9-10,12`；gold 见 `INV/pcheck_public4_gold.json`（agent）与 `DC/private_control.json`（root）；C-A 见 `INV/pcheck_public4_CA.json`。<br>• `/some/dir:x`、`rel_dir/sub:x`：base 与 C-A 是 `file:implicit`；gold 变成 ssh，主机名分别为 `/some/dir`、`rel_dir/sub`，且 `is_url=True`。<br>• `openfmri_s3?_url=s3://b/k`：base 与 C-A 是 file 加 query；gold 抛 `ValueError`。<br>• `weired_url:/p?x=1`：base 是 file 加 query；gold 与 C-A 都抛 `ValueError`（A2，两种都可接受）。<br>• `host1:22`：base 为 file；gold 与 C-A 都是 ssh（A1）。<br>两者只在前三行不同。仍记 T3（S2），不作处置依据 |
| 清单第 3 项（模型实际收到的消息）未核 | **仍然未核** | devcheck 的用户消息是 devcheck 指令，不是题面（`DC/orig/stub/requests/messages_000.json`），所以它没验证题面加提示的实际渲染 |
| 修订草案用 R-a（整段删掉 `HT:211-217`） | **改判为 R-b**（R-a 降为备选） | 理由见下 |

**改判理由（R-a → R-b）**：216-217 行其实把两件事绑在了一起。

- 一件**有依据**：由解析出的字段拼回的字符串要等于原串。依据有四处：类说明"能把自己重建成字符串供复用"（`NET:278-279`）；解析时往返不一致会告警（`NET:526-531`）；`parse_url_opts` 用 `str(URL(**fields))` 返回结果（`NET:600-608`）；base 对该输入本来就能原样重建（`DC/orig/captures/edge_case_survey.out` 同类输入为 file、无告警）。
- 一件**没有依据**：必须按 ssh 解析，且主机名带 `/`。

v1 §5 的 R-b 规定"有依据的行为要求必须保留"，所以只删没有依据的分类要求，保留"用解析出的字段重建原串"这一条行为断言，不整段删除。

这个判断与复核初判（R-b + R-c）一致。连带结果是：C-B 在修订版上仍判 0。C-B 把这类输入改成 ssh 以后，`str(URL(**fields))` 得到 `example.com:path/sp1/fname`，`parse_url_opts` 会返回指向另一台主机 `example.com` 的地址，每次解析还会告警。这是对 base 已有行为的回归，所以 C-B 不算角色卡补充规则 1 所说的"满足全部公开要求、也不破坏受影响旧行为"的合理修复，判 0 不是误拒。若改用 R-a 备选，C-B 会判 1。

**R-c 的补充**：复核初判的 R-c 只写了"补一个非示例实例"。D-eq 与 D-eq-minus 的实跑说明，还必须加一条不经 `URL.__eq__` 的字段断言，否则两者在修订版上可能得 1。详见 `card.md` 附录 A。

## 3. 汇总：旧结论与当前判断的关系

- **旧的环境侧结论基本成立**：评分可复现、解题条件核对过、`~` 键有固定解释。变化有两点：资源与时限随机器变化，本机须放宽到 1200 s；公开提示已改为 `.venv` 措辞。
- **旧记录没有语义审查**，本轮新增三类问题：T1（`HT:216-217`，C-A 实跑判 0）；S1（T2c，以及第 4 步 D-eq 实跑得 1）；gold 的 T3 边缘回归（现有执行证据）。
- **历史处置 `environment_qualified` 不能沿用为训练资格**。当前处置改为 `needs_repair`：材料缺陷已由实跑坐实，按 v1 §5 预授权的 R-b + R-c 修订、验收并经 Codex 复核后再评用途。另需满足链路条件：评分须放宽控制面时限。
