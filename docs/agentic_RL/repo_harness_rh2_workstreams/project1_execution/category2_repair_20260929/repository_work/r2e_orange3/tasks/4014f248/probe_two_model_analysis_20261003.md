# Orange4014：两模型首轮语义与行为分析

2026-10-03。**两模型首轮执行已齐备：Qwen正式1（27/27）且语义受支持；Coder正式0（26/27），属于正常结束后的有效求解失败。作者确认Coder漏修公开要求，不是验收新增过严，也不是原生构建或评分基础设施异常；待新增非作者语义/行为窄核。** 本次只读原补丁、轨迹及评分，无新实验，不重试有效失败。Qwen的[已封首轮分析](probe_qwen_first_analysis_20261003.md)与[独立接收收据](probe_qwen_first_owner_acceptance_20261003.json)按原范围复用，不回写其生成时Coder待执行状态。

## 1．修法与验收边界

Coder最终只改`Discretizer.create_discretized_var`。它把输入`points`复制成`lpoints`，排序并以`abs(point-existing)<eps*10`合并，局部`lpoints`供显示名称和`BinSql`使用；构造返回变量仍为原`compute_value=cls(var, points)`。`Discretizer.__init__`把原`points`存入transform，数值转换的`np.digitize`继续读它。因此“显示不再抛assert”与“返回阈值列表唯一”没有同时完成，显示/SQL与数值转换使用了不同切点。

这是对原baseline和原FrozenPatch的源码数据流判断。实际141→145、163→167、202→206及215→219都打印返回值`[1.0,1.0000000000000004,1.0000000000000004]`，重复点仍在；不是根据raw0猜测。最终公开自测有两个显示标签，却仍有三个原阈值。按源码默认digitize规则可推出，原四个输入的编码为1/1/3/3，而显示类别仅2个：编码与类别不一致。**后者是源码推导，没有在本次新执行，也不是正式日志已经测到的第二个失败。** 单一已实测失败已足以证明漏修，不需为此补CPU。

公开题面明确取`var.compute_value.points`，要求返回`points`列表所有值互异；中性brief还要求检查实际points，不能把异常被捕获后的0退出当成功。正式hidden第57行对同一公开例比较`len(unique(points))`与`len(points)`，实际2!=3，直接对应要求。断言来自原保留范围，没有要求Cython修法、固定gold切点、强制4箱或特殊容差；不能删该断言放行此候选。Python层修复本身可以合理，只是本候选没有把统一有效阈值交给实际转换。

Qwen修改的是pyx两个返回处，按数值精确去重，实际重编并在新进程得到唯一阈值，27项正式通过。其加载路径未显式读回与无独立source-only重建的已封局限继续保留；不能借这些局限将其正确结果与Coder的可见源码漏洞混作同类。Coder没有改pyx，所以不应把“没有native rebuild”当本次失败原因。

## 2．定位与纠错

题面/brief已给模块、复现和测试入口。Coder10→14直接读Python模块，23→27读pyx，36→40读公开测试；结果相对首generation分别0.625、1.538、2.029秒。67根据62的实际AssertionError初步指出相等边界；84打印具体重复阈值。89在推导zip区间时漏列相等中间pair，经102→106逐项输出、111明确纠正，说明能修正一次局部推导。

此后反馈解读没有闭环：128→132首次Edit后，145仍打印重复列表，150就称fix works。167显示有效数值区间的格式字符串“1 - 1”，172误判显示精度为仍需修复的相同边界，176→180放宽容差至eps*10并加入临时pass；189→193删pass并排序，最终只把局部显示切点进一步合并。206和219仍打印相同重复列表，211/224分别称clean/perfect，没有追查返回值与标签不一致。读对文件和找到中点重复不等于最终定位/修复完整。

## 3．工具使用与工件

Coder24工具：3Read、5Write、13Bash、3Edit，25CC turns/25generation，26HTTP含1count_tokens。工具层错误数0；62的异常被脚本捕获、106手工assert也被内部捕获，实际输出仍说明缺陷。不能用工具RC0证明没有错误。多数命令无Qt前缀，但实际导入/测试成功；后来276使用brief的Qt命令。没有真实环境失败可据此前缀差异归因。

原FP六项：一项Python源码修改，另五项新增`debug_issue.py`、`debug_issue2.py`、`reproduce_issue.py`、`test_fix.py`、`test_issue_fix.py`，都实际投影。最后`git diff`只显示tracked源码，不代表新增脚本不存在。原执行审查的hygiene/可投影结论不抹去这些脚本。未改既有公开测试或评分控制；未观察隐藏/gold、未来Git或网络答案读取，不能排除模型先验记忆。没有证据将此漏修定为恶意绕过。

## 4．并行

全部24工具为逐次单请求，最大batch1，25次generation中最后一次无工具。Qwen该题也是串行。源码与公开测试读取、修改后独立只读检查有潜在可并行机会；本次没有成组请求，也无工具开始/结束区间，实际执行层支持和并行能力不可判断，不能推断模型不会并行。

## 5．验证质量

Coder确实复现了原异常，并在115→119做修前3个公开EqualFreq测试。228→232修后同3项通过，241→245公开全文26项通过，276→280又重复3项通过；这些原公开测试没有新增precision用例，通过不代表题面已修。254→258创建的“proper test”未检查阈值唯一性：近值案例只assert非空并打印标签；复杂案例只assert非空及`points==sorted(points)`，排序不保证唯一，注释称unique也不能代替断言。263→267运行两函数输出All tests passed，但没有测到目标条件。

原正式评分完整collected27、26PASS/1FAIL、testRC1、无missing/unexpected，唯一失败`TestEqualFreq.test_below_precision`在57。该方法在此停止，因此66的另一分支、78混合值与90小量级四组断言在这份Coder日志**尚未执行**，不能称它们也通过或也失败。其它26项参考真实通过。installation明确SKIPPED/RC=null；wrapper执行0、harness退出0均不能替换testRC1。

最终298称阈值唯一、完整兼容、修复成功，超出了自己的输出及最终代码；26/26旧公开测试通过这一局部报告属实。Qwen此前自测与正式27/27更一致，但同样不证明全Orange回归。

## 6．完成效率与可比性

| 指标 | Coder | Qwen |
| --- | ---: | ---: |
| 正式原评分 / 参考匹配 | 0 / 26/27 | 1 / 27/27 |
| 累计输入 / 输出tokens | 558373 / 6641 | 641074 / 10290 |
| 最高单次输入 / 输出 | 28762 / 884 | 34247 / 1279 |
| CC turns / generation / 全HTTP | 25 / 25 / 26 | 27 / 27 / 28 |
| 工具总数 / 源码Edit | 24 / 3 | 26 / 1 |
| solve / CC总时长 / API秒 | 72.056 / 68.688 / 54.889 | 86.681 / 83.279 / 65.000 |
| actor trusted_init秒 | 216.601 | 203.903 |
| grader总时长 / wrapper测试秒 | 232.176 / 2.639 | 199.618 / 2.471 |
| TEST marker区间秒 | 1.577798 | 1.450 |
| 派发后整个job秒 | 560.859408 | 529.055722 |

Coder读取完整Python模块和公开测试，创建5个仓库内脚本、进行3次大段Edit、重复原例和相同3项回归。局部手工pair纠错和修前/修后检查有信息，但145/167/206/219已经提供关键重复列表，后续没有加入直接唯一性/编码一致性断言，额外时间没有解决已可见漏洞。可改进为检查被返回的实际对象并复用精确断言，避免把显示精度当数值正确性，也避免遗留调试文件。这个建议没有新执行或估算节省秒数。

累计输入重复历史，输出含模型生成文本；Qwen暴露thinking而Coder没有该块，不据此判断Coder不思考。API含服务等待与传输，工具call无timestamp，只能给首generation→结果延迟，不是纯定位/工具时间。trusted_init和grader准备与solve分列，派发前候槽未知，grader queue_wait0只限该管理器；wrapper/TEST marker/pytest正文不同口径。CC cost为元数据估算，不是自托管账单。

Qwen使用code4、Coder用code7；两臂实际镜像、prepared/host材料、expected map、评分scripts、题面/brief、求解及评分预算相同，关键entry/solve/frozen运输SHA相同。共用runtime有8项变化，本题optional prerequisite为null；不能称整棵代码一致。关联复核证明本题实际对象相同，可对修法作诊断比较；模型采样和暴露思考不同，单次耗时/token不能支持模型普遍优劣或因果架构排名。

## 7．结束分类、分母与下一步

Qwen与Coder均正常completed/end_turn/harnessRC0，有完整轨迹、原FP评分和双层清理；无预算截断/无效评分。原宽松预算196608 context、65536单响应、240回合、3小时求解，实际最高单次input为Qwen34247/Coder28762，未覆盖196K负载；CC32000metadata与实际65536分记。**正常完成率各1/1；正式成功Qwen1/1、Coder0/1；完整样本语义受支持Qwen1/1、Coder0/1。** 全部两次均留分母，没有剔除有效失败。

首轮请求已经returned，模型执行收齐不等于稳定能力。有效Coder失败不重试，不为该候选人工修补后重标原模型成功；题面/验收/共享consumer当前未发现需修订的问题。新增独立窄核完成后由当前接收收据承接，ack原结束回执并清活动指针。当前GPU未安排本题普通追加采样，不自行新发请求；后续仅依已有全批安排接续，任何新增样本另记身份，不能用重跑覆盖失败。若后续无复采计划，结论保留一次样本的局限，不自动称稳定能力。

## 原件和用途

- [aggregate_receipt](../../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/r2e-orange4014-r089-cpu-native-sysconfig-v1-20261003_two_model_v1.json)，SHA `755fc26460936e8c98d8ec35b7a45e3e1f13f071d9fa162766452172896a62b2`。
- [independent_execution_review](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/orange4014_coder_a1_execution_review_v1.json)，SHA `b157bf6388696b27eecb8567fcbce76d0c0f7990df088314e05e9218053205c8`。
- [trajectory](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange4014-coder-a1/attempt/trajectory.jsonl)，SHA `79aa421ffb4d49f6b91c455b1266361d555f73af67b58c08537187b541587c42`。
- [frozen_patch](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange4014-coder-a1/attempt/frozen/frozen_patch.json)，SHA `dfad77a2897cdbde7539bdb368423f963a19af437089a43ee99a8d97788da7fa`。
- [baseline_tar](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange4014-coder-a1/attempt/frozen/baseline.tar)，SHA `6a98b264a5025cfafdbd034355d7b65bcdc25750b72c5f05eda7abc43b9026ce`。
- [grading_report](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange4014-coder-a1/grading/report.json)，SHA `e5dbe0e9a54995cfcaa80a84610be025086080cbff978350d977ead2d09614de`。
- [closed_manifest](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-orange4014-coder-a1_closed_manifest_v1.json)，SHA `a0b8a3cfdb478ab3992c183c7049342717e7043dc571802304dfaa63f917993e`。
- [prompt](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange4014-coder-a1/solver_prompt.txt)，SHA `a277e518ddfa7fe3514c35841eebfd735358e87c032d14365aee45d92ebde53e`。
- [author_coder_evidence](../../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/orange4014_coder_first_author_evidence_v1.json)，SHA `be16a76385ecec28055fb4ccba63c4e7926c84cfab6fb1228d8d462450804b1e`。

作者实核总回执26项原件引用与Coder封闭157文件79,069,728B SHA/size，读取原FP六项源码与原baseline，逐事件索引保存完整工具输入/输出/模型文本。既有执行/身份/清理审查按范围复用，没有再次运行候选。

原baseline package lineage/material identity等null、qualification absent保持；权重来自既有固定revision/只读mount与作业前capture的操作谱系，无物理GPU权重哈希或逐POST证明；资源是有限采样、有CPU throttle，不能证明全程峰值/最低配置。first-byte1800与底层sock_read900边界不同，未触发不证明满预算承载。只支持本题材料/环境与首次方法诊断，不授予训练或留出资格。
