# Moto6114：首轮原始通过，安装和语义均未收口

2026-10-03。`gpu1003-moto6114-qwen36-a1`，执行者报告模型 `Qwen3.6-35B-A3B`，原请求 `swe-moto6114-identity-r7-20261003-v1`。**原始奖励 1，1F／34P 全通过；但 GPU 安装实际退出 2，且实际模型补丁静态确定破坏两条既有 Neptune 名称委托。不能报告语义成功，也不能把环境失败改判为模型 0。** 单一模型样本；旧请求已安全部分结束，Coder、重复及修复后旧 FrozenPatch 35参考复评分均未执行，未完成双模型请求。

模型来源现有操作链补证支持执行者报告 `Qwen3.6-35B-A3B`：两旧臂实际均用 Q12／services10，23／55 次生成与适配器、backend 记录逐项对应；固定下载 revision `995ad96eacd98c81ed38be0c5b274b04031597b0`、只读 `/model` 挂载和连续服务启动日志支持该配置谱系。题主核补充报告 SHA `761b47e3cd9fc2ffb9b17c7546f72245986c223557b348b7b1ea8d684e891656` 及32份来源字节。此为事后操作链推断：捕获发生在旧作业之后，没有旧job时点独立engine-ID，HTTP revision/checksum为null，下载manifest声明40项但明细37项，未重核约71.9GB权重或GPU内存。原 `checkpoint_identity_verified=false`／`config_only=true` 等字段保留。当前adapter实际命令有idle TTL14400，但不能证明旧作业每时刻配置或TTL到期行为。原始补丁、轨迹和分数不改。

## 实际修法及两个独立问题

唯一源码 entry 是 `moto/rds/models.py`。公开问题要求 describe_db_clusters 能按名称和 cluster ARN 查找指定对象。新增 helper 按 ARN 末尾 cluster resource name 查当前 backend，先 RDS 后 Neptune，普通名称优先次序和空参数列出全部的分支保留，没有第一项捷径。当前正常 ARN 的根因修复有依据；helper 没有验证完整 account／region，本记录不据此外加题面未要求的 AWS 规范。

模型还把 helper 扩到 modify／start／stop／delete／snapshot。非作者以公开 base 和实际 patch 静态确认：正常创建的 available Neptune 名称经 RDS façade start，原代码委托 Neptune 并返回 started，候选新增 stopped 条件抛 InvalidDBClusterStateFault；同类名称 delete 原能委托删除，候选先读取 Neptune DBCluster 不存在的 deletion_protection 属性，必然 AttributeError，尚未移除对象。独立 Neptune 客户端的未改路径不应被泛化为坏掉。

这些是候选引入的原行为回退，不是新增 AWS 功能要求，也不是把原 rename 缺陷算作模型引入。本题原 35 个参考没有覆盖两条跨 backend 名称路径，所以原始奖励与语义缺陷并存。报告 [非作者语义窄核](../../reviews/moto6114_qwen_a1_semantics_non_author_20261003.md) SHA256 `eb30f25349feac4b04d76087e270e76faf318d071647fcdd5a9fd23f7d40c13f`；两条实际 CPU base／精确 candidate 内容反例已运行，并由[非作者原件核查](../../reviews/moto6114_neptune_name_diagnostic_result_non_author_20261003.md)确认：base成功，candidate分别抛状态异常和缺属性异常。该诊断不重绑原 FrozenPatch，也未运行正式37参考评分。

另外 GPU 的 COPY wheel 文件权限导致 `make init` 找到 setuptools 72.1.0 后 Permission denied，实际退出 2。测试依靠已有 SDK 继续完成 35 参考。GPU root 已处理同 source／同 wheel SHA 的 0644 修复与实际 UID 检查，修复后未对原 FrozenPatch／原35参考窄复评。安全部分回执已收并核对，原始 raw1、安装2与未执行项保留；该供应修复没有证明重新安装通过，也不能消除上述源码回退。CPU 历史通过用的是另一物理 COPY 镜像，不静默否定或改绑原 CPU 验收。

## 定位、纠错与验证遗漏

轨迹第 62 条读 describe 段落，较早准确定位“直接按字典键查名称”；第 202 条首次修改前没有执行公开 API 失败复现。随后反复读相邻写操作，把本题 describe 修复扩大到通用 helper，九次 Edit 后形成实际冻结补丁。

模型做了普通 RDS ARN／名称的多次自测。第 740 条中间版 ARN delete 出现 KeyError，在 764 条用实际 identifier 修正后重跑成功；这个中间错误已被最终 patch 修掉，不列为当前故障。最后三次全 RDS 自测均记录 212 passed，但没有实际 mock_neptune／tests_neptune 或 RDS→Neptune 名称检查，无法排除跨 backend 回退。一次错误 clustersnapshots 文件名造成零收集，随后查目录恢复；部分 pytest 用 head／tail 管道，其工具成功标记不保证 pytest 成功。

扩展写操作增加了读改次数与中间错误，也让验证集中在新增 RDS ARN 功能，遗漏原跨 backend 行为。推荐的题级补救是先用原 base／实际候选最小两条名称路径确认差异，再按授权裁定补 P2P 保留检查；不把新功能扩展都变成本题必修要求，不按 raw1 直接接受候选。

## 实际效率与并行证据

| 指标 | 本轮实际值 |
| --- | ---: |
| solver 墙钟 | 179.003 秒 |
| CC 回合／gateway 生成／全部 HTTP | 56／55／55 |
| 工具调用 | 55：Bash 24、Read 22、Edit 9 |
| 累计输入／输出 token | 1039680／12491 |
| 单次最大输入／输出 token | 33971／795 |
| 候选安装／测试 | 0.630 秒（失败）／3.807 秒 |

manager 原时间记录 grade总计 231.697 秒、env reset 15.066 秒、prep 0.46 秒、test 5.047 秒、该manager评分队列等待 0 秒。这不是全局GPU排队时间，各字段也未分解总计的全部开销，不把剩余部分归为模型工具时间。候选安装／测试段计时与manager整段计时是不同范围。

22 次 Read、9 次 Edit 和反复跑 212 项 RDS 是可见效率成本；没有逐工具完整 start/end，不能精确分拆其墙钟贡献。累计 token 不当 context 峰值。初始 ls／find 存在同 message 多工具 batch，发出后才返回，执行链能够接受批次；缺逐工具时钟，运行重叠与加速不可量化。

宽预算为实际 context196608／输出65536／240回合／10800秒／1024 gateway，无压缩、length 或实际截断；grade 实际 setup／apply／test／whole300／120／1800／1800秒。尚不覆盖接近上限的长轨迹或压缩，也不从一个样本推出稳定能力。工具时间、环境总耗时和队列等待分别缺依据，保持未知，不用 solver 时长补齐。

## 固定证据与下一步

原件位于 `runs/ordinary_gpu_probe_20261002/remote/queue_v12/results/gpu1003-moto6114-qwen36-a1/`。FrozenPatch canonical digest `68557bc28b72fb3f45912e70d585b7c296ec1a7d1ec7a6e9eec57ce82f5f40d8`；候选 diff SHA256 `bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747`，轨迹 `84e8f68be83f41c2d06259fa3eae613e58113780f6ac240a26514fdf1f266e11`，评分日志 `b5134eb5f279b948ab2d053b5e9d13c5f6b3bd0bae82a7039d1594544e78f3a1`。题主核 33 件引用原件及 55 件 SSE 全部 SHA／长度一致；执行报告变化前固定快照保留，身份写入 `results.json`。

shared board 已记录旧 R7 的题级阻断并通知 GPU 暂停本题新的 Coder／重复。GPU 环境修复与原 FP 诊断重 grade 可继续；题主推进最小 CPU 反例和必要 P2P 修订，改变参考或环境另留新身份。当前不 ACK 未结束的两模型请求，不覆盖旧请求／旧 raw1，不宣称训练资格。
