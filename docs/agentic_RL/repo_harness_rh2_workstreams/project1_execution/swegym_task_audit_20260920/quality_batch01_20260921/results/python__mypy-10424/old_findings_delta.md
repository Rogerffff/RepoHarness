# python__mypy-10424：旧结论增量

协调者明确放行后才读 `R/runs/swegym_quality_batch01_20260921_v2/history/python__mypy-10424/refs.json` 所列唯一旧记录：`R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-10424.json`（以下 H）。R=`.`。未沿 H 中无完整定位的 dupidx/kcheck 等线索扩读其它题。

| 旧主张 | 处理 | 当前决定性证据与范围 |
| --- | --- | --- |
| 题面目标、base 根因、gold 对应；未强制实现 | 确认 | 前稿的完整比较→binder→meet 路径；五个 note 都比较可观察类型而不引用内部结构。gold 的谓词在 base 已有，不缺依赖。 |
| `is M` if 的期望是题面没讲的规格缺口 | 推翻其“缺口”归因 | 题面在 `is not M` 后 return，留下的恰是 `is M` 条件成立的路径；checker.py:4232–4233 明确交换两边映射。无需从 gold 的“无交集类型”注释倒推规格。复杂元类边界未规定应另记。 |
| 无 stage1 实跑，初态/分差没有运行佐证 | 过时于当前引用条件 | 09-19 本题 G/N 原始日志与 ledger:1 显示相同派生 grader 条件；N 的 main:11、17 实际为 `<nothing>`，G 完整 case PASS，missing/skip 为空、安装均成功。只是 grader 的一对证据，原例逐字和 actor 仍未验。 |
| 无条件 `return declared` 一行即可 RH2 满分、必须补 P2P，故 needs_repair | 确认静态漏测风险；满分事实未核实，必需修订和状态不沿用 | F2P 五条皆保留 Type[C]，相关公开普通缩窄旧测试未执行。H 没有该候选的原始运行。前稿独立提出更窄的“关闭 type 比较约束”候选及两个具体旧测试；它和 H 的全局禁 narrow 候选不同。须先实际证明 F2P=1 且旧语义退化，再决定有依据的最小测试修订，不能仅因 P2P=0 下结论。 |
| 应收全部同文件/相关目录作 P2P | 暂不采纳这个范围 | 选测试应由受影响行为支持。优先的 Union/Any→int 两个 case 已能区分具体错误路线，暂不需要把数百/数千 case 全改成 reward 参考；扩展只在新证据需要时做。 |
| 同 meet.py 三题应归同族、放同一训练评测侧 | 未核实，不采用同文件理由 | H 自己也说缺陷不同；没有本题与其它题的重复补丁/祖先包含关系证据。本次未获准读取其它题，不能以路径相同推同族或数据拆分规则。 |
| 无泄漏、hints_text 为空 | 旧输入字段范围有限；总体结论未核实 | 当前 public bundle 有 harness public_hints，静态 user_prompt 不等于真实 CC 消息。无 `.git` 的导出只说明导出范围，真实镜像/缓存/网络未验；不能填完整无泄漏。 |
| 无 fixture、无网络 | 校正表述，保留核心 | F2P 没有显式自定义 fixture/服务，但真正读取默认 lib-stub/builtins.pyi 与 typing.pyi，并需可写 tmp。业务执行无需网络；安装依赖由指定 wheel 配方固定，准备与运行阶段分开。 |
| test patch 纯测试数据、额外 exclusions 空 | 确认当前原件 | 日志实际恢复 check-narrowing.test，gold meet.py 被投影；未知的 runner 攻击面不自动形成排除规则。 |

没有根据旧标签修改历史前稿。`analysis_before_history.md` SHA256 保持 `4982fdb617b3e2c4495c553bb373ad8fae0dfad809a16523520f673c2b086a37`，配方补记保持 `00c4d384547796fe587e997d1852e311d5ef68001e26883974a40cb22e6fd95d`。最终仍为 `needs_review / static_review`：具体漏测候选待 CPU，actor 条件待验。没有执行新实验、修改原题或扩充评分参考。旧记录的 15 分钟不是当前成本，也不是工具观测的 token/wall time。
