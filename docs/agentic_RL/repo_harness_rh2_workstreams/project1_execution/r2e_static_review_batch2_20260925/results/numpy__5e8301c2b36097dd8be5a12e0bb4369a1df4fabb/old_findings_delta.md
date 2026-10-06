# 旧结论核对：numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb

- 角色：R2E 私有主审，2026-09-25。在 `analysis_before_history.md` 封存之后才读历史。
- **读了**：`refs.json` 列出的全部路径，即环境轮逐题的 `findings.md`、`screening_record.json`、`facts.json`，以及 `known_issues.json`（涉及本题的三族）、`decisions.md`、`results_20260924.md`、`packages/p2/README.md` 的本题行、复现脚本。另外读了旧记录引用的原始探针产物：`runs/r2e_env_repair_20260924/p2/dev_probe/numpy__5e83…/{dev_probe.json,root_init.log}`、`p2/followups/{followups.log,bare_pytest.log}`、`p2/pubtests/numpy__5e83….log`。
- **没读**：全池扫描与期望来源三方比对的产物（`runs/r2e_t0_batch2_20260924/{scan,provenance}/`）、`reconcile.json`、首批和 Codex 审查目录、本批 README 与 `assignments.json`。
- 判定词：**确认**、**推翻**、**过时**、**未核实**。旧记录用的是环境轮的 R01–R20 编号，不是 40 项清单编号。

## 1. 逐条对照

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| 1 | noop 的 0 来自 15 个目标键 `test_einsum_sums_*`，原因都是题面的 `ValueError: Size of label…`（findings；R02、R16） | 确认，并补充 | 两份 noop 日志的 15 个 `E` 行逐字相同，调用栈都是 `T:487` → `einsumfunc.py:1089` → `:712`。**补充**：15 键检查的是 helper 末尾同一个输入、同一对断言（`T:484-490`）；隐藏测试就是公开 `test_einsum.py` 加上这 8 行 |
| 2 | gold 35/35、reward 1、从 `/testbed/numpy` 导入、与参考逐键一致、同条件两次一致（R01、R08、R13、R15） | 确认 | 两轮 gold 日志归一化后逐字相同；日志头的隐藏测试树摘要与评分面一致；M3 来源镜像的两份 gold 原始日志都是 35 passed。reconcile 用到的 5 份 noop 参考日志没读 |
| 3 | `.venv` Python 3.7.9、pytest 7.4.4、无 pip、就地构建（12 个 in-tree `.so`）、在 `/tmp` 下导入失败（R05、findings） | 确认 | `dev_probe.json` 原始值：`IMPORT_FROM_TMP_RC=1`、`WHICH_pip=MISSING`；`followups.log` B 段 `so_count=12`、hypothesis 6.79.4；devcheck `env.out`（正式链，agent 身份）同样是无 pip、pytest 7.4.4、numpy 来自 `/testbed/numpy` |
| 4 | `/testbed` 必须在 `sys.path` 上（issue、solver_conditions、known_issues 族 `testbed_must_be_on_sys_path`） | 确认；**补充**：v3 提示没有告诉求解者 | `dev_probe.json` 的 `REPRO_OUTPUT`：放在 `/testbed` 外的脚本 `IMPORT_PLAIN=fail`。v3 `public_hints` 只说"从 /testbed 用 `python -m pytest`"，没提"放在 `/testbed` 外的脚本导入不了 numpy"；这句只写在给审查者看的 `environment_brief.md` 里。actor 待验 |
| 5 | 裸 `pytest` 收集会 `ModuleNotFoundError`（本题"同一构建方式，推断相同"；issue、solver_conditions） | **推翻推断依据；结论改为未核实** | 这个推断的依据是 `18b7cd9d` 的 `numpy/lib/tests` 缺 `__init__.py`（`bare_pytest.log`）。本题 base 的 `numpy/lib/tests`、`numpy/core/tests`、`numpy/tests` 都有 `__init__.py`（公开工作树；devcheck 运行后也出现了 `numpy/core/tests/__pycache__/__init__…pyc`）。在 prepend 导入模式下，pytest 会把 `/testbed` 放进 `sys.path`，所以对 `test_einsum.py` 大概率不会失败。没有执行验证。这不影响任何结论：提示和评分都用 `python -m pytest`。v3 `environment_brief.md` 沿用了这句，可改成"本题未实测，统一用 `python -m pytest`" |
| 6 | 公开复现成立：`optimize=True` 抛原句，`optimize=False` 得到 `(2,)`（findings；R03、R09） | 确认 | devcheck pr1（正式链，agent 身份）逐字复现题面报错；pr2 输出 `[10. 10.]` |
| 7 | `test_einsum.py` 35 passed，`test_ctypeslib.py` 能正常收集和运行（R09） | 确认，并补充 | pubtests 日志：plain 和 `-W ignore` 两种方式都是 35 passed；devcheck pr4 35 passed；`dev_probe` 的 `PUBLIC_RUN_TAIL` 为 7 passed。**补充**：这个公开文件就是隐藏测试减去 8 行，所以 20 个回归键都能在本地完整自检 |
| 8 | 全局提示写的是 conda testbed 和"pip already points at it"，与 R2E 实际不符（R03 引 E09；known_issues 的 `solver_hints:conda_wording…` 与 `no_pip_in_venv`） | **过时** | v3 `public_bundle.json` 的 `public_hints` 已经写 `.venv`、"`pip` may be unavailable"、`python -m pytest`；devcheck `activation_check.json` 按期望前缀 `/testbed/.venv` 核对通过。正式接线仍待 A 线审查（环境卡 §2）。本题无 pip 这一事实本身仍然确认 |
| 9 | 期望全 PASSED，没有 FAILED/ERROR 键（R06、R11 记 not_applicable） | 确认 | `expected_output.json` 的 35 键全是 PASSED。因此不存在"更完整的修复把失败键翻成通过、反而判 0"的风险 |
| 10 | gold 只改 `numpy/core/einsumfunc.py`；official 文件 = `r2e_tests` + `run_tests.sh`（R04） | 确认 | `gold.patch` 只有一个文件；gold 日志 `RH2_SETUP_RESTORED=2`、`RH2_SETUP_TEST_FILES=3` |
| 11 | chown 后 `/testbed`、site-packages、`.venv/bin`、HOME、`/tmp` 都可写，私有目录不可读（R07） | 确认；**补充一个没评估的面** | `dev_probe.json`：`WRITE_SITE=ok`、`WRITE_VENV_BIN=ok`；devcheck：`HIDDEN_0=DENIED:/root`，运行后 `.venv/…/site-packages` 下出现新的 pycache。agent 能改 `.venv`；这些改动会不会进入交付面，属于共享机制问题，本题没评估 |
| 12 | 无网络，解题和测试也都不需要网络（R10） | 确认；条件已更新 | 旧探针用的是 `network none`。devcheck 在正式链的隔离网络 + relay 下：`DNS_EXTERNAL=DENIED`，4 个禁止目标都 DENIED，relay 可连 |
| 13 | 峰值 489 MB、测试约 1 s；chown 22 s（R12） | 确认；chown 数值不适用于正式链 | 四份账本的峰值是 489–503 MB，测试 1.4–2.4 s。devcheck 正式链从容器启动到初始化完成约 8.5 s（没单列 chown 时间）。旧的 22 s 是并发条件下的探针值，旧记录本身也注明不作校准 |
| 14 | 每次都是 fresh 容器、缓存计数不变、候选没碰测试样路径（R14） | 部分确认 | noop 账本 `omitted_cache_count` 的 baseline 与 post 相同（19 个目录 / 162 个文件）；`cleanup` 和 `candidate_test_like_paths` 没逐项看 |
| 15 | git 清洗干净；残留的补丁样文件是上游跟踪的 `f2c_*.patch`；`install.sh` 是仓库通用脚本、不含修复（R17、R03） | 确认 | devcheck `attempt.json` 的 git_sanitize：refs、remotes、reflog、unreachable 都是 0，预检确认 HEAD 无子提交；`followups.log` A 段：7 道 numpy 题的 `install.sh` 摘要都是 `5f15d21e…`、56 行；B 段：6 个 f2c patch 都受 git 跟踪 |
| 16 | 不需要配方或材料修订，只有解题侧条件；分类 `solver_condition`，处置 `environment_qualified`（R18、disposition、results） | 确认（限环境口径） | 本次静态审查没发现环境缺口。本次的处置另记在 `scope=static_review` 下，与环境轮结论不冲突，见 §3 |
| 17 | `disposition.reason` 写"只差 R13…待中央复跑" | **过时** | 同一记录的 `review_notes` 和 `facts.json` 都显示 R13 已并入（noop、gold 各两次一致），但 reason 文字没有更新 |
| 18 | 复现脚本是在读隐藏测试和 gold 之前写的（findings 引 E06） | 未核实 | 这是流程主张，产物无法证明。脚本内容只包含题面示例，与主张相符 |
| 19 | 导入条件是本批 7 个 numpy 镜像共有的（R20） | 确认（限本题） | 本题由 `dev_probe` 与 devcheck 实测；其它 6 题没复核 |

## 2. 旧记录没覆盖、本次新增的判断

旧记录属于环境轮，只管环境资格，没有做题意—测试—gold 的对照。以下各项是本次新增的，证据见 `analysis_before_history.md` §3–§8：

- **N1 覆盖窄**（静态，待实跑）：只测题面这一个输入。只放宽一个方向的实现（C-C）、直接删掉检查的实现（C-D），静态上都能拿 1。
- **N2 gold 部分修复**（执行）：被求和的单例标签走 `tensordot`，以及三操作数的情形，gold 下仍报 `shape-mismatch for sum`（`DC/private_gold/private_control.json` pr3）。上游后来用 `broadcast_indices` 补了这一处。
- **N3 gold 的新报错文本把两个尺寸写反了**（执行，外观问题，没有测试覆盖）。
- **N4 跨题包含**（已逐文件核对）：本题 gold 与隐藏断言出现在 `numpy__43e333e2`、`numpy__d89bc4bb` 的公开初态里。
- **N5 真实题面消息仍未捕获**：devcheck 发给模型的是桩消息。
- **N6 材料注记**：`run_refs.json` 两条 noop 行的 `mismatched` 只列了 12 个，账本里是 15 个。

## 3. 主审是否改判

**不改判。** 读完历史后，暂定处置仍是静态候选：`needs_review`，理由为"静态候选待 actor 验证"，不是题意或测试争议。

历史没有与初判冲突的事实。它补强了开发条件的证据：`/tmp` 下导入失败、site-packages 可写、`install.sh` 是通用脚本。据此新增三点，都不改变处置：

- #4：放在 `/testbed` 外的脚本导入不了 numpy，而 v3 提示没告诉求解者。记为解题侧条件，actor 待验。
- #5："裸 pytest 会失败"对本题的依据不成立，建议更正 `environment_brief.md` 的措辞。
- #11：agent 能写 `.venv`，是否会进入交付面留给共享机制审查。

环境轮的 `environment_qualified`（环境口径）保留；本次处置限定在 `static_review` 范围内。
