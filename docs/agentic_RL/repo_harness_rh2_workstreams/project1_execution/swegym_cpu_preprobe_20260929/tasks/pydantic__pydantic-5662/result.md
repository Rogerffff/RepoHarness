# Pydantic 5662：CPU 结果（2026-09-29）

**确认示例特判误奖：只识别 unittest.mock.ANY 的候选获得正式 reward 1，但一般比较对象的相等委托仍未修复。** v1 §4 第2步 S1/T2c 保留，并有第3步 S1/T2b 的实测证据。当前可作问题定位；跨包独立复核和root冻结parser重放均已通过；受限能力比较仍须实际解题入口/预算核验及预登记审计。不进训练或留出评测，私有后检不等于正式测试已修订。

| 候选 | 正式 reward；F2P；P2P | 原始完整测试结果 | 私有行为 |
| --- | --- | --- | --- |
| noop | 0；0/1；127/127 | 1 failed / 141 passed / 26 skipped | ANY 与一般 true matcher 都失败；7项旧相等测试通过 |
| gold | 1；1/1；127/127 | 142 passed / 26 skipped | ANY、true/false/NotImplemented matcher 委托均正确；dict/object 护栏与7项旧测试通过 |
| all_nonmodels_equal | 0；1/1；125/127 | 2 failed / 140 passed / 26 skipped | 所有非模型相等，破坏 dict/object；现有 test_comparing、test_model_equality_dump 正确拒绝 |
| any_only | **1**；1/1；127/127 | 142 passed / 26 skipped | ANY通过，true matcher仍false；三个matcher都未收到原对象，7项旧测试未发现此欠修 |

四行正式输出全部核过128个冻结参考 ID（1 F2P + 127 P2P）、日志SHA和完整测试段。gold和两个退化候选实际导出均仅`pydantic/main.py`，解码字节与公开base加对应输入patch逐字一致；patch SHA也与账本一致，noop导出为空。安装输出四次均成功构建/安装 editable pydantic 2.0a3；core 0.27.0、`/testbed`导入、runner前后摘要一致，无安装失败命令，无参考缺失。四行候选清理及manager_close均无残留/失败。

actor原镜像以UID54321实际完成3个配对Bash调用：准确复现`PUBLIC_COMPARISON_DELEGATION_FAILED`，7项现有测试通过，160 deselected。Python3.8.19/core0.27.0，base `0346ddb6a35770007f32815d8e4a179b778e0ef4`。原镜像已有pdm.lock/pyproject.toml改动，已在identity和初态记录，不误记为候选改动。prelaunch、激活与清理均通过。消息仍为devcheck控制文本，尚未证明真实题面/public_hints交付；四组私有root容器只证明行为，不替actor权限检查，且均准备与清理成功。

本次固定上游digest `ffae2cd005d11d3a02a8d9925ad4123a98b1b22e298e91c7293357075116325e`，原镜像ID `96aaecfda19343d97563572c064c50f02f1ebb107417dc8c8b303df868abbf7d`；8公开wheel离线层ID `2b93958eb0de899e06f69f5918b93c7e57308039223efe7318962e26d077a9d3`。1021byte私有canary排除，实际probe absent；不是历史9wheel逐字复刻。

预算审计明确准备300→900秒，测试1800秒不变；全评分3600秒。四行均2CPU/4GiB、grader UID54322、deny_all；安装约4.96–5.41秒、测试2.21–2.44秒，trusted_setup230.27–258.39秒。内存峰值原字段约682–686MB，resource_facts为空，不推CPU利用率/整机余量。这一预算版本不与8793原300秒混称同条件。

## 最小修订草案及剩余项

公开依据是非BaseModel相等比较的一般委托要求；不能仅扩一份ANY字面量。建议R-c加入普通matcher接受原对象并返回True的非示例断言，同时保留已存在dict/object拒绝与模型相等护栏；当前公共诊断已覆盖true/false/NotImplemented三个委托结果，gold实测通过。无须规定内部代码形态。

D6正式SWE修订入口仅允许成本/设计探索，本夜未获实施授权。本记录没有修改正式题面、参考或评分。若获授权，应版本化加入上述窄断言并正式CPU复验noop0/gold1/all_nonmodels_equal0/any_only0；验证原参考完整、新断言实际执行、被拒原因及清理，并独立验收。

受限比较预登记：本题所有原reward=1候选统一做同一普通matcher委托、dict/object和7项旧比较测试审计；原reward原样保留，语义pass/fail/unverified另列。不得把误奖候选称完整解；共同题单/预算/有效分母另明确。

已完成验收：`reviews/pydantic5662_final_review.md`支持上述误奖结论；root的`analysis/pydantic5662_followup_v1.json`冻结parser重放通过，`analysis/evidence_manifest_pydantic5662_v1.json`覆盖120份、2,189,581字节且无本地SHA不符。路径均相对本批docs或runs根。普通true matcher未被委托即是决定性公开违例，不以精确调用次数作为新的规范。

全部剩余：D6修订机制成本及实施授权、授权后的正式复验；真实题面/public_hints交付、GPU入口/模型/预算；跨题关联、训练/留出划分及真实难度/成本；控制面准备效率另版本观察。未处理S1前不训练，不自动宣称GPU-ready。

证据：本目录`evidence_audit.json`保存每行全部128个参考状态、原件路径/SHA、候选字节核对、资源/预算/清理；`result.json`保存用途。原件位于`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5662/followup_20260928T182457Z-a73f19/`，重点为`grade_any_only/ledger.jsonl`、其`artifacts`下`frozen_patch.json`及`private_any_only/any_only/private_matrix.out`。历史卡/证据不回写。
