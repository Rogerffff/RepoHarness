# 第四组 P-B / P-C / P-D 独立反证审查（2026-09-16）

**结论：没有发现普通 file→dir 主路径的新 P0/P1；保留两项 P2 供主审裁决。** 默认测试 glob 移除、缓存窄政策、反向不要求支持、unsupported 沿旧 unsafe / 整组 DROP 都按已批准语义检查，不重开方向。未修改实现、维护测试或共享文档；本目录是本轮新证据。未运行 SSH、Docker、GPU、模型或 API。

核查入口：`impl_plan_20260915.md` §8/§9；代码指纹见 `source_state.json`。自建探针见 `test_pb_pc_pd_falsifier.py`，完整结果见 `probe_stdout.txt`。本目录测试断言**审查时的当前行为**，错误行为不是推荐验收结果。

## F1 / P2：冲突路径仍从错误文本反解，合法引号路径清理后再次丢失定位

- **当前行为 / 位置：** `rh2/src/repoharness2/adapters/slime/patch_exporter.py:279` 用只识别单引号的正则解析包含 `repr(path)` 的错误文本。`config'quote/default.json` → `config'quote` 是合法路径下的反向不支持形状，Python `repr()` 改用双引号，`object_path` 变成 None。`adapters/slime/generate.py:3339` 只把 reason / object_path / object_type 写入拒绝证据；异常 detail 没有进入 receipt。普通路径也只留下 child 和 `prefix_conflict`，没有祖先路径及双方操作。
- **违反的不变量：** §8.3 已要求清理后保留冲突路径、操作与原因，不能退回未知对象。当前把 reason 正确分为 unsupported，但并未完整兑现 durable 证据收口。
- **证据 / 可达性：** `test_pd_reverse_shape_receipt_and_drop_group` 调真实 `RolloutOrchestrator.generate`，复用正式链替身；确认容器已清理、未发起评分、receipt 已持久化、准入为 `DROP_GROUP`。正常路径 receipt 为 `object_path=config/default.json`；带单引号路径 receipt 为 `object_path=null`，Outcome 只剩 `object:?:prefix_conflict`，audit 为 `unsupported_delta_shape:?:prefix_conflict`。
- **影响 / 分期：** 不改变 reward 或整组 DROP 的正确性，但该次永久拒绝在清理后无法定位冲突。建议按既有证据余项在 P-D 收口前修，P2，不新增 gate 或平台。
- **最小修法：** 不再依赖 `repr()` 展示格式。让前缀冲突校验给出可识别的错误类型与结构化上下文，exporter 精确转换该错误；将 ancestor、child、各自 operation 与冲突原因写入既有 audit / Outcome evidence 或现有拒绝证据。排序、身份等其它 ValidationError 继续原样升级。
- **验收：** 普通名、单引号、双引号、含反斜杠的合法名，清理后仍能恢复两条冲突路径和操作；unsafe 仍 `present_complete` + `DROP_GROUP`；内部排序错仍 `fatal_run_halt`。

## F2 / P2：既有缓存目录变普通文件时，省略政策把已知反向形状藏成 add，最终误报 infra

- **当前行为 / 位置：** `adapters/slime/baseline_census.py:64` 省略基线 `.pytest_cache/old` 后，manifest 不含该目录下条目。候选把目录移除并写同名普通文件，`patch_exporter.py:77` 只导出 `add .pytest_cache`；artifact 不再有父子冲突，classifier 判 projectable，trusted split 也没有 unsupported reason。fresh grader 保留原来的 `.pytest_cache/`，`grading/manager.py:504` 实际执行时才报 `add_target_exists`。
- **违反的不变量：** P-C 要保留同名普通文件及类型边界，P-D / S1 要让已知不支持的候选 delta 走 typed unsafe，不能把候选造成的形状冲突伪装成评分基础设施损耗。此处不要求新支持 dir→file。
- **证据 / 可达性：** `test_pc_cache_named_regular_add_with_and_without_prior_cache_dir` 使用真实临时文件树、生产 census/export/classifier/projection 和真实 `SWEGradingManager.grade`。容器生命周期为 FakeDocker，**census 和冻结写入脚本由真实 bash 执行**；映射 `/testbed` 到临时树，没有放宽生产 spec。既有 cache 目录变同名普通文件：基线 omitted=1 dir / 1 file，export=add，projectable，最终 `failed_to_grade / infra_failure / reward=None`，detail=`delta_write_failed:add_target_exists:./.pytest_cache`。无旧目录的同名普通文件 add 对照可写入并 resolved。
- **影响 / 分期：** 这类候选的处理从已批准永久拒绝变成 infra 损耗，且 formal receipt 不会记录它是 unsupported。未发现实际 e1/e2 出现次数，不声称常见或远端已发生。建议 P-C/P-D 组合收口时修 P2；不是要求支持所有目录反向转换。
- **最小修法：** 在已有 omitted-directory 政策与类型变化检查之间补窄收口，识别“baseline 被省略的目录现在成为文件/软链”，沿既有 unsafe 通道；或使已批准忽略的 cache 目录在重放前有一致的规范化规则。不要把所有 add 冲突降为 unsafe，也不要扩大普通目录转换支持面。
- **验收：** `.pytest_cache/` 和 `__pycache__/` 的目录→普通文件/软链在 export/projection/apply 全链得到明确 typed 结果，不能落为普通 infra；原先不存在的同名普通文件、原先就是同名普通文件的修改仍保留；普通 file→dir 的内容完整落地。

## 已验证与主动降级

- 维护测试命令（在 `rh2/`）：`.venv/bin/python -m pytest -q tests/contracts/test_batch4_pd_pc.py tests/contracts/test_f2_2b_b2_exporter.py tests/adapters/test_replay_grade.py tests/adapters/test_w1b_prepared_task_face_v2.py tests/grading/test_w3b_grader_profile_unit.py`，**84 passed in 10.08s**。这不是全量测试，也不是远端验证。
- 独立 CPU 探针命令（仓库根）：`PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python -m pytest -q -s -p no:cacheprovider docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/implementation_review_20260916/falsifier/test_pb_pc_pd_falsifier.py`，最终复跑 **6 passed in 1.50s**。覆盖 F1/F2 的控制组、真实 file→dir 删除与子文件写入、完整 unsafe receipt / DROP_GROUP、内部排序错误 run-fatal。
- **P-B：** 两个 SWE spec 构造入口都撤默认 glob，保留 official 精确路径和 forbidden 规则；观测字段未写回 hygiene gate。现有安装期 conftest / stdout 篡改问题已在 §9.6 单独登记，不把已知且待决策的同族问题重报为新 P-B finding。
- **P-C：** 真实旧 e1 v1 fixture 的 policy 与完整 manifest digest 都通过既有测试；新增默认空字段不会进入旧身份。只对 `swe_gym_lite::` 选 v2；未知来源仍 v1。census 用 `-type d` 限定，普通文件/软链叶节点保留；不全树省略独立 pyc。不扩到“任意放在 cache 名称下的内容永远不影响评分”的保证。
- **P-D：** 独立探针以真实 bash 验证 `config` 普通文件删除、`config/default.json` 内容写入，manager 返回 resolved、hygiene replayed=True。逆向普通目录变文件与带引号变体都进 unsafe，并确实由准入判 DROP_GROUP。猴补 differ 输出乱序的探针抛 `rh2_contract_validation_failed`，receipt 为 `fatal_run_halt`，没有吞成缺员。
- **R5：** 现有 `test_pd_projection_excluded_ancestor_delete_is_recorded_not_graded` 在本次 84 项里执行并通过，真实 replay 入口记录 projection unsupported、未调用 grader、清理完成。未将空目录交付、通用反向转换或外部构造畸形 artifact 扩成当前能力要求。
- **非阻塞观测：** formal `generate.py` 的两次 census 没传 `omitted_sink`；grader sidecar 的 `omitted_cache_count` 实际是 fresh baseline 的计数，候选新增缓存数不随 formal 导出持久化。replay driver 会分别记 baseline/post。`test_batch4_docker.py:127` 明确断言候选新增两类缓存后 sidecar 仍为 0。这是观测口径不一致，建议接通现有 sink 或把字段标明 `grader_baseline`；不影响当前评分结论，不列第三项阻塞。

审查维度上，F1 属 M/E，F2 属 A/B/G/M；没有需要新增审查维度的发现。并发、GPU 性能、资源超时与 P-A 归因不在本子审范围，由主审及其它有界子审承接。
