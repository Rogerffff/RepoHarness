# 固定入口的公开 actor 与私有行为诊断

2026-10-03。这是已登记原材料的诊断，不运行或评分尚未登记的两题新增F2P。代码取首份不可变发布 `cat2-cpu-r2e064065-swe5-20261003-v1`，外部manifest摘要为 `282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f`；794个文件及48 R2E／216 SWE可信回读已核。

当前事实与证据路径见 [actor_results.json](actor_results.json)。6283首个实际attempt使用旧宿主runtime，宿主导入链报 `No module named 'torch'`。模型请求数为0，三条公开命令全部未运行；容器、网络、relay清理完成并复查零残留。这是基础设施失败，没有题目0分或模型结果。原输出不回写。

总协调已另发布 `runtime_cpu_v2`。本包保留旧输入快照，新增 `diagnostics_v1/inputs_v3` 并逐项校验四个文件SHA，新job使用新解释器。**6283／5662均已完成实际公开actor诊断**：每题四个桩请求、三条命令全部执行；UID54321、Python3.8、core分别0.42.0／0.27.0、源码SHA及可写性断言通过。两个原题面示例按已知基线问题失败在明确目标断言，已有公开测试分别为41passed／3xfailed和7passed。CC正常返回，2 CPU／4 GiB实际容器参数吻合，日志完整及零残留清理已核。

[run_actor.py](run_actor.py)调用冻结的SWE `devcheck.py`，2 CPU／4 GiB、原超时与收尾由该runner负责；整个进程由 `cpu_slot.py --mode run` 持锁。actor只使用原基础镜像、受信loader导出的公开bundle和公开命令，不挂载宿主release或私有修订目录。准备摘要在远端重新生成，未复用本地绝对路径。

提示来自公开bundle的原题面与原 `public_hints`，显式传入原入口并在首个桩请求核对；不能以默认控制提示证明公开交付。公开命令仅做UID/Python/core/源码与可写性核对、原题面示例复现和现有公开测试。gold、新私有断言和错误候选没有进入这些输入；完整题级验收仍须新consumer与正式CPU矩阵。

验证范围是上述公开诊断，不是全套startup验收。未执行BASH_ENV专用写入拒绝探针；原 `checks` 中该项False及未采用默认解释器输出标记产生的False保持原样。解释器身份另由 `public_identity` 的独立断言与PY_CHECK日志核实。没有导出FrozenPatch或比较完整baseline，不将本诊断冒作完整候选运输／基线稳定性验证。

本包固定在cpu-a，最终预留gateway18194／stub18195；本SWE devcheck直接使用stub18195，串行复用，未启动gateway或占用旧183xx。先查镜像缓存与端口，避免run槽隐式拉镜像或接入他人端点。另见[CPU资源页](../../../cpu_resources_20261003.md)：遇完整Git baseline同类差异时保留工件并停止，不忽略excluded摘要，不改绑baseline。第五版包含已审共同Git修复；GPU实际派发状态以统一探针线程记录为准，不从本包诊断推定。

## 私有安装与新增行为诊断

后续新作业绑定第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`（外部manifest `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`）及 `runtime_cpu_v2`。[run_private.py](run_private.py)先验证837个发布成员、确认镜像已缓存，再在本机新输出目录生成原受信材料的prepared身份；该prepared仅用于确认原题身份，不冒称已激活新断言。

真正的安装／行为调用使用冻结 `private_behavior.py`（SHA `379c4610b19aafa829fcf7967ad95d0ac9f5374c9e85f16c0b62a01a25cbb7bc`），全部私有输入仅复制进root诊断容器。每个候选独立容器，2 CPU／4 GiB／PID512、断网、无宿主挂载；整个矩阵在统一作业槽内串行运行。按顺序记录reset、base文件身份、候选应用、editable安装、从候选pyproject导出testing/testing-extra、测试依赖安装、实际解释器/core/源码哈希、测试补丁应用和非空收集的退出；预备步骤失败立即停止。实际cgroup值也由容器内断言核实。

**8511的三个候选已完成这一私有轮。** 每份安装与收集均为0，实际Python3.8.19／core2.14.5／`/testbed`源码导入正确。所选五项为原F2P及新增四项P2P：noop仅原F2P失败；gold原F2P及默认repr通过，但三类继承在创建子类时准确报 `TypeError: 'x' is a field but has no type annotation`；narrow五项全过。三个自有容器删除与查询均为0、剩余列表为空。这关闭了本轮私有安装执行的疑问，**不替代173项正式参考、正式安装consumer或非作者CPU核查**。

**8567的五个候选也已完成私有轮。** 实际Python3.8.19／core2.15.0／`/testbed`源码身份、2 CPU／4 GiB／PID512正确；五份安装与非空收集退出均为0，五个容器均零残留。运行原v4 F2P及新增B03／B06／N3，共四个节点；noop仅两项F2P失败、两个P2P通过，gold四项失败，upstream261原v4通过但三项新增均失败；c3_reorder和ok_post_attach四项全过。后两者因此获得本轮针对性行为支持，**仍需完整162参考及正式consumer验收才能认定完整正对照**。

8511／8567的固定输入见 [private_inputs.json](private_inputs.json)；运行与逐节点结果见 [private_results.json](private_results.json)。本轮只执行八份固定候选的五／四个节点，不重跑旧74或8567旧31格；没有FrozenPatch导出、完整baseline比较、正式reward、actor权限验收或模型探针。运行结果仍待非作者核查。
