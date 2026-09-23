# R2E 接线计划 · B 线复核

2026-09-20，Codex。对象为 [Claude 计划](../r2e_grading_wiring_20260920.md)与 [A 线审查](README.md)，不是实现验收。

**结论：同意接线方向，A 线五项修正有依据；修订计划后可以实施。没有新增需要重开训练语义或扩大架构的阻塞项。** DR1、DR3 推荐 A，DR4 保持来源对账与后续筛题的分期；DR2 应撤回错误二选一。以下均为审查建议，不替用户批准。

## 1. 对 A 线结论的独立核验

| A 线项 | B 线结果与处理 |
| --- | --- |
| R1：Prime 去色误读 | 确认。重新执行 A 探针，并补做 **336 份日志的归一化观测表与期望表逐键比较**，全部相同；带 ANSI 的 pillow 六题共 24 次 gold，来源函数都给 1。删掉虚构的双版本与错误验收，不让用户在错误事实之间选。 |
| R2：manager 来源语义与全缺席判据 | 确认。现有空 SWE 桶会把部分缺键也判成全缺席；P-A 候选归因和提前 infra 会丢失来源语义。应在 spec 构造时确定来源，贯穿真正的报告 producer，再验证训练运输。**这属于尚未实现的 R2E 路径启用前必须补齐的接缝，不代表当前 SWE 训练已经因此出错。** |
| R3：同组混来源验收 | 确认。改成同批不同题组；不能放宽 GRPO 同组同题约束。 |
| R4：24/48 输入路径 | 确认。M3 的 `probe_data/r2e_candidates_full.jsonl` 才是与 48 题单完全相等的合并材料。 |
| R5：build-time chown 成本 | 确认。rollout 54321、grader 54322 的实际初始化仍递归改属主；单镜像不能据此宣称两边的运行成本消失。沿用现有权限方案，真机先量正式 profile 的初始化与可写层即可。 |

**对 R2 验收范围的一处收窄**：A 探针的 `patch_apply_failed` 报告来自旧 diff/workspace 分支。计划的正式冻结路径在候选阶段 apply 失败就记 `apply_failed`，不进入 grader；冻结文件重放失败则是 infra。公共来源字段当然应一致，但无需为 R2E 另接一条旧 diff 评分入口或把旧分支当成本轮必跑场景。正常、提前 infra、P-A 等共享报告分支仍必须修。

## 2. B 侧补充：小范围澄清与验收

**B1 · `.venv` 排除不等于完全不参与基线身份。** 当前 [census](../../../../../rh2/src/repoharness2/adapters/slime/baseline_census.py) 对排除区不读文件内容，但仍列出文件路径；这些路径的摘要进入 manifest。排除区的这次遍历不会剪掉 `__pycache__`。所以不能从“.venv 不进候选 delta”推导出“预检产生缓存肯定不影响基线”。

- 最短条件：新增解释器预检在首次 census 前生成 `.venv` 内缓存，fresh grader 重建时没有同样路径 → [manager 的基线摘要比较](../../../../../rh2/src/repoharness2/grading/manager.py)不相等并停批。合成路径行调用真实 census parser/digest 已确认这个机制，**48 张实际镜像是否会新生缓存尚未验证**，不列现存 P1。
- 最小处理：R-d 明确把纯检查放在首次 census **之后、候选应用之前**；或确保双方基线前的步骤完全对称、检查不写缓存。R-c/R-d 增一个未经 Python 预热的 fixture 往返，R-f 首题确认相同边界。无需另改 manifest 契约、删除审计或新建缓存平台。

**B2 · gold 应比较应用结果，不要求补丁文本相同。** 原计划 R-a 同时说按 Prime `extract_gold_patch` 重建并与独立 runner 产出“相同补丁”。实际两者分别从来源 hunk 和 old/new 文件内容重建：**48/48 补丁字节不同；但纳入路径相同，在来源旧文件临时树中，两侧都通过 `git apply --check` 与实际 apply，48/48 应用后内容摘要相同。**

因此 R-a 写清“固定 Prime 来源实现；对账文件选择及应用后内容”，避免把 header、hunk 分块不同判成失败，也不要为凑字节一致再改一套 gold。此次只验证来源材料临时树，真实派生镜像的严格 apply 与冻结导出仍由 R-f 验收；不外推到未纳入的 4,530 题。

**B3 · 两处来源事实及一处实现细节。**

- 已跟踪脏树是 **aiohttp 5 + pandas 7，共 12/48**；计划引用的 3+3 是扩展 24 题的旧局部计数。当前 `image_embedded` 没有 reset/clean，文件系统 baseline 能保留这些兼容补丁，无需新增恢复机制。
- pillow `3ac9396e` 自定义 runner **会输出 pytest 形状的收尾**。本地 runner 原文（仅本地运行证据：`runs/env_overnight_20260916/M3/facts/3ac9396e8c99/r2e_tests/unittest_custom_runner.py`）及既有 gold 日志都有 `11 passed in …s`，不是仅仅“缺收尾不必然 None”；计划中的事实前提本身也应更正。仍按真实日志与既有 P-A 规则处理，不为 unittest 新增拒绝规则。
- R2E root setup 没有 `git apply test_patch`，复用 `grader_trusted_setup_attest_lines` 时，应在复制、重写与摘要核验**全部成功之后**提供该 helper 所需成功状态；它的 `RH2_APPLY_RC` 缺省为 1。这是 R-c 的接线细节，已有 fixture 验收可覆盖，无需新增用户决策。

## 3. 不建议扩大的范围与开工顺序

1. **隐藏测试方案 A 可以采用。** root 私有目录 + fresh grader 恢复原文 + 既有文件及祖先目录权限保护，结构上可以复用。M3 只收回文件属主的替换反例没有使用当前 sticky 祖先保护，不能据此断言现方案仍不成立。repo helper 可写与 stdout 伪造仍是已登记的边界，DR4 本片不额外处理，不宣称完全防作弊。
2. **保留脏树、`.venv` 排除可以沿用现有链。** 真实路径为初始化 → 血缘检查 → census → candidate → exporter/投影 → fresh grader 重建同一 baseline → 应用 delta → root 恢复隐藏测试 → 候选身份测试。没有理由复制另一套 exporter、controller 或 grader。
3. **派生 tag 重指不再升为新问题。** [SWE 接线记录](../swe_grading_wiring_20260915.md)已接受过检查与启动之间的该窗口。本片 overlay 已保存不可变 ID，若顺手用确认的 ID 启动两类容器，可作为窄实现选择；不以此重开此前验收。
4. **先完成本机 R-a/R-b，再接 R-c/R-d 与真实报告运输。** R-0 归 B，在真机批前落实最终收口状态外显；历史清理错误后来已解决，不应仍报整批失败。A 的 manager 清扫/日志修复已登记实施，本片需基于其完成快照合入；不要继续按“生产尚未修”维护临时绕行，也不在本轮代替验收 A 的修复。
5. **真机先少量代表题，再 48 题 noop/gold。** 覆盖纯 pytest、xvfb、自定义入口、dirty tree、expected ERROR 仍 resolved、冷镜像 baseline、P-A 与超时。观察分歧再决定重复哪些题，无需机械重跑旧 24 两遍。用最新正式 profile 估算成本，不能仅从测试中位 9 秒推整批耗时。

**决策建议仍是 DR1=A、DR3=A、DR4=来源对账，DR2 撤回。** DR3 的配方构建按用户后续安排派发，本轮不把文档中的 owner 当成已启动。接线验证通过也不等于 48 题具备训练资格；expected 中已有环境失败、两个 gold=0、单键信号、helper 边界与正式 actor 环境消费留在各自已定阶段。

## 4. 证据、限制与停止条件

- [B 探针](probe_b_materials.py)、[本轮输出](B_probe_results.json)：重跑 A 的 CPU 探针；336 日志逐键比较；48 gold 双侧应用；排除区路径摘要合成反例。探针退出 0，ruff E9/F 通过；记录本轮实际代码与材料摘要。
- 按审查标准 §10.4 安排一组 Production Tracer / Falsifier，交叉核对容器边界；主审独立检查调用顺序、原始材料及关键探针。未发现上述范围外的新阻塞。
- 仅新增审查工件与导航。未改生产代码、维护测试、环境配方、参考集或评分规则，未运行 Docker/远端/GPU、租机、提交推送或通知其它任务。现有实现中的 R2E parser/spec 尚未落地，不能宣称整条 R2E 评分通过。
- **停止条件**：作者落实 A 的五项及上述局部澄清后，即可按对应切片实施；实现后只验证真实 producer、冷镜像边界和本批对账，不重新审已收口的 SWE 全池或增加一轮宽泛反作弊设计。
