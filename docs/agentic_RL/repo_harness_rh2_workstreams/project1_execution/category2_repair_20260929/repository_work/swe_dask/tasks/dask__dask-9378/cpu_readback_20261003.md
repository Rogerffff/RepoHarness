# Dask9378：按 B 规格的实际 CPU 读回

2026-10-03，题主执行并读回。**真实公开 actor 与六候选私有对照符合 B 规格，等待修订材料正式评分及非作者结果核查。** 本文是作者运行报告，不授予模型探针或训练资格。

原镜像以固定 digest 拉取，实际 ID 为 `sha256:1e5a0ee850161b35d33d26445f73e872488a45e0e436195af239190b68574096`，与 manifest `sha256:d59dc8d2aa23abc26c301754af4623f7bbad5d798713a6c5caa2d2113b6691b1` 对应。HEAD 是 `8b95f983c232c1bd628e9cba0695d3ef229d290b`，初态干净，不改依赖。准备输入快照 `9a984c4ce36a871a` 的 17 文件逐 SHA 一致，修订测试 SHA 仍为 `9fc1a9d5ae885d9cc30388a875ab7ed629081de7ba7bdcc8571f3aca604a248a`。

镜像准备用已经在途的初版 source 完成；新 actor/私有作业绑定已部署第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest SHA `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，再次校验发布成员。它含已审 Git 修复，**还没有登记本题新测试**。本包辅助脚本 SHA 为 `0428357fca1fcfa24b947709e0c788d962bf006abc826cb8b4adb617214bb0ff`，只编排冻结的 prepare/devcheck/private_behavior，不改共用源码。

## 原公开 actor 条件

实际作业 `dask9378-diagnostic-cpu-c-20261003-v1-q01` 经统一 run 槽完成，容器 2 CPU / 4 GiB，UID54321；真实 Claude Code 2.1.205 配脚本桩，**无基座模型推理**。原 public_hints 和题面进入首条实际请求，problem_statement 字节一致。

身份和 `/testbed/dask` 导入通过；Python3.10.14、NumPy1.26.4、SciPy1.14.1、pytest8.3.2。原题面输出实际是 `[1 1 1]`，NumPy 为 `[1 1 --]`，base 最后位置 mask 丢失，公开复现的 rc1 正好来自该差异。原公开 masked 模块 134 passed，creation 模块 `-k arr_like` 为 320 passed、394 deselected，未应用私有新测试。

启动前与激活检查均通过，绑定挂载为空，activation 写权限被拒，解释器前缀正确；harness rc0、日志完整、容器和网络无残留。泛用启动报告中两个固定标记检查为 false，是本题命令未打印这些标记；实际身份/激活/权限用对应原件核实，不将泛用标记说成通过。

## 私有测试对照

每候选用独立干净 root 容器，生产补丁及新测试分开应用，串行执行完整 `test_masked.py`。只解析 Start/End 内输出，3 F2P + 134 P2P 逐 ID 核对，**下表不是正式 reward**。

| 候选 | 新测试私有行为 | pytest | 拒绝点／接受范围 |
| --- | --- | --- | --- |
| noop | 拒绝 | 3 failed、134 passed | 顶层三种输出都丢 mask |
| gold | 接受 | 137 passed | `da.ma` 三种入口的 mask 和相应值正确；不声称顶层入口也已修复 |
| toplevel_only | 接受 | 137 passed | 不新增 `da.ma` 入口，正确顶层路线被 B 规格接受 |
| ma_mask_none | 拒绝 | 2 failed、135 passed | ones/zeros 的新增 mask 比较；empty mask 控制通过 |
| ma_mask_invert | 拒绝 | 2 failed、135 passed | ones/zeros 的新增 mask 比较；empty mask 控制通过 |
| wrong_values_seven | 拒绝 | 2 failed、135 passed | mask 比较通过，未屏蔽的 ones/zeros 值比较失败 |

每份均有全部 137 个参考，134 P2P 全 PASSED，参考缺席为 0，准备／测试确实执行；每个独立容器移除和查询 rc0，无残留。这个结果同时核了两条合理路线，不能用只接受 gold 的旧强制 ma 版本代替。本轮没有增加惰性、empty 未初始化数值等新要求。

## 证据与剩余

忽略证据根 `runs/category2_repair_20260929/swe_dask/` 下，镜像准备的 `image_preparation/dask9378-cpu-c-20261003-v1/remote/` 有 18 文件、12080 字节；实际运行的 `cpu_diagnostics/dask9378-cpu-c-20261003-v1/remote/` 有 79 文件、555773 字节，均逐 SHA 下载并有 `readback_manifest.json`。运行目录 `run/status.json` 保留全部逐参考状态，`run/actor/` 保留 prompt 请求及命令原件，`run/private/<candidate>/<candidate>/revised_test_file.out` 保留每份完整测试输出。

材料[非作者静态窄核](../../reviews/non_author_7656_9378_7138_material_review_20261003.md)已经通过。仍需共用发布者提供本修订正式版本，以可信非 root 身份正式核 0/1/1/0/0/0 及逐参考状态，完成实际结果独立核查后，逐题提交统一 GPU 队列。所有新正式 reward 字段继续为 null。
