# conan-io__conan-15422：历史对照增量

历史前稿已先落盘并通知协调者，SHA256 `89895705a8a99d0a807f2f77f33bb22614a64a5b64687f7afa1739ff0a034878`。协调者明确开放本题 `runs/swegym_quality_batch01_20260921_v2/history/conan-io__conan-15422/refs.json` 后，才读取它所列两个 JSON。未改前稿字节；未读 reviewer。

旧件 A：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/records/conan-io__conan-15422.json`。
旧件 B：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/conan_pilot/records/conan-io__conan-15422.json`。
以下原件路径、行号和证据层次详见保留的 `analysis_before_history.md`；源码均为本题精确 base。

| 旧主张 | 本次处置 | 新的决定性证据与限制 |
| --- | --- | --- |
| A.1/2/20：版本与补丁对应，缺字段为初态失败；B 记录原镜像 noop/gold 0/1 | 确认 | 本次直接比较 S2 三 bundle 第 38 行、patch 内嵌值和日志哈希；noop 原日志 932–940 明确 KeyError jobs；gold 997–1005 明确 PASS、整命令 rc=0；ledger:1–2。 |
| A.23 将 jobs 来源/默认值未逐字写入题面列轻微问题；B 否定其规格缺失推论 | 推翻 A 的问题归因，确认 B 的收窄 | 公开 `cpu.py:8–28` 明确配置优先与 CPU 默认，`cmake.py:11–19` 已消费；题面 JSON 16 是举例。需读仓库才能确定不等于依赖私有信息。生成器适用性和零/负值仍非唯一规定，此处不扩张结论。 |
| A.24：只观察结果，不锁实现；A.25/B：只测显式 42，漏默认/其它值 | 确认但限定范围 | test.patch 全部新增内容只断言第一个 preset.jobs==42；已展开 TestClient 到实际 CLI/文件。不同内部路线可接受；并未证明所有正确实现均通过。条件写 jobs 的候选仅静态预测，未做新 RH2 反例。 |
| A.26：40 P2P 因“回归面较宽”记 pass；B：无默认/第二配置 jobs oracle | 确认 B；收窄 A | 本次实际读单/多配置的每次安装与断言（538–660），及路径、用户预设、Ninja/MSVC 的相关 P2P。结构回归有证据，新增字段的各路径语义无完整保护。未逐条语义展开所有 cross-build/Android P2P，不将计数作完整性证明。 |
| A.27 / gold_introduces_host_dependent_output：CPU 默认随机器变化即新增稳定性风险；B 否定 | 推翻该风险依据 | 默认本来就是可用 CPU；F2P 显式 42、P2P 不比较默认 jobs。变化本身是预期行为，不足以要求重复资源实验。本次独立发现的 generator 兼容风险来自 NMake 排除和 Visual /MP 等不同证据，不能与此旧主张混同。 |
| A.19：parser 产生 [1] 假键但不影响参考；B 确认 | 确认“本题无参考缺席/跳过影响”；假键细节未核实 | 直接读当前原日志 44 collected、3 个非参考平台 skip，以及 ledger reference_missing/reference_skipped=[]。未读取旧 stage1 status_map，不能说本次重新验证了旧假键的生成机制。当前 parsed=42 不当作执行数。 |
| A.6/7/11 与 B：无需 CMake/网络完成官方字段测试 | 确认评分测试范围；actor 条件未核实 | 新测试只 install+JSON，日志三个 requirements 均已满足、deny_all 下测试可执行。此结论不涵盖用户实际 cmake build；actor 身份、激活、资产尚无运行证明。 |
| A.3 “hints 无额外信息”/A.ready_for_probe | 对当前输入与准入范围已过时 | 当前 bundle.public_hints 是 harness 操作指令，不是 A 引的原 issue 社区答复；静态渲染不是实际消息。现模板要求静态候选 needs_review/static_review，grader 成功不可代填 actor。 |
| A.5 要求与 14296 同侧，B 表示未定 | 未核实具体关系，拒绝同文件即泄漏的推导 | 本次没有读取 14296 的需求/补丁/commit。仅同文件、P2P 重合不能证明答案派生；不建重复簇，不制定 train/eval 分组。 |
| A.29 “无静态泄漏” | 收窄；完整可见资产未核实 | 当前静态导出无 .git；题面未给 helper 修复。未查真实镜像、未跟踪文件或祖先历史，不能升级为答案泄漏全排除。 |
| A.31/B 的 conftest_user 控制面线索 | 源码入口确认；实际利用能力未核实 | 本次直接见 `conftest.py:235–239` 与 `TestClient:425–431`，可覆盖默认 profile。未运行候选、未重审最新投影/清理链；保留仓库级待核，不加本题路径排除。 |

本次主判断保持：明确限定用途的静态开发诊断候选，needs_review/static_review；不是最终训练/评测批准。新增独立细化是 F2P/helper/Mock 全展开、真实日志与参考项对照、generator 兼容疑点、actor 分阶段开发条件及实际消息缺口。旧稿没有把这些问题证毕，不能因为历史有 probe_candidate 标签略过。

唯一优先下一步仍为真实 actor 的公开 JSON 对照（不同显式值、缺省与多配置追加），与“只传显式配置”的 CPU 负对照比较官方结果。不要求为 CPU 默认可变性再作无目标的资源重复实验。历史读取本身未触发新增代码执行。
