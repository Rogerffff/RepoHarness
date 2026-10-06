# DataLad088：Coder 首臂独立关键原件核查

整理日期：2026-10-03。题目为 `r2e_gym_subset::datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb`，本臂作业为 `gpu1003-datalad088-coder-a1`。

**结论：本臂诊断回执和决定性评分证据通过独立核查，候选 raw 0 可信。** 完整 eval 为 15 PASSED、2 FAILED、1 XFAIL；17 个 expected key 匹配 16 个，唯一偏差为 `test_url_samples`。固定 `~` 失败符合 expected；候选在转义冒号本地路径上留下空 scheme，造成真实回归。本次未发现新的题级材料缺陷。此结论仅验收本臂诊断证据，不是候选通过、完整训练／留出准入或题主总账 ack。

审查者不是本修订或模型作业作者，已接触私有材料，不是 fresh 公开盲审。只读固定原件，不 SSH、不运行模型／CPU／候选，不改原件或共享文件。复用执行者对 492 原件的全链检查，本次独立核决定性源码／FP／diff、actual hidden 与 runner 绑定、完整 17 键、首真实请求、终点和清理；不重复遍历全部成员、机器／权重证明或完整七维轨迹分析。后者及两模型首轮汇总、总账确认由题主负责。旧 CPU／Qwen 单臂报告保持原样。

原件固定 root：`runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-datalad088-coder-a1/`；本臂结果位于其 `queue_v29/results/gpu1003-datalad088-coder-a1/`。492-member manifest SHA 为 `1d1abbfae6509be88de2db2eb8783b46da6f3e9bd5ee6a6c8e5e97e5a7ca9740`。所独立核查的关键文件均重算 SHA 并与 manifest 条目一致。执行回执实际上位于全局 `runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-datalad088-coder-a1_execution_receipt_v1.json`，SHA `17f49918008a51b311b46cdfd9a60e844a22e4771a551fbdae6052cbeb9cd3d3`，不在上述 root 的 migration 子目录。独占审查脚本／读回为 `runs/category2_repair_20260929/r2e_datalad_088_independent_review/gpu_coder_review/{key_original_audit.py,key_original_readback.json}`。

## 真实回归与动态范围

原 diff 只在 `datalad/support/network.py` 增加八行：若仍无 scheme／hostname、path 含冒号且不是绝对路径，则先 `_split_colon(fields['path'], 1)`，仅当返回两段时设置 SSH 的 hostname、path 和 scheme。原始 baseline 没有这个 `elif`，该输入原会走后面的默认 `file:implicit` 分支。

实际 hidden `test_url_samples` 先通过题面例 `weired_url:/` 及前面的 SSH 字段检查，然后在保留的 `example.com/path/sp1\:fname` 失败。该冒号已转义，`_split_colon()` 的 `(?<!\\):` 不拆它，只返回一段。新 `elif` 却已接管控制流：内层 `if len(parts) == 2` 不成立，又不会继续走外层 `else`，因而 scheme 保持 `''`。随后 `_check_url()` 的直接字段比较实际报 `AssertionError: '' != 'file:implicit'`。原 diff、冻结源码和完整调用栈一致，足以证明候选回归；**这不是 Qwen3.6 的误判 SSH 后字符串重建断言机制**。

该转义路径是原材料／065 的保留项，不是 088 的两项新增断言。材料增量与此前 CPU 证据见 [既有独立核查](../followup_k7_k8/independent_review_20261003.md)。本臂实际覆盖如下：

| 用例／依据 | 实际结果 | 结论范围 |
| --- | --- | --- |
| 转义冒号本地路径，`test_url_samples` | 字段比较实际失败，scheme 为空 | 唯一 expected 偏差，支持 raw 0 |
| 088 query 增量，`test_parse_url_opts` | 整个函数 PASSED，新增断言在直接执行路径 | 此增量实际通过 |
| 较后的 slash 前缀 round trip | 同函数此前已失败，未执行到 | 没有本臂动态结果 |
| 088 `/some/dir:x` 绝对路径增量 | 同函数此前已失败，未执行到 | 不能称动态通过；新增代码静态上排除了以 `/` 开头的 path |
| `test_get_local_file_url_linux` | `file:///a~ != file:///a%7E`，FAILED | 与 expected FAILED 一致，非新增回归 |
| yield `test_get_url_straight_filename` | XFAIL | 不计入 17 expected key |

## 冻结身份、控制材料与评分

独立重算 FrozenPatch canonical digest 为 `sha256:193740cbeae51bd151c15a67aceecde3dca738b6a75fd29bf932c4f3aae579ac`，baseline canonical digest 为 `sha256:ee60bf13a0d71b4360c7c566c2f27121013a72f00f2bbd4eadfe4e8d03c81d4a`，均与原 FP／projection／status／result 一致。baseline 246 项，本次从实际 `baseline.tar` 读 source 旧字节，匹配 manifest 与已核公开输入；995 字节原 diff 的 hunk 能逐字重建唯一 FP 内容，其 payload SHA 为 `bd27a2623a36260ae39f99a60a25697ca2494116363cc8c5c5b5a0b400bb57cc`。实际 image `sha256:c5d390400a668256e8946daeefe9758a9064f64d518418727cdb013a907ec346`、head `2753d4722fbf88015c59135f246b2cac82389612` 与本臂 attempt／baseline 绑定。

本臂 FP 与 projection 只有 `datalad/support/network.py`；没有取消公开测试注释或改变公开 `datalad/tests/test_network.py`。其 baseline 字节与已核公开原件相同。可信 setup 的三项仍为 `r2e_tests/{__init__.py,conftest.py,test_1.py}`，另恢复 runner；actual eval 自证 hidden tree `2a62382c…`、runner `8285765f…`。闭合快照 host grading 中的 `r2e-mr-088`、三份 hidden 文件 SHA、expected map 与已独立验过的本题字节一致；本臂没有再携带旧 build context 的完整 hidden payload，不冒充此次重新读取了它。完整日志所示失败输入／helper 行号与已验材料一致，setup 成功、四项 official 文件齐全、Install SKIPPED、Start／End 成对、pytest 到 100%、test RC 1。

完整原 eval log 为 8404 字节，SHA `sha256:0bb28e54d225e839cb320537720fbf54abcc7564c2b4e500c8e3cac546a493ec`。独立解析 17 个不重复 key，与 expected 集合完全一致，仅 `test_url_samples` 不匹配，故二值 raw 0。原 report／status／result 及执行回执同值；`infra_failure_detail`、`execution_failure_stage` 均空，不将公开 pytest 的一次非零退出误判成正式运输／评分失败。

`excluded_pathset_changed=true` 和 classification 的 `runtime_private_pathset_changed=true` **如实保留**；实际 classification 为 `projectable`、`reason_codes=[]`。冻结 `FrozenPatchArtifactV1` 明确该字段只哈希排除区路径名集合，不含内容／mode／target，不能单凭它判定 tamper；判定另需权限／命令／ownership 证据。该旗标不是“不变”，本窄核也未取得独立的 post 排除路径清单来归因具体变化，不能将其静默写成无变化或已证明无篡改。原件仍支持当前诊断评分和控制材料恢复，未见由此产生的题级材料阻断；formal 准入不由本报告授予。

## 交付、正常结束、清理与用途

首真实 HTTP 请求位于 root 的 `services_v27/coder/gateway/<job>/requests.jsonl`：路由与 body 为 `Qwen3-Coder-30B-A3B-Instruct`，真实 `max_tokens=65536`；user 第二块逐字等于原题面加批准 brief，第一块为 currentDate reminder。原题面 SHA `a0f4c92e…`、brief SHA `68688ecf…`、实际交付 SHA `2ba74c21…` 与两份 prompt／`attempt.public_delivery` 一致。本报告只直接核路由身份，复用执行者已有运行身份证明，不把接口名称当作独立权重驻留证明，也不把 CC 元数据 `maxOutputTokens=32000` 当成 HTTP 参数。

16 个原 HTTP response 均 status 200、无 stream error；末 `resp_16.sse` 有 `end_turn` 与 `message_stop`。完整 trajectory 205 记录，末 result success、`is_error=false`、`terminal_reason=completed`，harness RC 0、stderr 空、日志完整，solve 35.238 秒，没有预算截断证据。模型结尾称既有测试除 `~` 外均通过，只描述它看到的公开测试结果，不能替代本臂 hidden 评分或证明没有回归。原 session_close 为 revoked／drained、active=0；solver residual=0、删除 RC 0、无剩余标记资源；grader manager_close 为 created／removed 1／1、open／supply／cleanup_failures 空、regrade 0，清理闭合。

**用途保留为 `versioned_baseline_diagnostic_only`，`training_or_holdout=false`。** 本臂 baseline 的 `environment_package_digest` 仍为 `null`，冻结 contract 所述 formal 环境血缘阻断未闭合；prepared 另有 `677b5a1a…` 不能伪填进 baseline。全局 pair execution receipt SHA `2b7911d2ebc949c85a51bb7be16d95ec26c87b90d8e0b4c3512385019eea9e1b` 记录两模型执行已结束，但本报告只核 Coder 首臂，不代题主完成双模型分析、总账 ack 或后续采样决定，不扩展到同仓另外四题。
