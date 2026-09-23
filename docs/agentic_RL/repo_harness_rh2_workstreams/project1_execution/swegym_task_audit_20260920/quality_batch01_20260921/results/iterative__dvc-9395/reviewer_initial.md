# iterative__dvc-9395 独立复核初判（封存）

2026-09-21。独立 reviewer；本包第二题，已先封存 5839。未读本包任何主审/公开读者/旧质量审查结论。第一阶段仅静态原件阅读与元数据校验；没有运行项目、安装、Docker、SSH 或模型。下述新 CPU 实验全部未执行，初判落盘后不改。

路径约定：`R=${REPO_ROOT}`；`P=R/runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-9395`；`Q=同材料根/private/iterative__dvc-9395`；源码行号相对 P/base；`E=R/runs/env_recipe_repair_20260919/dvc_tail_v1/tasks/iterative__dvc-9395`。

## 独立结论

题面清楚要求 `repro --pull` 自动取回本次复现必要的缺失数据，特别指出只有 outputs、没有 command 的 data source。base 在 Stage.run 的 data-source 分支只验证缺失文件，未尝试拉取；已有 run-cache restore 只在本地存在可用运行记录时尝试取输出。gold 增加全仓 run-cache 拉取及每个 changed stage 的 pull，原始运行证明它能使本题所执行 30 项全部通过。

但我不建议直接把本题列为无语义争议的模型探针候选。需先做窄 CPU 对照：新增 `mock_checkout.call_count == 3` 把某个内部实现路径变成 F2P 必要条件；新增 import 测试执行过，却不在冻结参考集；gold 的新拉取在 `dry=True` 时仍执行，并在任何 stage 判断前要求默认 remote。后两点都有明确源码链，属于高置信静态回归线索，尚非当前执行证明。还有 changed stage 的旧输出已不再必要但远端缺失时，提前 fetch 可能阻断本来可本地重算的路径，需要定点确认。

处置为 `static_review / needs_review`，仅 development_diagnostic。环境维修的 gold/noop 对照有效，但不能代替测试标准与 gold 回归审查。可以受限用于“有本地默认 remote、非 dry、缺失 data source/run-cache 恢复”的开发诊断；必须检查补丁真实行为，并保留调用次数误拒及参考集漏项，不能将它的 reward 当全功能正确性标签。

## 暴露与身份核对

已读四份方法/环境卡；P 的 user_prompt、public_bundle、environment_brief、base_identity；Q 的 grading、test.patch、gold.patch、validation、run_refs、source_refs、environment_record。environment_record 暴露 verified_environment_pair、gold/noop reward，以及 compat_v1/dvc_install_v1c/dvc_tail_v1 的 history 与 analysis 路径名；没有打开那些汇总。此前已经见过 5839 的原件、gold 和自己的初判，不是公开盲读者。未读任一 public_read、analysis_before_history、old_findings_delta、card、screening_record、任何 review、质量 history、manifest、主计划、method_adjustments 或其他角色结论。

P/base_identity 声明 commit `c75a5583b3840ba90a8e800a0f42c1cb120916db`、tree `865bc0582bc98990dc7eface03520a6c6335a6fa`、608 tracked entries、无 Git 元数据；公开/私有 base 一致。本次没有重建 tree。标准库文件校验确认 test.patch=grading.test_patch，gold.patch=validation.golden_patch，gold SHA-256=`4a5017f1dfa6375041fd1a4ce055a5bcc1a7bedc221ccada2cc0732044667d4a`，两份指定 eval.log 哈希均匹配 run_refs。

## 需求—断言与反向来源

| 要求/合理回归 | 公开或源码依据 | 实际测试断言与参考身份 | 覆盖/冲突及证据 |
| --- | --- | --- | --- |
| 缺失普通 data source 能恢复并供下游使用 | 题面主例；stage/__init__.py:242–244,564–584 | 新 F2P `tests/func/test_repro_multistage.py::test_repro_pulls_mising_data_source`：本地 dvc_gen foo、push、建 cp foo bar 阶段、删 foo 与它的 cache；唯一显式断言 `assert dvc.reproduce(pull=True)` | 跑真实本地 repo/命令，非纯 Mock；执行正常路径可验证 source 可用，但未直接断言 foo/bar 内容和 stage 身份，简单返回真值也可能越过此断言，需看其他 F2P/P2P 约束 |
| 缺失 imported data source 也可取回 | “all missing and necessary”；is_data_source 定义包含 import | 新 `test_repro_pulls_mising_import`：本地 erepo 建并 commit foo、dvc.imp、push、删工作文件/cache，assert reproduce(pull=True) | 原 noop 失败、gold 通过；**不在 2 个 F2P 或 27 个 P2P 中**。已执行不能自动等同冻结 reward 有此保障；只让此项失败时的实际 reward 仍需 CPU 定点确认 |
| 缺失中间输出自动恢复 | 题面 all necessary；旧 StageCache.restore | 新 P2P `test_repro_pulls_intermediate_out`：echo 产生 foo，cp 到 bar，push 后删 foo/cache；assert reproduce(pull=True) | noop 已通过；不检查拉取与重算的区别、不阻止 echo 重执行、不检查内容。证明该例可完成，不证明这次新增拉取路径必要 |
| 丢失本地 run-cache 时仍恢复缓存并不重跑 command | 原 test_restore_pull 意图及 stage/cache.py:178–213 | F2P `tests/func/test_run_cache.py::test_restore_pull`：push 改为 run_cache=True；删 bar/lock/cache、新增删 stage_cache.cache_dir；spy restore 恰一次且 pull=True,dry=False；Mock cmd_run 不得调用；bar 与 lock 存在，foo 可 unlink | 新场景扩充合理；noop 因缓存记录缺失走被 Mock 的 command 后 bar 不存在失败，gold 通过。bar 没有直接内容断言，存在性与旧缓存机制共同约束 |
| 同一恢复可用不同合理实现 | 公开目标不规定 output.checkout 次数 | 上项新增 `mock_checkout.call_count == 3`，原本为 2 | 额外 pre-pull/checkout 的 gold 路径被固定。保留 source/import 拉取、让 pipeline 原有 StageCache.restore 处理缓存，或先 fetch 后按必要对象 checkout，可能业务正确却调用 2 次；这是需执行的具体误拒候选，未声称已经证实 |
| dry 只展示，不改工作区/下载 | commands/repro.py:138–144；stage/run.py:125–151；stage/cache.py:201–213；func/test_repro.py:287–305 | 评分 P2P `test_do_not_save_on_no_exec_and_dry` 仅 dry=True，无 pull；原 test_repro_dry 不在本题执行文件/冻结参考集 | 缺 pull+dry 组合。gold 新的 stage_cache.pull 与 repo.pull 没有 dry guard；后者会 fetch 并 checkout。静态有回归链 |
| 没有缺失文件时正常跳过，不凭空要求 remote | Stage.reproduce:424–429；公开 “missing and necessary” | P2P 的 unchanged、frozen、command/deps/outs/lock 变更大都 pull=False | gold 顶层在任何 changed 判断前 stage_cache.pull(None) → get_remote_odb → get_remote；无默认 remote 时 NoRemoteError。可构造全本地 unchanged pipeline 与 base 对照；未执行 |
| 仍可重算变更输入后的输出，旧无用输出不应阻断 | Stage.changed_deps、run_stage 的缓存 miss→cmd_run；题面必要性 | 无“deps 已变 + 旧输出 cache/remote 都缺”的 pull P2P | gold 在重算前 pull(stage)；allow_missing 只传 checkout，fetch.py:122–125 仍抛 DownloadError。是否因此阻止可合法重算需定点验证 |

## 全部 F2P、相关 P2P、fixture 和调用链阅读范围

两份完整 base 测试文件 `tests/func/test_repro_multistage.py:1–399`、`tests/func/test_run_cache.py:1–185`，加 test.patch 所有新增/修改部分均已逐条阅读。冻结 F2P 共 2，已在上表逐项核。冻结 P2P 共 27，实际分组如下，不把数量替代覆盖：

- multistage：non_existing_stage_name、repro_frozen、downstream；repro_when_cmd_changes；new_deps_is_added_in_dvcfile、new_outs_is_added_in_dvcfile、new_deps_is_moved、new_out_overlaps_others_stage_outs、new_deps_added_does_not_exist、new_outs_added_does_not_exist、lockfile_gets_deleted；cyclic_graph_error；multiple_params；list_of_commands_in_order[True/False]、list_of_commands_raise_and_stops_after_failure[True/False]；新增 intermediate_out。核了 exception、stage 顺序、文件内容、lock/参数持久化及停止后续命令等断言。其中 in_order 测试的 multiline 构造随后被固定 YAML 覆盖，两个参数并未真正形成不同输入；为原测试弱点，不是 gold 新增回归。
- run_cache：push_pull、restore、save、do_not_save_on_no_exec_and_dry；outs_no_cache_deactivate_run_cache 的 metrics_no_cache/plots_no_cache/outs_no_cache 三项；memory_for_multiple_runs_of_same_stage、memory_runs_of_multiple_stages。核了 run-cache 文件数量、不同输入恢复内容、cmd_run 未调用及元数据，未据此声称 pull=True 的所有分支受到保护。
- fixture：读 tests/conftest.py:1–220 的 autouse 日志/UI/clean_repos/webbrowser/isolate（含 pygit2 常量），tests/dir_helpers.py 全文的 run_copy、erepo_dir；dvc/testing/fixtures.py 全文的 tmp_dir/dvc/make_local/make_remote/local_remote；dvc/testing/tmp_dir.py:1–223 的 init/gen/dvc_gen/dvc_add/add_remote/chdir；tests/scripts.py 的 copy.py fixture；test_run_multistage.py:220–226 的 supported_params 常量。local_remote 为本地临时目录并配置默认 remote；erepo 是本地 Git+DVC；新增三测试的 mocker 参数本身未用于伪造 pull。相关新功能不需要公网服务或 Docker。
- 源码：完整 reproduce.py；Stage 的类型、changed、reproduce、run/checkout 分支；stage/cache.py 的 hash/load/restore/transfer/pull；stage/run.py:119–151；完整 repo/pull.py、fetch.py 相关 45–174；data_cloud.py:1–110；output.py:1084–1119。读 CLI common kwargs/pull/dry 帮助；沿 experiments/run.py 的继承和 executor/base.py:477,556 调用核潜在影响，不声称审完 experiments 全链。额外公开回归测试抽查 func/test_repro.py:287–319,656–685。

## 八方面判断

1. **公开需求**：明确扩大缺失输入/输出恢复，源码足以发现 data-source 和运行缓存两路；“necessary”不应变成无条件下载所有数据。CLI 帮助 gold 未更新仍只提 run-cache，是文档欠完整；不能靠改文案代替修数据路径。真实 CC 消息/hints 适用性未知。
2. **材料/初始故障**：base 与题面路径吻合；补丁/日志哈希一致。原 noop 实际两 F2P 与 import 抛出业务异常，非 pygit2 环境失败；当前环境维修证据适用该版本。
3. **测试命中**：三个新用例和一个修改用例、两 F2P、全部相关 P2P 已核；import 在执行集但不在冻结集；intermediate 非新增能力鉴别；新数据源测试只有 truthy 返回；实际本地文件执行仍提供比单纯 Mock 更强证据。
4. **合理解误拒**：call_count=3 的业务必要性无公开依据，需用少一次无用 checkout 的真实恢复实现区分。旧 restore.assert_called_once 的内部形状也限制重构，不能为满足测试故意补无用 checkout；未跑替代实现，保留疑点。
5. **gold/回归**：gold 主例成立，但静态可见 dry、no-remote、HTTP run-cache 不支持（cache.py:224–231）和 version-aware/worktree remote（data_cloud.py:105–109）问题；后三者源于新顶层 run-cache 操作。stage pull 范围包括 changed command/deps，并非仅 missing outputs；旧输出必要性和本地修改保护仍待测。未宣称所有问题已经实测复现。
6. **开发条件**：公开 pyproject/tests fixture 可找到本地开发入口；pygit2 固定是现有诊断配方事实。actor 是否消费配方、解释器激活/权限、实际 Git/shell/包资产均待验，不因 grader 30 passed 填正常。
7. **交付评分边界**：test.patch 仅两份 tests 文件；原日志恢复这两文件再应用官方补丁。gold 只改 dvc/repo/reproduce.py，ledger projection included_paths 对应、ignored_paths=[]；合理普通源码修复不被官方文件恢复覆盖。实际镜像可见答案、共享 parser/投影安全及真实 actor .git 未审，未设额外路径排除。
8. **关系用途**：已审 5839 为早期 metrics 参数问题，本题为 2.56 多阶段复现/缓存；没有材料证明同问题派生。源码迁移/同仓不足以并簇。此上下文见过私有答案，只作审查和 development_diagnostic，不计独立模型求解或预估学习价值。

## 历史真实 RH2 运行与冻结参考分开记录

E/{gold,noop}/ledger.jsonl 第 1 行，2026-09-19，recipe=`dvc_tail_v1:iterative__dvc-9395`，实际本地派生镜像 `sha256:e64191bff363b956d9f4fc6f2abde42eecbcc21cbf4fe47a01b7404f942f457b`，不同于 public manifest。grader 为 rh2grader/54322、deny_all、2 CPU/4 GiB、64 MiB shm、PID512、tmpfs1 GiB，/opt/miniconda3/envs/testbed 可写；candidate apply_user=agent/54321 不能证明 CC actor 环境。

- gold 指定日志 `evallog_replay-er19-dvc_tail_v1-_66688534.eval.log:208–216` 为恢复两个官方文件并应用 patch；`:624–631` DVC 2.56.1.dev27+gc75a5583b.d20260919、pygit2 1.14.1、安装 rc=0；`:641–653` Python3.9.19/pytest7.4.4 运行两个文件、30 collected；`:2434–2468` 30 passed、rc=0，包括两 F2P 与 import。ledger reward=1、F2P2/2、P2P fail0/27、import=/testbed/dvc/__init__.py、cleanup removed=true。
- noop 指定日志 `evallog_replay-er19-dvc_tail_v1-_d7bf896d.eval.log:584–610` 同版本/成功安装/同两个文件；`:698–726,855` data source 缺 foo；`:1010,1145` import 缺 foo；`:1244–1492` restore_pull 在被 Mock 的 cmd_run 后保存阶段时缺 bar（不是仅 call_count 失败）；`:2950–2984` 27 passed、3 failed、rc=1。ledger reward=0、F2P0/2、P2P fail0/27。第三失败 import 不能悄悄算入 2 个 F2P。
- ledger num_parsed_tests=31，pytest 明确 30 collected/终态；本审查按测试体/官方终态判实际执行，未把 parser 数当新增测试证据，未另审 parser。
- E/gold/recipe/recipe.json 先从 `/opt/rh2/compat-wheels` 离线安装 pygit2==1.14.1，再 editable 安装 `.[all,tests]` 并报告 metadata；scope 为 diagnostic spec、原 driver/projection/manager/tests。读的是指定原日志，不是独立复跑。

## 开发需求和最小后续验证（全部未执行）

| 需要的操作/资产 | 公开依据 | 现有证据/适用范围 | 缺口 | 最小验证与预期 |
| --- | --- | --- | --- | --- |
| 工作区 DVC/Python/pytest 导入 | pyproject.toml:1–123；CLI entrypoint；测试文件 | grader import 与版本确定 | actor 实际激活、依赖与源码是否生效未知 | 统一 actor 入口打印 id/pwd/sys.executable/dvc.__file__/pygit2 version；应导入工作区，具备历史兼容依赖 |
| 本地 source→remote→缺失→repro | fixture make_remote/local_remote，tmp_dir.dvc_gen，公开描述 | 所有原新增用例用本地临时目录；无需公网/Docker服务 | actor cwd/tmp 写权限、cp/echo/Git 与实际资产未知 | 本地建 foo.dvc 和 cp 阶段，push 至临时 remote，删 foo/cache，运行 `dvc repro --pull`；检查 foo/bar 内容与 pipeline 结果 |
| run-cache 与 import 开发 | run_copy/copy_script；erepo_dir 本地 Git | grader 已实际执行；pygit21.14.1 由配方提供 | actor 是否有 compat wheels/安装权限，不是已知可用 | 先运行公开 `python -m pytest -q tests/func/test_run_cache.py tests/func/test_repro_multistage.py`；另在私有 CPU 诊断入口执行官方 patch，不把 hidden tests 交给 solver |
| 交付修复 | reproduce/stage/cache 为普通源码 | gold projection 有据 | 实际镜像源码基态/写权限待验 | 修复应提交仓库源码；临时 cache、remote、Git repo 由验证生成，无需把系统包修改当最终补丁 |

**唯一优先下一步**：做一个本地 CPU base/gold 回归对照，先锁定最少的两个条件：①已有完全 unchanged pipeline，未配置 remote，`reproduce(pull=True)`；②local remote 中有数据、工作区/cache 缺 source，`reproduce(pull=True,dry=True)`。记录异常、工作区和缓存前后差异以及真实进程身份。静态预期 gold 在①新增 NoRemoteError、在②实际取回/checkout 文件，而 base 不会有这两种新副作用。若确认，先修正 gold/测试版本，不将它们解释为环境维修未生效。

独立保留的第二个必要实验是合理替代方案校准：在非 dry、存在 local remote 的核心场景，避免 pipeline 的多余预先 checkout（source/import 仍按需拉取，run-cache 可恢复），核内容、命令是否执行、原 F2P 的 checkout 计数是否成为唯一拒绝原因。并以“只使 import 恢复失败”的变体核本题实际 RH2 评分是否忽略该未列入参考的测试。第三个候选为 deps 已变且旧输出远端不存在时应允许重算。三者都尚未执行，不能把设计当结果。

本文件封存；继续第三题原件初判，三份 initial 全部落盘后才等待协调者统一开放其他角色结论。
