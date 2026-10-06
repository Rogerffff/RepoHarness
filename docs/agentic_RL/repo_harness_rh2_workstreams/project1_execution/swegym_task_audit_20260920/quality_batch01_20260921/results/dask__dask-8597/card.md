# dask__dask-8597

**受限开发诊断静态候选；needs_review / static_review。** base `c1c88f066672`。公开正文明确 `(3,0)` 数组经 `[0]` 列表索引应得到 NumPy 一致的 `(1,0)` 空结果；标题“0-D”不影响定位。

| 需求／旧行为 | 测试与覆盖 |
| --- | --- |
| 原例构图、计算、shape/dtype | 唯一 F2P 的 assert_eq 直接覆盖；noop 除零失败，gold 通过 |
| 非空列表块规划、True 拆块 | 116 P2P 两侧 PASS，相关 take 测试保护 |
| 默认大块警告 | 旧测试实际 PASS，但不在 P2P |
| 空轴+True、返回 Array | 新测试单形状/默认配置；helper 的 Dask 检查有类型条件，覆盖不足 |

八方面已查公开需求、材料/初态、断言/helper、旧行为/调用者、gold、开发依赖、投影评分及用途暴露。实际 actor/消息、全仓后端、镜像泄漏与跨题关系未验。

compat-v1 原件：pytest 7.4.4 安装成功，gold 全模块 119 passed/2 skipped/2 xfailed、RC0；两项额外 PASS 不在来源参考。此为 grader/54322 证据，不能证明 actor 已消费安装配方。gold 仅扩展零元素 guard，未发现已证回归。

主审与独立初判都提出“仅 split=True 时算阈值”的部分修复：可能过原参考，却丢默认警告、漏修 True 空轴。**未执行，未证明误收**；来源覆盖限制也不是 RH2 接线故障。

独立复核已完成。唯一优先下一步是该候选与 noop/gold 的真实 CPU/RH2 对照；结果明确后再决定模型用途并验 actor。详证据见 `analysis_before_history.md`、`old_findings_delta.md`、`review.md`。原题未改，审查产物不得给 solver。
