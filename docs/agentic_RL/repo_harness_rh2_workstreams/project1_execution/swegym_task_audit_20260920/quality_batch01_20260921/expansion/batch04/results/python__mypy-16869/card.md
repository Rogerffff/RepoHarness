# python__mypy-16869

目标：修复stubgen遇到`Generic[*_Ts]`的崩溃，保留泛型解包语义。base为`8c2ef9dde8aa`。建议列为**受限静态开发诊断候选**，保留 **needs_review / static_review**，仅作development_diagnostic；完整证据见[封存初稿](analysis_before_history.md)，旧主张核对见[delta](old_findings_delta.md)。

| 要求/旧行为 | 公开依据 | 断言与证据 | 覆盖判断 |
| --- | --- | --- | --- |
| 星号泛型类生成且不崩溃 | 原复现；普通Generic公开旧例 | 两个Py311 F2P固定`D(Generic[*Ts])`；分别解析/语义分析 | 既有RH2：noop两例均目标TypeError，gold均pass；非原`_Ts`文件CLI逐字复现 |
| 显式Unpack及object基类行为 | 公开泛型/基类逻辑和旧例 | 两Unpack P2P、两object P2P | 历史noop/gold均4/4；不保护全部共享打印器回归 |
| 接受语义等价输出 | 公开类型检查用例支持Unpack；题面无唯一pyi | 隐藏输出逐行固定`*Ts` | Unpack候选可能误拒；仅静态疑点，尚无合法候选实验证明 |

八方面已查：公开目标与提示字段；base/test/gold对应及真实初态；六参考和helper双向映射；替代实现空间；关键调用者/公开回归；安装配方与原日志；两官方测试文件恢复及源码投影；审查曝光和用途。未查真实消息、actor运行条件/可见资产、全面回归、共享评分安全、跨题关系与模型表现。题意核心清楚不等于check3渲染已验；grader成功不等于check29资产已验。

分别保留两项范围问题：F2P只用公共Ts，原名称与混合泛型未覆盖；gold仍按既有默认规则过滤`_Ts`声明，可能生成引用未声明名的草稿stub。后者与文档的私有过滤约定有关，不能直接判gold未修crash或强增新要求。

环境证据为2026-09-19的install-wave1派生镜像、Python3.12.4、离线wheel，gold六例全过、noop两失败四通过且无skip。旧“必须先加-n0”和skip当前阻断说法未获该运行支持；actor是否消费同一镜像、激活/权限仍未知。主审已见隐藏测试、gold及获准旧记录；独立复核已完成，证据判断基本一致。

**唯一优先下一步（未执行）：**实现保留语义与正确导入的Unpack候选，先核公开原例/窄回归，再对照base、gold和候选的真实RH2六例得分，区分合法等价输出误拒与候选自身错误。当前不改测试/规格，不新增文件排除。

协调者收口：采纳[独立复核](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch04/results/python__mypy-16869/review.md)的受限候选建议。六例reward只能解释固定输出与已查回归；等价输出须另核，不能直接用作正确性标签。原文件CLI走create_source_list，不要求运行时导入模块；原例base/gold检查并入上述唯一Unpack对照。无新运行，actor门仍未验。
