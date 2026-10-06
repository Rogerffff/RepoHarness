# Moto6114 v4 入口与已完成 noop 复用非作者窄核

2026-10-03。审查者：Codex 非作者 subagent。范围只包括 v3→v4 工具差异，以及 `moto6114-cpu-ffe3a2e97334` 的本地运输原件；不重核材料语义，不执行远端、项目、测试或 Docker，仅新增本报告。已读私有评分和对照材料，不是公开盲读者。

**结论：v4 已从静态路径上消除 gold 输入／结果目录冲突，候选选择只裁减既有三臂，未发现阻断按既定版本补跑 gold／wrong_first 的新问题。该次 noop 原件可复用，不需要重跑。** 本次总体 job rc1，只有 noop 完成；gold／wrong_first 均未执行。本报告不把总体失败改成整体矩阵通过，也不授予真实 actor、完整 CPU 验收、探针或训练资格。

**修正先前审查结论：** 我在 [v3 静态窄核](moto6114_tools_static_non_author_20261003.md) 中漏掉了 `out/gold` 同时作为 export-gold 输出目录和 gold row_dir 的必然冲突；先前“v3 编排静态无阻断”结论对该入口问题不成立。新报告保留旧结论及实际失败原件，明确以本次 v4 窄核作为接续依据，不修改旧字节或回写历史运行。

## v4 差异与当前入口

固定版本仍为 R7 `cat2-cpu-r2e088-swe12-git-20261003-v1`，外部 manifest SHA `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`。v4 manifest SHA `0a3968d13043a3baab1f40ae150da54cae3577e7501844964635f2a7134e479c`、`matrix.py` SHA `51e94a18a5d653dce1c081d091027a9762713b211a49e667713676b554c75691`，均与题主交接相符；manifest 三件成员的 SHA／长度全部匹配。expected_runtime 与 image_recipe_binding 两件分别与 v3 **逐字相同**。

| 改动 | 静态核对与结论 |
| --- | --- |
| gold 输入目录 | v4 `matrix.py:155`–`:157` 的 export-gold 及 SHA 检查都改用 `out/gold_input`，gold candidate 的 `gold-dir:` 也在 `:165` 指向该目录；结果 row_dir 仍为 `out/gold`。三个引用同时修改，消除原冲突，不修改 gold 内容或哈希。 |
| 既有候选选择 | `:54` 的 `--controls` 使用 `nargs='+'`、封闭 choices noop/gold/wrong_first，默认仍全部三臂；`:56` 拒绝重复，在创建输出目录或开始命令前执行。参数必须有至少一个合法值；固定三候选循环在 `:167`–`:168` 跳过未选候选，没有新增候选、转换候选或改变预期分数。 |
| 独占目录 | 本轮 job 格式及 `out.mkdir(exist_ok=False)` 没变。使用新 job 可得到新的 prepared/private/gold_input 及结果目录，不复用或改写旧 job 的 noop 工件；已选择候选才创建它自己的 row_dir。 |
| 原正式调用 | prepare／export-gold／run 仍调用同一固定 R7 CLI；完整命令派生、1 F2P／34 P2P、原 `make init`、五份脚本摘要、实际派生 image ID、profile 限额、分段及清理预算均未改变。候选 run 参数除 gold 输入路径外逐字未变。 |
| 状态范围 | scope 新增 selected_controls；执行结果改为 `selected_controls_completed_pending_raw_readback_and_independent_review`，含本次选择和实际行，formal_cpu_accepted／actor_executed 仍 false。所选顺序不决定执行顺序，循环仍按 noop→gold→wrong_first；验收按候选名和实际行对账。 |

v4 可用新 job 的 `--execute --controls gold wrong_first` 接续；这是静态核对到的用法，本审查者未实际运行。两臂结果须与下述旧 noop 原件组合验收，不能把只有两行的新结果叫作本次单 job 全三臂完成。

## 原 job 的失败边界

原件根目录：`runs/category2_repair_20260929/moto_cpu_20261003/moto6114-cpu-ffe3a2e97334_evidence/`。运输 manifest SHA `ebd2bbd9499bf4e7b6679ae3f133e0cfafd97dbefbef0107ee4726a8cb9022f3`；所列 **43 件**原件的 SHA／长度均独立重算匹配。

- `job/status.json` 为 finished、returncode=1；`job/stderr.log` 明确在 v3 `matrix.py:167 row_dir.mkdir()` 抛 `FileExistsError`，路径为当前 job 的 `gold`。export-gold 已先成功创建该路径。
- job stdout 显示 verify_release、image_inspect、prepare、export_gold、run_noop 均开始并 rc0 收口，没有 run_gold 或 run_wrong_first 开始记录；原件也没有它们的命令／退出文件或 ledger。**后两臂为零执行，不是失败评分。**
- noop 独立 CLI 已在目录冲突发生前结束并清理，其 `run_noop.exit.json` 为 0。外层题级编排后续异常不使该已完成评分行失效，也不改变总体 job rc1。

## noop 的身份、实际执行与清理

ledger 仅一行，task ID 为本题，run ID 为 `moto6114-cpu-ffe3a2e97334-noop`，`stage_error=null`、candidate apply_method=noop。实际 frozen_patch entries 为空，projection included_entry_paths 为空，分类 projectable、无理由码；基线／公开身份、materialized HEAD 及 runtime_image_digest 都有绑定，不是作者只填一个 reward 的记录。

| 核对项 | 原件中的结果 |
| --- | --- |
| 固定材料 | `consumer_readback_before_checks.json` 中所有已核字段都与 v4 未变的 expected 对上；包含 public／grading／environment digest、base、完整命令、原 1／34 参考、有效补丁 SHA、revision context 与五份生成脚本 SHA。runtime_inputs 外部 manifest 为固定 R7，scope 的工具 SHA 为原 v3，不能改称 noop 是 v4 运行。 |
| 派生镜像／预算 | CLI command、ledger 实际 image_id、frozen runtime_image_digest 均为 `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`，recipe 为固定 COPY-only；candidate/grading/cleanup/image 预算为 900/1800/120/1800 秒。policy 记录 2 CPU／4 GiB／512 PIDs、64 MiB shm。 |
| 可信 setup | sidecar 的 setup footer 为 apply_rc=0、restored=1、expected／present_test_files=1、absent=0、irregular 空、setup_ok=1；control_surface expected_files=1、missing=0、protect_ok=1。git sanitize 状态 verified，HEAD 保持 base，远端／reflog／unreachable 均 0。 |
| 原安装 | 原 eval log `:357` 执行 `make init`；两段 editable 构建的依赖、metadata、wheel build、卸载／安装均完成，分别有 `Successfully built moto`／`Successfully installed moto-4.1.0.dev0`。未出现真实 `RH2_INSTALL_CMD_FAILED=` 或安装 error；install_rc=0、未跳过、日志不残缺。sidecar 观测导入为 `/testbed/moto/__init__.py`，runner_integrity_changed=false，安装观测摘要前后相同。这里核了日志，未仅凭段末 rc。 |
| 完整测试 | eval log `:529` 命令为 `pytest -n0 -rA tests/test_rds/test_rds_clusters.py`；collection=35，完整逐条 short summary 为 34 PASSED／1 FAILED；测试汇总 `1 failed, 34 passed, 165 warnings`，`RH2_TEST_RC=1`、Start/End 标记和结束时间齐全。candidate exec rc0 表示脚本完成，不等于测试全部通过。 |
| 失败原因 | 唯一失败为 `test_describe_db_cluster_after_creation`。实际 traceback 显示名称查询之后，在有效补丁的 `clusters = client.describe_db_clusters(DBClusterIdentifier=cluster_arn)["DBClusters"]` 处抛 `DBClusterNotFoundFault`，对象为 `cluster-id2` 的实际 eu-north-1 ARN；属于 base 的预期目标失败。它在新身份断言前停止，不能称 noop 已执行全部新增断言。 |
| 逐参考结果 | 从原 log 的 PASSED／FAILED 节点重新抽取，对上 expected 的完整原清单：唯一 F2P 失败，34 P2P 逐项全通过，未见额外失败。revision sidecar 两分区的 missing／skipped／unaccounted 均为空，parser num_parsed_tests=35、outside_segment=0、reference_missing_count=0，state=parsed、apply_ok=true。 |
| 原报告 | reward=0、outcome=unresolved、failure_category=tests_failed，F2P 0/1、P2P fail 0/34，infra_failure_detail=null；与实际失败及节点对账一致，不是环境／parser 故障造成的零分。 |
| 两层清理 | ledger candidate cleanup.removed=true、steps=[rm:ok]；CLI 最后 manager_close containers_open=[]、supply_open=[]、cleanup_failures=[]，created_total=removed_total=1。halted／aborted 都 null，final_status.exit_code=0、reason=ok。另 residual_noop 的容器／网络查询均 returncode=0、stdout／stderr 为空，确认本 run 双资源零残留。 |

关键原件 SHA：noop ledger `1f6e7089780d1c3097c5efa15987d267f48d9e1954fa344ff6b82812d05f985f`；原 eval log `8517cb5e76350ab9895b76fa50cfed3ded736131f845a23d0286b09b692c4f47`。完整原件和运输清单保留，不转写为新 job 或新工具版本。

## 接续验收范围

已完成的是 **R7／v3 的一条有效 noop 负对照**及其独立原件核查。v4 只改题级目录和候选筛选，consumer／材料／镜像／脚本／预算未改，因此复用该行有具体依据，没有必须重跑 noop 的受影响行为。

尚需 v4 的 gold 与 wrong_first 实际执行原件：gold 全 35 参考通过、原安装／测试／footer 完整；wrong_first 因返回错误集群触发新增身份断言失败，34 P2P 保持、没有缺席或 skip；每臂均须原 CLI 正常收口及自有容器／网络零残留。它们的读取条件沿原三臂验收，不新增公共契约或审批闸门。补齐前不宣称完整 0／1／0。新宿主 UID smoke 与公开历史路径复用另见 [对应窄核](moto6114_public_actor_reuse_non_author_20261003.md)，不由本次 noop 评分替代。

本轮停止条件：入口冲突的静态修法明确，已完成 noop 的身份／实际节点／安装／测试／清理原件充分。未发现必须先改的 v4 差异；本轮未执行任一候选，也未改生产、题主材料或旧原件。
