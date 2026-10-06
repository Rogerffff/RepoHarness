# dask__dask-9378 指定history解封后的差异记录

2026-09-25，by=e25_main_dask。协调者已明确release且核验三题全部初判；本题前稿SHA256=`60adde210415e69e3cfec504986bf5d5b747eaf5dbd32ea93a70d6d43b4bea3c`保持不变。先独立核SHA再全文读取以下sources，未沿链接扩读原旧运行、其它任务、汇总或未来版本，未读reviewer。文件完整性校验不是旧主张正确性保证。

- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-9378.json`；SHA256 `49439945d350b6b1fa60865297dffe5426fd4f1ffd9387a79d47b9c451ae47d0`，匹配。
- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/dask_pilot/records/dask__dask-9378.json`；SHA256 `2ebcee39e02a6d5456251ff3b7e034e987a9293826d4d66b359936aeb033d7c0`，匹配。

路径约定与原始证据：PUBLIC=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/dask__dask-9378`；PRIVATE=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-9378`；本题[封存初判](analysis_before_history.md)§6已列精确原ledger行、log路径/hash、配方与逐测试状态。下文“旧记录记述”只代表上述历史文档的主张；“确认”需有本题公开原件或本次已核原运行支持。全部为静态阅读，无新项目运行、模型或环境实验。

## L1_dask旧主张与dask_pilot复核逐项处理

| 位置/主张 | 处理 | 本次决定性证据及限定 |
|---|---|---|
| L1 public_view、checks.1/2；pilot public_contract/base_source_evidence | 确认限定事实 | 题面提出mask-preserving新版本并点名ma路线；base ma.py无三个API；test/gold同题。noop缺ma API不能直接代替题面顶层mask丢失运行复现 |
| L1 checks.3：raw hints链接会误导；pilot纠正不可见raw hints | 确认pilot对计划输入的纠正，actual未知 | 当前public_bundle.public_hints为通用操作提示，没有raw creation.py permalink。未扩读raw字段，也未获取actual actor消息；不作实际误导/实际完整输入证明 |
| L1 checks.4/17；pilot同项 | 确认有限范围 | 非测试ma.py补丁投影、test_masked.py可信恢复；空排除规则保留，不推广一般交付安全 |
| L1 checks.5及pilot cross_task材料 | 未核实 | 不扩读旧十四题或其它任务；本次不复用唯一性、跨题关系或全池去重结论 |
| L1 checks.23/issues[0]命名空间有误并建议改题；pilot保留解释空间不直接改题 | 采纳收窄，不据历史自动确认所有合法解 | 题面末段确实提出ma API；顶层-only修复会缺新入口是结构事实，但没有具体合法完整候选执行。保留check23/24 unknown，不把示例直接改成base不存在的ma函数 |
| L1 checks.24列举其它实现“都能过”；pilot注明未执行 | 确认非唯一写法，运行断言未核实 | 新测试不查函数体/装饰器；本次未执行替代解，不把可能路径写成全P2P已过 |
| L1 checks.25称按条扣分、固定shape/mask排除硬编码、需要真正分块 | 反驳过度结论 | 固定3×2/int/固定mask无法排除硬编码；assert_eq可接受eager NumPy输出，不直接要求返回Dask Array。三项F2P诊断不是部分reward证明。本次只观察noop reward0/gold1，未独立读scorer部分完成公式 |
| pilot对固定fixture/分块过度结论的反驳 | 确认 | 本次test.patch及assert_eq实现支持；保留运行/覆盖区别 |
| L1/ pilot称ones/zeros“比较掩码数组” | 补上核心遗漏，不能据对象类型推mask equality | 本次独立初判已读 utils.py:172–177,373–374：比较最终使用np.ma.allclose(masked_equal=True)，没有逐位mask equality；只有empty显式getmaskarray。这是两份旧记录均未识别的关键check25/32疑点 |
| L1/ pilot确认empty只比较mask | 确认正确边界并保留缺口 | 规避未初始化值比较合理；但原empty返回dtype/类型与惰性无直接断言，不能以empty的良好边界掩盖ones/zeros缺口 |
| L1 checks.26与pilot“建议不等于已验证” | 确认pilot限定 | 当前无新增回归执行或已证gold新增旧行为破坏，check26 unknown |
| L1 checks.27/issues[2]：NumPy无docstring则导入崩溃；pilot反驳 | 直接反驳旧L1，并独立确认pilot | 新核读本题 base/dask/utils.py:765–774，doc is None显式置空字符串；不保留该臆测风险。不是由另一记录结论替代源码 |
| L1 checks.29、pilot：题面路线暴露 | 确认公开路线，重分类 | 题面map_blocks+ma是授权公开辅助，不等于hidden gold泄漏；actual actor目录/消息未取，check29 unknown，审查私有历史暴露在usage |
| L1 checks.6/7/11/9；pilot environment_evidence | 确认本次已经核过的原RH2限定事实 | 同一baseline01 w01-1 ledger11/12、日志hash，Python3.10.14/pytest8.3.2，安装RC0；noop3失败134通过，gold137通过。不是维修派生镜像；实际image ID仍null；不比较其它题所谓“最干净” |
| L1 proposed_regression_tests | 部分保留/纠正ID精度 | masked构造/tokenize是相关P2P；顶层对应本base实际公开测试为test_arr_like/test_arr_like_shape，并非旧记录列的三个test_ones_like等独立名称。范围按是否改creation决定，不硬要求全仓 |
| L1 ready_for_probe；pilot probe_candidate、next_action优先模型观察namespace | 收窄并改变优先级 | 有未核actor条件和核心mask断言缺口，本次state=needs_review/static_review。先定向查错mask是否漏放，比模型选择namespace更直接；不按旧状态自动派发模型或CPU |
| pilot validation_limits、quality_certified=false | 确认方法限制，不当结果保证 | 历史记录自己限制为静态非认证；本次同样不执行。旧流程合规不能证明本次无漏检/误杀或抽样偏差 |
| 旧costs/跨任务汇总数字 | 不移植 | 非本轮成本或授权范围；本轮未观测值为null |

## 对本人封存初判的具体修正

新补读本题 `base/dask/utils.py:564–571,740–751,755–812,815–869` 后，收窄初判§3/5的dtype参数风险：`get_named_args` 排除 **kwargs，`_derived_from` 找出NumPy存在而wrapper未显式声明的参数，`unsupported_arguments` 会在有对应文档参数行时标记“Not supported in Dask”。因此，虽然dtype被map_blocks消费、不传内核的静态机制仍存在，但不能仅因gold签名接受**kwargs，就认定dtype是承诺支持的公开参数，更不能把它直接作为gold违反题意的证据。当前未读取安装NumPy的实际签名/docstring，也未运行生成docstring，具体哪些参数显示该标记仍unknown。 还需注意 `_derived_from` 的参数枚举在 `inspect.signature` 抛 ValueError 时会跳过；NumPy包装器若只暴露 **kwargs，也不会枚举出dtype。helper具备机制不等于gold在该环境必有该标记。后稿将其降为支持范围说明，不作为优先CPU疑点。

这不改变独立发现的核心mask断言问题：ones/zeros保留逐元素mask是题面明示；对该要求缺少直接比较不依赖dtype或其它额外参数的契约。静态推理提出保留shape/dtype/MaskedArray类型、仅改错mask的错误解类别，尚未执行mutation，不写“已证满分漏放”。

前稿哈希不变；修正只在本delta/card/record体现。唯一优先下一步为任务二的私有错mask断言诊断，对照显式getmaskarray比较并保存RC/逐项状态。本审查不执行、不派发，actual actor公开流程验证仍是将来准入的必要证据而非本次已通过事实。
