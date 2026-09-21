# 零分审查：mypy 与 Modin 已恢复对照

2026-09-19，Codex 主审。覆盖 mypy 全部 63 条零分（主批 40 条）及 Modin-6298 在 PID=2048 条件下的 1 条 noop 零分；只读本轮证据。全部 64 条都找到目标失败依据，其中 4 条还并存独立问题。

**mypy 的 63 条记录，F2P 全部有 FAILED 输出，P2P 全部 PASSED。** 逐题阅读 Expected/Actual、内部异常与 gold 对照；实际失败包括类型缩窄、错误诊断、stub 生成和类型检查器内部断言。不能把被测 mypy 的 parser 错误或内部异常误归为 RH2 日志 parser/基础设施故障。

| 特别核对 | 结论 |
| --- | --- |
| mypy-10308（主批及 soak） | 协议子类型比较触发目标内部断言，gold 修复；另一个参考外 testHashable 缺 `test-data/unit/fixtures/object_hashable.pyi`，noop/gold 同现。两种失败独立。 |
| mypy-11352（主批及 soak） | noop 三个 contextmanager 泛型用例确有类型输出差异；同步项多出 S，两个 async 项的泛型签名退化为 `*Any/**Any`。gold 严格应用失败，因此没有成功的评分对照，另记来源/base 契约问题。 |
| mypy-11857 | 包括 PEP561 在内的失败是 `tuple[str, ...]` 与 `tuple[str]` 的类型输出差异，不能仅因用例名涉及安装便归为环境问题。 |
| Modin-6298，PID=2048 | noop 的 `Boolean array expected ... int64` 来自 argmax/argmin 的 where 参数顺序；gold 交换参数后通过。这里已实际测到目标行为，不能把 Ray 包装的异常一概当资源故障。默认 PID=512 的超时属于另一条记录。 |

**63 条 mypy 零分的安装段均有真实 pip/构建依赖失败，段末 rc 却为 0。** 当前运行仍载入候选工作区并产生明确目标差异；这支持这些具体 noop/gold 对照，不保证依赖或编译产物被候选修改后仍能正确安装。安装问题单列，不据此把 63 条正常目标失败都归为环境致分。

宿主采样未观察到本切片的 OOM；mypy 采样 PID 最大 38。采样不能排除所有瞬时事件，但没有发现资源错误取代上述目标失败的证据。

逐条记录：`runs/full216_rh2_diagnostic_20260919/zero_audit/root/records.jsonl`。另一位审查 agent 独立核对全部 64 行状态、抽读 15 题原日志，未发现推翻分类的反例，并修正了上面 11352 的精确描述；见 `zero_audit/moto/root_crosscheck.md`。
