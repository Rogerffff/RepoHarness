# 240d 首轮：端口修复通过与最终语法破坏分开记录

整理：2026-10-03，Asia/Singapore。固定请求 `aiohttp240d-r082084-probe-wide-v1-20261003`，题面082、隐藏083／expected084的33键、中性brief和 `probe-wide-v1`。两个模型各一次正常结束并清理。Qwen原完整候选33/33通过；Coder早期端口修复通过，但最终撤回兼容预置后不能导入。原评分 `failed_to_grade / test_log_parse_failed / null` 保持，33参考均未执行，不改成0。

| 项目 | qwen36-a1 | coder-a1 |
| --- | --- | --- |
| 原始正式结果 | reward1，33 PASSED／33键 | reward=null，收集0／1 error |
| 原候选 | 仅connector，1项 | client／connector／server／worker与2脚本，6项 |
| 生成请求／工具调用／CC回合 | 19／19／20 | 26／25／26 |
| 累计输入／输出 token | 554,448／4,687 | 728,626／5,209 |
| solver 用时 | 38.170秒 | 55.654秒 |
| CC API／CC总用时 | 31.541／34.992秒 | 48.143／52.307秒 |
| 环境 trusted_init，solver外 | 8.193秒 | 8.560秒 |
| 正式评分用时 | 10.261秒 | 10.847秒；未执行参考测试 |

计数采用各自原件口径；token为累计，不是峰值上下文。API不是纯模型计算，CC差额不是纯工具时间；没有足够调度时间戳计算GPU模型作业排队。环境与评分单列，不把report的grading queue_wait=0解释成整条GPU队列无等待。

## 端口定位与验证

Qwen从真实 `ClientRequest` 的host和port及 `ProxyConnector._create_connection` 定位到重建absolute URI时只使用host。第6轮运行正式公开复现，实际path丢1234；第7、9轮修改host/port构造并导入HTTP_PORT，默认HTTP80省略、其它端口保留；第10轮实际1234路径正确，第11轮公开ProxyConnector13测通过，正式33键全部匹配。候选没有修改CONNECT后续端口追加逻辑，也没有硬编码示例端口。

Qwen随后对HTTP1234、显式80、隐式80的真实connect检查通过；HTTPS测试进入旧client发送路径，碰到预置 `create_task(..., loop=...)` 的TypeError。整份公开connector测试另有旧TCP／Unix两项失败；这两项本轮评分已按既定CPU修订删除，模型这里没有修改测试。

Qwen第15轮试图用 `git stash` 对照，连同预置兼容修改一起暂存，纯旧HEAD因此报client.py:140 SyntaxError。这个过程没有证明原TCP／Unix两项在兼容初态的具体失败原因。第16轮 `stash pop` 恢复全部预置及修法，第18轮最终公开1234复現重新通过；最后Frozen只包含connector。记录实际恢复，不把stash对照误称有效baseline实验。

Coder先读client／server／worker，再定位connector；第11轮真实公开复現丢1234，第12轮增加按HTTP80／HTTPS443默认规则构造host/port的修法，第13轮目标通过、第14轮公开13测通过。第15轮全connector仍有上述旧TCP／Unix失败。

第17轮Coder自制HTTPS测试也遇到旧 `create_task(loop=...)` TypeError，随后把辅助脚本改成手动复制port表达式并打印通过。手算表达式没有走真实 `connect()`，不能计为HTTPS链路通过。第20轮真实HTTP1234复現仍通过，支持那时的目标修法。

## 最终撤回与归因

第21轮Git diff显示solver开工前已有兼容预置。第22轮Coder实际执行：

```bash
git checkout -- aiohttp/client.py aiohttp/server.py aiohttp/worker.py
```

工具请求在trajectory267行、成功结果在271行。三个文件共四处从 `asyncio.create_task` 回退到 `asyncio.async`；client.py为140和512行。第24轮原复現已SyntaxError，第25轮公开test_connect也收集失败；它最终仍说环境问题存在但自己已修好。早期通过的验证不能代表最终交付。

题主核全部58个baseline条目、6项最终原内容与投影；actor baseline、Frozen、完整grader日志同源且指向同一client.py:140语法错误。Qwen在同基线恢复后能完整评分，Coder在冻结前就自身复现错误，未发现候选关键字节被运输改写。Git dirty兼容预置是实际误判诱因，但不推翻候选操作导致最终破坏的归因。其它三个语法回退是字节证据，不虚构grader逐一执行到它们。

原正式自动分类因qualification缺席仍是unattributed/null。另记有证据的正常结束后候选失败，不补资格、不清理原候选、不删helper、不把33个缺席参考写成33 FAILED，不重解或重判求通过。

## 工具、并行与边界

Qwen使用Read7／Bash10／Edit2，有1个同轮双Read批次；Coder使用Read7／Bash14／Write3／Edit1，无同轮多工具请求。工具错误标志还包括目标初态断言、旧HTTPS API限制、旧公开测试失败及模型撤回后的语法错误，不能全算基础设施失败。独立阅读与独立URL复現可并行，修法／复验／恢复有依赖；没有完整工具起止时间，不判真实重叠或稳定能力。

当前接受Qwen典型HTTP端口行为和既定33参考的探索性结果；不称所有URL形式、实际HTTPS隧道、全仓client/server或IPv6都恢复。HTTPS旧API限制在两侧实际扩展测试中出现，仍属于已经说明的旧路径兼容边界；没有为了这些超出已验开发路径的尝试热改环境。Coder恢复兼容后的假想候选是否33/33，本条记录没有答案，不制造成绩。

Qwen作业来自Q11，runtime按固定code_v4/入口链SHA及GPU服务证据外部关联；原空code_snapshot_id、有限资源采样和输入config_only限制保留。每模型仅一次，同条件第二阶段重复待统一安排。训练／留出资格未授，aiohttp整仓划分；本轮没有新增CPU求解／评分。

机器记录见 [首轮行为](trajectory_analysis240d_20261003.json)、[Qwen题主核收](results240d_qwen36_a1_20261003.json)、[Coder候选失败](results240d_coder_a1_20261003.json)。
