# python__mypy-10174 · 历史差异

记录UTC：2026-09-20T21:35:11.383597+00:00。初稿保存UTC `2026-09-20T21:30:43.290121+00:00`，SHA256 `d1f6f217d865901b32575afab76ef58cd42be5c104c867b5fd07f97c5e443b0a`；父协调者于UTC `2026-09-20T21:30:59.391928` 明确放行后，才读取 `runs/swegym_quality_batch03_20260921_v1/history/python__mypy-10174/refs.json` 及其唯一记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-10174.json`。初稿未回写。没有追旧文中stage1、dupidx、kcheck_all、p2p_mechanism或邻题记录。

| 旧主张 | 复核结论 | 决定性证据与本轮处置 |
|---|---|---|
| 原题清楚、base含缺陷、gold移动Any guard修复规范化顺序 | 确认，证据更新 | base meet.py:164-176与types.py:1777-1783,1801-1806形成静态因果；09-19原NL:494-527目标F2P失败、GL:521-539三过。不依赖未展开的旧stage1汇总。strict-optional正对照本身并不能唯一推出内部根因，需源码支撑。 |
| F2P与题面“逐字一致（含flags）” | 语义确认，字面修正 | 题面用inline配置，data case用两个--flags，行为等效；空诊断断言有公开依据，无内部helper形状强制。 |
| 两P2P测未导入Any/any提示，不能保护strict-equality和overlap | 确认 | 完整base check-expressions:2771-2780、semanal:4728-4761与messages:45-55；原日志两例均真执行通过。它们不是Any重叠的正反测试。 |
| 若关闭比较/恒返回True即可满分，且属本包最高风险之一 | 部分确认、运行结论及排序未核实 | 一条具体窄路线：non-strict optional时dangerous_comparison直接False，静态预计过官方1/2而丢失同配置下真不重叠诊断。尚未构造/执行，不能称已得满分；未做全包风险比较。旧示例函数名 `_is_overlapping_types` 也不应替代本base实际函数名 `is_overlapping_types`。 |
| selector子串命中AnyLower为良性过选，并证明P2P来源机制有问题 | 选择事实确认；缺陷与因果表述收窄 | test.patch上下文含testUnimportedHintAny；历史spec_vendor:183-197读case标签；-k再匹配AnyLower。原执行3、解析3、参考1+2恰好相同，无未评分额外节点。该任务支持“邻接case进入选择与子串匹配”的机制，不单独证明参考集历史生成因果或当前错选。 |
| 40/40均由选择闭包产生，14题P2P空，应全仓重建P2P | 未核实，不纳入本题事实 | 旧聚合不在放行范围，未读；逐题回归缺口已能成立，不借全仓统计强化。全文件/全仓回归的成本与必要性未评估，不作为本题强制前置。 |
| 必须造三个假补丁并跑全部相关文件 | 建议收窄 | 只保留一个最有区分力实验：base/gold/一个non-strict关闭比较候选，同时跑官方1/2和同开关 `1 in ('x','y')` 公开负例。先验证是否真存在满分错误解，再决定修订；不强制造第二份正确解或三个广泛破坏补丁。 |
| 共享meet.py的10424/10658等是同族而不重复 | 未核实 | 旧记录带来邻题路径级线索；未查看这些题，不以共享文件证明同族、重复或独立。此次暴露如实记录。 |
| 无泄漏 | 证据不足 | 公开题面未见修复代码成立；旧记录称raw hints空，未另取raw行核查。实际actor可见Git对象/镜像/缓存、工具网络及模型轨迹仍未知，不能继承全局“无泄漏”。 |
| 环境可恢复，test patch与gold不冲突 | 在本题09-19条件下确认 | 原spec安装日志成功；派生镜像只COPY wheels+ENV；仅恢复check-expressions.test，不覆盖meet.py。test_globs为空，无新增排除依据。当前正式actor与离线资产可复用性仍未知。 |
| needs_repair、旧用时18分钟 | 不沿用处置与成本 | 回归缺口值得审查，但尚无本轮执行的错误解反例、修订或actor验收；机器处置统一needs_review/static_review、development_diagnostic；当前未知成本null。 |

历史未改变初稿的主要判断：目标分差可信，gold静态合理；P2P缺少相关负对照，需窄实验区分“实际可骗过”和“静态可能漏测”。历史新增的跨题/全仓/旧运行线索只作为暴露记录，未当独立证据。优先CPU建议未运行，原评分、gold、测试和来源资料均未修改；reviewer尚未读取。
