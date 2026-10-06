# Orange4014：两模型首轮语义与行为独立窄核

2026-10-03。**新增作者分析核查通过，未发现作者、题面、验收或共享 consumer 的必修项。Coder 是有效求解失败：只消除了标签构造时的异常，返回的 `compute_value.points` 仍重复，未满足明确公开要求。保留原 raw0 / 26/27，不重试或改标成功。** Qwen 原 raw1 / 27/27 与语义支持结论按已封独立报告范围复用。两臂各一次、均正常完成，不构成稳定能力或模型排名。

本轮只读本地 Coder 原 FrozenPatch、实际 baseline 相关源码、完整轨迹、公开题面/brief、对应固定断言、正式日志及时间原件；复用既有执行/身份/工件核验，没有重复闭合原件或 baseline 全套审计，没有候选、CPU、GPU、SSH 或新测试执行。只新增本 md/json，不改作者 sealed 文件、原评分、旧报告、请求或队列状态。

## 被审版本与复用依据

| 文件 | SHA256 |
| --- | --- |
| [作者两模型分析 md](../tasks/4014f248/probe_two_model_analysis_20261003.md) | `5ce1a9ae0a712b71e11ef78f76ed6a88b63e76b14e92972433e9f1c19eedefd2` |
| [作者两模型分析 json](../tasks/4014f248/probe_two_model_analysis_20261003.json) | `6f6c312c8e39de257be4342c3950dd2c03c0fd0a1671dd577d6574d553cd3004` |
| [双臂原总回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/r2e-orange4014-r089-cpu-native-sysconfig-v1-20261003_two_model_v1.json) | `755fc26460936e8c98d8ec35b7a45e3e1f13f071d9fa162766452172896a62b2` |
| [Coder 原执行独立报告](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/orange4014_coder_a1_execution_review_v1.json) | `b157bf6388696b27eecb8567fcbce76d0c0f7990df088314e05e9218053205c8` |
| [Qwen 原执行/语义独立报告](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/q15_orange4014_qwen36_a1_execution_semantic_review_v1.json) | `12bf75a1d0b4939886dde2bb1695b6bfcacb07a5e43cb5c1e0676652a745d613` |
| [Qwen 新增行为独立窄核](orange50_4014_qwen_first_behavior_review_20261003.json) | `ab7a413a3494a3a309fc3e65742fde58080a6b452ffafed42b45eec55c48554a` |

上述 SHA 已核。作者 JSON 的待独立状态为生成时快照，本轮另记接收结论，不回写旧文件。作者证据索引 `orange4014_coder_first_author_evidence_v1.json` SHA `be16a76385ecec28055fb4ccba63c4e7926c84cfab6fb1228d8d462450804b1e` 只作索引；决定性结论回到原源码、事件与日志。

Coder attempt 为 `gpu1003-orange4014-coder-a1`。轨迹 302 行，SHA `79aa421ffb4d49f6b91c455b1266361d555f73af67b58c08537187b541587c42`；FP SHA `dfad77a2897cdbde7539bdb368423f963a19af437089a43ee99a8d97788da7fa`。以下事件均为原 `attempt/harness/trajectory.jsonl` 一基行号，具体工具 ID、结果 SHA 和指标原件见[同名 JSON](orange4014_two_model_semantic_behavior_review_20261003.json)。

## 公开要求与唯一失败是否一致

交付的公开题面取 `points = var.compute_value.points`，明确要求这个返回列表全部互异；brief 又要求检查实际 points，不能把异常捕获脚本的零退出当成功。Coder 补丁没有满足这个要求：

- 最终源码 69–87 复制、排序并以 `eps*10` 近似去重局部 `lpoints`，89–92 用它生成标签与 `BinSql`。
- 同文件 97–98 仍创建 `compute_value=cls(var, points)`；29 把这个原列表保存为 `self.points`，40/46 的数值转换继续用原列表。
- 原工具结果 145、167、206、219 都实际打印 `[1.0, 1.0000000000000004, 1.0000000000000004]`。最后 206 的显示标签已缩为两个，但返回列表仍有三个阈值、两个唯一值。

因此不是按 raw0 反推漏洞，而是实际输出与完整数据流直接支持漏修。固定 `r2e_tests/test_1.py` SHA `ea9b779f3d1f34b31cec43a3b4fd57bf79d8bd19a25c7c4b4153d22659d72b47` 的 51–57 使用同一公开例并比较 `len(unique(points))` 与 `len(points)`；正式日志 44/45 为 `2 != 3`，源位置 57。它没有强制 Cython 修法、固定 gold 切点、四箱或特殊容差，不是新增过严边界，不能删该断言放行。

Python 层修法本身可以合理；本候选的问题是未统一标签、SQL、返回阈值和数值转换。仍保留原 `low < high` 断言且未触碰 grader，未发现恶意绕过证据，归为不完整修法及验证误读。Coder 没有修改 `.pyx`，不以未做 native rebuild 归因这次失败。

最终原 points 对公开四个输入的默认 `np.digitize` 编码可推为 `1/1/3/3`，而标签只有两个，数值与类别不能一致。**这是基于源码及已打印点集的静态推导，没有新执行，不是正式日志中的第二个失败。** 同样，`eps*10` 会合并本来互异的极近显示边界；本轮不虚构未执行的其他输入回归结果。

## Coder 七维事实与作者结论核对

1. **方法。** 原因涉及相等阈值，模型找到这一点，但三次源码 Edit 均只整理局部标签列表，未把实际转换的原点集修好。128→132（`toolu_9aeb589226e5d414`）先按 eps 去重；176→180（`toolu_25a8b9d263596f19`）放宽 eps*10 并加入临时 `pass`；189→193（`toolu_ccebf02e3dbf791e`）删除临时块并排序。最终仍是双份点集。作者关于漏修的机制判断成立，修法位置本身不被禁止。

2. **定位与纠错。** 题面/brief 已提供模块、复现与测试入口。10→14 直接读 Python 模块，23→27 读 pyx，36→40 读公开测试，不能称无提示盲定位。67 从 62 的真实异常定位到相等边界；84 打印具体重复点。89 推导 zip 时漏掉相等中间 pair，106 逐项输出后 111 纠正，确有局部纠错。但 145 仍打印重复 points，150 就称 fix works；167 的 `1 - 1` 是格式精度，172 错当作无效数值区间，随后扩大容差；206/219 再打印重复列表，211/224 称 clean/perfect，没有闭合反馈。不能把早期诊断正确写成最终定位完整。

3. **工具与工件。** 实际 24 工具：Read 3、Write 5、Bash 13、Edit 3，所有结果 `is_error=false`。62 的真实 AssertionError 被复现脚本捕获；106 手工 pair 断言也在脚本内部捕获，零工具错误不代表无缺陷。多数 pytest 命令没加 Qt 前缀，但实际导入及测试成功，没有环境失败可据此归因。原 FP 除 Python 源码外，仍包含五个新增 debug/repro/test 脚本，全部投影；289→293 的 `git diff` 只显示 tracked 源码，不能据此说工作区只改一文件。既有公开测试和评分控制未改，未见隐藏/gold、未来 Git 或网络答案读取，不能排除先验记忆，也不能推恶意绕过。

4. **并行。** 原 adapter 与 SSE 对应 25 次 generation，二十四次各单工具、一次最终无工具，最大组为 1；没有观察多工具 batch。Qwen 本题也是单工具组。缺工具起止区间，执行层支持与并行能力未知，不能说模型不会并行。可合并或并行的只读操作是建议，未测收益。

5. **验证。** 115→119 base EqualFreq 三项通过，228→232 修后三项、241→245 原公开全文 26 项、276→280 再次三项均真实通过；这些原测试没有新增 precision 用例。254→258 的自制“proper test”近值段只 assert 非空并打印标签，复杂段只 assert 非空和排序；注释称 unique 并没有唯一性断言。263→267 的 All tests passed 不证明目标条件。正式日志完整收集 27、26 PASS / 1 FAIL、test RC1、无 missing/unexpected，唯一失败在 57；同方法 66/78/90 **未到达**，不能声称也通过或也失败。installation SKIPPED/RC=null 与 wrapper/harness RC0 分列。最终 298 称阈值唯一、完整兼容及修复成功超出代码与输出；原公开 26/26 通过这一局部事实属实。

6. **效率。** 完整模块/公测读取、五个仓库内脚本、三次整段 Edit、重复原例和三轮相同三项回归耗费了操作，但没有对已打印的重复返回值加入直接唯一性或标签/编码一致性检查。手工 pair 的纠错有信息，后续把显示精度当数值精度导致错误方向上的额外工作。改进建议是追踪实际返回对象、按公开条件断言、避免留下调试文件；未执行这些建议或估算节省量。Coder 本次 solve 更短但没有满足同一要求，不能据此称解题效率更高。

7. **结束与稳定性。** 302 为 success / `end_turn` / completed，harness RC0、轨迹完整、评分有效，未见预算截断。分类为正常完成后的有效模型失败，保留分母，不重试或人工改补丁后重标原样本。两模型正常完成各 1/1；正式成功与本样本语义支持为 Qwen 1/1、Coder 0/1。各仅一次，不支持稳定性、模型普遍优劣或架构因果排名。

## 指标和比较边界

| 指标 | Coder 本轮独立核 | Qwen 已封核查复用 |
| --- | ---: | ---: |
| 原评分 / 参考匹配 | 0 / 26/27 | 1 / 27/27 |
| 累计输入 / 输出 tokens | 558373 / 6641 | 641074 / 10290 |
| 最高单次输入 / 输出 | 28762 / 884 | 34247 / 1279 |
| CC turns / generation / 全 HTTP | 25 / 25 / 26 | 27 / 27 / 28 |
| 工具 / 源码 Edit | 24 / 3 | 26 / 1 |
| solve / CC总时长 / API，秒 | 72.056 / 68.688 / 54.889 | 86.681 / 83.279 / 65.000 |
| gateway generation 请求时长之和，秒 | 54.325 | 64.337 |
| actor trusted_init，秒 | 216.601 | 203.903 |
| actor attempt 起止墙钟，秒 | 327.073998 | 328.047051 |
| grader总时长 / wrapper测试段，秒 | 232.176 / 2.639 | 199.618 / 2.471 |
| TEST marker区间，秒 | 1.577798 | 1.450 |
| 派发后 job 起止墙钟，秒 | 560.859408 | 529.055722 |

作者 Coder token、请求、工具与时间数值均独立按原响应 usage、terminal、attempt、report、marker 和 job 起止核对一致。首 generation 到 Coder 首 Read 14 为 0.624789 秒、pyx Read 27 为 1.537789 秒、公开测试 Read 40 为 2.028789 秒；base 复现 62 为 5.946789 秒，首次 Edit 132 为 26.267789 秒。都包括生成、派发、工具和返回，不是纯定位或纯工具执行时间。

累计输入包含反复发送的历史，不是上下文峰值。Qwen 暴露 thinking 块，Coder 没有该块，不据此判断 Coder 没有思考。CC API 与 gateway 请求时长包含服务等待及传输，不是纯 GPU 计算；估算 `costUSD` 不是自托管账单。环境准备和评分与 solve 分列；grader queue_wait=0 不代表派发前候槽为零，wrapper/marker/pytest 时间也不混算。两臂最高单次输入远低于 196608，未验证接近上限的长负载；CC metadata32000 与实际 HTTP65536 分记。

同题实际镜像、prepared/host 材料、expected map、评分 scripts、公开题面/brief、预算与实际 baseline 内容相同，关键 entry/solve/Frozen 运输摘要相同，按原执行复核承接。Qwen 为 code4、Coder 为 code7，共用 runtime 八项不同，本题 optional prerequisite=null；**不称整个 runtime 逐字一致**。baseline tar SHA 也不同，不把相同内容/manifest 写成同一归档字节。可以比较本题修法与可见反馈，不能据此扩大为所有运行因素一致的模型因果比较。

## 接收结论与限制

`independent_result_review_complete=true`、作者新增分析受支持、`necessary_fixes=[]`（作者/材料/consumer 范围）。Coder 候选存在明确漏修，`coder_public_requirement_satisfied=false`；这两个判断并不矛盾。保持原 0/1 评分和历史 Qwen 接收文件不变，不追加普通采样、不重试有效失败。

双臂首轮执行已 returned；本报告只记录独立语义/行为接收，ACK 与清活动指针由题主后续当前接收收据处理，本轮未操作。Qwen 的扩展路径未直接读回、未独立 source-only 重建等限制继续按其原范围保留，不套成 Coder 未改 pyx 的失败原因。

原 qualification absent、材料/环境 lineage 部分 null、有限资源采样和 CPU throttle、端点谱系而非物理 GPU 权重哈希证明、first-byte1800 与底层 sock_read900 等边界仍有效。本轮不授予训练或留出资格，不证明完整峰值、最低资源或满预算承载。
