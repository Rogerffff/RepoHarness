# DVC9395 R20 六控制正式 CPU 与历史公开 actor 适用范围窄核

核查日期：2026-10-03。结论：**当前固定 R20 的六项正式 CPU 运行证据、版本绑定及清理可验收，未发现新增阻断。** 依次为 noop/gold/c3_frozenfix/c3_missing_only/up351_port/w_swallow3，正式 reward 为 **0/0/1/0/0/0**；每项实际执行41个节点，其中40个计分参考，均无 skip、缺席或收集错误。正对照是 c3_frozenfix；原 gold 在当前有效版本确实失败，不能替换成成功，也不能由此推断旧原版正式成绩。

本结论支持关闭此题当前六控制 CPU 窄核、固定 CPU 验收和继续已授权普通基座诊断的 GPU 交接。尚无新 R20 actor 执行、GPU 部署／模型结果；不授予探针通过、训练／holdout、稳定性、完整安全或最小资源资格。本人已经阅读私有材料和既有结论，**不是 fresh 公开读者验收**。本轮只用本机 stdlib 离线核对；没有运行 CPU、SSH、Docker、pytest、模型或上述 helpers，也没有改输入、正式 parser、评分、旧日志或旧报告。

## 1. 原件范围和重建方法

按题主固定交付，读取六份归档及对应 manifest/receipt、prepare/completion/invocation、prepared 三文件与私有 host view、完整 eval.log/diagnostics/ledger、候选／FrozenPatch／baseline manifest／projection、slot 状态、进程退出和 cleanup 原件。前三项复用本人的已核逐行读回并重新核当前文件 SHA；新增后三项逐份核全部成员 SHA、size、精确集合及 tar 内字节，再从完整 pytest 状态行自行重建。共216份 raw 成员副本，六份 tar 各另含一个 manifest；此数包含重复 prepare 等成员，不是216个互异事实。

正式 matrix 实读 SHA `759924ac16166deae54144b6be02cd9e040f73c5d02d064bdd505fadc421e3be`；逐项与独立重建的状态、报告、参考分区、原件和退出链一致。它当前仍标 `formal_controls_complete_non_author_review_pending`／`qualifies_for_probe:false`；该状态不被本报告静默改写。作者 checkpoint 与 collector 摘要仅用于导航，未用其 actual_states 代替日志重建。

原件公共前缀为 `runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/`，根名均为 `formal9395_r20_<candidate>_032003_v1`，同名 `.tar.gz` 和 `.receipt.json`。以下是实际读回，不直接相信 receipt 的 verified 标记：

| 候选 | raw数 | tar字节 | tar SHA256 | manifest SHA256 |
| --- | ---: | ---: | --- | --- |
| noop | 35 | 89149 | `5d32ae145e8692532717c1fd9d3a635f03854f39410eb7bb12f59792cb80e183` | `d05c23bbd975b851eedb95ff4a8dd7f0b4c8ad02111792601ac0e861790860df` |
| gold | 36 | 103013 | `d5c2313f6ea050a9b4685fa638417ee28b21932a887860c97c87cfedb7391a69` | `610dfa54232153132cb981fff67c926d140c367ec55386cd2774270621572fa8` |
| c3_frozenfix | 37 | 96902 | `c3dce31c58a6f4ccd85a595b288d54a12b6d1415465e6370c76cc5ac475b90f4` | `17433df1b07582644568a1a8d7ac9830dff1729be01ec75cce89e8e4b35c5aae` |
| c3_missing_only | 36 | 96415 | `ea769fd93494930f52bc4d4db173071adde4888ddd0c343b7c189c915caf748e` | `a611a73e1d1f93c1df519b2c8f1aeea25893378b6faef6075a346c0a635bb4a9` |
| up351_port | 36 | 110483 | `fcb40fc285bf68a3b0d95128cc25a2f01b07f8499ff82f993e6b39a0a3f3418f` | `b7e2181a424e8196460f0bae16380fe77c308886621c978242faddad2c19abb4` |
| w_swallow3 | 36 | 97692 | `350bb8d48ccb4fcf741308ae9f2e4038a163f2da42b3551d4d0429d5b467ed60` | `9537632ad3a7fca2d7a59c77ff4dd2816de73fff7c95e614722b191b3447370f` |

六根实际普通文件集合均严格等于 manifest.files 加 manifest.json；成员路径无重复；tar 普通成员集合亦相同，逐成员字节与落盘一致。raw 的完整路径／SHA／size 就在上述已固定 manifest，不另复制一份作者清单。没有遍历重核 release 全部1479成员或重审其它题：release／consumer 变化复用已完成 R20 窄核，1479是 wrapper／部署的记录，不能计作本轮1479项独立源码重审。

## 2. 新 prepare、固定材料与实际调用链

prepare 为 `dvc9395-r20-prepare-20261003-031559`，2026-10-03 03:16:06–03:16:15 UTC，正式 `replay_grade.py prepare` 实际退出0；六项均消费这一份新 summary。没有重绑旧 R14 prepared 或旧 FrozenPatch。prepare input、成功 completion 固定 summary SHA；run input 固定 completion SHA，并与 task/release/runner/runtime/summary 同一链。summary 再固定 manifest 与 private host view，manifest 固定两个公开文件；已从字节独立重算。

| 对象 | 实读 SHA256／绑定 |
| --- | --- |
| R20 release manifest | `2a4ceb0315ea959232151d70f29ccc48bd34bdb0cb7dcfbb4aa177fec07bd393` |
| prepare_input.json | `db0ca992989946682244948a9f659eb0cc9da3a5d54e7a2614943fcfd69f87a1` |
| run_input.json | `e459f6f54bd71a152cfdcccd1eb724b9e9332602269c62eba3a481e687c32d3d` |
| formal_cpu_check_v2.py | `16a78e7019827e126d0788dcbb4bf13bd0ce913a9df842b79b9c110e75dc24c0` |
| prepare invocation | `b9fe9b18463c916f44b373efb2341ae1bc81e2b84ec4fc5854d54023a0e6baf8` |
| prepare completion | `ee5b6654a0a107a5335c219bd817879c732a154e73a0f6b402b209744d8afd06` |
| prepared/replay_summary.json | `47d78323f469bab6a4462cebc8c91a005345e0865a51e088e9d1e2cfc57a56f1` |
| prepared/prepared_manifest.json | `756fa907f464bf58edafb812845869558012ce35a266f1f2e1086e63cc8942ef` |
| prepared/prompts.jsonl | `5bfbc9056521434fa789707feb1bbeb0fd19bfe13c3eec6a7eed7c6b2ab8a367` |
| prepared/rollout_task_views.jsonl | `a81d2e0d8a2cf61c2bd7d84bbf1c728a5d0683246357a742eb846ce5d7d6bac9` |
| private/host_grading_views.jsonl | `21198a8ee0f8b99e693b93110834b00d4445f5de4755a933c4a7708da51ab34e` |
| prepared_actual_spec_readback_v1.json（六份相同） | `a26d4876d59ab6866725afa032a4b631daa3793052387135e3cc15918d02205b` |
| source revision registry | `815811717d21fa259b354eaf85a1598241d66d85b5af547d9208b2835c4edace` |
| publication receipt | `dd6e6894a4079e141d2fe54ab3775d012d58f3b0adbfedfede8813598f0447cb` |
| fixed preparation policy | `d417dbb8d3140e6a0082f2f12cda02fd492feb14db9375ace3d69222e48acdab` |

新 host view 内嵌 grading 对象规范 JSON 摘要独立重算为 `b939c2ea3070d0187a663891f33affc5347ee0029c048cf0c984be4f0d02f8f8`，test_patch UTF-8 SHA 为 `964c80ef786b71091fcc722d8b3fdcd8afe8ba7e3f5fb511d6cb9661a25c2777`。revision=`dvc9395-behavior-v2-draft`，材料身份=`9d456666b845fd90146499033601805ce2ecdc3d88e26202f8b9855cf287f68a`，scripts digest=`ec5f61cf288b78aaafd469b40013bcd571e93e1ab5db7c32c8852b6a83f035f3`，environment digest=`62df73d0a7bf30057b6b4e585cc799a09c853c320310e32f93f9f7b6aaaf437e`。六份实际源数据、spec读回和 ledger 均闭合到此版本。

实际派生镜像 ID 均为 `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60`，ledger.image_id_actual、FrozenPatch.runtime_image_digest、run --derived-image 和实际 spec 一致；local-build 的 image_manifest_digest／image_digest_expected **为 None**。这与公开基础镜像 manifest `sha256:479c3af753c367bfe088c4879524980c8f4ba0e67958c38db3ba6c5d2c4e0c0e` 是两个不同字段，不能混用。

R20 policy 精确核 task/revision/grading digest/test patch/image+None，request_input_sha=`3bf174133d17334cc752c4a9775acf9782fc2017b76cd4682d5202081c1ddf57`。actual spec 和六 ledger 的 env_reset=900；candidate_stage=900、whole grading=3600、cleanup=120、image_pull=1800，与实际 invocation 参数一致。static review 已证 replay 用同一实际 spec 写预算并传 candidate/manager.grade；本轮没有自由加预算或改保护。旧静态 replay 8例替代 Docker／candidate 并在捕获完整 spec 后主动停止，仅证明接线／落盘／拒错镜像，仍不计入这六次真实 CPU 或 pytest。

各 run 实际为冻结 release 的官方 `replay_grade.py run`、repeat=1、独立 job/ledger/eval/artifacts 路径，task=iterative__dvc-9395。前三个和后三个 job 均为 `dvc9395-r20-<candidate>-20261003-032003`，唯 c3_missing_only 是实际成功入槽的 `...-a5`，不能把之前 slot75 排队当执行。wrapper/slot/官方进程均退出0；负候选 pytest 退出1是完整 segment 的正常测试失败，不能把 shell exec0 或 wrapper0写成 pytest0。

## 3. 候选、baseline 与 FrozenPatch

六份 baseline manifest 的规范 SHA 均为 `0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec`，materialized head 均为 `c75a5583b3840ba90a8e800a0f42c1cb120916db`，public bundle digest=`1f95551f8b887dc01d5a2c2fba8aef01a449c701e1577dec4905181f14abafd9`。原 candidate.patch 与 run input 固定 patch 字节相同；逐条解码 FrozenPatch.content_b64 并核 content_digest、规范 artifact digest与 projection/ledger一致。classification均projectable，excluded_pathset_changed=false，未投影 test/conftest/fixture。

| 候选 | 原 patch SHA256（noop为空字节） | FrozenPatch 规范 SHA256 | included paths |
| --- | --- | --- | --- |
| noop | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `66f9049d2a2db26e7eee3aa098499f3f80160e3f2d20baaad74bc5b29fd6068f` | 空 |
| gold | `4a5017f1dfa6375041fd1a4ce055a5bcc1a7bedc221ccada2cc0732044667d4a` | `81b958919ecebf52c9b23485080653e5a2fbdae01b623670359914cd6e0ab760` | `dvc/repo/reproduce.py` |
| c3_frozenfix | `94d448480d67d7e74bc97e90266b69d99a1f58e499992dab45161491b4412040` | `abff93487ce3763ca0df7f9d854481ba0e754cc6871430476e1f2794361631ce` | `dvc/repo/reproduce.py` |
| c3_missing_only | `ac0a90ac6ec289ea632582201224dfd17526b0fa1df636d0772c867d352566c6` | `8e565f8931ae87940923c447ceaf5219cc517dc555a4fed4c5efc70762567364` | `dvc/repo/reproduce.py` |
| up351_port | `ca53ee797f31c61d3412e297e2aad73e0afc2d5dabb3d53bc4fab5b1f1c321c2` | `5e2bdf94d283f1bc093694c933d550fddc6de4e25082dd459174fc2bf366a33c` | `dvc/repo/reproduce.py`, `dvc/stage/__init__.py` |
| w_swallow3 | `dcc198d267a8f79072a219e6eea3921d8ce8a49083477f531c4313d411ccce2a` | `8a0f4d62213d1a094e4534cd765f3455a3bbc04b31f45710a34816308d155771` | `dvc/repo/reproduce.py` |

这是原 FrozenPatch 内容／清单读回，未以阅览 diff冒充工件，也未再次运行 git apply。baseline归档只有 manifest而非全部源码字节；真实恢复的补足证据是冻结 trusted script、固定两基线测试 SHA、运行 setup attestation 与 candidate sanitize。原公开基线测试 SHA 分别为 multistage `ca738a7a94b991881a48abdb02aa1d27565f087e5742511d1fbbd752afde99e1`、run_cache `0d9bfa7a96c4e29e178c89b96357ec1adae59bfa27027173f07b234b08504960`。

## 4. 完整运行和逐参考矩阵

执行命令均为 `pytest -rA tests/func/test_repro_multistage.py tests/func/test_run_cache.py`。参考分区为 bound_source_f2p=2、added_f2p=1、bound_source_p2p=27、added_p2p=10，合计40；另外执行原公开行为 `test_repro_pulls_mising_import`，没有计分。此处“import”是测试名称，noop 的实际行为失败不能被解释为 Python import／收集错误。

| 候选 | PASS／FAIL／skip（分母41） | F2P通过／3 | P2P失败／37 | pytest rc | reward／outcome | 安装 rc／slot及官方进程 rc |
| --- | --- | ---: | ---: | ---: | --- | --- |
| noop | 37／4／0 | 0 | 0 | 1 | 0／unresolved | 0／0 |
| gold | 30／11／0 | 2 | 10 | 1 | 0／unresolved | 0／0 |
| c3_frozenfix | 41／0／0 | 3 | 0 | 0 | 1／resolved | 0／0 |
| c3_missing_only | 40／1／0 | 2 | 0 | 1 | 0／unresolved | 0／0 |
| up351_port | 35／6／0 | 3 | 6 | 1 | 0／unresolved | 0／0 |
| w_swallow3 | 30／11／0 | 2 | 10 | 1 | 0／unresolved | 0／0 |

各40参考 missing、skipped、unaccounted为空，六次 reference_missing_count=0；不是凭“reward符合预期”倒推覆盖。下表从完整 pytest 状态行重建：P=PASSED，F=FAILED；M=`tests/func/test_repro_multistage.py::`，R=`tests/func/test_run_cache.py::`，只缩短重复路径前缀，节点拼写／参数保持原样。分区 S-F=bound_source_f2p、A-F=added_f2p、S-P=bound_source_p2p、A-P=added_p2p、extra=未计分。列依次 N/G/C/M/U/W，对应上述六候选。

| 精确节点（前缀缩写） | 分区 | N | G | C | M | U | W |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `M:test_non_existing_stage_name` | S-P | P | P | P | P | P | P |
| `M:test_repro_frozen` | S-P | P | P | P | P | P | P |
| `M:test_downstream` | S-P | P | P | P | P | P | P |
| `M:test_repro_when_cmd_changes` | S-P | P | P | P | P | P | P |
| `M:test_repro_when_new_deps_is_added_in_dvcfile` | S-P | P | P | P | P | P | P |
| `M:test_repro_when_new_outs_is_added_in_dvcfile` | S-P | P | P | P | P | P | P |
| `M:test_repro_when_new_deps_is_moved` | S-P | P | P | P | P | P | P |
| `M:test_repro_when_new_out_overlaps_others_stage_outs` | S-P | P | P | P | P | P | P |
| `M:test_repro_when_new_deps_added_does_not_exist` | S-P | P | P | P | P | P | P |
| `M:test_repro_when_new_outs_added_does_not_exist` | S-P | P | P | P | P | P | P |
| `M:test_repro_when_lockfile_gets_deleted` | S-P | P | P | P | P | P | P |
| `M:test_cyclic_graph_error` | S-P | P | P | P | P | P | P |
| `M:test_repro_multiple_params` | S-P | P | P | P | P | P | P |
| `M:test_repro_list_of_commands_in_order[True]` | S-P | P | P | P | P | P | P |
| `M:test_repro_list_of_commands_in_order[False]` | S-P | P | P | P | P | P | P |
| `M:test_repro_list_of_commands_raise_and_stops_after_failure[True]` | S-P | P | P | P | P | P | P |
| `M:test_repro_list_of_commands_raise_and_stops_after_failure[False]` | S-P | P | P | P | P | P | P |
| `M:test_repro_pulls_intermediate_out` | S-P | P | P | P | P | P | P |
| `M:test_pull_dry_preserves_workspace_and_cache[source]` | A-P | P | F | P | P | F | F |
| `M:test_pull_dry_preserves_workspace_and_cache[output]` | A-P | P | F | P | P | F | F |
| `M:test_pull_without_remote_when_nothing_missing[normal]` | A-P | P | F | P | P | F | F |
| `M:test_pull_without_remote_when_nothing_missing[dry]` | A-P | P | F | P | P | F | F |
| `M:test_pull_without_remote_preserves_modified_source` | A-P | P | F | P | P | F | F |
| `M:test_pull_without_remote_still_errors_for_missing_source` | A-P | P | F | P | P | F | F |
| `M:test_pull_no_run_cache_does_not_download_runs` | A-P | P | F | P | P | P | F |
| `M:test_pull_existing_output_without_hash_can_run` | A-P | P | F | P | P | P | F |
| `M:test_pull_changed_dependency_can_recompute` | A-P | P | F | P | P | P | F |
| `M:test_pull_restores_from_http_with_local_run_cache` | A-P | P | F | P | P | P | F |
| `R:test_push_pull` | S-P | P | P | P | P | P | P |
| `R:test_restore` | S-P | P | P | P | P | P | P |
| `R:test_save` | S-P | P | P | P | P | P | P |
| `R:test_do_not_save_on_no_exec_and_dry` | S-P | P | P | P | P | P | P |
| `R:test_outs_no_cache_deactivate_run_cache[metrics_no_cache-True]` | S-P | P | P | P | P | P | P |
| `R:test_outs_no_cache_deactivate_run_cache[plots_no_cache-True]` | S-P | P | P | P | P | P | P |
| `R:test_outs_no_cache_deactivate_run_cache[outs_no_cache-False]` | S-P | P | P | P | P | P | P |
| `R:test_memory_for_multiple_runs_of_same_stage` | S-P | P | P | P | P | P | P |
| `R:test_memory_runs_of_multiple_stages` | S-P | P | P | P | P | P | P |
| `M:test_repro_pulls_mising_data_source` | S-F | F | F | P | P | P | F |
| `M:test_repro_pulls_mising_import` | extra | F | P | P | P | P | P |
| `M:test_pull_recovers_frozen_stage_for_downstream` | A-F | F | P | P | F | P | P |
| `R:test_restore_pull` | S-F | F | P | P | P | P | P |

失败均落在已收集的行为调用／断言，不存在安装失败、import error、collection error、缺节点或 infra充当错解拒绝：

- noop：原 missing-source、原 restore_pull、新 frozen-stage downstream三个F及额外import行为均失败。分别为 MissingDataSource(foo/raw)→ReproductionError，或 OutputDoesNotExist(bar)→ReproductionError；完整日志首错误／最终错误位于741/875、1094/1229、1471/1609、1832/1975行。
- gold：原 missing-source 在701行 `AssertionError: assert []`，restore_pull及新F通过；十个新增P全部失败。dry[source]改变run-cache快照（968行），dry[output]发生下载错误→ReproductionError（1374/1508），四个 no-remote场景得到NoRemoteError，no-run-cache快照被改（2374），existing-output与changed-dependency经PromptError/ConfirmRemoveError到ReproductionError（2577/2827、2992/3242），HTTP场景RunCacheNotSupported（3412）。因此当前gold reward0真实且可解释。
- c3_frozenfix：41/41通过、40/40参考通过，正常resolved/reward1。
- c3_missing_only：仅新 `test_pull_recovers_frozen_stage_for_downstream` 失败；800行MissingDataSource(raw)，940行ReproductionError(download)，5611行失败状态；说明仅补 missing-source尚不能恢复 frozen producer以供 downstream使用。其余40实际节点通过。
- up351_port：F3/3通过，但dry[source]快照变更770行、dry[output]下载错误1190/1320行；normal/dry无缺失、modified-source、missing-source四个no-remote场景分别NoRemoteError 1607/1782/1955/2131行。六个A-P失败，35/41实际通过。
- w_swallow3：missing-source在712行FileNotFoundError(foo)，dry[source/output]快照变更874/1117行，四个no-remote场景1412/1581/1748/1918行，no-run-cache快照变更1989行；已有无hash输出未运行（2156行manual≠foo）、changed dependency未重算（2285行before≠after），HTTP RunCacheNotSupported2455行。吞异常并没有实现目标行为，F2/3而A-P10/10失败，30/41通过。

这些是当前固定六控制的必要行为解释；没有重审题义、扩断言或要求全部历史重跑。尤其旧 gold与新c3不是同一候选，后续对照应保留其不同身份。

## 5. UID、安装、保护、资源与清理

实际 candidate prerequisite 六次均在用户54322、HOME=/home/rh2grader执行，exit0、verified，stdout精确为 `RH2_DVC_BEHAVIOR_UID54322_WHEEL_BYTES_OK=1`。固定脚本 SHA=`1ef738bb44a2fd27407a54d08d9f4903c973a90d9e635f4badbdb8c6ebab2c6e`；脚本检查 os.geteuid()==54322、PIP_NO_INDEX=1、PIP_FIND_LINKS=/opt/rh2/build-wheels，O_NOFOLLOW打开7个普通wheel并逐SHA核字节（packaging24.1、pygit2 1.14.1、setuptools75.1.0、setuptools_scm8.1.0、tomli2.0.1、typing_extensions4.12.2、wheel0.44.0）。不是只核root能读wheel，不能把root trusted setup与candidate安装／测试执行身份混为一谈。

六次 trusted restore/apply均成功：restored2、expected/test_files2、apply_rc0、absent0、irregular空、RH2_SETUP_OK=1；保护均RH2_PROTECT_OK=1、expected/protected_files2、protected_dirs6、missing0、testbed root stat `0 1777`、writable prefixes done1。安装未跳过、完整segment、install_failed_commands空，RH2_INSTALL_RC=0；测试RC原日志与diagnostics/ledger一致，candidate exec exit0只表示携带状态的脚本正常完成。实际导入 `/testbed/dvc/__init__.py`，prefix owner54322，runner前后digest相等、runner_integrity_changed=false。

| 候选 | 安装秒 | candidate测试秒 | trusted setup聚合秒 | ledger mem_peak_mb |
| --- | ---: | ---: | ---: | ---: |
| noop | 9.622 | 30.239 | 209.157235 | 947.297 |
| gold | 9.88 | 26.8 | 248.715881 | 948.949 |
| c3_frozenfix | 10.18 | 31.588 | 161.07287 | 947.293 |
| c3_missing_only | 9.608 | 26.364 | 148.966321 | 947.203 |
| up351_port | 10.286 | 35.08 | 213.27916 | 947.766 |
| w_swallow3 | 11.089 | 32.88 | 203.056073 | 947.047 |

六次 ledger.policy均声明2CPU、4GiB、PID512、UID54322、deny_all、64MiB shm、1GiB tmpfs。**全部成功 ledger.resource_facts均null**；上表peak字段保留为运行记录，不能单独证明全程采样、OOM/PID状态、稳定性或最小资源。唯一可读live inspect为c3_frozenfix的单时点resource_observation（03:35:24.920694 UTC，SHA `bcd716a50b78c21a84b11913c6ce597f725b1f95085790c44619429b7be181ff`），对应准确job label/image：NanoCpus=2000000000、Memory=4294967296、PidsLimit=512、NetworkMode=none、安全配置和运行中/OOMKilled=false。ConfigUser为空表示镜像默认root用于trusted setup/protect；非candidate exec用户。不能把gold的空inspect列表或ledger政策当成其它五项实际HostConfig，也不能把这个快照扩为全程无OOM。

所有trusted setup聚合值148.97–248.72秒，均低于旧300；R20此次成功与900配套运行已证，**未证明“靠扩预算才恢复”或准备效率根治**。旧两次R14均实际protect300超时，具体子步／宿主争用仍未知。

两层清理六次均完整：ledger.cleanup为removed=true、rm:ok、detail空；进程manager_close created_total=removed_total=1，containers_open/supply_open/cleanup_failures为空，final_status.exit_code=0；每项另有cleanup_readback，按精确run_id查询containers/networks，rc0、stdout/stderr空、ids=[]，与receipt附本一致。这是当时该标签对象无残留，不扩为宿主所有资源全程无残留。后三项外层读回时间分别03:55:55.774401、04:02:21.467146、04:08:38.480160 UTC。

## 6. 离线collector计数边界与旧失败保留

旧collector v1 SHA=`adbeccb10d9b986229ccedcf1815a00a15a28df781d7670a9dd7cf850721a5a7`保留；当前v2 SHA=`f901a8b89a7b8e172d6efa37eb9f258fca2bedc0045bb102de1b9139724cf10d`，CLI仅9395，状态解析限所选两pytest文件路径，未改官方parser／材料／原日志。本人的完整日志重建与v2结果一致；captured logging的 `ERROR dvc.commands.freeze:freeze.py:19` 或 `ERROR dvc_data.hashfile.transfer:transfer.py:44`不是pytest额外节点。

官方diagnostics自身 num_parsed_tests也保留原值：noop/c3/c3_missing=42，gold/up351/w=43；这些值包含非参考logging字符串，不能充当实际分母。三参考F、37参考P及额外原import行为逐节点均已独立核满，没有skip/missing；无证据显示多出的非参考字符串改变此六次reward，不因此虚构需要重跑CPU。官方parser的这一计数限制仍存在，未被v2修复。

supervisor session81811退出1及最后旧collector断言42节点的原因，来自题主观察记录 `9395_r20_offline_collector_correction_v1.json`（SHA `42bb8e13d58e46e344e2a183ccc66060f23bceac81ea3d884d5b0251d98a820a`），不是本轮另获的supervisor原stdout；所有六个独立slot/官方进程0和原件完整可独立确认。v2 offline exit0／candidate_reruns0按该观察记录披露，不冒称有另一份原进程日志。原件字节和matrix链未变，不能将此末尾汇总失败分类为候选或模型失败。

`9395_r20_official_parsed_count_boundary_v1.json`实读SHA `81bef64da4129ca670af4a074b7923a1e806668b3b4598f1a148b6c39473d3e2`，与本人六项42/43及41/40分母核对一致；owner checkpoint SHA `7eaf101cac92ccf85d1ba362181e49128f3d507c1bd1c4dca3baf8d47f53c753`仅属导航。

旧R14首次与recovery的reward=null、protect300 infra、UID预检／安装／tests未开始和两层清理结论，原报告及原件保留；不改成0，不计本次六候选，不用隔离成功冒充正式恢复。当前R20六项已真实完整，故本次可关闭当前固定CPU窄核；旧原版30执行／29参考的私测及尚无sealed original-install-only正式consumer，仍不能代替旧原版正式reward。

## 7. R5公开actor在R20的适用范围

复用既有actor runtime与R5→R14报告，本轮实际读R5 input及三prepared对象，再比R20新prepared：public对象逐项相等，public_bundle_digest同 `1f95551f8b887dc01d5a2c2fba8aef01a449c701e1577dec4905181f14abafd9`；solver prompt字符串UTF-8字节相等（807B，SHA `46ec1915682bd11fc7859e70076f010adb0a27922fc3780bf79c26a223f468a7`）。只environment_package_digest由R5的 `36147168516f265f8660a3899c68b5ea99bbffc6f681cf1f03741530dc47ca74`变为当前 `62df73d0a7bf30057b6b4e585cc799a09c853c320310e32f93f9f7b6aaaf437e`，对应prompt.metadata也变；整份rollout/prompt JSON绝不相同。

R5公开prompt文件SHA `0ab244930d0c028a9336a2d032f848cd78cf530857d64f3fe6f6f99f79ef5e43`、view文件SHA `7c616d96f1c70e07ca6cd7949c5b6e4114e562632685c0b75c88b19dcfe2708b`；R5实际input SHA `da833fcf54eb27c870f797fae067d61b1541ae8c6b62e36fff4270f1d3151c41`；neutral brief SHA `7323939989fe68455a468c41cecb83884eb2c9dd863cc8a98b6873c4810a8456`，public commands SHA `49c50eedd24522d54343e8c39b841745ba211755506c005ca6b2ea48551e3508`，未因私有grading修改。原public问题/CRLF、工具/工作目录/base commit/公开image manifest均相同；原actor实际派生c093与当前CPU actual spec匹配。

当前release与R5的下列执行字节相同，不只凭发布声明：

| actor相关文件 | R5=R20 SHA256 |
| --- | --- |
| scripts/replay_grade.py | `d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3` |
| devcheck.py | `75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160` |
| acceptance_startup_2.py | `c67194f09e202c1cd1e83a3a1fbf5df7706952d2e542f97a4b2f3882604dc5d1` |
| stub_anthropic_endpoint.py | `dab06b7a5ed681e9938c6033f41e3bd6947cdc19c0e333e7fc5a859d805f5138` |
| sandbox_profile.py | `313bfd7691c5dca775aa0e9992f13561e20936f062ddfa3d269892b6bf4895ee` |
| bringup.py | `019cbd01c06c20f5109160e555e78e7e1015ffb2614b16f6c74ab7b6c266fe3f` |
| envpack/bundles.py | `f107d1a09979cc52890a1d5dbfb7697c6744179157041aa2bb6d1d0530d7c988` |

prepared_task_face.py整文件变为SHA `190616105945f649c102aa15d7b86a810a63f77c6723b297e062378ada1f24cc`；AST核actor侧 PreparedTaskFace.load/verify_dispatch/rollout_spec、rollout_spec_from_view均相同，变动在私有grading构造。adapters/replay_grade.py SHA `22836b6ac9d57dde0717880a77af829e620a8674bb9cf8fb400e808e49f87ef5`，prepare_for_replay与加载准备路径AST不变，replay_one私有评分变化按旧R20报告复用。因此继承的公开actor入口/profile/CC命令路径无此次新增变动；并非整个release源码完全相同。

可复用的是**历史R5真实CC2.1.205、controlled stub四公开命令rc0、UID54321、testbed源码与基线公开tests 17 passed、权限/profile和清理事实**，适用于已核相同public/code/image范围。首请求为原issue+中性brief，未混新私有测试；不是新R20 actor执行或真实模型质量。仍保留旧限制：pytest-q未给完整verbose节点列表、helper计数null但raw17passed；source pin／guard未另存完整stdout，未封存容器全部baseline字节；8GiB writable quota仅配置；不证明训练typed actor集成。这一复用也不能替未来GPU不同image免除实际镜像绑定。

## 8. 当前GPU准备helpers和交接边界

仅离线读源码；题主在本核期间已执行staging builder，已产生 `gpu_source_binding9395_r20_v1.json`（SHA `95b6c150f719503108aa9f8725836ad00d45f8386856359ba658e226abf8c13b`），本人重核21个文件refs SHA（含7wheel字节）；状态仍 `staging_bindings_only_not_a_probe_request`，gpu_actual_image_id=null，CPU c093只是历史证据。没有GPU deployment／probe request提交。finalizer和board submit仍未执行，其静态窄核未见新增阻断。

| 当前helper | 实读SHA256 |
| --- | --- |
| build_r20_gpu_bindings_v1.py | `8a91ee3138e1e742f11237fd9aaeb8d7682c40e58be25a5394a0a0588a79fa39` |
| finalize_r20_probe_v1.py（已新增checkpoint回执要求） | `1241364352b1fbe7eb24fd87074dab622fe0be6410dfa33a454ea2f9216d522a` |
| submit_r20_probe_board_v1.py | `e1ee017b311a0c3f484e420b149ff53e916a29adc7e4d686123cdd42fa2d488e` |

当前helpers CLI限9395；finalizer要求题主完整读报告且no_open_blocking、固定三份review SHA，再绑定six matrix与历史actor、newprepared相等事实；staging不自行授予资格。board submit路径保留revision检查和active_request空前提，本人未执行或发消息到其它Codex聊天。

若实际GPU image ID不同c093，现CPU closed policy不会自动接受：必须由共享发布给出精确new image/policy/consumer配对并受影响窄验，实际spec/ledger继续900，不能冒填CPU ID、加自由timeout或悄悄退回300。GPU要newprepare，solver不挂私有grading/控制/题主材料/release parent；新模型回执还须实际checkpoint目录版本、原权重manifest+SHA、服务启动参数/live service绑定，不能仅信请求模型名或结果model字段。这里是已读的交接要求，尚未证实GPU消费或执行。

## 9. 关键原件定位与保留SHA

各候选根的 `formal/jobs/<上文job>/` 内，eval_logs/*.eval.log为完整执行／失败证据，*.diagnostics.json为预检/保护/segment，ledger.jsonl为正式报告与政策，artifacts/...为baseline/FrozenPatch/projection，process.log/completion.json/slots/.../status.json为退出，cleanup_readback.json为外层回收。本表列最少原件身份；全部其余路径／size／SHA在第1节已核manifest。

- **noop**：receipt `10045d002dcfe6a5610895d2629f3dcd9d79a8a4826a4ce1412abbac9e938827`；完整eval.log `201e797cb59d91ac85bbb3715c376f3515e957e9d35b0d7dd63553acf46902c5`；diagnostics `e011170f35491a224e06bee8437e8ae115d3e574d56de0d8461af745d75bdff7`；ledger `365e8be833643175939bad592eff3b58a57dd5f52e6c10b75100330dc4215029`；completion `e1b18c7284beed7027bead9b6ef3459704267776ee008c2141e809c2596216cf`；cleanup_readback `09ab6060e8ff248814388a48e1d31522748adf522e494354d253f5d78288661a`。
- **gold**：receipt `9992d917dca23ecd0f83642c671a3877ea9eefe13f6067544698d0dbf6eb5e46`；完整eval.log `2507d64fb35a1ca95fac9b036f54cf0f00970adf89e675708d652cea9feec0c0`；diagnostics `66cccda82e823295ec299569b69b18142361f70c0582ef2e81f252fd2d23b199`；ledger `1261daaf7d83ad45988b579a19e34f0f91960022a2d4377cb937921c3e4e061c`；completion `0dceebba9004799143f2fceb12f44c19aeac7c1083cf74cba3a74b549b273573`；cleanup_readback `6e848d2a0ddba44f3da07fe8a5272acb6a00970e380fa69996e2d5c2da056937`。
- **c3_frozenfix**：receipt `7ed91c4b065b927611e686cc9c472880563501eec0b720dd5d093b72045c22ff`；完整eval.log `ad39655e9f099a334256954d0e968ed637c691da4284283db91ac14b0d95d9ee`；diagnostics `2ef925de29e3128c28e987fffdbfa50628f452705d4a8a11ba511f865a8f99a4`；ledger `0a1c25464b6ca027daa6983e4cd4d7eb14e3462e538b304404cd430127ad4a31`；completion `828f1a710698ce041fafbb4bd1fd04f697ab20b41bd7bbbe5d0b8eb236ad28cd`；cleanup_readback `a266197e36f998bb9db6928adc9509fc97ecd8cebb5c5b8de51c0700a0d722f7`。
- **c3_missing_only**：receipt `a695c5cf34836fbda9e30088844a4dd6aee11d7cbd1cf05c42aaf34733563e5a`；完整eval.log `e82f65d3fe0e6260ed2d37392d290167808dfdabc9b076b42627a78efffa99e8`；diagnostics `516fe8ffa756c4530680ba73e4c4c5eeaaaa43840750eaede724f84ffdd9979c`；ledger `ce1fa1f2deb5c3216ba241227a94fa6848ff5b6252a2cb72afe432ea8c8f5351`；completion `3f34b134ae917c5e908231dd57dd8d8a4e36ce593107f1016eaf6fd6cf2e8d6e`；cleanup_readback `7ab239ed704bae817c4e447bcd418d1ba8a61985293a188031dabb517a8b3a7d`。
- **up351_port**：receipt `861ddb09f70eac763f2e26545b9e59675f57164207d688183d8409e21f7b8540`；完整eval.log `f4434f658a56fcc0dcccdfdb888fe60356e6e0c7adc37c2d841d826718b39a7b`；diagnostics `9371d5ae55e5ea7f5eca2d62591d8ef792ea3c5c57d6025f913f8e46d6ce12d4`；ledger `ecd2f720b9fdfb4cbe8d145770e797b8cba2c7bcdada7cee56d3dfaf6540ebeb`；completion `3c2d5310d77d695e95d497897b08014d461dab7f50c97f1a848336ed2538c64e`；cleanup_readback `a44fd50b91cd2e73a659abec3a0d588b49d69c74e19fac24f208ef53227675f0`。
- **w_swallow3**：receipt `86dd20b94631e55b0c14cdb7c17b28a4fe93374d36bae1cb4342811053ba1c4b`；完整eval.log `6f8800a3bf9ad5c153f0e14eee7a2c334537c1ede5e48ae5fc30f35a8ef66207`；diagnostics `13517f5eddb72436863e1588bfd4f4cbf8311ff53254f0bbd89a5217ca645b9d`；ledger `a3cd99c779868645c3c663ab1da5cd533c10ee227730b5de134bddc2b2389511`；completion `ecbaf278b971a11a65d934e719513a473a525df76e2f511e732f44b1789e964b`；cleanup_readback `90211412db6f644e3d9d60719bf3e7edc4405e05492a65a3153b70e0e513dc5b`。

复用报告：`non_author_dvc9395_r20_budget_support_review_20261003.md` SHA `88c26bddb9becd4ced787eb77b6b094acd59e3ae57d7b050728fe649bb27320b`；`non_author_public_actor_r14_reuse_review_20261003.md` SHA `24276eef103c12df70f261a9b05a56c33a251a98a480300555582a3b561f9c97`；`non_author_actor4166_9395_runtime_review_20261003.md` SHA `c914c520234eaee7da6fd9d3c20d9a84c8bd67aa509236d0c00c752ceab55632`；两次R14失败审查SHA分别 `174d5908963aec91039cbc7d708f4a168c8bd630a5bbc6411d883ac46df2b351`、`a07cfbf374473dbf1dedfd4b94cb0d12a78e525a3faf87dc72a2b98ceb381776`。既有材料语义／原历史矩阵不重复审批；GPU模型／权重／最终普通探针闭环仍待真实原件。
