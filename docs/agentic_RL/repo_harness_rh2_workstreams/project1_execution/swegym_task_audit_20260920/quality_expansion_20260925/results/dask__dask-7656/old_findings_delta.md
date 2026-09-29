# dask__dask-7656 指定history解封后的差异记录

2026-09-25，by=e25_main_dask。协调者已明确release且核验三题全部初判；本题前稿SHA256=`237f904308a75fe658fa1d20d03af08e5ba3e3e139e7f6ae47ded040b8dcc668`保持不变。先独立核SHA再全文读取以下sources，未沿链接扩读原旧运行、其它任务、汇总或未来版本，未读reviewer。文件完整性校验不是旧主张正确性保证。

- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-7656.json`；SHA256 `dbe2c8ee153fe1c06e2bc4b014a08efd6e7ae7b4e0146a14ce83115ce135d46c`，匹配。

路径约定与原始证据：PUBLIC=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-7656`；PRIVATE=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-7656`；本题[封存初判](analysis_before_history.md)§6已列精确原ledger行、log路径/hash、配方与逐测试状态。下文“旧记录记述”只代表上述历史文档的主张；“确认”需有本题公开原件或本次已核原运行支持。全部为静态阅读，无新项目运行、模型或环境实验。

## 旧主张逐项处理

| 旧记录位置/主张 | 处理 | 本次决定性证据及限定 |
|---|---|---|
| public_view、checks.1/2：缺失init=False字段被无条件getattr | 确认 | PUBLIC题面、delayed.py:110–115、原compat_v2b noop AttributeError b；gold对应非测试源码补丁 |
| checks.3/29、issues[3]：题面自带field.init or hasattr修复片段 | 确认公开内容，纠正“actual泄漏”标签 | 题面Fix段确有路线及代码；属于来源公开提示，可记录辅助强度和用途。actual actor是否看到该题面及额外私有答案仍unknown；不将审查授权gold暴露混入check29 |
| checks.3/29：raw hints为空 | 未独立核实 | 未扩读raw原行；不需要它来确认当前public内容，也不能据它保证actor没有其它输入 |
| checks.4/17：测试源码边界及空排除规则 | 确认有限范围 | gold仅delayed.py、test.patch仅test_delayed.py；原gold投影和可信恢复日志成立，不推广任意交付形状 |
| checks.5：与另一题后续base含本题gold，应训练评测同侧 | 未核实 | 本次只可读本题记录，未读另一题base/补丁/assignments。旧记录提供关系线索但不足以重新确认具体派生或留出重叠；不按共用文件机械设划分政策 |
| checks.23：F2P公开可推 | 确认 | 缺失b与a=delayed(3)最终求值都有公开缺失属性目标和旧同名测试依据；不限制hasattr具体写法 |
| checks.24及候选oracle=RESOLVED_FULL | 未独立核实运行；语义问题收窄 | 旧记录声称DeepSeek用if f.init并通过；限定release不含该candidate.diff/oracle原件，不沿链接扩读，所以不作为本轮已核模型或替代解执行证据 |
| checks.24、issues[1]：“gold保留已赋值init=False，if f.init丢数据；post_init案例可证明前者过后者败” | 反驳其必然性 | gold仍生成 `(apply,typ,(),(dict,args))`，utils.py:32–36直接func(**kwargs)，不是构造后恢复属性。标准dataclass init=False属性虽存在却不接受为__init__参数；gold可能TypeError。仅按init字段重建反而会再执行post_init，不能推断它必丢该派生值。该旧实验预期不能当已知正确oracle，需先界定状态语义 |
| checks.25、issues[0]：第二处to_task_dask dataclass修复没覆盖 | 确认结构，收窄“错误半修复” | F2P走当前unpack_collections；P2P test_to_task_dask:44–83没有dataclass。只改当前路径可能过评分，但gold多改一处不是公开必须修两处的规格依据；属于check25边界覆盖，而非已证错误解 |
| checks.26：提出回归即可pass | 不接受证明强度 | 本次无新增回归执行，未证gold新增旧行为回归；check26 unknown |
| checks.27、issues[2]：base.py公共compute/persist还会读缺失字段 | 确认静态遗漏，限制任务范围 | base.py:424–436仍无条件getattr且gold未动。原题明说delayed调用；更广compute路径是邻接既有问题，不直接否定窄目标gold，也不是已证新增回归。旧“候选主动补所以不是理论风险”不构成运行证明 |
| checks.6/7/11/9：安装、无skip与noop/gold对照 | 用本次可核原运行确认限定事实 | compat_v2b实际Python3.9.19/pytest8.3.2，离线pandas1.3.5 + SETUPTOOLS_USE_DISTUTILS=stdlib，安装RC0；noop1失败49通过2xfail、gold50通过2xfail；expected F2P1/P2P48均对应，不继承旧stage1环境为actor资格 |
| proposed_regression_tests：base公共遍历、to_task_dask分支 | 部分保留 | 公开test_base.py::test_unpack_collections主体存在并已读，是否加本题验收需明确范围；post_init“区分两个候选”的预定方向如上不成立，不机械加测试 |
| disposition_hint：“训练样本可用、正确性评测需补P2P” | 收窄 | 可作为有公开修复提示的development_diagnostic静态候选；无actual actor证据，不作训练/正式评测批准，也不以补任一P2P自动准入 |
| costs.minutes=28 | 不沿用 | 非本轮成本；本轮未执行项目或模型，未观测量填null |

## 对已封存初判的影响

初判已有“init=False已有值传构造kwargs可能TypeError”和“未读替代解运行”的限制，历史没有推翻它。后稿明确拒绝旧记录把gold当post_init oracle的假定；这使建议更保守、更贴近公开目标，不需要修改前稿。公开Fix片段应影响用途解读：本题可观察把公开线索应用到实际base的能力，不能作为纯独立定位能力证据；不能凭此直接称低难度或已污染模型。

唯一优先下一步不变：任务二实际actor原题Entry→delayed→compute，同时检查other_field默认值与嵌套字段求值，记录真实消息/初态/解释器/身份/RC。当前没有新的私有变体证据足以取代该公开流程验证；不执行、派发或创建后续任务。
