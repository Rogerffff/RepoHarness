# DVC6954：Qwen 首臂题主语义审计

2026-10-04 SGT。作业 `gpu1003-dvc6954-qwen36-a1`，请求 `swe-dvc6954-behavior-r14-v1-20261003`，预算 `probe-wide-v1`。只读原首臂，独立语义报告与成对核收另存；未执行新模型、候选或评分。

**本轮合法负数修法正确，正式raw1，3F／12P及11个额外节点全过。** Qwen使用真实parser断言、临时DVC仓库和lock读回验证；存在未核清的扩展实验测试失败及非数字一元边界，不能将这些省略或声称全仓测试通过。

## 原件与候选

[完整原件与工具读回](qwen36_a1_owner_evidence_readback_v1.json) SHA `44887a779fe772e2bd71bc6cbd86b747d9da1d55a502472e72d534cd06eff719`：417件、36,635,646字节逐件SHA／size一致；baseline tar552条目核类型、执行位和内容。609行CC、42工具完整输入／结果和模型陈述、43份gateway／adapter响应已核。

baseline canonical SHA `be0c03047652bd7c8ac13b696722f056a7b498ca5dd3c12fceba519a642c8625`；完整FP canonical SHA `1bcd6de39c9ad447208100b8c023afd361a248beaf5f073d74a10f262639f487`。仅一项业务 `dvc/utils/serialize/_py.py`，projection相同；没有正式测试改动或根目录脚本残留。临时仓库位于/tmp，不进入FP。

## 1. 根因、修法与范围

Python负数字面量以 `UnaryOp(USub, operand)` 表示。原scalar helper不支持UnaryOp，外层忽略ValueError／AttributeError，因而负数赋值缺失。候选递归读取operand，USub执行 `-operand`，UAdd执行 `+operand`，其它一元运算抛ValueError；容器已有分支调用该helper，合法负整数、负浮点和容器元素因此生效。

26个实际节点全过：15个参考为3F／12P，另11个原有功能节点未计分。无missing／skip／无法归属，eval SHA `cecdf3e986beca2873b09f1525b2a89bc32d4494c73b0d8b3ac2edbc7842e51d`。原sum／constructor仍被忽略，不能把递归UnaryOp扩展称作完整表达式求值或任意嵌套容器支持。

候选没有数字类型限制：对字符串或None做正负号可抛TypeError，原外层不捕获该类型。这是静态范围限制，未在本轮执行为新增失败。Coder额外UAdd直接返回operand，而Qwen执行真正一元正号；合法数字行为相同，非数字边界不同。本轮冻结目标不扩非法operand规范，不因静态疑点擅改正式评分。

## 2. 定位与纠偏

工具5读dependency的LOADERS接线，工具6读错不存在的serialize.py后，通过loader搜索找到目录；工具10约4.439–4.841秒读到_py.py。工具11／12查看正负号AST，工具19重复检查Python3.9的Constant／旧Num兼容，工具21确认 `isinstance(Constant, ast.Num)` 为true，避免无依据重写常量分支。

唯一业务Edit是工具22约17.136–19.240秒；工具23立即用六个真实parser断言验证正／负整数、浮点和一元加。轨迹没有修前parse缺参复现，只有AST和源码根因证据，不把修后CLI补记成修前失败。没有错误业务修改或回滚；末段stash只为核实验测试基线，之后pop恢复原修复，最终diff和FP一致。

## 3. 工具使用

42次为Bash35、Read6、Edit1。唯一is_error是不存在路径Read；管道后的pytest失败不一定进入该标记，因此“1工具错误”不代表所有命令测试均成功。定位阶段多次广泛find／grep及重复AST枚举，可收敛为一次接线搜索和一组AST检查。

后半程依次执行六例parser断言、公开dependency20项／params show11项、真实init→repro→lock、多个参数的force repro→lock、四容器parser断言、serialize目录筛选、experiments params筛选、单项基线对照、源码／diff核对。没有安装／解释器故障。第二临时仓库只有初始化没有继续使用；重复源码读回和六例parser带来的新增信息有限。

## 4. 可观察并行行为

43个生成请求每个至多一个工具，没有实际成组工具调用或可证的后台重叠。独立源码／测试读取可批量，多组AST例子可合并；真实DVC init→文件写入→repro→lock以及stash→基线测试→pop必须保持依赖。同工作区测试可能共用缓存／状态，不能按文件数直接要求并发。

本轮较Coder多6个工具及6个生成，却solve稍短；不同模型与单次运行不支持吞吐、并行收益或稳定速度排名。效率比较应同时保留调用、token与实际验证信息。

## 5. 自测、失败与最终陈述

六个parser例子与四个容器例子使用真实 `assert result==expected`。临时Git/DVC仓库用 `PYTHONPATH=/testbed` 真CLI执行issue；工具28实际读回lock中 `my_int:-1`。工具29加负浮点／一元正数／字典负数，force repro后工具30读回lock内 `my_float:-3.14`、字典a:-10等。lock读回是可见正确值，未写自动lock断言；强制repro不是不变值跳过或修改负数后的自动依赖触发。正式新增测试的这些行为不能补写为模型自测。

公开dependency20＋params show11项通过；末段31项重复通过不能累计。serialize目录当时只有2个YAML测试，不能称为Pythonparser覆盖。工具33选择9个experiments params用例，4pass／5fail；`head -80`截断了后续堆栈／终局汇总。工具37stash后单独跑 `test_update_py_params` 仍fail，工具38恢复修复。这仅支持该单项不是此次补丁才引入；另4个YAML实验失败的完整原因和基线未核，不归为模型错误或已经证明的环境故障。

最终所称“31项在两个指定模块全过”与原输出一致，负数lock陈述有实际值支持。它没有提扩展实验失败，因此对验证过程的报告不完整；不能将准确的31项范围放大为全仓无回归。候选正确与报告遗漏同时保留，没有Coder那种把失败断言改成无断言的步骤。

## 6. 效率、身份与资源

solve56.742秒；CC duration53.119／API38.013秒；gateway响应加总37.060秒、首请求至末响应53.046秒。累计输入695,745／输出5,648 token，单次最大29,352／550。cost3.619925美元是CC估算，非实付。43请求均实际max_tokens65536、HTTP200、attempt1、SSE完整无stream error，无输出长度终止或观察到的压缩恢复；context196608／240 turns／10800秒／1024请求未见耗尽。

[双臂条件与实时capture题主读回v2](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/dvc4166_6954_pair_operational_owner_readback_v2.json) SHA `1c3f40bb23366f78c918749738d9ff54f8897e13ca29323a87f3afc9f3709922`核公共prompt原字节、baseline／镜像／HEAD一致；sandbox实际profile仅proxy18081→18082不同。Qwen作业前16:09:50 UTC实时capture核revision `995ad96eacd98c81ed38be0c5b274b04031597b0`、只读mount、engine／adapter argv与HTTP配置，BF16／TP1／context196608／max-running1。列表37文件含26权重分片逐项size一致；声明40与列表37不一致，未重新逐权重SHA或证明GPU内存权重。

grading total215.181、reset14.747、prep0.238、report test5.447秒；candidate install3.316／test1.519秒、pytest正文0.79秒，trusted setup193.954秒分别记范围，不算模型思考或纯chown。22行有限取样按各自run_id分actor6／grader14／relay6；memory.peak已采最大分别952,459,264／929,918,976／27,459,584字节，已采OOM kill和PID limit事件均0。grader采样最大小于report1017.270MiB，取样未覆盖终点，不能拿采样替代终局报告或推全生命周期／最低配置。baseline环境包digest和diagnostic resource_facts的null保持；v2只纠正v1按actor ID筛grader漏样本，原件未改。

## 7. 结束原因与用途

CC success／end_turn／completed／exit0，gateway revoke／active_requests0，actor／relay／网络和grader cleanup均true；manager创建／删除各1、无遗留或失败。UID54322 prerequisite0、install0／test0，runner摘要不变，env qualification未另跑。退出依据为原completed记录加精确PID1成功journal，不以已退役unit默认0补造退出证明。

本次为冻结合法负数行为的有效单次正确候选，验证质量与非数字范围限制分别保留。既有CPU／公开actor与Coder审查复用，新Qwen独立语义及题主成对核收另存；不在本文预先ACK。普通重复暂缓，不从双模型各一次通过推稳定性、全源饱和、训练或留出资格。
