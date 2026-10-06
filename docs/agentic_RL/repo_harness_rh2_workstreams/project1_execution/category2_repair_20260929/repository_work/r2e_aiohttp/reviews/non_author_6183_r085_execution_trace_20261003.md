# aiohttp6183 最终R085：非作者执行追踪

2026-10-03（Asia/Singapore）。**当前证据足够按既有流程进入6183探索性单题GPU探针。** 最终R085全文已进入真实CC首请求，身份、预检、空工件和清理原件完整；旧v5六方49键结果及不变评分材料／配方可以复用。发现一项非阻断的历史正对照名称对调，须按slot和patch SHA更正。后续GPU仍须核实际模型请求中的最终题面及已审中性brief；本次脚本桩没有交付brief。

## 范围与固定身份

本报告承担Production Tracer（真实执行追踪），只沿已有原件确认交付、环境、材料复用和生命周期。非作者、非盲审，实际读取私有评分材料与正式原日志。没有SSH、容器启动、模型调用、重跑矩阵或项目代码执行；只新增本报告及ignored机器摘要。同SHA brief、公开reader、Expected Behavior修正、wrapper和Git机制复用既有结论，不重复审机制或从头解题。1c1／240d在途矩阵不属于此次结论。

固定请求包为 `review_handoff_6183_r085_cpu_20261003.json`，SHA256 `8c59b154aff8b14b5ed85ae0997db2515fc5b27dd890968506a0d66b6c4281e5`。10项fixed_inputs、3份raw_receipts、6组ledger/log均重新计算SHA并吻合。三receipt分别38/38、80/80、59/59，合计177个登记原件的摘要与长度吻合；80文件delivery receipt含240d，但本次只解析6183执行正文，没有把240d计为验收通过。

R6发行：`cat2-cpu-r2e080087-swe8-git-20261003-v1`。直接回算其manifest SHA `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`、registry SHA `4e379ab64f382897be6531030041f59798ac697f8f6d84f015eda4876a27d179`、pins SHA `34528bd130cb003d8c1d5aa4cfb275a1390e9ec138c406adc0a6bcc740a63e1b`，均与发布绑定一致。

下文路径简称：

- **P6**：`runs/category2_repair_20260929/r2e_aiohttp/cpu-b/revised_prepare_r6_v1/final_artifacts/`。
- **D6**：`runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/delivery_artifacts_v1/`。
- **R4**：`runs/category2_repair_20260929/r2e_aiohttp/cpu-b/public_actor6183_draftdev_r4_v1/final_artifacts/`。

## 最终题面确实先于桩响应送达

执行链：R6准备 → P6公开／宿主grading view → R2E solve入口 → 共用solve入口 → CC → gateway真实请求 → 脚本桩 → CC工具调用 → 静止屏障 → FrozenPatch导出 → drain／清理。

1. `P6/prepared/rollout_task_views.jsonl` 的6183行含最终题面，解码UTF-8 SHA为 `ab73a3ec70cb08e3fd6846b8ceead6552ea82082d6f837fd9118787a0e4f004d`。公开bundle digest为 `9587eedfc18ddba5f8f27d3467d4e3af893e8b947f55fb034130ecad6c839139`，与attempt、FrozenPatch一致。
2. `D6/delivery6183/stub/requests/messages_000.json` 文件SHA `b4e01dc4acc9424cec21f3d3bdb8a5d65af832aa50f0d4db3bbe1980df224f37`。消息0为user；文本块1包含103字符修复请求前缀，随后为2386字符完整最终题面，后缀为空。抽取该全文重算SHA与R085相同；不是仅匹配标题或作者proof布尔值。
3. `D6/delivery6183/gateway/aiohttp6183r085delivery1003v1/requests.jsonl` 首行seq=1、POST `/v1/messages?beta=true`，User-Agent为claude-cli/2.1.205；body与桩首请求JSON逐字段完全相同。`attempt/harness/trajectory.jsonl` 有真实CC init、Bash工具往返及success result，harness log完整、stderr为空。
4. `delivery6183/stub_script.json` 只回应预检Bash、解释器Bash和“Probe prototype steps done.”，没有题面echo。因此全文来自请求输入，不能解释为桩事后回显。它仍不证明真实模型理解或求解。
5. attempt记录R2E入口SHA `10a71cca67af24c9ab5a6de09cb1845751c643632559842bb61dbce6ebc01d5a`、共用入口SHA `00ca849909150de02769f297374a9bbfacf2746347c425474775d9c3e22a04f9`，与R6快照同路径文件字节一致。这里只绑定执行版本，没有重复机制审查。

R4旧prompt没有被当作最终交付证据。[已审brief](../public/6183_development_brief.md) SHA `f1636164b5669015333ba0281f73dc696c8ac803c0b914246fb1a083b01b233e`未变；`neutral_brief_actual_delivery_this_stub=false`与首请求一致。GPU首请求仍应核中性brief实际交付，不能把本次题面送达顺带记成brief送达。

## 实际身份、预检、空工件和清理

`D6/delivery6183/attempt/attempt.json` SHA `d3aa536e36bc734fbcdfe837e42a3d11de5ed03b68c004599046afde9f2cc0c2`；从18:42:41.824366Z到18:43:23.151871Z，harness_exit_code=0、termination=completed。

- `facts/agent_env_facts.txt`实录UID/GID54321、`/testbed`、`/testbed/.venv/bin/python`、Python3.9.21；activation原件核同一prefix与VIRTUAL_ENV。`facts/prelaunch.json`再次实录UID54321、2CPU／4GiB／512pids、DNS及直接外网拒绝、无bind mount和无特权。
- `stages.image_identity`、prelaunch、overlay和FrozenPatch共同指向实际image `sha256:28682e5ad429ad323e4903845b86a71d5ffdc5325aa085fab5f925733cf91523`。物化HEAD `ff3dec422bd18b5e9078b5f29be1c9a6a1373f5a`等于本题base_commit。
- `facts/r2e_preflight.txt`三项均ok：解释器可执行、hidden不可读／无公开副本、HEAD无子提交；CC工具结果也有三行及正确解释器路径。
- `frozen/frozen_patch.json`文件SHA `29f8cc959daadcf94c5cd87eb6e69bf80957912ae05060005f94df14938277b1`。以sorted compact JSON重算canonical digest为 `e22b47dd85f916c08690d2679e9d121d7191e25b0461d04aca8cbee0c946496b`，与attempt相同。entries为空、excluded_pathset_changed=false，baseline digest `5b0e8e05ca86a233ed2741046cc277d6f572dcde406eb31d7c1cc378c1fb4ac2`，classification=projectable，pip freeze未变。
- pre_drain_stop及quiescence的进程残留均0，workspace稳定双读；gateway drained=true、active_requests=0、revoked=true。cleanup_ok=true、container_rm=0，container_left为空，network／relay失败及标记容器／网络残留列表均为空。

这是空FrozenPatch导出与清理证明。此stub没有评分，不能替代非空工件直评共用验收，也不能声称已产出模型修复。

## 旧v5与新R6的复用绑定

旧 `s2_r2e/ingest_history/material_v5_20260929/grading_bundles_r2e_v0.jsonl` 的6183行，与P6宿主grading行逐项一致：base_commit、expected JSON全文及SHA、hidden文件清单和tree SHA、run_tests_sh全文及SHA、parser_id、normalization_version。R6 registry中的044／045与旧v11 registry对应条目完全相同；新增085只改公开题面。

| 绑定 | 共同值 |
| --- | --- |
| hidden tree | `23b524a89a3137272d0d4bda1c4f1d9e3a3e9e0851f462c061d2fd988dac85af` |
| expected JSON | `3390e85fe2f0807791b3def432def784f6da255b28b8d9e63c9af052218ace3f`，49键、全部预期PASSED |
| run_tests.sh | `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf` |
| base manifest | `67aefa179aab4b224a367b97446b72c033d9884ad10dcda09f7165a0e4b4e65b` |
| recipe | `r2e_derive_v1+material_v2+sysconfig_v1`，SHA `70ceace9f6ab1e015cd3fa26ea20bb9180125711597c569acff70e30adf68c7a` |

旧v5实际image为 `b93c5d43ab2871f0b39ccccd2f53b9517b6e0560a7085579e4ab5bc076397be6`；新CPU-b为 `28682e5ad429ad323e4903845b86a71d5ffdc5325aa085fab5f925733cf91523`。**ID不同，不宣称位级相同或在新image重跑六方矩阵。** 旧 `formal_v5/remote/build.log:3`绑定044、旧image及同recipe；新 `baseline_derived_v1/final_artifacts/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/facts.json`绑定同hidden／entry／base／recipe、全部integrity项ok、failures为空，并核源码／依赖保留、解释器搬移、hidden权限与HEAD。新facts SHA为 `592fb90ac15b1d0e7c8f3df893b36d6aea8e6728620003370fc79045fd8fad55`。

R4在当前CPU-b同image上执行公开base/gold对照，两段命令分别base rc1/1、gold rc0/0；base日志显示空write与终止块后仍有数据，gold两段输出为空且断言通过。两方公开protocol回归均47 passed／63 warnings，解释器、UID和清理一致。R4可支撑开发行为，不证明R085送达，也不等于49键私有评分。

六份正式v5日志均按Start／End Test Output限定段，逐状态行重建结果；每份键集合恰等于49个expected键，不缺键、不加键。测试结束标记、ledger、runner_integrity_changed=false和removed=true均相符。

| 原件slot／实际名称 | patch SHA前缀 | 匹配expected | reward |
| --- | --- | --- | --- |
| gold | `ce89afa45fb0` | 49/49 | 1 |
| noop | 空补丁 | 45/49 | 0 |
| s1／AP1 | `62fb5c2c2ee0` | 47/49 | 0 |
| s2／AP1m | `05e094d58842` | 47/49 | 0 |
| s3／AP2 | `0548e104256c` | 49/49 | 1 |
| s4／A1 | `5b38357b44e6` | 49/49 | 1 |

完整ledger/log SHA、固定行号、重建结果和材料对比保存在机器摘要；本轮未调用项目parser或重跑评分。旧矩阵的复用支持现有探索性GPU步骤，不升级为当前image新完整矩阵验收。

## 非阻断项、未覆盖与停止条件

**AIO-TRACE-01（P2，摘要标签更正）：**固定handoff的old_formal_logs和 `results6183_v5_log_readback_20261003.json` 的rows把s3／0548…称A1、s4／5b38…称AP2；原 `formal_v5/remote/slots_manifest.json`与plan恰为s3=AP2、s4=A1。违反的是候选名称与实际patch对应一致性。两行都是49/49、reward1，可按SHA准确定位，故不是评分翻转或GPU阻断。最小处理为独立更正说明，保留历史原件和固定SHA，并在probe_request正确标注。验收条件是两个名称与slot／patch SHA对应可直接核对；不需重跑或新修法。作者已提交独立更正 [correction6183_v5_candidate_labels_20261003.json](../correction6183_v5_candidate_labels_20261003.json)，SHA `7b7e6815f31e139f04a5efc1103d1227e55a05515b0cbf79035e586893f3ba6e`。本轮直接核其SHA、两行slot／patch／log／ledger及固定行号，均与本报告原件核对一致；原handoff和readback保持原SHA。因此AIO-TRACE-01已闭环，后续请求采用更正映射，不等待另一个回执或新增运行gate。

没有其它实质缺口。当前足够进入既有探索性单题GPU安排；实际模型请求、题面与中性brief同时送达、模型修复／reward、非空FrozenPatch直评、全仓兼容、正式训练／留出资格不在本轮验证范围。脚本桩成功不能计作基座能力；这些是原流程待做事项，没有新增审批闸门。

停止条件已满足：最终真实请求、实际身份与生命周期、材料／配方绑定和六方原log各完成一次追踪。不等待1c1／240d、不扩候选、不重复Git冒烟。机器摘要：`runs/category2_repair_20260929/r2e_aiohttp/non_author_6183_r085_trace_20261003/summary.json`，SHA `f0a0ab5c95189b6ed955843017e00b2ff338e9475768eb86064fde1bb2258da5`。
