# 6183 Coder 单 job：执行归因复核

日期：2026-10-03。角色：非作者 Production Tracer，依据 [review-standards §10.4 / §10.5](../../../../../review-standards.md)。范围只限 `gpu1003-aiohttp6183-coder-a1` 的实际调用、候选捕获、评分运输与生命周期。这是已见私有材料、模型轨迹和作者结果后的有界离线结果复核，不是 fresh 公开盲审，也不是 aggregate、其它 job、模型表现或训练资格审查。未运行 SSH、Docker、模型、pytest、矩阵或安装；仅用标准库解析已有原件。

## 结论

**当前决定性证据支持“模型实际工具操作回退了环境兼容修改”，没有发现这四处 `asyncio.async` 是捕获或运输改写的证据。** actor 启动时四个文件已使用 `asyncio.create_task`，但 Git HEAD 保留 `asyncio.async`。模型查看 Git diff 后执行了四文件 `git checkout --`；同一调用同时存在于 gateway 原始 SSE 和 Claude Code 轨迹，执行结果成功。冻结候选相对实际 actor baseline 保存了这四处回退。grader 重建了同源 baseline，再应用该 Frozen；完整评分日志与 actor 回退后的自身验证均在 `aiohttp/client.py:171` 报相同 SyntaxError。

这个判断是离线因果归因。**原报告仍是 `failed_to_grade` / `test_log_parse_failed`，reward 与 expected 计数均为 null**，`infra_failure_detail=reference_all_missing:unattributed:qualification:absent`。本复核不将其补成 0，不填资格或材料账本字段，不要求模型重跑，也不据此判断未执行的 49 个测试会通过或失败。

## 实际操作与关键字节

完整 [harness trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/attempt/harness/trajectory.jsonl) 共 503 行、549756 字节，SHA256 `af175c6facb7c1236730f21dc6b88d5eebeb931cbe7d9989011c996b39ef1072`；与 [attempt trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/attempt/trajectory.jsonl) 完全同字节。末行 `type=result`、`subtype=success`、`is_error=false`、`terminal_reason=completed`；这是求解正常结束，不是测试通过。

| 证据位置 | 直接观察及含义 |
| --- | --- |
| [attempt.json 的 materialize_probe](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/attempt/attempt.json) | HEAD 为 `ff3dec422bd18b5e9078b5f29be1c9a6a1373f5a`；四个兼容文件在 solver 启动前已是 modified。 |
| trajectory 394 / 398 行 | `git diff` 成功输出：相对 Git HEAD，四文件的 `asyncio.async` 已改为 `asyncio.create_task`，并另有模型的 protocol 修复。实际 baseline 的四个文件原字节与此一致。 |
| trajectory 407 / 411 行 | `toolu_8f2a2f127c0e71cb` 的 Bash 命令为 `git checkout -- aiohttp/client.py aiohttp/client_reqrep.py aiohttp/server.py aiohttp/worker.py`；结果 `is_error=false`。 |
| [gateway resp_34.sse](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v14/coder/gateway/gpu1003-aiohttp6183-coder-a1/resp_34.sse) | 原始 SSE 重组出的同一 tool ID、工具名及 checkout 参数与轨迹精确一致；回退指令确实出自该次模型响应。 |
| trajectory 451 / 455 行 | checkout 后的 `git diff` 只显示 protocol 修改：四文件现在等于 Git HEAD，因此不再显示相对 HEAD 的差异。这不等于它们没有偏离真实 actor baseline。 |
| trajectory 468、481、494 行 | checkout 后 `reproduce_issue.py`、直接 import 验证、公开 pytest 验证均报 `client.py:171` 的 `asyncio.async` SyntaxError，工具结果均为错误。 |

四处 Frozen 相对 baseline 的精确变化是 `client.py:171`、`client_reqrep.py:447`、`server.py:147`、`worker.py:31` 的 `asyncio.create_task(` → `asyncio.async(`；每个文件除此替换外字节一致。模型另修改了 `protocol.py` 的压缩输出，并添加 8 个调试/验证脚本。没有证据显示模型直接用 Edit 将 `create_task` 字符串替换成 `async`；可见的实际操作是 checkout 恢复 Git HEAD。

模型最终正文把 Python 3.9 语法问题称为与修复无关，并声称全部验证通过；这与其 checkout 后三份实际工具结果不符。本报告使用工具结果和原件，不使用最终自述作为验收证据。

## baseline、Frozen 与 grader 运输

独立按 canonical JSON 重算 [baseline manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/attempt/frozen/baseline_manifest.json) digest 为 `096115266c81b72a6f28e517ccfdeb2e8903c44f7822031113bf2daedb1f5781`，与 actor、Frozen 和 grader status 绑定一致。按 [baseline.tar](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/attempt/frozen/baseline.tar) 原件逐条核了 124 个文件的内容 SHA 和 Git mode，并核两份 census 的全部 manifest 条目。actor [baseline census](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/attempt/frozen/baseline_census.txt) 与 [grader rebuild census](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/grading/baseline_rebuild_census.txt) 完整 83799 字节相同，SHA256 `a624870e536f5ca4e6294444e2481bf574cf7e2a33638baa5e56d61be536c876`。

独立重算 [Frozen](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/attempt/frozen/frozen_patch.json) canonical digest 为 `221f72cfdb29c248ef9b38d856dbd6f466c25f8b45ff3316270646ebc5441102`；13 个内容 payload 的 SHA 均一致。[projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/grading/projection.json) 精确包含这 13 条路径。将 [review diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/attempt/candidate/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2.diff) 的全部 hunk 在内存重放到该 baseline，得到的各文件均与原 Frozen payload 相同。实际 applied-entry-set digest 独立重算为 `7a693c230987611c25ec94e8d27363d44069b78269c48581cfd52246a3c76e5f`，与原 hygiene 报告一致。

固定 [code_v4 entry.py:224](../../../../../../../../runs/ordinary_gpu_probe_20261002/frozen_code_v4/rh2/experiments/ordinary_gpu_probe_20261002/entry.py#L224) 的 `source_from_original` 直接读取 actor 原 baseline / Frozen，核 attempt 与公开身份并建立 projection；`grade_original` 直接将它交给 manager，未消费 review diff、未另建替代候选。[grading/status.json](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/grading/status.json) 与 [result.json](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/result.json) 均记录 `source=original_frozen_patch`、`baseline_rebuild_passed=true`；三处 report 内容相等。这组证据足以将当前错误连接到实际 actor 候选和 grader 输入。

## 材料、镜像、profile 与 49 键

按本 job [input_check.json](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/input_check.json) 及 [固定 inputs manifest 的本题引用](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/config_v16/fixed_inputs_manifest.json)，独立核了本题 21 个固定引用的字节 SHA，以及实际 tasks / prepared summary / gateway config / adapter config / brief / overlay 的 SHA；没有读取其它 job 的结果。关键原件绑定如下。

| 对象 | SHA256 / 事实 |
| --- | --- |
| 固定普通探针 entry | `a1efff44dc2cbedfc81d93b2da8d84a92f6c9c88b15c2a10bf96db2026a4e82c`，与 attempt 和 input_check 一致。 |
| prepared manifest / 私有评分原件 | `65dd97b9a8e973690ec06555d4071a7fda8b57f55df9a695a8f5d083cd5aae41` / `29498864385387299840f0b0426dfeb8d5fa349417d205119328dd067942a1f3`。 |
| expected 原始 JSON | `3390e85fe2f0807791b3def432def784f6da255b28b8d9e63c9af052218ace3f`，独立解析为 49 个精确键，状态均为 PASSED。 |
| hidden tree / 测试入口 | `23b524a89a3137272d0d4bda1c4f1d9e3a3e9e0851f462c061d2fd988dac85af` / `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf`；private、overlay、derived facts 和已读完整评分日志的实际 setup 读回一致。 |
| 实际 derived image | `cfc4f547e3336c59f39841883b209ab0568cc719144aea87e4c7ee73aadc0d13`：overlay、actor actual image、prelaunch、baseline、Frozen 与 grader diagnostics 一致。 |
| recipe | `r2e_derive_v1+material_v2+sysconfig_v1`，digest `70ceace9f6ab1e015cd3fa26ea20bb9180125711597c569acff70e30adf68c7a`。 |
| delivered prompt | `4b1d409d4382de29d50f548240be82806e9a75828043ee19fdb783c37950396d`；actor 两份 prompt 同字节，gateway 第一份实际请求包含完整原 prompt，brief SHA 为 `f1636164b5669015333ba0281f73dc696c8ac803c0b914246fb1a083b01b233e`。 |

共同机制只按相同 SHA 复用 [先前 R6 聚焦复核](non_author_1c1_240d_r6_execution_trace_20261003.md)：shared solve entry `10a71cca…`、base solve entry `00ca8499…`、grading manager `b6b10f98…`、baseline / Frozen 契约和 parser 与本次 fixed code 逐字节相同。普通探针 entry / spec_overrides 单独核当前固定 SHA 与调用点，未把先前共同机制结论扩成本单 job 的实测结论。

actor 的 [prelaunch 原件](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/attempt/facts/prelaunch.json) 记录 UID 54321、2 CPU、4 GiB、swap 0、PIDs 512、无 bind mounts、isolated network、禁止直连及 root 隐藏检查通过；profile canonical digest 重算匹配 `4a6435bc16d26c517b34eb1a4e40e83cdeef3ef08e813a136e9ae06ed67e22b6`。actor interpreter 实测为 `/testbed/.venv/bin/python`、Python 3.9.21。固定 entry 将同一 profile 传入 grader manager；本单 job 不包含可独立覆盖 grader 全部 Docker inspect 参数的完整原件，因此这一项完整运行参数读回仍 unknown。grader diagnostics 的实际 image、资源事实、保护面与 runner 前后 digest 有记录；runner digest 前后均为 `067c6080788af8288ff8c5d9cf94560b3bf62d24f37833995ec57b7ba74633e9`，`runner_integrity_changed=false`。

完整 [eval.log](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v16/results/gpu1003-aiohttp6183-coder-a1/grading/eval_logs/evallog_gpu1003-aiohttp6183-code_bbb71c81.eval.log) 为 3279 字节，SHA256 `599f6baef1045ccff31cbff9b757c8292e3989dd3c22ebc71369caa97d855b17`，与 report 原锚一致。setup apply RC 0、restored 2、expected / actual protected test files 均为 3、absent 0；测试段有开始/结束标记，`RH2_TEST_RC=2`，没有超时或截断。Python 3.9.21 下 pytest `collected 0 items / 1 error`，入口 import 链到 `client.py:171` 的 `asyncio.async` 语法错误。

只抽取固定 parser SHA `339b7c80cca516dc7d1bcf9c11e3ff9a42f1bc993b5027a0d06c41c85d024b58` 的纯函数 AST 重解析日志，观测精确为 `{"ERROR r2e_tests/test_1.py":"ERROR"}`；49 个 expected 键全部缺失，唯一 unexpected 键是该收集错误。这是未收集，不能写成 49 个测试执行失败，也不能用 diagnostics 的 match 0 替换 raw report 的 null。

## 生命周期、缺项与停止条件

actor `harness_exit_code=0`、完整轨迹和正常终止之后，quiescence 记录 agent process residual 0、workspace 稳定双读、无 timeout；actor container / network / relay 清理成功，labeled 容器和网络残留为空。[gateway session_close](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v14/coder/gateway/gpu1003-aiohttp6183-coder-a1/session_close.jsonl) 记录 revoked、active requests 0、drained。gateway 原始请求/响应各 43 行，其中 42 次为模型请求，另有一次非模型请求；42 次模型响应均为 HTTP 200、stream_error null，末次 end_turn，与 42 turns 终止一致。grader manager close 记录 created / removed 各 1、open / supply / cleanup_failures 均为空、regrade 0。

以下字段与额外覆盖保留可见：

- `grading_materials_identity`、`grading_revision`、baseline 的 `environment_package_digest`、`code_snapshot_id` 均为 null；不能因其它原件身份已绑定而称这些字段已填。
- `env_qualification=absent`、`compile_probe=null`。因此 raw 自动分类仍 unattributed；本离线证据没有补齐自动分类契约，也没有新增 reward 规则。
- gateway `checkpoint_identity_verified=false`，input_check 的 service_readback 为 config_only / runtime_request_and_sglang_readback_verified false。实际请求可证明路由名称和发送参数；本轮没有独立核 loaded checkpoint / SGLang runtime 身份。
- 41 个实际 tool ID 均可对应 gateway SSE，但所有 tool input 并非逐字节相同：离线比较记录了 9 处差异，已读示例包括移除 `cd /testbed &&` 和注释尾空格。决定性的 checkout input 精确相同，Frozen 匹配实际记录的 Write 内容；没有继续追全部非关键参数规范化，剩余来源关系 unknown，不能声称整个工具层无任何变换。
- 本地没有该 job 的 `queue_v16/requests/<job>.json`；本轮依实际 input_check、固定 config、prepared、entry 和 gateway 原件绑定，不声称已核完整正式 dispatch 请求。最终 aggregate 在本轮收口时已由父审查者告知返回，但本报告没有读取或复核它，也不判断两模型合并结果。

自有 [离线解析摘要](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/non_author_6183_coder_a1_attribution_20261003/summary.json) 保存当前原件 SHA、124 条 baseline / 13 条 Frozen / projection 检查及原 raw report。摘要的 `failures` 包含上述 9 处整体参数不等，以及 checker 使用了错误 setup 字段名造成的 2 次字符串匹配失败；这两项机器匹配未在停止前修正，不能把该摘要称为“零失败验收”。报告的 hidden / entry 一致性依据已读完整原日志及 private / overlay / facts，而非那两个错误字段名。未为了清空摘要继续读取或验证。

**停止条件已满足：一次完整实际模型响应 → 工具成功执行 → actor 原 baseline / Frozen → grader 同源 rebuild / projection → 完整 SyntaxError 日志与清理链已追踪。** 当前足以登记本单 job 的模型操作归因，保留 safe partial / null 的原结果并进入原计划结果汇总；未发现需要修 shared 捕获/运输代码或重跑模型的实质阻断。额外 runtime 身份、完整 grader inspect、非关键 tool 参数变换和正式 aggregate 覆盖留在上述边界，本轮结束，不主动扩审。
