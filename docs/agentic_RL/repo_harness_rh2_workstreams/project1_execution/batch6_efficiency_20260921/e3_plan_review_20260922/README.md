# E3 Brief 聚焦复核

2026-09-22 / Codex（A 线）。对象：[E3 Brief](../e3_routing_tape_brief_20260922.md)，受审代码基线：主仓库 `110bbd91`（代码提交 `0b5a5189`）。**结论：主方案可以推进；下列兼容边界与验收修订并入 Brief 后实施，不增加用户决策。** 本次是计划复核，尚不存在可验收的 E3 生产实现。

## 1. 对四个问题的明确答复

| 问题 | 复核意见 | 理由与边界 |
| --- | --- | --- |
| 是否允许改 `adapters/slime/projection.py`，三个方案选哪个 | **采用主方案，接受本片窄偏离** | 这是 RH2 自有投影模块，非 `rh2/src/slime/` vendored 源码。已批 I23 允许无损内部表示优化；此处是实际热点。不应为了文件零改动增加代理与第二套输入形态；旧输入接受/拒绝语义、工件和契约仍须保持 |
| `TurnTape` 字段改名 | **同意 `routed_experts_le_int32`** | 单位从整数元素变成字节，保留旧名字容易让 `len()` 静默变成四倍。直接同步内部消费者和测试构造，不加旧名兼容别名。基准脚本也消费旧字段，须同步 |
| E3b 现在做还是后置 | **允许本阶段做，排在主体之后、独立提交与验收** | 元数据重序列化确有逐轮成本；只优化已验证的顶层 routing 字符串，不建通用 JSON 框架。不让它成为 E3 主体前置条件 |
| §4 验收是否够 | **主要链路已覆盖，补 §2 的边界和 §3 的测量口径** | 重点是旧接受矩阵、真实 support-mask 包装链、叶间写入隔离和最终 ndarray 消费；不用扩成全 dtype/任意对象的测试平台 |

### 冻结约定的处理

`projection_ext.py` 原文确实说“冻结面零触碰”“冻结面一行不改”，不能把它重新解释为旧约定只要求语义不变。[既有迁移方向](../../../tmp/miles_migration_gate_and_spike_plan_20260824.md)与 `miles_spike/spike-log.md` 也说明其用途是保留迁移回退对照。

本次依据用户较新的第六组决定，对该 RH2 自有模块接受**限定于 E3 的内部等价优化**，属 T1 强报告；不宣布全面解冻，不改变 I18，也不将任何当前测试自动改成新的语义 oracle。保留当前提交与旧输出作为差分对照，原有 slime/pin 与 miles 接线均应继续工作。若实作需要改变拒绝类别或 routing 来源，则超出本片。

零触碰代理备选还需兼容 miles wrapper 临时写入的旧 top-p 字段；提前复制成代理快照可能看不到这些字段。既然主方案在当前授权内，没有必要为绕开文件修改引入这层接缝。

## 2. 实施前需并入的修订

### ER1：bytes 快路径不能直接包含所有 memoryview

**性质：已复现的计划兼容性缺口；不是当前 HTTP 生产链的训练污染。**

现有 `decode_int32_tape` 在类型分支前先执行 `.tolist()`。所以它对 memoryview 的实际处理和 docstring 的粗略“bytes-like”说明并不相同。

| 输入 | 旧规范化结果 | 按 Brief 直接返回原字节 |
| --- | --- | --- |
| `bytes(b"\x01\x00\x00\x00")` | `[1]`，4 字节 | 相同 |
| `memoryview(b"\x01\x00\x00\x00")` | `[1, 0, 0, 0]`，16 字节 | `[1]`，4 字节 |
| float32 memoryview，值 1.0 | `tape_element_not_int` | 被解释为整数 1065353216 |

主审[小探针](plan_probe.py)与[结果](plan_probe.json)确认了上述行为。引擎 HTTP JSON 正常给出 base64 字符串，memoryview 反例只限定兼容 helper 的实现，不能据此宣称训练已经受损。

**最小修订**：base64 `str`、普通 `bytes/bytearray` 走直通；有 `.tolist()` 语义的对象先保持旧归一化。不要借此修正旧 memoryview 语义，也不用为它设计新的通用 buffer 类型系统。非法 base64、非四字节整除仍保持原错误分类。

同理，建议新增明确的 `_make_artifact_ref_from_bytes` 入口，旧整数序列入口保持原义；不要让同一参数中的 bytes 同时可能表示“字节载荷”或“整数序列”。若 `_routing_flat_and_dims` 原本返回整数列表，也不要沿用旧名字和调用约定、悄悄改成返回字节。可以保留它作慢路径，另设字节 payload 入口；具体函数划分由实现者选择。

### ER2：回退不是拒绝，三维形状仍须对配置校验

**性质：验收口径修订，避免等价优化引入新拒绝或漏校验。**

Brief §4.5 将“张量 dtype 非 int32”列在反例里容易产生歧义。真实旧 `_build_routing` 的结果是：

| 输入 | 旧行为 |
| --- | --- |
| int32 与值域内 int64，同样数值 | 均通过，工件摘要相同 |
| int64 超 int32 值域 | `tape_value_out_of_int32` |
| float/bool | `tape_element_not_int` |
| tensor `[2,3,2]`，配置 layers=2/topk=2 | `routing_shape_mismatch` |

int32 快路径必须保留配置的 layers/topk 对照，以及 `_build_routing` 的引擎行数公式。只用 `.shape` 生成引用不够。其他 dtype/维数继续旧路径，不能统一拒绝，也不能强制 cast 后把浮点/超界值接受进来。转换不适用时回退即可，不把整个哈希/落工件阶段包进吞异常的 fallback。

错误对照也要按真实入口区分：超范围整数列表在旧 capture hook 的 `_store_int32` 抛原生 `struct.error`，在投影层 `_int32_bytes` 才包装成 `tape_value_out_of_int32`；主审已直接复现。Brief 用后者替换所有 fallback 不能同时宣称异常类别完全不变。非快速输入保留各自旧路径即可，不顺带统一异常机制。正常 base64 int32 wire 不存在数值超出其编码值域的情况。

空 buffer 的 `frombuffer` 与旧空张量构造存在差异，可直接回旧分支；正常入训 routing 不依赖零行，无需为零行另建支持能力。主审还确认非连续数组、int32 边界值、大端 ndarray 转为小端 C 顺序时可保持旧字节；非目标主机字节序仍按 Brief 回退，不新增硬件支持承诺。

### ER3：明确“共享一份”的边界与张量生命周期

**性质：内存表述与验收修订，不否定 compact 方案。**

可以做到“每轮 `TurnTape` 与该轮 artifact store 引用同一个不可变 bytes”；不能称整条链路只有一份缓冲区。按当前保留方式：

- 投影阶段仍可能同时持有全部逐轮 bytes、各叶 tensor/bytearray、各分支 bytes 工件。
- `generate` 返回后，canonicalize 还会为 miles 创建独立 numpy 副本；此时原叶 tensor 也可能仍存活。
- 全部轮次的捕获数据仍按既有生命周期保留，不能只留下最后一轮；E3 不承担工件提前释放或磁盘留存策略。

`torch.frombuffer(bytearray(buf))` 本身合理：张量共享这份专属可写 buffer，PyTorch 保持 buffer owner 的引用，局部变量离开作用域不导致悬空。[PyTorch 官方说明](https://docs.pytorch.org/docs/2.14/generated/torch.frombuffer.html)

准确验收为：每叶持有独立可写缓冲区；修改叶一不影响不可变捕获工件或叶二；局部引用释放后张量有效；canonicalize 的 ndarray 仍为独立、连续 int32。**不需要为了措辞“自有内存”再加一次 `clone()`。** 当前下游未要求该 tensor storage 可扩容。

## 3. 对 §4–§5 的最小补充

保留原多轮、多叶、前缀裁剪与工件逐字节对照，再补以下少量场景即可：

1. **真实包装链**：一个 `return_sampling_mask=True` 的样本组合走现有 `project_group_with_sampler_support → project_from_slime → canonicalize`；输出的 routing ndarray、mask、capture 归属和工件引用与基线一致。无需本片运行真实 loss/GPU。
2. **类型与形状**：ER1/ER2 中的兼容对照；值域内 int64 作为接受正控，配置轴数不一致作为拒绝反例。保留一个无 torch 的回退测试与无 layers/topk 的既有保底行为。
3. **生命周期**：两叶修改隔离、捕获 bytes 不变、释放 hook/临时引用后训练侧数据仍有效；未裁剪时验证 `TurnTape` 与逐轮 store 共享同一 bytes 对象。不要测试“全生命周期只有一个 buffer”。
4. **完整记录对拍**：固定 `_now_utc` 等非输入事实后比较 `GenerationCaptureRecord`；否则改动前后的真实时间戳自然不同，不能因此改 oracle。
5. **E3b 单列**：除已有 Unicode、嵌套、多大串、阈值边界外，加入其他字段带同样值/占位文本的情况。目标字段的 JSON 位置必须按结构定位，不能搜第一个占位字符串后替换。

E3b 推荐只针对已经成功严格 base64 解码的顶层 `routed_experts`，复用这一事实；其余键仍使用原 `json.dumps(sort_keys=True, ensure_ascii=False, separators=(",", ":"))`。按排序后的键构造前后部分并保留目标字符串的引号，原始函数继续作为 oracle。性能计时要包含快路径判定和前后部分生成，不能把额外扫描大串的成本排除。现有提交的基准脚本没有 E3b 实验，144→35 ms 仍属作者的独立测量，本轮没有把它记成主审复现。

### 测量口径

主审直接运行 Claude 的原基准，保存[原始输出](baseline_bench_output.txt)：

| 行数 | hook 合计 | 每叶张量化 | 每叶投影再展开/打包 |
| ---: | ---: | ---: | ---: |
| 8K | 99.2 ms | 1048.2 ms（含首次 torch import，不用于比较） | 265.9 ms |
| 16K | 192.3 ms | 191.0 ms | 530.1 ms |
| 32K | 358.5 ms | 343.0 ms | 1047.0 ms |

量级支持 E3 优先级。该脚本 `ru_maxrss=1872.8 MiB` 是**整个微基准进程的累计峰值**：它同时保留 hook 结果，又另做 flat、pack、tensor 和投影，不是生产单轮内存的归因证据。`tracemalloc` 只导入未采集；25 轮与 heartbeat 也尚不在此脚本中。

实施后将分项计时与生命周期内存分开；旧新版本用独立进程、相同保留对象与轮次/叶数。多轮可用缩小规模先验证存量结构，再按机器容量测代表规模。若把脚本带到 Linux，修正 `ru_maxrss` 的平台单位（当前按 macOS bytes 换算）；不得让测量本身制造额外驻留后宣称是生产开销。心跳先让测量协程进入调度，再调用同步 commit，统计 adapter/owner 各自的延迟；真实占用率与 GPU 影响留 E5。

## 4. 调用链与验证边界

- **生产可达性已核实**：当前单 RolloutManager 下，各 engine 不分担这些 Python 转换；全 run 的逐轮 hook 共用 adapter 循环，backfill/投影/canonicalize 共用 owner 循环。`RH2_FA_LIMIT_MODEL_CALL=32` 是 model-call 限额，不能当作全部 session 或 tape 存量的上界。
- **冻结面已核实**：主审核读 `projection_ext` 的旧文案、迁移记录与用户最新 I23 授权；按当前授权接受窄偏离，原文不回写成“从来只冻结语义”。
- **独立验证**：原基准重跑一次；[小探针](plan_probe.py)覆盖旧类型接受矩阵、Brief 的 memoryview 反例、数组字节等价与 buffer 引用生命周期。运行 `test_project_from_slime.py` 及两条真实 backfill 维护测试，共 **36 passed**。这些是基线/方案证据，未验收未编写的快路径。
- **分工**：依 §10.4 对当前跨循环数据生命周期作 Production Tracer 与 Falsifier/Simplifier 两路检查；主审独立复现关键边界并去重。没有扩展到 I18、第五组已提交代码、网络依赖供应或整个训练链。
- **改动范围**：仅本报告、审查探针/结果与导航/账本；未改作者 Brief 的方案正文、生产代码、维护测试、配置或 fork；未运行 Docker/GPU/远端，未提交/push 或发送跨任务消息。

**停止条件：** 作者将 ER1–ER3 和上述必要验收修订并入后可实施主方案，无需再等待 owner 拍板或单独召开一轮设计决策。交付时检查实际代码与差分证据；E3b 单独验收，可独立回退。其余纯理论输入不作为继续阻塞的理由。
