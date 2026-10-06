# Dask 两题收口复核（2026-09-25）

结论：支持 7894、9212 保持 `quality_first`、`ready_for_probe=false`，26/27 保持 `unknown`。未发现需要推翻 pack11 裁定的事实错误或新增硬前置。这里的具体质量疑点足以支持选择性私有对照建议，但不代表已经观察到用户结果回归，也不把这些对照设成全池准入门槛。

复核范围：两题公开原题、完整 gold/test patch、决定性 base 源码链、pack11 report/followups、最终 card、record 的裁定与26/27；抽样旧日志的 Python、collected、结果汇总及测试 RC。没有执行或 import 项目代码，没有测试、容器、SSH、网络、模型调用；没有全量复核 expected/P2P、角色过程或身份哈希。不声称盲审：本次先读取了 pack11 report，随后依据原件重建关键推导。

## 7894

- 原件根目录为 `runs/swegym_quality_expansion_20260925/{public,private}/dask__dask-7894/`。`base/dask/array/core.py:477–481,685–699` 明确先删除轴、再插入新轴。因此 `drop_axis=0,new_axis=0` 下原轴1仍位于输出1。`private/gold.patch:23–26` 只按 kept_axes 压缩重编号，将深度 `{0:0,1:1}` 改成 `{0:1}`，确实遗漏新轴位置。
- `base/dask/array/overlap.py:102–123,142–167` 用输出轴号读取深度，并以切片裁剪。上述 gold 路径在新轴0上使用1，在原轴1所在的输出轴1上取默认0；base 的原字典在该特例恰好对应输出轴。`mean(0)[None,:]` 的新增轴实际长度1，静态切片差异为新轴上的 `slice(1,-1)`。这支持潜在**新增回归**方向；不推断已观测异常类型、运行阶段或实际 shape。
- boundary 问题是另一层：新增七参数全部取 `(0,"reflect","nearest")`，裁剪仅区分 `"none"` 与其它值，故新断言无法区分“同时重排 depth/boundary”与“只重排 depth”的候选。混合 none 的例子用于暴露**半修复残留/漏接收**，不能当作 gold 已新增 boundary 回归。完整 expected 是否接收半修复仍未运行。
- pack11 的 drop0/new0 小数组 base/gold 对照成立，先记录 lazy shape/chunks，再计算或记录准确异常即可。若 base 也失败，不能继续称此例证明新增回归；报告已经保留这个限制，无需增加其它组合、模型或全仓测试前置。

## 9212

- 原件根目录为 `runs/swegym_quality_expansion_20260925/{public,private}/dask__dask-9212/`。`private/gold.patch:16–18` 对普通 Enum 返回短类名、成员名、值；`audit_a.Color.RED` 与 `audit_b.Color.RED` 都变成 `('Color','RED',1)`。`base/dask/base.py:923–935` 对表示字符串求摘要，故这是输入表示相同，非随机摘要碰撞。`utils.py:578–600` 按 MRO 查注册；IntEnum/IntFlag 先命中 int，不影响这里选用普通 Enum 的反例。
- 同一个 `delayed(pure=True)` 函数是有效控制：`delayed.py:618–643` 以同一 func_token 和参数构造 key，`:213–231` 将 pure 路径交给基础 tokenize。因此函数返回 `type(e).__module__` 可以观察两输入差别，同时避免两个函数自身 token 不同掩盖参数碰撞。同步本地调用本身无需导入虚构 module 或分布式序列化。
- 可补充比“图合并可能覆盖”更直接的机制：`Delayed.__dask_tokenize__` 在 `delayed.py:522–523` 返回 key；`base.py:435–447` 的 `unpack_collections` 按 token 去重，`compute` 在 `:585` 调用它。因此同 key 的两 Delayed 甚至可能在合并图之前成为同一个 collection。该链增强联合 compute 提案的针对性；本次仍未实际运行，不能把静态推导写成已测结果。
- base 普通 Enum 在 `base.py:1003–1021` 的默认非严格确定性配置下使用 UUID fallback。它可区分本次两任务，但不意味着 base 已满足同成员稳定性。建议的 base/gold 对照需保存配置/初态；若启用严格确定性而 base 抛错，应据此收窄比较，不能伪称已得到 base 正确结果。

## 历史证据边界

按 `run_refs.json` 指向的旧日志抽样，7894 noop 为5失败/75通过、gold为80通过，测试RC分别1/0；9212 noop为2失败/124通过/3跳过、gold为126通过/3跳过，RC分别1/0。与 pack11 一致。这些旧 core grader 结果未覆盖上述新提案，不能解决26/27或证明实际 actor 已可用。未重新核验105 expected、全部解析差异、安装步骤和镜像身份；这些仍以已有审查的明确范围为准。
