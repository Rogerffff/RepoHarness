# E3 / E3b 实施复核

2026-09-23 / Codex（A 线）。对象：E3 `45c67de3`、E3b `d4a11940`；旧基线 `110bbd91`。**结论：两个提交的生产实现通过本轮聚焦复核，没有发现阻塞的训练语义或生命周期回归；有一项 P2 性能证据修订，修基准与文案，不要求回退实现，不阻塞后续切片。无新 T0。**

本结论限于已批准的 I23 内部等价优化。I18 的路由来源仍未定，未将当前末轮路由方案批准为正式训练方案。原 [Brief §7–§9](../e3_routing_tape_brief_20260922.md) 及历史结果保留；下面对性能解释的修订优先于原 §8.3。

## 1. 唯一待修项：EP1 / P2，生命周期基准混入测量成本与非代表输入

**问题在收益证据，不在 compact 实现。** 原报告的 69.2→2.6 秒、6867→627 MiB 是特定合成压力条件下的读数，不能用来证明目标路由表示的实际收益；“单轮 0.54 秒，第 25 轮 5.1 秒，所以随存量出现分配器/GC 恶化”也缺乏同条件对照。

有三个可直接复现的原因：

1. [`lifecycle_bench.py:91`](../../../../../../rh2/experiments/batch6_e3_20260922/lifecycle_bench.py) 在计时前打开 `tracemalloc`，而单轮脚本没有。旧路径需要大量 Python 对象，跟踪开销明显偏向旧路径。主审用同一旧源码、8 轮增长到 8K、相同随机 int32 输入，仅改变跟踪开关，捕获合计从 **734.6 ms 变为 5295.4 ms**，最后一轮从 **132.7 ms 变为 1132.7 ms**。这不是代码变慢，是测量条件改变。
2. 同脚本第 73 行用 `randbytes` 生成整个 signed-int32 值域的数值；当前 48 层、top-8 的 Qwen3-30B-A3B 配置是 **128 个专家**（[模型配置](../../../../../../reference/miles-rh2-integration/scripts/models/qwen3-30B-A3B.py)）。实际编号范围应为 0–127。主审在本机解码 2048 个值：专家编号只引用 **128 个**不同 Python int 对象，随机 int32 引用 **2048 个**；所以随机值显著改变旧表示的分配与驻留成本。任意 int32 适合做字节等价压力测试，不适合不加说明地代表此模型的路由内存。
3. 心跳的 `await sleep(0)` 不能确保之前构造合成 response 的同步成本已经结算。主审给计时函数外增加 80 ms 准备工作、被计时函数只运行约 5 ms，原计数仍报 **89.6 ms**；等待准备阶段的心跳结算后报 **4.4 ms**。因此原 7.5 秒不能全部归给 hook。这个计时器没有进入生产代码。

证据：[小型机制反例](measurement_mechanics_probe.py)、[结果](measurement_mechanics.json)、[完整差分和测量入口](review_probe.py)、[汇总](probe_summary.json)。主审未覆盖、回写作者历史结果。

**给 Claude 的最小修改要求：**

- 将计时与内存跟踪分成不同运行；时间和心跳列明确关闭跟踪。
- 代表基准使用目标模型的专家编号范围；保留随机 int32 为单独标注的压力条件即可。
- 让心跳先结算夹具准备工作，或用独立、明确起止的心跳测量；不要把合成响应成本归到生产 hook。
- Brief §8.3 与后续汇总采用修正后的口径；撤回已证明“随 session 存量出现 GC 恶化”和实际全 run 停摆 7.5 秒的结论。原数据保留并标注条件即可，无需改写历史 evidence。
- 顺手更新 Brief 页首仍为“未实施”的状态。此项是文档同步，不增加实施闸门。

无需重跑全库、Docker 或八卡才能修这个报告；可直接复核本目录的脚本和结果。后续真实运行的吞吐与事件循环占用仍归 E5。

## 2. 修正条件后的实测：收益仍然明确

本机 Apple Silicon / CPython 3.12.13 / torch 2.13；每个版本独立进程，先导入 torch。25 轮增长到 32768 行 × 48 × 8，保留全部逐轮记录、tape、工件及两叶；编号范围 0–127，每个 token/layer 的 8 个编号不同。**下表时间全部关闭 tracemalloc，夹具准备不进入 hook 计时，心跳先结算准备阶段。** 每个形态测一次，是受控微基准，不是多并发吞吐或真实训练收益。

| 指标 | 旧 `110bbd91` | E3 `45c67de3` | E3b `d4a11940` |
| --- | ---: | ---: | ---: |
| 25 轮 hook 合计 | 4475.8 ms | 2426.6 ms | 1198.1 ms |
| 最后一轮 hook | 380.2 ms | 179.6 ms | 89.4 ms |
| hook 心跳最大延迟 | 370.3 ms | 179.4 ms | 89.4 ms |
| 两叶各自 backfill | 307.4 / 324.5 ms | 2.8 / 2.0 ms | 1.1 / 1.2 ms |
| 两叶各自投影 | 1228.7 / 995.1 ms | 18.1 / 18.3 ms | 17.0 / 16.9 ms |

**内存另起进程测量**，同规模同编号范围：25 轮捕获后 Python 可追踪存量 **1875.4 → 627.4 MiB**（旧→E3b），峰值 2083.6→755.7 MiB。该运行的时间不并入上表；存量不是总 RSS。关闭跟踪的完整基准进程峰值 RSS 分别为 4236.6 / 2638.0 / 1888.3 MiB，包含 import、夹具构造、捕获、两叶与工件等，不能归因为生产单轮峰值。

这支持保留 E3 与 E3b：逐轮捕获、逐叶投影和驻留内存都改善。也说明修正性能口径不会推翻本片工程价值。没有据此决定并发参数、上工作线程或展开 I18。

## 3. 生产代码与等价验收

| 边界 | 主审核验 |
| --- | --- |
| capture → 逐轮 store / TurnTape | 同一个不可变 bytes 被两处引用；全轮次保留。改名的维护消费者均已同步，未发现生产旧字段残留 |
| backfill → 多叶 | 元素数按字节数除以 4；前缀裁剪乘以 4；每叶独立 bytearray，PyTorch 保持 owner 引用；改变一叶及释放 hook 后，其它叶和捕获工件仍正确 |
| 投影 → canonicalize | int32 快路径保留配置轴数、引擎行数公式和工件内容；canonicalize 仍显式复制独立连续 ndarray |
| ER1 / ER2 兼容与异常 | memoryview 仍走旧 `.tolist()`；值域内 int64 接受，float/bool/超界及异常优先级保持既有口径；空、非三维、无 torch/非小端按原回退处理。hook 超界 list 的原生 struct.error 未被改成投影错误 |
| E3b 摘要 | 只有严格 base64 和四字节对齐检查成功后才走字符串直通；按 JSON 键结构拼接，无占位文本替换。原 canonical_json_digest 保留为 oracle |
| 真实包装链 | 新增用例确实走 wire → record_turn/commit → backfill → sampler-support wrapper → projection → canonicalize，核到训练侧 ndarray 和 capture 引用。HTTP、harness、容器与评分为替身，未模拟生产双线程调度 |

主审从 git 分别导出三个版本的 `rh2/src` 到临时目录，用同一解释器和固定 integration fork 各起独立进程重跑作者差分；结束自动清理临时源码，不切换共享工作区。三个输出除 `tree` 外相等，**包括 E3b 的 raw_meta_info_digest**；显式检查 canonicalize 真正执行，没有把三份同样的“unavailable”当成通过。

证据：[旧输出](differential_old.json)、[E3 输出](differential_e3.json)、[E3b 输出](differential_e3b.json)。覆盖三轮混合载荷、精确/裁剪两叶、无配置保底、13 项错误矩阵及 hook 超界反例；不声称有限测试证明任意 Python 对象等价。

依审查标准 §10.4 复用 Production Tracer 与 Falsifier 两路限定检查。前者核实生产调用和所有权；后者做额外 180 组 JSON 往返摘要、36 组数组布局/类型小对拍，未提出生产阻塞项。主审独立检查关键函数并跑上述维护测试、三版本差分和性能反例，结论不按多数票决定。

## 4. 验证、范围与停止条件

主审执行：

```sh
cd rh2
.venv/bin/python -m pytest tests/adapters/test_project_from_slime.py tests/adapters/test_slime_generate.py tests/adapters/test_e3_routing_tape_compact.py tests/adapters/test_e3b_meta_digest.py -q
# 114 passed
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" .venv/bin/python -m pytest tests/adapters_miles/test_e3_routing_tape_chain.py tests/adapters_miles/test_b2_mask_chain.py -q
# 2 passed
```

改动的两个生产文件、三个新增测试和本目录探针 ruff 通过。未重复作者双 lane 全目录、五目录全量；作者的这些结果是作者证据。本轮未跑 Docker、GPU、远端或真实 SGLang。

A–N 适用性：A/D/G 重点核 capture 到消费的所有权和真实入口；B/C/F/H 保持训练分布、拒绝语义、既定范围及事实来源，无新挡板；E 检查真实包装链与差分是否真的运行；J/K 检查字段改名、有限快慢分支与专用摘要 helper，无需新通用框架；L/M 的性能证据缺口归 EP1；N 检查既有形态与旧契约，未变更依赖或公共 schema；I 以本片验收为止，不扩到 I18、网络供应或 B 的评分。

**后续：Claude 修 EP1 的基准/文案即可，本片生产实现无需等待新用户决定，E1/E2/E4/E5 可以继续。** 真实 GPU 收益和并发占用保留在 E5。主审只写本目录审查工件、批次导航与 infra 留言；未改生产代码、维护测试、manifest、fork 或作者历史结果，未提交/push，也未发送跨任务消息。
