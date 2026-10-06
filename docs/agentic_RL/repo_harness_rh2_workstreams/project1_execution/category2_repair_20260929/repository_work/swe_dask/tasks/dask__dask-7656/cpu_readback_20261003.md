# Dask7656：cpu-c 实际 actor 与私有诊断读回

2026-10-03，题主执行并读回。**公开 actor 条件及四候选私有测试符合预期；仍等待修订材料正式发布和评分，尚未提交模型探针。** 本文是作者运行报告，不是非作者验收报告。

实际作业为 `dask7656-diagnostic-cpu-c-20261003-v2-q01`，经 `cpu_slot.py --mode run` 在 cpu-c 完成；每个容器 2 CPU / 4 GiB，候选串行。宿主用 `runtime_cpu_v2`，执行源码固定在 `cat2-cpu-r2e064065-swe5-20261003-v1`，manifest SHA 为 `282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f`。本次再次校验该发布的成员。它只含原 SWE 材料，不代表本题新测试已正式登记。

准备输入快照 `cd9e9b527da778bd` 的 22 文件逐 SHA 读回一致。新测试 SHA 为 `d3b711c9eb53cbdb6477314eae82f3ae5ca49e5c052a352c7da3959289c287db`，候选沿用现行矩阵的原件。运行辅助脚本 SHA 为 `b252ac81904fadafd32ef6b6161e2071223aaa389e0c6a575ffa5ec0a885e27b`；它只串接冻结的 prepare、devcheck 和 private_behavior，不改变共享源码。启动器首次因误读快照清单文件名而在启动前停止，原件保留，未开始 actor 或测试；成功作业使用新尝试 ID。

## 实际公开 actor

使用真实 Claude Code 2.1.205 和脚本桩端点，**没有基座模型推理**。公开 prompt 为原 public_hints 加原 problem_statement；首条实际请求中的题面与原字节一致。已知公开 Fix 提示仍需在题目用途和后续模型结果中注明。

| 命令 | 实际结果与含义 |
| --- | --- |
| 身份、HEAD、导入 | UID54321，工作区 `/testbed`；HEAD 为 `07d5ad0ab1bc8903554b37453f02cc8024460f2a` 且初态干净；源码从 `/testbed/dask` 导入 |
| 原题面例子 | rc1，准确触发缺失 `primary_key` 的 AttributeError，复现未修复问题 |
| 默认对象与嵌套公开控制 | rc1，同样在第一个对象建图时失败；本次不能声称后面的嵌套分支已经执行 |
| 原公开回归 | 3 passed、49 deselected，未注入新私有测试 |
| 配方生效 | Python3.9.19、pandas1.3.5、pytest8.3.2；正式激活读取 conda hook，stdlib distutils 生效 |

启动前及激活检查均 `ok=true`，实际 cgroup 为 2 CPU、4 GiB、swap0、pids512；activation 文件 agent 不可写。容器没有宿主 bind mount，私有测试、候选和预期只进入后面的独立 root 诊断容器。harness rc0，日志完整，本次容器、网络、桩清理确认，无残留。

通用启动检查里的 `interpreter_in_tool_result` 和 `bashenv_denied_for_agent` 为 false，原因是本题命令没有打印它们要求的固定标记，不能将这两项泛用标记说成通过；实际解释器路径和 activation 写权限分别由本题 identity 命令及正式启动前检查确认。

## 新测试的私有行为对照

每份候选用干净 actor 配方镜像独立执行完整 `dask/tests/test_delayed.py`。只将 Start/End 标记内的 pytest 输出交给冻结 Dask parser，逐个核 1 F2P + 48 P2P。私有 root 身份不等于正式评分身份；下表的接受／拒绝是测试行为，**不是 reward**。

| 候选 | 私有行为 | 全文件 pytest | 实际拒绝点 |
| --- | --- | --- | --- |
| noop | 拒绝 | 1 failed、49 passed、2 xfailed | 缺失未初始化字段 `b`，未进入新类型断言 |
| gold | 接受 | 50 passed、2 xfailed | 类型、默认值和嵌套控制均执行通过 |
| wrong_result_type | 拒绝 | 1 failed、49 passed、2 xfailed | 被调用函数内 `isinstance` 断言，实际输入为 `namespace(a=3)` |
| opaque | 拒绝 | 1 failed、49 passed、2 xfailed | 原类检查通过；字段仍是 Delayed，比较值触发 Truth of Delayed TypeError |

四候选均有全部 49 个参考状态，48 个原 P2P 均 PASSED，参考缺席与 P2P 失败为 0。全文件还包含不在正式参考中的测试，所以上表 pytest 总数不等于参考数。所有候选准备成功且只改生产文件；测试补丁随后独立应用。每次容器 rm 和清理查询均 rc0，无残留。

两层镜像基础层、历史 base ID 和 pandas wheel SHA 一致，actor 干净 HEAD 已确认；`pip check` 仍有历史 distributed/fastparquet/xarray/chest 冲突。实际本题导入、公开窄回归与完整私有测试已经运行，结果只覆盖这些路径，不证明全部依赖可用。

## 证据和下一步

完整原件位于忽略目录 `runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7656-cpu-c-20261003-v2/remote/`；67 文件、304405 字节逐 SHA 下载，清单为该目录的 `readback_manifest.json`。逐参考状态在 `run/status.json`，actor 题面交付原件在 `run/actor/stub/requests/messages_000.json`，逐候选完整输出在 `run/private/<candidate>/<candidate>/revised_test_file.out`。

材料[非作者静态窄核](../../reviews/non_author_7656_9378_7138_material_review_20261003.md)已通过，未覆盖本轮动态结果。剩余为共用发布者绑定本修订、以正式非 root 身份及 setup900 配方评分 0/1/0/0、核实际参考和拒绝点、非作者结果核查，然后逐题提交统一探针线程。
