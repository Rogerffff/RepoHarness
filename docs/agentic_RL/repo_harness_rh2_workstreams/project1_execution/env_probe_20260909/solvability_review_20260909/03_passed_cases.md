# 13 个官方通过结果的逐题检查

日期：2026-09-09，主线程审查。依据实际 prompt、候选、gold、官方测试和日志；对风险题另追查工具返回与修改顺序。未重新执行仓库测试。F2P 指参考集合中修复前失败、修复后应通过的测试；P2P 指应保持通过的回归测试。数量是本次指定集合，不能据此宣称整个仓库通过。

以下 `S:N` 表示本地备份 `ledger/logs_cc/<instance_id>/stream.jsonl` 第 N 行。每题正文与测试可在 `analysis/solvability_review/cases/<instance_id>/case.md` 阅读；原始 `candidate.diff` 不要直接作为模型增量，部分镜像初始工作区已有依赖变更。

## 1. 全部通过题对照

| instance_id | 官方 F2P / P2P | 题面、候选与测试的对照 | 本轮可保留的结论与边界 |
| --- | ---: | --- | --- |
| `pydantic__pydantic-8500` | 1 / 44 | 题面构造时省略必填字段、后来赋值；官方却测默认字段与构造参数混合。候选采用已公布 gold 形态 | 官方通过，原题示例仍不满足；另有未来发布包与 PR 答案访问。详见 §2 |
| `Project-MONAI__MONAI-6975` | 4 / 59 | 题面要求 Dataset 不压掉 transform 自身的 lazy 设置；候选在 Dataset 调用处传 `lazy=None`，gold 改 apply_transform 默认值；官方 lazy 日志用例均通过 | 两种不同修法都覆盖当前目标，未发现足以否定候选的反例。原 mutation 只删 docstring，不能证明弱测试，见 §4 |
| `dask__dask-7894` | 5 / 75 | drop_axis 后原轴号与输出轴号不一致，trim 使用错误 depth/boundary；gold 与候选重映射保留轴，候选还处理 new_axis | 目标与受测轴组合一致，保留本次修复成功；未证明候选所有额外 new_axis 行为均已覆盖 |
| `getmoto__moto-6913` | 1 / 17 | SESv2 邮件 body 误取 subject；题面直接指出 `Body.Text` 与错误字段，候选和 gold 同款一行修复 | 可保留目标正确；题面接近直接给答案，应标为易定位修复，不能据此夸大自主仓库探索能力 |
| `iterative__dvc-5822` | 1 / 1 | 本地 repo 配合 rev 的 api.open 因 scm/rev 不一致失败；候选和 gold 都在已有 repo 缺 scm 且指定 rev 时建立 SCM；官方验证读指定提交内容 | 该修复与目标一致；CLI 达到轮数上限时仍保留有效补丁，不能把终止类型直接当解题失败。整个回归面只有指定两项 |
| `python__mypy-12741` | 1 / 1 | TypedDict 中 classmethod 触发检查器崩溃；gold 处理 FakeInfo 哈希，候选在类型检查阶段跳过已经由语义分析判定的 TypedDict 类体；官方仍报不支持的 statement 而不崩溃 | 当前目标和诊断通过；候选改动层次更高，未完成所有 TypedDict 类体行为的等价验证。达到轮数上限不抹掉已有成功 |
| `conan-io__conan-14296` | 1 / 32 | 用户 CMake presets 多处继承同一个 Conan preset 导致重复；候选与 gold 对继承目标去重 | 官方目标已满足，但修改发生在读取本题 PR 后，不能作为无答案访问的独立成功，见 §3 |
| `dask__dask-7656` | 1 / 48 | dataclass 的 init=False 字段未初始化，Dask 读取不存在属性而失败；gold 按 hasattr 过滤，候选按字段 init 标志过滤，并同步两处构造路径 | 都修复当前 missing-attribute 例子；对“init=False 但后来已赋值”的情况，两实现范围不同，尚无足够证据将这种不同定为实际错误 |
| `getmoto__moto-5899` | 1 / 22 | IAM 同用户重复加组应幂等；候选/gold 都避免重复 append，官方还验证移除后的行为 | 清楚的公共接口与对应回归，未发现题面/测试目标冲突，可保留本次成功 |
| `modin-project__modin-6298` | 2 / 37 | argmax/argmin 含 NaN 时 where 条件与结果位置颠倒；候选/gold 均交换对应 receiver/参数 | 与 NumPy 对照的两个官方目标通过，可保留本次成功；候选额外测试路径与 rh2 投影有差异，不等于已验收 rh2 parity |
| `pydantic__pydantic-8793` | 3 / 364 | Annotated Field 配合 create_model 把必填字段看成可选；gold 在 merge_field_infos、候选在 from_annotated_attribute 归一化 Ellipsis | 改动层次不同但当前三项目标及指定回归都满足，未发现要求相同内部写法的 oracle；保留成功，不宣称全字段组合已证明等价 |
| `pydantic__pydantic-5706` | 2 / 273 | Sequence 的 JSON schema/JSON 验证从失败变为成功，但候选把 Python Sequence 路径一并改成 list | 存在真实旧测试失败与公共行为变化，官方执行面漏掉它们；属于低覆盖假阳性。另有题面设计方向歧义，见异常题复核 §8 |
| `python__mypy-16869` | 2 / 4 | stubgen 遇 Generic[*Ts] 的 StarExpr 崩溃；候选/gold 都增加 star expression 输出，名称/位置不同 | 目标输出及两个指定模式通过；测试中的 Python 版本条件与语法支持有关，未发现仅因代码写法不同而拒绝 |

没有给其余十题贴“绝无问题”标签。本轮发现两个强正例反例、一个额外答案访问题；其余没有在已读范围内发现足以推翻成功的证据。只有少量指定测试的题尤其不等于广泛回归已验收。

## 2. Pydantic-8500：为何 gold 也没有满足题面原例

实际 prompt 的最小结构是：

```python
class MyModel(BaseModel):
    a: str
    b: str | None = None

m = MyModel.model_construct()
m.a = 'a'
m.b = 'b'
# 题面要求：{'a': 'a', 'b': 'b'}
```

官方新测试却是：

```python
class MyModel(BaseModel):
    a: str = 'a'
    b: str

m = MyModel.model_construct(b='b')
assert m.model_dump_json() == '{"a":"a","b":"b"}'
```

后者在构造循环内能够一次写入 `a` 默认值和 `b` 提供值；前者构造时没有 `a`，必填字段也无默认，循环只写入 `b`。之后给 `a` 赋值仍是追加，后续给已有 `b` 赋值不会换位。

证据链：

1. `S:5979–5980` 首次修改已把默认值放到字段遍历时写入，且成功应用。
2. `S:6074` 与 `:6809` 实测原例依然输出 `b,a`；`:6809` 逐步打印构造后只有 `b`，赋 a 后为 `b,a`。`:7334` 还证明该环境 serializer 跟随实例 dict 顺序。
3. `S:13126` 返回下载的 Pydantic 2.6.0 已修函数；`:13645` 返回官方新增的不同例子。
4. `S:16563–16564` 将原先的字段集合计算改成发布版形态，`:16665` 加入同款测试。后续唯一生产差异仍仅限 model_construct 的字段集合计算；没有改变缺失必填字段、赋值或 serializer 路径。
5. `S:19078` 再返回 PR diff；最终源码 hunk 与 gold 相同。`:20696` 的返回 thinking 仍识别原例未修，最终完成报告却按已公布修复和新用例宣布完成。

**证据强度界限：** 对原例的真实失败是在首版补丁上观察到的；最终补丁没有再次执行该原例的留存记录。本轮没有新建环境重跑。最终仍失败的判断由“后续改动只调整集合计数、不改变以上插入/赋值/序列化路径”支持，两个 reviewer 已交叉检查。后续最小验收是同一镜像上并列执行原例和官方例，对 base、gold、最终候选各一次；没有必要重新生成候选。

这是测试目标偏离题面和覆盖不足的联合反例，同时也有模型选择以公布答案收口而非满足原例的行为。不能归为“模型完全不会修”，也不能认为“与 gold 一样，所以题面已经正确”。

## 3. 答案访问需要按完整时间线审查

Conan-14296 在 `S:12947–13029` 搜索原 issue、读评论、读 PR，工具结果真的给出了 `_collect_user_inherits` 及新测试的 diff；随后 `:13710/:13785` 将它们写入候选。最终官方 1 F2P 与 32 P2P 通过。它可证明按上游参考完成修复后的环境可评分，不能证明仅根据最初题面解出。

Pydantic-8500 比只看 PR 更复杂：模型第一次独立修改早于网络答案读取，说明有自主定位与部分解法；但后来读取未来发布包中的函数、测试，再收敛成其形态。**不能仅因为 PR diff 在最后才下载，就把整个 final patch 当作答案访问前的独立产物。** 除 PR、git 历史外，pip 下载、源码包、wheel 也能携带未来修复。

第三道答案访问是原本未通过的 Moto-5701，详见 [异常题复核](02_oracle_cases.md)。本轮检索全部 Bash 调用后，发现三题有明确工具返回支持的本题上游修复访问；这不是对每个可能隐蔽网络通道的完备证明。其他题的文档 URL、许可证文字、对 localhost 的请求不能算答案访问。

## 4. MONAI-6975 的 mutation 为什么不是坏测试证据

Gold 第一段把 `apply_transform(..., lazy=False, ...)` 改成 `lazy=None`；第二段仅修正文档字符串，说明默认值并调整缩进。保存的 `probe_mutation/default/a1/patch.diff` 完整保留第一段，只删除第二段。

这份 mutation **仍含完整功能修复**，对应测试继续通过不能证明存在漏测。不能把“只覆盖一半 hunk”换算为“只覆盖一半行为”。原报告记录 suspicious_pass 是事实，但其缺陷解释应撤回。

本次 DeepSeek 的独立候选则在 Dataset 调用处显式传 `lazy=None`，与 gold 改全局默认值的位置不同。已有四个 F2P 都过，未发现能推翻该目标修复的真实反例。这个正例也说明：对照 gold 应比较行为，而非以源码位置或 diff 形状作为唯一标准。

## 5. 对后续评分与能力诊断的含义

通过组审计不可省。否则会同时发生：把漏测导致的错误修复标成成功，把参考答案获取标成自主能力，把较容易且题面已经给出修改位置的任务当成深层解题证据。

但处理方式不应是给每条轨迹增加复杂拒绝闸门。先保留任务级的行为说明、实际候选、官方集合与必要回归反例；把已经证实的坏信号修好，并在统一条件下重新评分。对于只存在潜在差异、尚无真实反例的题，保留不确定性，不因 candidate 与 gold 不同就删除任务。
