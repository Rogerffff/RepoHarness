# Dask 8801 R16 宿主读回工具准备独立窄核

2026-10-03。最终适用工具：[finalize_8801_formal_behavior_r16_20261003.py](../../../../../../../../runs/category2_repair_20260929/swe_dask/finalize_8801_formal_behavior_r16_20261003.py)，SHA-256 为 `7d31edc355114a86266f94cefc0d320327928c5e9e600719c8c03e1a63f8af4b`。

**本次发现的来源封闭缺口已由作者修正，最终候选的有限准备核查通过，范围内没有剩余阻断。** 独立重跑 `--check-inputs-only` 通过；28 项路径／输入检查及 18 个隔离的合成读回条件符合预期。这是工具准备审查，不是 R16 CPU、当前公开题面实际交付、新鲜语义裁决或训练资格验收。

只写本报告和[同名 JSON](non_author_8801_r16_readback_tool_preflight_review_20261003.json)。检查使用本机 `rh2/.venv/bin/python`（实际 Python 3.12.13）；合成文件隔离在本核的临时 runs 目录并已清理。没有运行 CPU／Docker／SSH，没有修改共享或封存资产、实际 CPU 原件，也没有读取校准／留出 verdict、期待标签或新建子代理。

## 原缺口及修正核销

最初工具 SHA 为 `ef7c0ec681c090485ba2eae3828513ceaae68b07364e641824357117b869ae78`。对其中日志映射表达式做了精确本机复现：

```text
账本路径：REMOTE / ../prior/eval.log
映射结果：RAW / ../prior/eval.log
resolve 后：逃出本次 RAW
```

`Path.relative_to(REMOTE)` 不会清除或拒绝 `..`；随后仅按账本自带 SHA 读取，可能消费本次回收目录外的旧日志。旧代码还允许空运输清单，不要求所有消费文件属于该清单，未交叉核正式摘要已保存的 ledger／eval-log SHA，也未绑定固定 attempt 和候选 run ID。这是旧版的静态缺口与路径表达式复现，不冒称旧版已读取任何真实 CPU 数据或产生实际语义 job。

作者新增 `closed_raw_path` 和 `verified_readback_manifest`，本核按最终 SHA 重验：绝对路径、空路径、`..`、RAW 根／祖先／文件／子目录 symlink 均拒绝；运输清单须非空、无重复、每项 SHA／大小正确，实际消费原件必须列入清单。manifest、queue、state、固定 attempt／instance／revision、候选 run ID、固定账本路径及正式摘要中的账本／日志 SHA 都重新绑定；日志必须位于本候选的 `run/name/eval_logs`。

最终隔离反例中，越界日志、空清单、未列出的现存账本、重复清单成员、不同 attempt／run 和账本／日志 SHA 不符均在创建匿名 job 前停止。原缺口在当前版本已核销。

## 实际执行的准备检查

独立运行工具的 `--check-inputs-only` 得到：

```json
{"state":"fixed_local_inputs_verified_only","cpu_result_verified":false,"semantic_verdicts_created":false,"rows":29}
```

该路径实际核固定输入及 R16 manifest 中 1,369 个成员的 SHA／大小；代码的固定 revision、矩阵、config、prompt 和宿主协议身份匹配。它立即返回，不访问实际 CPU 读回目录，不创建裁决目录或 CPU 报告。这次没有重新判定这些发布资产的语义或用途资格。

其余条件使用真实固定矩阵／revision 构造合成的 29 行、每行 45 参考原件。为避免产生任何伪正式结果，本核在 `jobs.mkdir` 安装独立拦截：健康合成材料仅证明到达了准备边界，随后立即停止。坏材料必须在到达此边界之前被拒绝；所有检查均未创建匿名语义目录或 CPU 读回报告。

| 本机合成条件 | 最终结果 |
| --- | --- |
| 完整健康 29 行／45 参考、全部身份相符 | 到达 job 准备边界，由独立拦截停止；未创建 job／报告 |
| 无 manifest、空清单、漏账本、清单重复、未列入清单的现存账本 | 到达边界前拒绝 |
| 日志 `..` 越界，ledger／log SHA 与正式摘要不同 | 到达边界前拒绝 |
| 错误 manifest attempt、state attempt、候选 run ID | 到达边界前拒绝 |
| 29 行缺一行，单账本出现两行，45 参考缺一项 | 到达边界前拒绝；缺参考触发 KeyError，未写完成 |
| 安装段未完成或清理未确认 | 到达边界前拒绝 |
| 来源账本的空 image ID 被填成来源 config ID | 到达边界前拒绝 |
| 绝对／空／父目录路径及各层 symlink | 路径 helper 拒绝 |
| 运输成员 SHA／大小错误，布尔冒充大小、自引用或 excluded 非空 | manifest helper 拒绝 |
| 已存在输出原件 | `open("x")` 拒绝覆盖，原字节保留 |
| 固定 revision SHA 被改变 | 固定输入校验拒绝，未进入 CPU／语义步骤 |

这些结果是在固定本机输入上做的工具条件检查。合成 recovered-file 检查替换了 `check_inputs()` 返回值以专门检验恢复数据边界；固定输入校验已由单独的真实 `--check-inputs-only` 路径覆盖。不能把健康夹具当成真实 CPU 成功证据。

## 行为、来源和语义边界

工具要求正式矩阵状态、固定 release／matrix／revision SHA、完整且顺序对应的 29 行，及每行完整 2 F2P／43 P2P 共 45 参考。它核单账本、候选 `agent/54321`、评分 uid 54322、2 CPU／4 GiB、干净 base HEAD、patch SHA、运行材料／修订身份、测试段结束、安装完成／成功、无安装失败项、清理完成和实际日志 SHA；行为分与正式行及固定行为预期分开校对。缺材料抛错后不能生成完成报告。

来源 image 的 config ID 由矩阵前 inspect 独立记录为 `695d2cc28…124b1`，固定 manifest 为 `21e77aea…48483`。来源评分账本中的 `image_id_actual` 必须继续是 null，运行 manifest 身份另核；输出也保留 null，没有用准备阶段 config ID 冒填逐候选运行事实。合成“填上来源 ID”的反例实际被拒绝。

只有上述原件核实之后，工具才从每行已绑定的账本和实际 eval-log 路径调用 `judge_job_from_formal_log.prepare`。该 adapter 的 SHA 固定为 `1a4c9a97…51d12`；它从测试日志封包生成匿名输入，把候选／case 绑定留在私有宿主原件。读回工具没有读取校准 verdict、没有导入 finish、没有将历史裁决复制为新候选结论。本核没有实际生成新匿名 job，也没有裁决任何可见诊断。

行为分 0 进入独立的 `fail_behavior`；行为分 1 仍须得到完整采集并等待新鲜语义裁决。采集不足时报告为 `needs_evidence`，否则最多写 `complete_behavior_pending_fresh_semantic_and_independent_review`。这一名称明确只说行为阶段，不能解释为原因正确、整体诊断通过或训练完成。所有输出保留 `automatic_training_reward_authorized: false`；代码及报告限制明确不授予探针／训练资格。

## 最终身份和未完成事项

| 材料 | SHA-256 |
| --- | --- |
| 最终读回工具 | `7d31edc355114a86266f94cefc0d320327928c5e9e600719c8c03e1a63f8af4b` |
| R16 manifest | `f98eddad0c75df00e8e8352d52819d602a06d5e5ccb8d40feacb8c2658a2b80a` |
| 固定矩阵 | `02668ef71feef69b0db6c8e0f8b7723de11397bde3723abb2a562b18615d4f81` |
| 当前 revision | `fddedb82581076d5b7277693fb3bef44aa73c0a5216e3c243e3ee0133167b87e` |
| v3 bound config | `7e7e861112af22ec7be814a084e395070a5806777eff908dd02c746e8c8acfea` |
| v3 prompt | `9d49671b56ae155f9183d8a0280ff7e779959de2697cdf3887ba4f558f2c19c1` |

收尾检查确认作者的实际 `formal_semantic_r16_20261003/dask8801-formal-cpu-c-20261003-v2` 目录与 `formal_cpu_behavior_readback_r16_20261003.json` 均未因本核创建。没有消费实际 R16 CPU 数据，也没有读取真实 `messages_000` 或新语义输出。

后续仍需以实际回收原件核远端来源与运输 provenance、CPU 完整行为、当前公开题面交付，并对必要匿名输入逐份做新鲜裁决及独立验收。本报告仅核准备工具与有限坏输入边界；它不自行证明运输源真实，不重建整个共享 grader 的判断，也不授予自动 reward 或训练资格。
