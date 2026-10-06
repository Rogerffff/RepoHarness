# Moto6114 Neptune P2P v2 固定发布输入：非作者增量静态提交核

2026-10-03。结论：**未发现这份固定发布输入需要提交前修复的静态阻断。** 全部直接 source／candidate 引用 pin 与实物吻合，嵌入 request／matrix 与对应文件一致；新材料保留原公开题面／base／1F34P／R7 ARN/name 断言，只追加已批准的两条名称保持 P2P。四臂预期 0／1／0／0 全部仍是计划，不是新版实际得分。

本次仅标准库文件／JSON／SHA256／内存文本 patch 应用／AST 核对，没有执行项目、SDK、测试、Docker、CPU、远端或模型。只新增本报告，不修改固定发布输入、配套材料或先前报告。我已接触 gold、私有参考、构造负对照和实际模型源码，不是公开盲读 solver。不重复已完成的测试语义、工具设计或两容器运行原件审查；本次检验它们是否以正确固定身份封装进新请求。

新输入当前尚未提交。按题主本轮提供的实际状态，旧 probe 的安全终局及 ACK 尚未到达；本报告没有核发该终局／ACK，不能把静态可提交写成既有流程已完成或发布可以立即生效。两条 P2P 范围已批准，不要求重新审批。

## 固定输入与完整 pin 核对

本题工作包根为 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_moto/`。

| 实读输入 | 字节 | SHA256 |
| --- | ---: | --- |
| `publication_requests/swe-moto6114-neptune-p2p-publish-20261003-v2/input.json` | 32264 | `404cfda907c38498757657291f9f21e0c144b542a94845b31e66314aa22a3229` |
| `neptune_name_preservation_v2/revision_request.json` | 13651 | `0d0d522b0f00fcb0de1c6c3c5b19f9743ea479bcbf782fc48be75a71208fd157` |
| `neptune_name_preservation_v2/acceptance_matrix.json` | 3405 | `ff974f92f482f1053d9e98f07ff4a825c8a120e032bcb8641d9a65d74fe68b20` |
| `neptune_name_preservation_v2/exact_qwen_a1_source.patch` | 6463 | `bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747` |

后三件位于 `tasks/getmoto__moto-6114/` 下。实读字节均与题主固定输入一致。`source_and_candidate_refs` 的 **21 个直接引用** 逐一核对路径、SHA256、字节数，全部匹配；再递归核嵌套的 path／SHA／bytes pin，覆盖 **22 个唯一实物**，额外包括旧 R7 有效 patch。没有缺失或不匹配 pin。

上述引用覆盖新 req／matrix、原 proposal／brief／effective patch、实际 Qwen diff、作者诊断读回、四份既有非作者报告、题级决定、原 grading／public／base identity／base test／source refs／original test patch、gold／wrong_first 对照以及 CPU 供应 receipt。嵌入 `revision_request`／`acceptance_matrix` 与对应实物 JSON 完全相同；这些实物本身又受到原始 SHA／bytes pin 约束，没有另附一套不同参考或控制计划。

原 proposal／brief／effective patch 及先前报告 SHA 保持：proposal `8eeba063ece96a69992f73fb12d1ee386c6ff41f8f275432ec02a93c336edf31`、brief `00c07d1bf57535fb9470091684b655e90bf2cbaa49258e93fd2a577fc467ec3f`、有效 patch `2a9661d78743cf5e36f8363e308d63260ab2076bf4bc1d68de8a9e5fd226dda4`。材料非作者报告仍为 `58a9bf4a8130ba4103e4d19712f80349e588b662005e3523d1420c44172e088c`，两容器结果非作者报告仍为 `3702de4ad65adc0bec7b2d132b0c3c80dc8425e80682087084a38c72b872b946`；本次沿用固定结论，没有回写历史。

## 原公开材料、参考和命令保持

request 的原公开 JSON／base identity 与原 R7 消费记录绑定同一 base `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`，public digest `sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2`。原 public 文件为 2755B／`f2f5829daa1c062f3839f1eea23876c7fba0e117fddc6c7d8dda268dac7e4928`；有效 test patch 只改私有测试文件，没有新增公开题面或功能要求，request／input 均 `public_change=false`、solver_visibility private_only。

原 grading 为 4225B／`b26dccd671637cac4cf79dd15f6e1e0973b8cccb6157142b1b2e15220e025066`。它的 1 个 original F2P、34 个 original P2P 与 request、原 proposal 和 R7 固定分区逐项及顺序一致。新 `proposed_fail_to_pass` 完全等于原 F2P；`proposed_pass_to_pass` 完全等于原34P后附：

- `tests/test_rds/test_rds_clusters.py::test_rds_facade_preserves_neptune_name_start`
- `tests/test_rds/test_rds_clusters.py::test_rds_facade_preserves_neptune_name_delete`

added_fail_to_pass 为空，added_pass_to_pass 恰为这两项，合并后37个唯一引用。matrix 1F／36P与request一致。新有效 patch 字节未变，因此既有材料报告已证明的“严格应用原 base、旧35函数源码及AST完整保留、ARN／name精确对象身份断言不变、只新增2函数”适用于此次封装，无需重新全审断言。交付要求明确完整有效 patch 直接应用原 base，不能在已应用旧 patch 的测试文件上二次叠加。

原 grading 的字面 `eval_cmd` 是 `pytest -n0 -rA`。request 的 source／proposed test command 都是 **R7 消费者派生后的完整命令** `pytest -n0 -rA tests/test_rds/test_rds_clusters.py`，与已有 R7 `expected_runtime.json` 和实际旧执行一致；不是改写了原命令规则。原 `make init` 保留，新四臂计划要求完整安装／测试／逐参考状态和两层清理，不能以简化定向调用替代正式37项。

## 实际 Qwen 源码身份和四臂计划

`exact_qwen_a1_source.patch` 与 `gpu1003-moto6114-qwen36-a1/attempt/candidate/getmoto__moto-6114.diff` 原件逐字一致，唯一 diff 目标为 `moto/rds/models.py`。标准库在内存中按原行号、上下文及旧／新行数严格应用其 **5 个 hunk** 到原公开 RDS base，没有 fuzz、offset 回退或工作区写入；结果 AST 可解析，**161961B／`05e9b6a1d3f57caaeba1a616fa3a1a9529ffa6f6aa6d91be9a5963a239b5171d`**。

结果逐字等于原 FrozenPatch 唯一源码 entry 的完整 base64 解码。entry 是 regular／100644、modify `moto/rds/models.py`。原 FrozenPatch 文件仍为 216817B／`6acc1b2d3de238b08780adfb493883abe617aa1c0e1983fdbda9a0bd2fc8405c`，原 runtime 仍为 GPU `sha256:43f685f4308354a90d8d88d3a2fd31dcc01bdd41fff3f04210d2668281716e20`；没有把该 FP 静默绑定到本次 CPU image 或未来新材料。

四个控制臂的数量、补丁、角色和预期一致：

| 新材料下计划控制臂 | 固定补丁身份 | 预期奖励 |
| --- | --- | ---: |
| noop | null | 0 |
| gold | 635B／`bfae681e1044acffe64d7d65c1615b5545f4b62b2625961b7a6fe7d0ad591bbc` | 1 |
| degenerate_first_object | 492B／`5c042121e4bf56693c71f418c139b628d108b0c1fcd67bc0af48201e471c6451` | 0 |
| qwen_a1_exact_source | 6463B／上述原 GPU diff | 0 |

matrix `formal_run_count=4`、status planned_not_run、actual_rewards=null、formal_cpu_accepted=false、probe_submission not_submitted。历史 wrong_first 原材料奖励1、Qwen旧R7 GPU raw1是带来源的旧观察；新37参考下“原35通过／新增2失败”和0／1／0／0均仍为预期。已核两容器行为报告提供最小代码对照依据，不等于这四臂已正式评分。实际 Qwen 臂明确生成新材料下的新本地诊断候选；不能用原 GPU FP 身份直接冒充它，也不能把 `role=actual_model_regression_negative` 当新的自主模型或训练 actor。

## R7 环境、source 与 CPU 供应收据

parent R7 manifest 实读 `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`、905个成员，与 request 一致；相应 producer SHA `9bf50d0a4e14ace49eac459c50ad630d9e228365d606e0dcfc9d9f529b88615e`、registry SHA `27e1b01dfec9aa2284e79fec753f70b62f6bd45462346483484f98785a59ae22` 和旧有效 patch 1336B／`fe211059864c661a557758f5c5ed4106016c767cbe98eaef4718733008a87d5f` 均匹配。旧材料身份没有被新版名称覆盖。

供应字段保留本题 source manifest `sha256:cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a`、source ConfigID `sha256:fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249`，CPU COPY-only actual `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`。receipt为1439B／`497c0736359dd7964b6db8abaaa26fd4716f366868001ab298459b6da4c8cf47`；input 嵌入的 contents 与真实 receipt 完全一致。它是 image_preparation_only 收据，不能单独当正式CPU准入。

本次仅将其与已独立验过的两容器 `image_inspect.json` 身份对接：source／actual ID一致，source13层是CPU14层去掉末层后的逐字前缀。receipt 的旧 Dockerfile／wheel manifest及三件历史 wheel pin保持；三件本地 wheel SHA／长度也重算匹配。已固定 R7 CPU供应的真实性不依赖旧GPU镜像的条件。本次不要求新环境配方，`environment_change_requested=false`；未来 GPU若需自己的新供应actual ID须另记，不能复用CPU的actual ID或静默改旧GPU FP。

setup300／apply120／test1800／candidate stage900／whole grading1800／cleanup120秒、2CPU／4GiB／PID512／shm64MiB与原R7计划及记录一致。新材料消费下仍要求补核实际 UID54321、激活、模块来源、环境及恢复保护；旧环境通过不代表新消费者的37引用已正确生成或已运行。

## 已批准范围、未来 consumer 与剩余状态

scope decision为2330B／`db149b0657615ae9562d5723387607387ef6d42eaabbce04f4121722df3ab716`，固定批准仅这两项既有名称P2P，保留题面／base／原1F34P／ARN identity／预算。input 请求 `requested_operation=replace_test_patch_append_p2p`，request同名；`requested_consumer=replace_test_patch_and_append_p2p` 是发布请求的能力描述，不能当作已存在、已受测试或已部署的消费者证明。

request明确 formal_revision_registered=false／formal_revision_activated=false，input formal_revised_cpu_accepted=false、old_gpu_raw_reward_override=null。发布者后续负责只限本题两个固定名称的 consumer／registry／producer实施与窄核，生成新的grading／context／registry／material／prepared身份，部署后实际默认prepare读回37引用、脚本、公开face和预算。当前输入不能证明该受限实现已经完成，也没有申请任意执行入口或全局评分／训练规则改变。

有一项**非阻断的陈旧检查清单文字**：request `release_remaining` 仍列“独立核两容器行为原件”，`cpu_validation` 也保留此前作者读回措辞。但本封装的 `independent_material_evidence` 已固定完整非作者运行结果报告，SHA／字节吻合。因此该项实际已完成，以固定结果报告为准，不重复列作运行证据缺项；它仍没有把37参考CPU验收写成已完成。本次保留固定输入，不为此要求重新生成已批准草案。

旧请求 `swe-moto6114-identity-r7-20261003-v1` 的安全收尾／终结与ACK是现有流程的待完成状态，input明确 `gpu_request_to_close_before_normal_publication`。本次没有替它出具终局，也没有提交新input。此限制来自当前既定状态，不是本报告新增的审批。两容器行为、公开原face复用边界和旧UID事实均只能支持各自范围；新材料发布、实际消费者补核、四臂37参考评分与独立验收完成之前，不能宣称CPU准入、typed actor或训练资格，也不能派新模型冒充已验材料。
