# Moto5406：Qwen 首轮轨迹与语义分析

2026-10-03。`gpu1003-moto5406-qwen36-a1`，执行者报告模型 `Qwen3.6-35B-A3B`，原请求 `swe-moto5406-east1-r5-20261003-v1`。**本轮原始奖励 1，1F／27P 全通过；安装、测试真实退出均 0。实际源码修法与公开区域问题一致，暂未发现目标语义缺陷。** 只有一个样本；Coder 首轮及必要重复尚未覆盖，不能称两模型请求完成或能力稳定。

模型来源现有操作链补证支持执行者报告 `Qwen3.6-35B-A3B`：两旧臂实际均用 Q12／services10，23／55 次生成与适配器、backend 记录逐项对应；固定下载 revision `995ad96eacd98c81ed38be0c5b274b04031597b0`、只读 `/model` 挂载和连续服务启动日志支持该配置谱系。题主核补充报告 SHA `761b47e3cd9fc2ffb9b17c7546f72245986c223557b348b7b1ea8d684e891656` 及32份来源字节。此为事后操作链推断：捕获发生在旧作业之后，没有旧job时点独立engine-ID，HTTP revision/checksum为null，下载manifest声明40项但明细37项，未重核约71.9GB权重或GPU内存。原 `checkpoint_identity_verified=false`／`config_only=true` 等字段保留。当前adapter实际命令有idle TTL14400，但不能证明旧作业每时刻配置或TTL到期行为。原始补丁、轨迹和分数不改。

## 实际修法与验证

唯一冻结 entry 为 `moto/dynamodb/models/__init__.py`。模型在 Table 保存调用方传入的 region，用它生成 table ARN，同时令 StreamRecord 的 awsRegion 取同一 Table region。原公开问题来自 ARN 固定 East1；该修法使用实际地域而非改成另一个常量，普通调用方已传入所在 backend 的地域。候选没有改评分测试、私有材料或额外项目文件。

轨迹第 34／48 条创建并执行自拟公开复现，确实得到 East1 与 East2 不符；第 85 条首次明确定位 `_generate_arn` 的地域硬编码。随后读 constructor 与 StreamRecord，在 161／175／189 三次 Edit 改源码。第 207 条复现通过；第 225 条原 East1 检查通过；后续模型记录 create_table 12、range_key 29、主无 range_key 文件 162 项通过，再自拟五个地区及 stream／SSE 检查通过。这些是模型当时的自测记录，未当本次独立重跑。

独立评分完整恢复可信测试，28 个参考逐项通过，无缺失／跳过。题主复核 GPU 执行报告引用的 33 件原件和 23 件 SSE 逐 SHA／长度一致；执行核查覆盖 baseline、冻结对象、投影、测试还原、解析参考、完整 HTTP／SSE 和 actor／grader 两层清理。冻结 canonical digest 为 `70b6bd6281a2d78bb0dff267c2e67dc49216e5686536513d6ccf02b9bae53cec`，没有按模型最终文本代替冻结实际源码。

## 工具行为、效率和并行边界

| 指标 | 本轮实际值 |
| --- | ---: |
| solver 墙钟 | 67.969 秒 |
| CC 回合／gateway 生成／全部 HTTP 请求 | 25／23／25（另 2 次 count_tokens） |
| 工具调用 | 24：Bash 14、Read 5、Write 2、Edit 3 |
| 累计输入／输出 token | 896259／6266 |
| 单次最大输入／输出 token | 51845／1302 |
| 独立候选安装／测试 | 2.621／2.739 秒 |

manager 原时间记录 grade总计 218.598 秒、env reset 12.715 秒、prep 0.438 秒、test 5.971 秒、该manager评分队列等待 0 秒。这不是全局GPU排队时间，各字段也未分解总计的全部开销，不把剩余部分归为模型工具时间。候选安装／测试段计时与manager整段计时是不同范围。

累计输入是多次请求累计，不是 context 峰值。主要可见浪费是一次读完整 1872 行 models 与 1103 行 responses，随后每回合携带扩大后的上下文。先读不存在的 `/tmp/public_repro.py` 产生一次工具错误，模型自行创建复现；误找 backup 测试文件时 pytest 零收集，随后查目录恢复。几条 `head`／`tail` 管道掩盖了真实命令非零，输出仍显示失败；工具 `is_error` 的 1 次计数因此不能当全部失败数。正式评分的独立真实退出比这些自测管道可靠。

存在两组多工具批次：15／19 同一 assistant message 发出 find 与 Read，结果 23／24 逆序返回；66／70 同时发出两次 Read，结果 74／75 逆序。全部请求均早于该批首个返回，说明执行链支持多工具 batch。缺逐工具开始／结束时间，**无法量化运行重叠或并行加速**，不把结果逆序当完整性能证据；其余依赖源码修改后的验证应按依赖串行。

没有 context 压缩、length 终止或实际预算截断。`probe-wide-v1` 实际 HTTP／adapter 输出上限 65536，context 196608、240 CC 回合、10800 秒、1024 次 gateway 请求；CC 元数据的 maxOutputTokens 32000 不当实际 HTTP 限制。普通探针 grade 实际 setup／apply／test／whole 为 900／120／1800／3600 秒，与此前 CPU 的 300／120／1800／1800 不同，保留实际执行条件，不称预算逐项相同。工具耗时、队列等待和并行收益没有足够逐工具时间依据，不用 solver 或 grade 总时长代替。

## 证据与后续

原件位于 `runs/ordinary_gpu_probe_20261002/remote/queue_v12/results/gpu1003-moto5406-qwen36-a1/`；轨迹 SHA256 `45f453e6ea2238c465cae1a16aef9e38ae0919fefcffb71346f33420af60f188`，候选 diff `227f2c7d03e77effc5929680b1eed3465d6fa7bd6d4278a87fbc7c01ec130dc9`，评分日志 `cefb044733de6dc153bf2d16cbcec360d54f20167e8fa0f6d1a97082f10ca9d3`。题主固定执行报告快照及批次分析位于 `runs/category2_repair_20260929/moto_cpu_20261003/qwen36_a1_owner_readback/`，详细身份与摘要写入本题 `results.json`。

保持原请求 claimed，接续 Coder 首轮，按整批约定安排必要重复；本轮不触发题级源码或测试修订。actor／grader 实际源镜像与冻结 code4 绑定已核，`env_qualification=absent`，普通诊断不证明 typed actor 训练租约或训练资格。
