# E3 窄实施 Brief：路由 tape 紧凑表示（I23）

2026-09-22 / Claude（A 线分叉）。**状态：Brief，待 Codex 聚焦检查；未实施。** 依据：[第六组决定 2 与 E3](README.md)（I18 暂缓期间对"不动路由链路"的窄范围补充授权）、[方向检查](claude_a_direction_review_20260922.md)与 [Codex 复核 §2.1](codex_direction_review_20260922.md)。

## 1. 范围

**做**：路由 tape 从引擎响应到训练样本之间，去掉 Python 整数对象的反复展开与重复打包，全程只保留一份规范的小端 int32 字节。

**不做**：不改捕获内容（全部轮次、全部分支照旧）；不改任何工件的字节、`ref_id`、sha256 或 `byte_size`；不改 `GenerationCaptureRecord` 等契约 schema；不决定 I18 的路由来源；不引入工作线程或异步提交队列；不动 top-p tape（体量小两个数量级）；不动 fork 侧的 `tobytes/sha256`。

## 2. 真实调用链与基线

一份 32K 行的 tape（48 层 × 8 路由项，原始 48 MiB，base64 64 MiB）今天经过的形态：

| # | 位置 | 发生什么 | 时机 |
| --- | --- | --- | --- |
| 1 | `capture_wire.py` `_send_once` | `r.json()` 把整个响应解析成 dict，base64 串留在 `PendingTurn.raw_response` 里直到 commit | 每轮，事件循环上 |
| 2 | `projection.decode_int32_tape` | base64 → bytes → `struct.unpack` → `list[int]`（1,258 万个元素） | 每轮 |
| 3 | `generate.py` `_store_int32` | `struct.pack(f"<{n}i", *values)` 再打回 bytes，算 sha256，放进 `artifact_store` | 每轮 |
| 4 | `generate.py:1026` | `tuple(routing_flat)` 存进 `TurnTape`，整个 session 期间常驻 | 每轮 |
| 5 | `generate.py:988` | `canonical_json_digest(dict(meta))`：把含 64 MiB base64 串的整个 `meta_info` 再 `json.dumps` 一遍、encode、sha256 | 每轮 |
| 6 | `backfill_leaf_sample` | `list(last.routed_experts_flat)` → 可能裁前缀 → `torch.tensor(list(flat))` | 每叶 |
| 7 | `projection._build_routing` | 张量 `.tolist()` 成三层嵌套列表 → 递归展平 → `struct.pack(*values)` → 第二份工件 `{trajectory}_{branch}_routing_tape` | 每叶 |
| 8 | `canonicalize._convert_routed_experts` | 张量 → numpy（C 路径，不经列表） | 每叶，**不需要改** |

**本机微基准**（调用上述真实函数，合成响应；Apple Silicon / Python 3.12，不是目标机，只看相对大小。脚本：`rh2/experiments/batch6_e3_20260922/baseline_bench.py`，从 `rh2/` 用 `.venv/bin/python` 直接运行）：

| 行数 | 逐轮 hook 合计 | 其中 #2 解码 | #3 打包 | #4 tuple | #5 meta 摘要 | #6 每叶张量化 | #7 每叶投影再展开 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8K | 76 ms | 18 | 16 | 1.5 | 29 | —（含首次 import，不计） | 240 ms |
| 16K | 157 ms | 36 | 38 | 6 | 62 | 164 ms | 504 ms |
| 32K | 374 ms | 73 | 70 | 6 | 116 | 333 ms | **1,081 ms** |

逐轮数字与清单 I23 的历史探针（86 / 172 / 346 ms）吻合。两点此前没有单列：**#7 是最大单项**（每叶，32K 时超过 1 s 的同步计算）；**#5 占逐轮成本约三分之一**，它不是"表示"问题，单靠换表示去不掉。单个 32K 轮次的处理让进程峰值 RSS 到 1.9 GB（含 torch 约 0.3 GB）。

**这些成本落在哪个事件循环上**（已读代码核对，回应 Codex 复核 §2.1 的提醒）：

- 逐轮的 #2–#5 在 **adapter 循环**上同步执行：`rh2_record_turn` 包装 vendored `TrajectoryManager.record_turn`，在 adapter 的 HTTP 处理里、响应 flush 之后调 `registry.commit(sid)`，hook 在锁外同步跑完（`capture_wire.py:754–`、`1474–1478`）。adapter 是 `run_app_in_thread` 起的**单个** aiohttp 线程，整场 run 的全部会话共用它（`bringup.py:1034–1045`）。
- 每叶的 #6–#7 在 **owner 循环**上：miles 的共享后台 `AsyncLoopThread`，rollout fn、worker、buffer、评分队列和全部在飞执行都在这一个循环上（同一段注释）。
- 所以当前生产拓扑下，"全 run 的并发"确实落在各一个循环上，不会被多个进程分摊。并发上界是模型调用 32（`RH2_FA_LIMIT_MODEL_CALL`）与 miles 的在飞成员数。

仍然成立的保留：上表是单次同步成本，实际占用率取决于真实的每轮时长与上下文长度分布，那要八卡作业才有；没有证据表明 GPU 已经因此空等。

## 3. 改动（函数级）

### 3.1 `adapters/slime/projection.py`

**先说一个需要 Codex 明确表态的点：这个文件按既有约定是"slime 冻结面"**（`adapters/miles/projection_ext.py` 模块头：回退面语义，改动会污染既有测试面的对照基准；当时为此把新枚举的接线放到了 miles 侧，冻结面一行没动）。E3 要动它的三个内部 helper。我的判断是这不违背冻结的本意——冻结防的是语义漂移，而本片对任何输入的输出（工件字节、摘要、形状、错误码）逐位不变，并且正好用那套既有测试面不改断言地通过来作对照。但这是对约定的一次偏离，所以单列出来：

- **主方案**：按下面三条做最小内部改动。
- **备选（冻结面零触碰）**：只改 `generate.py` 一侧（§3.2），投影层保持现状。代价是最大单项 #7（32K 时 1,081 ms/叶）原样保留，E3 的收益只剩逐轮部分。
- **折中（同样零触碰）**：在 `generate.py` 调投影时传一个只读视图，仅把 `rollout_routed_experts` 换成规范字节，让投影走它**现有的** bytes 输入路径（仍经一次 list 与打包，按 §2 分项估约 0.12–0.15 s/叶，比现状快约 7 倍）。代价是多一层代理对象，且投影看到的输入形态与 miles 侧拿到的张量不是同一个对象，需要用等价测试钉住两者内容一致。


- 新增 `decode_int32_tape_bytes(value, *, field_name) -> bytes`：base64 串与 bytes-like 输入只做 `b64decode` / `bytes()` 和"长度是 4 的倍数"检查，**原样返回**。理由：今天的 `pack("<Ni", *unpack("<Ni", raw))` 对任意 4 字节模式都是恒等变换，所以返回原字节得到的工件字节与 sha256 逐位相同。嵌套列表、扁平列表等其它形态走现有 `decode_int32_tape` + `_int32_bytes`，错误码不变。
- `_routing_flat_and_dims` / `_build_routing`：输入是张量或 ndarray 时，不再 `.tolist()`。鸭子类型取 numpy 视图（`detach().cpu().numpy()` 或 `numpy.asarray`，函数内惰性 import，本模块仍不 import torch），要求 `dtype == int32` 且 3 维，形状直接读 `.shape`，载荷为 `numpy.ascontiguousarray(arr, dtype="<i4").tobytes()`。dtype 不是 int32、维数不对或取视图失败时**回落到现有慢路径**，保证 `routing_shape_ragged`、`tape_value_out_of_int32` 等既有错误语义一字不变。
- `_make_artifact_ref` 增加接受现成 bytes 的入口（或新增 `_make_artifact_ref_from_bytes`），digest 计算不变。

### 3.2 `adapters/slime/generate.py`

- `GenerationCaptureHook.on_generate_response`：路由 tape 改用 `decode_int32_tape_bytes`，`_store(f"{record_id}_routing", routing_bytes)` 直接落工件；`TurnTape` 持有**同一个 bytes 对象**（不再多一份）。
- `TurnTape.routed_experts_flat: tuple[int, ...] | None` **改名**为 `routed_experts_le_int32: bytes | None`。改名而不是原名换类型：`len(bytes)` 是元素数的 4 倍，原名换类型会让漏改的消费者悄悄算错；改名则漏改处直接 AttributeError。`TurnTape` 不进契约；测试里只有 4 处以 `routed_experts_flat=None` 构造，同步改名。
- `backfill_leaf_sample`：元素数取 `len(buf) // 4`，行数核对与 `routing_rows_mismatch_backfill` 判据不变；前缀裁剪改成字节切片 `buf[extra_rows * per_row * 4:]`；三个 `rh2_routing_backfill_*` metadata 键照写。
- `_shape_routing_experts`：torch 路径改为 `torch.frombuffer(bytearray(buf), dtype=torch.int32).reshape(rows, layers, topk)`（`bytearray` 给张量一份自有、可写的内存，一次 memcpy）。无 torch 的回退、以及缺 `layers/topk` 配置时交付扁平列表的保底形态，继续用 `struct.unpack` 生成与今天相同的 Python 结构。小端主机以外（`sys.byteorder != "little"`）整条快路径不启用，走现状。

### 3.3 可选子片 E3b：`raw_meta_info_digest` 的流式等价计算

`canonical_json_digest(dict(meta))` 的成本几乎全部来自那一个 base64 大串：`json.dumps` 复制一遍、`.encode` 再复制一遍、然后才哈希。base64 字母表里没有需要 JSON 转义的字符，所以可以只对"去掉大串的 meta"做 `json.dumps`，在大串的位置把哈希拆成三段 `update(前缀)`、`update(串的 ASCII 字节)`、`update(后缀)`，得到**逐位相同**的摘要，省掉两次大拷贝。只在值是纯 base64 字符串且超过阈值（例如 1 MiB）时启用，其余走原函数。

本机对 32K 行的 meta 单独实测（随机载荷，与 §2 表里的 116 ms 是同一量级的两次测量）：现函数 144 ms（`json.dumps` 114、encode 7、sha256 23.5），三段式 35 ms，**摘要逐位相同**。也就是大头是 `json.dumps` 对大串的处理，不是哈希。

这一片改的是契约字段的**计算方式**（不改值），所以单列、单独验收；Codex 若认为不值得现在动，E3 主体不受影响。剩下的约 35 ms 主要是哈希与一次 ASCII 编码，要再降只能移出事件循环，那不属于本片。

### 3.4 不改的地方

`capture_wire.py` 的 `PendingTurn.raw_response` 继续持有完整响应直到 commit（vendored 链与 hook 都要读它）；`canonicalize.py` 已是 C 路径；契约与 fork 不动。

## 4. 等价性与验收

同一份输入，改动前后逐项相等（用现有 mock 会话 + 合成多轮多叶捕获，含一个需要裁前缀的叶）：

1. 全部 `ArtifactRef` 的 `(ref_id, sha256, byte_size)` 与 `artifact_store` 字节：逐轮 `{record_id}_routing`、逐叶 `{trajectory}_{branch}_routing_tape`。
2. 每条 `GenerationCaptureRecord` 全字段，含 `raw_meta_info_digest`（E3b 的专项：随机 meta、含非 ASCII、嵌套结构、多个大串、恰在阈值上下，各与原函数比对）。
3. 每个叶的 `sample.rollout_routed_experts`：`torch.equal`、dtype int32、形状一致、内存自有；裁前缀的三个 metadata 键。
4. `canonicalize` 输出的 ndarray 与现状逐元素相等。
5. 反例保持原错误码：base64 非法、字节数非 4 的倍数、行数与引擎约定差一行、嵌套列表不规整、张量 dtype 非 int32、请求了 tape 而缺失、最后一轮缺 tape。
6. 无 torch 环境（lane A 形态）下回退路径仍得到与今天相同的 Python 结构。

既有用例不应需要改断言；需要改的只有 4 处 `TurnTape` 构造的字段名。双 lane 计数若因新增用例变化，按约定同步 manifest。

## 5. 测量（分别报告，不互相推算）

- **同步成本**：§2 的微基准改动前后各跑一次，8K / 16K / 32K，逐项列出；预期逐轮的 #2–#4 合计降到原来的约三分之一以内、#6–#7 降一个数量级，但以实测为准。
- **峰值内存**：同一脚本的 `ru_maxrss` 与 `tracemalloc` 峰值，单轮与"25 轮逐轮增长到 32K"的 session 两种；只报实测值，不外推到多并发。
- **事件循环阻塞**：在 mock 会话里加一个 10 ms 心跳协程，记录 commit 期间的最大心跳延迟，改动前后对比。
- **真实占用率**不在本片测：拓扑事实见 §2（各一个循环、全 run 共用），每轮时长与上下文分布要八卡作业才有，归 E5 的测量清单——清单里加两项：adapter 循环与 owner 循环的心跳延迟分位数。

## 6. 归属、顺序与风险

- 文件：`projection.py`（冻结面，见 §3.1 的说明）、`generate.py`（A 线）；测试在 `tests/adapters/`、`tests/adapters_miles/`。第五组 I21/I22 已于 2026-09-22 提交（`0b5a5189`），E3 从干净的 `generate.py` 起步。E3b 新增的流式摘要函数只在 hook 调用点使用，`contracts/_base.py` 的 `canonical_json_digest` 不动，并作为等价测试的对照。
- 风险一：快路径与慢路径并存，判定条件写错会让某种输入走错路。对策是 §4 第 5、6 条的反例与"dtype / 维数 / 字节序不满足即回落"。
- 风险二：`torch.frombuffer` 对只读缓冲区会告警并共享内存，所以固定经 `bytearray` 拷贝一次，保证张量自有内存（`canonicalize` 文档要求下游持有期间上游释放引用也安全）。
- 风险三：E3b 触碰契约摘要的计算路径。对策是单列、专项等价测试、可独立回退。
- T 级：无训练语义、公共契约或安全边界变化；`TurnTape` 改名属内部表示（T1，实施后报告）。

## 7. 并入 Codex 计划复核的修订（2026-09-22，实施前）

[Codex 复核](e3_plan_review_20260922/README.md)：主方案可推进，冻结面的窄偏离按用户第六组决定接受（T1 强报告，不宣布全面解冻）；`TurnTape` 改名同意，不加旧名别名；E3b 允许本阶段做，排在主体之后、独立提交与验收。以下修订全部 accepted，上文 §3–§5 以本节为准（上文不回改）：

| 项 | 修订 |
| --- | --- |
| ER1 bytes 直通范围 | 直通只覆盖 base64 `str` / `bytes` / `bytearray`。memoryview 与带 `.tolist()` 的对象在旧实现里先 `.tolist()`（bytes 底座的 memoryview 变成逐字节整数），**保持旧归一化，不修正**。新增独立入口 `_make_artifact_ref_from_bytes`，旧整数序列入口原义不变；`_routing_flat_and_dims` 保留为旧路径、原名原义，另设快路径函数返回字节 |
| ER2 回退不是拒绝 | 快路径条件：3 维、非空、int32（ndarray 取整数 kind 且 4 字节宽，大端 / 非连续按 `<i4` C 顺序转换）、小端主机；**保留 layers / topk 配置对照**与 `_build_routing` 的引擎行数公式。其它 dtype / 维数 / 空张量回落旧路径：值域内 int64 仍接受、超界 `tape_value_out_of_int32`、float / bool `tape_element_not_int`、配置轴不一致 `routing_shape_mismatch`——都是旧行为，不统一成新拒绝，也不 cast 后接受。旧路径的错误**顺序**也保持：先行数公式再打包 |
| ER2 异常类别 | capture hook 对非 wire 形态（list）沿用旧的 `_store_int32` 打包，超界整数仍是原生 `struct.error`；投影层旧路径仍是 `_int32_bytes` 的 `tape_value_out_of_int32`。不顺带统一异常机制 |
| ER3 共享一份的边界 | 准确表述：每轮 `TurnTape` 与该轮 store 的 `{record_id}_routing` 引用**同一个**不可变 bytes；投影阶段仍可能同时持有逐轮 bytes、各叶张量、各分支工件；canonicalize 仍为 miles 建独立 numpy 副本。E3 不承担工件提前释放或磁盘留存策略。`torch.frombuffer(bytearray(buf))` 不再加 `clone()` |
| §4 验收补充 | 真实包装链（`return_sampling_mask=True` 经 `project_group_with_sampler_support → project_from_slime → canonicalize`）；ER1/ER2 类型与形状对照（值域内 int64 正控、配置轴不一致反例、无 torch 回退、无 layers/topk 保底）；生命周期（两叶修改隔离、捕获 bytes 不变、未裁剪时 `TurnTape` 与 store 共享同一对象）；固定 `_now_utc` 后比较完整 `GenerationCaptureRecord` |
| §5 测量口径 | 分项计时与生命周期内存分开；旧新版本用独立进程、相同保留对象与轮次 / 叶数；`ru_maxrss` 是整个基准进程的累计峰值，不是生产单轮内存的归因证据；`tracemalloc` 实际采集；心跳先让测量协程进入调度再调同步 commit，adapter / owner 分别统计；带到 Linux 时修正 `ru_maxrss` 单位 |
| E3b | 只针对已成功严格 base64 解码的顶层 `routed_experts`；按排序后的键结构定位（不是搜第一个占位串替换），其余键仍用原 `json.dumps(sort_keys=True, ensure_ascii=False, separators=(",", ":"))`；原函数作 oracle；等价测试加"其它字段带同样值 / 占位文本"；计时包含快路径判定与前后段生成 |

## 8. E3 主体实施记录（2026-09-22，Claude，已实施、本机验证）

### 8.1 改动

| 文件 | 改动 |
| --- | --- |
| `adapters/slime/projection.py` | 新增 `decode_int32_tape_bytes`（wire 形态直通；其余交旧归一化）、`_make_artifact_ref_from_bytes`、`_routing_int32_array_payload`（3 维 int32 张量 / ndarray → 小端 C 顺序字节）、`_routing_fast_payload`（快路径 + 配置轴对照 + 扁平载荷判据）；`_build_routing` 先试快路径，不适用时**原封不动**走 `_routing_flat_and_dims` + `_make_artifact_ref`（旧错误顺序保留）。`_int32_bytes`、`decode_int32_tape`、`_routing_flat_and_dims` 原名原义 |
| `adapters/slime/generate.py` | `TurnTape.routed_experts_flat: tuple[int, ...]` → `routed_experts_le_int32: bytes`；hook 对 base64 / bytes 用 `decode_int32_tape_bytes`，store 与 TurnTape 引用同一个 bytes；list 等形态沿用旧 `decode_int32_tape` + `struct.pack`（超界仍是原生 `struct.error`）；`backfill_leaf_sample` 全程按字节（元素数 = len // 4，裁剪 = 字节切片），无配置保底仍交付 list；`_shape_routing_experts(payload: bytes)` 小端 + 非空时 `torch.frombuffer(bytearray(payload))`，空载荷 / 非小端 / 无 torch 走旧构造 |
| 测试 | 4 处 `TurnTape` 构造改字段名；新增 `tests/adapters/test_e3_routing_tape_compact.py`（12 例：直通等价、ER1 非 wire 形态与错误码、ER2 快 / 旧路径同工件、拒绝与顺序、非小端回退、hook 共享同一对象、固定时间的完整记录对拍、裁剪 + 叶隔离 + 释放后有效、无配置保底、空 / 非小端 / 无 torch 三种回退）、`tests/adapters_miles/test_e3_routing_tape_chain.py`（真实包装链：`return_sampling_mask=True` 经 wire → commit → backfill → `project_group_with_sampler_support` → canonicalize，逐轮 / 分支 / ndarray 与按定义打包的期望逐位一致，mask 事实与 B2 相同） |
| 未改 | `contracts/`、`capture_wire.py`、`canonicalize.py`、fork、manifest |

### 8.2 差分证据（旧树 `110bbd91` vs 新树，独立进程）

`rh2/experiments/batch6_e3_20260922/differential_probe.py` 只调用两棵树都有的生产入口（hook、`backfill_leaf_sample`、`_build_routing`、`_convert_routed_experts`），固定 `_now_utc`。同一场景（3 轮：base64 / 嵌套 list / 含 int32 边界值的 base64；两种叶：精确、裁剪 2 行；无配置保底；13 项错误矩阵；hook 超界 list）的输出 JSON **除 `tree` 字段外逐字节相同**——包括捕获记录全字段（含 `raw_meta_info_digest`）、逐轮与分支工件的 sha256 / 字节数、张量 dtype / 形状 / 内容摘要、裁剪 metadata、canonicalize 的 ndarray、每个反例的异常类别与 reason_code。结果存 `results/differential_{old_110bbd91,new_e3}.json`。

### 8.3 测量（本机 Apple Silicon / Python 3.12 / torch 2.13，旧新各自独立进程，脚本在 `rh2/experiments/batch6_e3_20260922/`）

单轮微基准（`baseline_bench.py`，只调生产入口）：

| 行数 | hook 逐轮：旧 → 新 | 每叶 backfill：旧 → 新 | 每叶投影：旧 → 新 |
| ---: | ---: | ---: | ---: |
| 8K | 182 → 50 ms | 923 → 492 ms（两者都含首次 torch import，不用于比较） | 349 → 5 ms |
| 16K | 294 → 101 ms | 207 → 0.9 ms | 718 → 9 ms |
| 32K | 544 → 420 ms（新树本次 32K 偏高，下面生命周期基准里同规模最后一轮为 194 ms；其中 meta 摘要 117–137 ms 两者相同，是 E3b 对象） | 416 → 3.8 ms | 1,375 → 23 ms |

生命周期基准（`lifecycle_bench.py --turns 25 --rows-max 32768 --leaves 2`，一段 session 逐轮增长到 32K 行，保留对象与生产一致；心跳 10 ms，先让心跳协程进入调度再调同步函数）：

| 指标 | 旧 `110bbd91` | 新 E3 |
| --- | ---: | ---: |
| 25 轮捕获合计 | 69.2 s | 2.6 s |
| 最后一轮（32K 行） | **5,074 ms** | 194 ms |
| 捕获期间心跳最大延迟 | 7,521 ms | 296 ms |
| 25 轮后 tracemalloc 常驻 / 峰值 | 6,867 / 7,076 MiB | 627 / 836 MiB |
| 每叶 backfill（心跳延迟） | 390 ms（391） | 1–2 ms（2） |
| 每叶投影（心跳延迟） | 5,866 / 4,095 ms（同） | 17 ms（7–17） |
| 进程 maxrss | 9,827 MiB | 2,644 MiB |

单轮微基准看不出来的事实：旧表示的逐轮成本在 session 内**随存量恶化**（同样 32K 行，单轮 0.54 s，第 25 轮 5.1 s），与 tuple 里数千万个 Python 整数对象带来的分配器 / GC 压力一致；心跳延迟 7.5 s 意味着 adapter 循环上其它会话的请求在这段时间全部停摆。新表示下最后一轮的 194 ms 里约 130 ms 是 meta 摘要（E3b）。tracemalloc 只计 Python 分配器可见内存（torch 张量存储不在内），maxrss 是整个基准进程的累计峰值，都不外推到多并发。

### 8.4 验证

既有测试面不改断言全部通过（`test_project_from_slime.py` + `test_slime_generate.py` 91 passed；其中 `test_base64_and_decoded_list_payloads_produce_identical_refs` 现在恰是快路径 vs 旧路径的交叉对照）；新增 12 + 1 例通过；差分探针逐字节相同；ruff 通过。完整套件结果见 infra.md 当日条目。

### 8.5 与 Brief 正文的差异

- §3.1 原写"`_routing_flat_and_dims` 输入是张量时取 numpy 视图"——按 ER1 改为不动该函数，另设 `_routing_fast_payload`。
- §3.2 原写"`frombuffer` 给张量一份自有内存"——按 ER3 表述为"每叶自己的可写缓冲区，PyTorch 持有其引用"；不加 `clone()`。
- 空张量：快路径不启用；零行本来就过不了 `RoutingTensorRef` 契约（`num_rows ≥ 1`），旧新都在同一处以同一类异常拒绝，测试按此钉住，不为零行另建支持能力。
