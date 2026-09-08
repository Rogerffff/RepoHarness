# N11 miles 增量审读：作者自查记录

日期：2026-09-08。正文：[N11_miles_incremental_audit_20260908.md](../N11_miles_incremental_audit_20260908.md)。

**状态：限定范围源码审读、作者自查和15项隔离CPU检查完成；没有独立reviewer，没有完整集成重建或GPU验证。** 本次任务是用户批准的“miles增量精读和分析”，不是依赖升级或训练实现任务。

## 1. 实际证据身份

项目读取快照为 `Rogerffff/RepoHarness@32b615c4e4f869b448174e5974e7a8d29fc4612c`，分支 `miles-migration`。上游固定 `radixark/miles@3de96596f16b9e6d23ba550c4c47de3479c9f14c`。PR2596另按 `nanjiangwill/miles@d17f5716d92b936c6ac585fa6b6f318ba7dda8f8` 查看，不把未合并PR当作main。

项目I只根据集成manifest、patch说明、部分关键patch源码和P的实际消费者恢复合同；未checkout到 `98a0272e…`，未执行16个patch的git am、完整tree比对或两lane测试。正文16patch矩阵明确标出这一范围，避免把说明级复核写成逐行审计。

原N11作为历史U/I/W结论使用，不按今天的H改写历史。对比区间分别是 U→H=309 commits、W→H=7 commits；大区间文件列表可能有限，不报告一个未核实的“全部文件变更数”。

## 2. 代码路径覆盖

已通读H的 `train_async.py`、`fully_async_rollout.py`、`fully_async_data_buffer.py`、`types.py`、`filter_hub/base_types.py`、`common_filters.py`、`weight_version.py`、`rollout_executor.py`、`weight_update/updater.py`、`weight_update/session.py`、session `samples/merge.py`、`tests/fast/rollout/test_filters.py`。

已定点读H的训练转换、Megatron训练步、Dockerfile；P的generate入口、canonicalize字段和转换/版本逻辑、group admission入口与成员检查、faithful DIS合同；PR2596当前head的采样mask门控。没有扩张成全repo、全部模型、多LoRA或所有transfer protocol审计。

对关闭路径做了额外全仓关键词检索，找到session HTTP和其他组件的aclose；因此正文结论限定为“所读fully-async生成者/消费者链没有统一关闭”，没有写成“整个miles没有任何关闭代码”。

## 3. CPU检查怎样得到

容器不能通过公网DNS下载或clone。五份connector取得的完整源文件在本地转存，逐一核对Git blob SHA后作为实验输入：

| 文件 | 核对通过的blob |
| --- | --- |
| `miles/utils/types.py` | `a4d6de01d3d500faae0039c462a2199a46e5958a` |
| `miles/rollout/filter_hub/base_types.py` | `96e887c66887cb677badcf1e3f3da5f9a2bf1357` |
| `miles/rollout/filter_hub/common_filters.py` | `498c63c01022ef7f0a80a649034c4873b777f9d8` |
| `miles/rollout/fully_async_data_buffer.py` | `58fd5cd83669d0f5cc2366eca453b40144e2c294` |
| `miles/utils/weight_version.py` | `480689607cbf67e6cb155d97e6d76ca409378200` |

不是手写一个近似DataBuffer替原实现测试。执行脚本从这些文件AST中保留实际函数/类/常量，去掉imports及TYPE_CHECKING；只有三个明确替换项：动态函数加载器对已给定callable/None直接返回、LoRA禁用、未用的sampling-mask类型占位。数据结构、过滤、版本解析、asyncio条件变量等逻辑来自原源码。

实际执行命令：

```bash
python /mnt/data/miles_incremental_20260908/probe_semantics.py \
  --miles-root /mnt/data/miles_incremental_20260908/upstream \
  --output /mnt/data/miles_incremental_20260908/probe_results.json
```

Python3.13.5、torch2.10.0+cpu、numpy2.3.5。15项全部观察到预期结果，包括正常往返、裁剪、背压和合法零reward对照。结果保存于[JSON](../sources/N11_miles_incremental_20260908/probe_results.json)，完整[检查脚本](../sources/N11_miles_incremental_20260908/probe_semantics.py)可对相同checkout复跑。

**没有运行完整上游pytest、真实imports、Ray actors、engine RPC、Megatron gradients或GPU。** `P15`只是close API缺席检查，不是资源泄漏复现；`P13`只是通知守卫检查，不是新旧补丁组合的driver实验。所有PASS表示观察与笔记一致，而非证明该设计普遍正确。

## 4. 自查时收紧与纠正的表述

| 易误写之处 | 实际处理 |
| --- | --- |
| 309个提交是最近一天新增 | 拆为项目基础U与旧在线W两个比较基准 |
| 原生版本区间代表严格完整性已解决 | 区分表示、裁剪、序列化与null/空列表/类型/覆盖校验 |
| 字段集合不变就兼容 | 检查真实值类型；用原Sample执行P01，确认为字符串访问`.spans`报错 |
| 旧dump加载自动恢复训练版本 | P14记录legacy旁路字段与active空区间，不能替代实时桥接 |
| 缺reward抢先过滤是普遍上游bug | 明确其上游测试刻意保证该行为；问题是与rh2 formal检查组合后的错误优先级 |
| 负lag helper应独立负所有责任 | helper只算术；项目边界校验和upstream默认合同分开 |
| avg_staleness问题本轮首次发现 | 注明原N11已记录，本轮用当前源码重验 |
| JIT差异永远恰差一次更新 | 改成明确条件的时序例子，不给发生率；一般情况按发布和消费实际顺序判断 |
| 零梯度optimizer更新必然是bug | 指出Adam动量/weight decay可以是正常算法语义；skip属于项目选择 |
| 版本通知守卫已经使I失败 | 只列未来迁移组合风险，I当前不含该守卫 |
| 所有16patch已逐行审核 | 按manifest/说明、实际patch片段与H消费点标证据层次 |
| 新main不值得使用 | 改为不应直接替换当前候选；列出原生span、共用filter和权重职责拆分的复用价值 |
| 读取commit证明获得性能收益 | 全文不写本项目加速比，保留实测缺口 |

本轮本地转存`types.py`时曾发现两处字符串排版与原文不一致；在探针执行前回原文件修正，最终整文件blob与connector返回值相等。没有拿未校验转存件报告实验结果。

## 5. 建议后续独立复查的最短路径

先核P01涉及的field-set与constructor；再核新missing-reward分支与P组gate的调用优先级；随后核H driver的prefetch/publish顺序，以及P0014的JIT修改。最后核P0002/0003与H通知守卫的组合假设，避免把守卫函数反例等同真实driver故障。

若准备真实迁移，再重建I并对新candidate做完整patch/依赖/数据面测试；若只是讨论是否迁移，不需要先为所有残余风险设计新平台。探针脚本不是训练验收框架，不应自动纳入生产启动闸门。

## 6. 本轮收尾边界

**待拍板T0：**本轮无已实施T0变更。真实迁移、过滤顺序、zero-update通知和新关闭合同都仅是候选决定。

**自主T1：**限定源码范围；单独新增N11伴随笔记；用隔离CPU源码检查补强静态结论；不覆盖原稿或共享索引总数。

**临时挡板：**只对阅读探针限定固定源码与普通assert模式，避免误用结果。未新增或解除任何训练闸门。

**修正旧结论：**原N11的单数session版本描述仅在旧快照成立；H原生区间和控制面已更新。现有staleness指标口径被再次验证，不作首次发现。

**证据状态：**15项隔离检查，正文链接/章节/脚本语法自查；无独立审查、无GPU、无完整I重建。发布前后由交付操作读取分支并核对仅四个专属文档/研究文件变更，最终commit在回复中给出。

本轮没有改变已定案的reward、loss、组准入、staleness阈值、依赖pin、数据集、恢复、安全或上游代码。没有向外部仓库创建issue、评论或PR。
