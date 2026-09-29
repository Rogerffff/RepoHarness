# 旧主张核对：numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764

- 角色：R2E 私有主审，2026-09-25。本文写于 `analysis_before_history.md` 保存之后。
- 历史来源：只有 `v3/history/.../refs.json` 列出的这些文件。
  - 09-24 环境审查第一轮 P2 包的逐题记录：`screening_record.json`、`findings.md`、`facts.json`；
  - `known_issues.json` 中与本题相关的三族；
  - `decisions.md` 的 E02–E16；
  - `results_20260924.md`；
  - 复现脚本；
  - `packages/p2/README.md`。
- 为核对历史，另读了三份原始件：`runs/r2e_env_repair_20260924/p2/followups/{followups.log,bare_pytest.log}` 和该包本题的 `dev_probe/.../agent_probe.log`。
- 新证据：协调者在当前覆盖表镜像 `sha256:4bd9cf42…`（derived9）上的正式评分，账本是 `runs/r2e_actor_20260925/grader/ledger_na5ea_{noop,gold}.jsonl`。我核了三件事：两份日志的 sha256 与账本一致；日志内容与 R-f 日志相比只差时间戳和耗时；两次运行的 overlay 配方摘要都是 `0da821a1…`。

## 0. 结论

**历史的性质。** 历史只做了环境资格审查，按 E03 不判题目质量；给本题的处置是 `environment_qualified`，分类是 `solver_condition`。

**逐条核对的结果。**
- **没有推翻任何实质主张。**
- **过时 3 条：**
  - 镜像 ID：当时是 `cb0ee55e`，现在的覆盖表用 derived9 `4bd9cf42`；
  - 提示措辞：历史说全局提示写的是 conda；
  - `facts.json` 里的 `public_hints_mention_conda: true`。
- **补强或更正 3 条：**
  - R16 "断言无消息"；
  - public_test_noise 这一族对本题的适用范围；
  - 裸 `pytest` 的推断依据。
- **未核实 1 条：** R15 中 noop 一侧与参考 runner 的对账。

**历史补上了我初判漏掉的一点。** 公开读者建议在仓库测试文件之外自测，比如用 home 下的临时脚本；我的初判照搬了这条建议，没有指出问题：
- 脚本不在 `/testbed` 里时，即使 cwd 是 `/testbed`，也导入不了 numpy，因为 `sys.path[0]` 是脚本所在目录；
- 必须设 `PYTHONPATH=/testbed`，或者把脚本放进 `/testbed`；
- 证据：`agent_probe.log:122` 的 `IMPORT_PLAIN=fail (ModuleNotFoundError…)`。

**初判的变化。**
- 初判唯一的关键未知项（当前构建上有没有隐藏测试评分）已由协调者补上：noop 0（31/32，只有目标键 FAILED），gold 1（32/32）。它不再是未知项；下一步改为实跑候选。
- 其余初判不变：`needs_review`（静态候选，待 actor 验证），不需要材料修订。
- 我的 `needs_review` 和历史的 `environment_qualified` 不冲突：前者是静态题目审查加 actor 条件，后者是环境资格，范围不同。

## 1. 逐条核对

| 旧主张（出处） | 判定 | 决定性证据 |
|---|---|---|
| 分类 `solver_condition`，"环境本身无缺口"，处置 `environment_qualified`；范围是 expected_v0 + `r2e_derive_v1` + 默认 profile（记录 disposition） | **确认**，范围扩到 derived9 | 在 `4bd9cf42` 上评分：noop 0 / gold 1，逐键结果与旧构建相同。devcheck 走正式启动路径，预检三项都是 ok。环境资格不等于题目质量，本轮新增的问题见 §2 |
| R01：镜像 ID 与覆盖表一致（当时是 `cb0ee55e`） | **过时**；在新构建上重新成立 | 覆盖表现在是 `/work/b_r2e/derived9/overlays.jsonl`，镜像 `4bd9cf42`。devcheck 报 `image_is_overlay_derived_id=true`；新账本的 overlay `recipe_sha256` 与旧构建相同 |
| R02：noop 为 0，只因为 1 个键不符 | **确认** | 3 次 noop（R-f、中央复跑、derived9）的不符键都只有 `TestTile.test_tile_one_repetition_on_array_gh4679`，`keys_equal=true` |
| R03：prompt 1116 字符、复现成功；全局提示写 conda，属 E09，不计入本题 | 复现一项**确认**；提示一项**过时**，并有新问题 | devcheck pr1_1 输出 `[2 3 4 5 6] True`。v3 公开包的提示已经是 `.venv` 措辞；但正式链的用户消息只用 `render_user_prompt`（`rh2/src/repoharness2/adapters/slime/generate.py:1976`，HEAD `9d741bd4`），提示只写进容器文件 `/rh2/public_task_bundle.json`（环境卡 §2；`envpack/ingest_r2e_subset.py:197-201` 的注释，该文件在工作区未跟踪）。真实任务消息仍未捕获 |
| R03 / R17：`install.sh` 是本仓库通用脚本，不含修复 | **确认** | `followups.log` 的 A 段：7 道 numpy 题的 `install.sh` 摘要都是 `5f15d21e…`，都是 56 行 |
| R04：官方测试文件是 `r2e_tests/{__init__.py,test_1.py}` + `run_tests.sh`；gold 只触碰 `shape_base.py` | **确认** | grading bundle 的 `hidden_test_files`；3 次 gold 的投影都是 `included_paths=["numpy/lib/shape_base.py"]` |
| R05：解释器是 `.venv` 3.7.9，pytest 7.4.4，没有 pip；就地构建，`/testbed` 必须在 sys.path 上；有 gcc / make | **确认** | devcheck `env.out`（agent 身份，新构建）：`/testbed/.venv/bin/python`、`No module named pip`、从 `/testbed/numpy/__init__.py` 导入。`agent_probe.log:16-17,26-28`（旧构建）：`WHICH_gcc=/usr/bin/gcc`、`IMPORT_FROM_TMP_RC=1` |
| R06 / R11：期望全是 PASSED，不适用 | **确认** | `expected_output.json` 32 键全为 PASSED |
| R07：`/testbed`、site-packages、HOME、`/tmp` 可写，私有目录不可读 | **确认** | devcheck `prelaunch.json`：`WORKDIR_WRITABLE=1`、`HOME_WRITABLE=1`、`TMP_WRITABLE=1`、`ACTIVATION_WRITE=DENIED`，预检 `HIDDEN_TESTS=ok`。`post_run_facts` 显示 agent 往 `.venv/.../site-packages/pytest_env/__pycache__` 写了文件 |
| R08：从 `/testbed/numpy` 导入；gold 32/32 | **确认** | 3 次 gold 的 `RH2_OBS_IMPORT_PATH` 都是 `/testbed/numpy/__init__.py` |
| R09：`test_shape_base.py` 31 passed；`test_ctypeslib.py` 有 1 个 nose 遗留 ERROR | **确认** | devcheck pr5_4 为 31 passed（修复前）；私有 gold 对照为 31 passed。`followups.log` F5 段：`6 passed, 4 warnings, 1 error`，`fixture 'self' not found` |
| R10：无网络，也不需要网络 | **确认** | 正式路径是隔离网络加 relay：`DNS_EXTERNAL=DENIED`、`NET_forbidden_*=DENIED`，只有 `NET_relay=CONNECTED`。这比历史探针用的 `network none`（E02）更接近正式链 |
| R12：内存峰值 272 MB | **确认** | R-f 与复跑账本的 `mem_peak_mb` 在 271.9–274.8 之间 |
| R13：同条件两次运行一致 | **确认并扩展** | 两次构建上共 3 次 noop、3 次 gold，逐键相同 |
| R14：fresh 容器；`candidate_test_like_paths=[]` | **确认** | 各账本字段 |
| R15：与参考 runner 对账，2 行都一致 | gold 一侧**确认**；noop 一侧**未核实** | 我逐键比对了 M3 两份 gold 日志与 RH2 gold：32 键都是 PASSED。M3 的 noop 原件不在 run_refs 里，`reconcile.json` 我没有读 |
| R16：目标键对应题面；"noop 原因行只有 FAILED（断言无消息）" | **确认并补强** | short summary 那一行确实没有消息，因为 AssertionError 的消息以换行开头。但失败回溯里有 `x: array([2, 3, 4, 5, 6])`（R-f noop 日志 :123-128），与题面的 "Actual output" 逐值一致。R16 只核了"键对应题面"，没核覆盖范围，见 §2 的 N1 |
| R17：HEAD 没有子提交，refs / reflog / remote 都是 0 | **确认** | devcheck 在新构建上的 `git_sanitize`：`REFS_REMAINING=0`、`REMOTES=0`、`REFLOG_ENTRIES=0`、`UNREACHABLE_OBJECTS=0`。作为对照，来源镜像在 M3 里是 `fix_reachable=commit`、refs 285、remotes 1，说明派生清理这一步是必要的 |
| R18：不需要配方或材料修订 | **确认** | 静态审查也不提议修订 |
| issue：`/testbed` 必须在 sys.path 上；裸 `pytest` 收集失败（18b7cd9d 实测，本题是推断） | **确认**，推断依据补强 | `bare_pytest.log` 记录 18b7 的失败原因是 `numpy/lib/tests/__init__.py` 不存在；本题工作树的 `numpy/lib/tests/` 同样没有这个文件。本题仍未实测。新增一点影响：公开提示不进模型消息，所以"用 `python -m pytest`"这句模型默认看不到 |
| known family `public_test_noise`（本题因为 `test_ctypeslib.py` 被列入） | **范围更正** | 噪声只出现在与本题无关的 `numpy/tests/test_ctypeslib.py`。与修复相关的 `numpy/lib/tests/test_shape_base.py` 修复前后都是 31 passed，没有噪声。本题被列入，是因为探针固定取第一个测试文件（P2 README §7 第 3 条） |
| `facts.json` 的 `public_hints_mention_conda: true` | **过时** | v3 的 `public_bundle.json` 已改成 `.venv` 措辞 |
| `facts.json` 的 `testbed_owner_derived: root` | **不矛盾** | 镜像里 `/testbed` 属 root；rollout 可信初始化之后 `WORKDIR_OWNER=54321`（`prelaunch.json`） |

## 2. 历史没有涉及的新发现（不构成推翻）

- **N1 覆盖窄（清单 25、26）。** 唯一的目标键就是题面原例。只修标量 `reps=1` 的部分修复、丢掉 `ndmin` 的回归型错误，预计都能得 1。这是静态推断，依据是隐藏测试全文，待候选 B、C 实跑。
- **N2 题目关系（清单 5）。** 同仓 6 道较新 numpy 题的公开工作树里，都有本题修复的重构版本（注释逐字相同）和目标测试 `test_tile_one_repetition_on_array_gh4679`。逐字代码比对只命中 1/3 行，所以漏报。
- **N3 公开提示不进模型消息（清单 3，链路级）。** 见上表 R03 行。
- **N4 共享控制面（清单 31）。** 隐藏测试的断言函数来自 `numpy/testing/utils.py`，候选可以改它，评分时不会重置。这是共享机制，本题不下定论。
