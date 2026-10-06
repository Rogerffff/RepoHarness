# 6283 v2：PrivateAttr 条件草稿的非作者材料窄核

2026-10-03。审查对象为 `tasks/pydantic__pydantic-6283/revisions/pyd6283-behavior-v2`，对应 base `a29286609e79c79b2ecd71bc7272eea43ed9fccd`。结论：**材料可继续按既有流程推进，值得作最小私有保护条件；未发现测试、原参考或合法修法之间的具体冲突。** 当前仍是条件草稿，真实 Python 3.8／pydantic-core 0.42 观察、正式发布及新矩阵验收尚待，不能写成 v2 已通过。

我已读过私有对照、原 Qwen FrozenPatch、旧评分和先前审查上下文；这是非作者接续窄核，**不是 fresh 公开读者**。本轮仅用本地标准库读取、SHA／大小校验、统一差异的内存应用和 AST 比较。没有导入 Pydantic、运行项目测试、安装依赖或启动 CPU／GPU 作业；也未修改 v1、草稿、原 FP、原分或请求。

## 新条件的依据与适用范围

唯一新节点是 P2P（既有通过行为应继续通过）：

```python
def test_root_model_construct_preserves_private_default():
    class PrivateRoot(RootModel[int]):
        _secret: str = PrivateAttr(default='abc')

    assert PrivateRoot.model_construct(42)._secret == 'abc'
```

公开缓存源码 `docs/usage/models.md:464–465` 明确允许 RootModel 将 root 值按位置传给 `model_construct`；同文件 `476–477` 规定 construct 应与普通初始化一样初始化私有属性。公开 `tests/test_root_model.py:253–275` 已演示 RootModel 的 `PrivateAttr(default='abc')` 默认值读写，`315–323` 另有私有属性参与相等的测试。新条件只组合“可信构造”与“既有默认值读取”，并不声称公开问题示例本身包含这个组合。题面和 hints 继续引用原公开材料，私有测试不交给 solver。

断言只读取公开属性并比较公开默认值。它不读取 `__dict__`／`__pydantic_private__`，不比较 base 构造对象的相等结果，不添加验证器或输入验证要求。因而原相等缺陷不会把这个 P2P 变成额外 F2P；是否在真实指定依赖下确实为 P2P，仍需实际 base 通过结果确认。不同内部存储或修复位置均可满足这个条件，未见绑定 gold 实现。此节点不覆盖私有默认工厂、未设置属性、继承组合或用户自定义 post-init 的一般语义。

## 对照机制与预期

| 对照 | 本轮源码结论 | 草稿整题预期，尚未观测 |
| --- | --- | --- |
| noop | 保留 base；私有初始化路径支持新节点，原相等 F2P 仍未修复。 | 0 |
| gold | 在 BaseModel 中避免给 RootModel 写入多余占位状态，保留 `if cls.__pydantic_post_init__: m.model_post_init(None)`；没有删除初始化生成的私有字典。 | 1 |
| validate_construct | 直接返回 `cls(values['root'])`，会走普通验证。新私有默认值节点自身预计通过；它仍应由原有 `test_construct`／嵌套构造等参考检出验证语义错误。 | 0 |
| qwen36_a1_pop_private | `super().model_construct` 完成 post-init 后，无条件 pop 私有状态，破坏默认值读取。原模型补丁逐字保留作具体负对照。 | 0 |

这些是代码机制与旧证据支持的**预期**，不是新矩阵结果。特别不能把 validate_construct 的整题 0 归因于新 PrivateAttr 节点：公开 `test_construct:182–187` 的 Base64Str 信任构造／转储、`test_construct_nested:190–202` 的不验证语义已有独立保护；公开文档 `469–472` 也规定 construct 不做验证。

Qwen 回归的源码链条可接续[原候选初审](../model_audits_20261003/6283_qwen36_a1_preliminary.md)：`_model_construction.py:92–106` 给私有属性类安装 post-init，`222–236` 初始化默认值字典；`main.py:218–219` 在 construct 返回前执行它。RootModel 的类级 `__pydantic_private__ = None`（`root_model.py:36`）遮蔽基类 slot；候选源码 `root_model.py:66` 删除实例中的真实私有字典后，`main.py:685` 读取路径对类级 None 下标。已有本地标准库机制重放得到 base 可读 `abc`、候选 `TypeError`，本轮复用而未重跑。**这不是实际 Pydantic／core 的运行回执。** 当前[真实观察请求](../coordination_20261003/6283_privateattr_semantic_observation_request_v1.json)仍待。

gold 保留了上述 post-init 调用及其初始化结果。避免占位污染与保留真实私有状态是相容的；无条件删除两种状态才是该候选的具体缺陷。新断言不要求改动必须位于 BaseModel，也不要求采用 gold 分支结构。

## 字节、基线及参考核对

独立核对本目录全部 **13 个文件**。草稿清单列出的 **11 项**大小和 SHA 全部吻合；另两项为清单自身和随后加入的 README。README 未在 `draft_manifest.json` 中，是正式封包时需同步的条件，**不是有效测试或修订单的字节失配**；该清单明确标记 `conditional_private_draft`，不能用作正式 publication 输入。

| 入口 | 大小 | SHA-256 |
| --- | ---: | --- |
| v2 effective_test.patch | 1049 | `30037d927f57145f7c0a80281e60861000183d10ae20e4bf10c03bcd8f5c7cde` |
| v2 revision.json | 11404 | `db97058ef881a5d44c91a3b297fd72fc0202575915fc0c7f53acd004a568ce37` |
| 原 public test baseline | 13254 | `402ccfd0f8d1745cb6173a017a463905f813cd19e5bb54cc2938d697b38e02ef` |
| 原 Qwen diff／负对照 | 1011 | `0b591db84fb791e562fbd9c90f0f11bb2f1ea3c3d9406fe65dfe926da407e351` |

v2 的 parent revision SHA 与当前 v1 完全一致。原 patch、public test baseline、E10 install recipe、noop／gold／validate_construct 均与 v1 逐字相同；公开 source bindings、base commit／tree、原参考和 F2P 顺序均未改变。v1 的 effective patch SHA 仍为 `785d1d6ccdbb74a141c4178f84c21ebd69e6a68ef3a57b04ab1682ee7626bc26`。

原 patch、v1 effective patch、v2 effective patch均可在公开 baseline 上按原 hunk 行号、上下文和行数精确应用，无偏移或模糊匹配。v2 应用后全文为 13708 字节、SHA `6bb8bce7277436102efc2bb43a61dcddd2ccf9830730b7e3026b7add680129e8`。**v1 应用后的完整字节是 v2 的前缀**，新增部分恰为上述一个函数；v1 的全部 42 个顶层 AST 节点（其中 34 个 test 函数定义）完整保留。AST 定义数不等于参数化运行节点数。extra_tests 两函数 AST 与有效补丁一致，新节点未添加 skip／xfail 或参数化。原 40 参考按原序保留，仅追加新 P2P，形成 **2 F2P＋39 P2P＝41**；无重复或 F2P／P2P 交叉。

四份 control 的 SHA／来源副本均吻合，均精确应用于公开生产源码；变更后的源码及测试用 `ast.parse(feature_version=(3,8))` 可解析。这只证明语法解析，不证明 Python 3.8 依赖执行。Qwen control 应用产物与原 FP 的 base64 解码源码逐字相同，源码 SHA `2e8b2748bea649c5bde853049ba9255d62dd6eb033ad9c979dac90765f644b44`，绑定 FP canonical digest `sha256:1ac717446957b1463305cabaceb2e71f8a9b0685c8377f0659869820b8b829d5`。

完整 baseline 的 391 个 regular 成员内容与执行位核对已在原候选初审完成；本轮复用该逐成员证据并重新核对 archive／manifest／FP／diff 原件 SHA，未重新解包冒作新验收。公开必要源码的五项 SHA 也与该初审一致。完整清单、应用产物 SHA 及复用边界见[机器记录](non_author_6283_privateattr_v2_material_review_20261003.json)。

## 剩余条件与用途

材料层面没有新增决定性阻断，建议保持这一最小条件，不扩展为一般 PrivateAttr 穷举。可以继续准备已授权的窄发布；进入正式验收仍需接续以下现有工作：

1. 在权限修复后的真实 Python 3.8／core 0.42 候选环境保存最小观察：普通初始化可读默认值、原 Qwen construct 的实际读取结果及源码身份。以实际结果接续源码推断；同时通过新矩阵的 base／gold 结果确认 P2P 分类和合法正对照。
2. 由题主固定新的正式 publication 清单和请求，明确当前 revision／有效测试／安装 recipe／四个 controls／公开 baseline／README 与审查报告的字节身份。旧 v1、原 FP、旧请求和原分保留；条件草稿清单不替代正式清单。
3. 用正式 consumer 取得四行各 41 参考的原件与实际安装身份，验 noop／gold／validate_construct／原 Qwen 预期 0／1／0／0，并接续非作者运行验收。所有预期仍标为未观测。

E10 recipe 保持 v1 字节（SHA `6e50864b8f8976413f6fb32df2fd11060e1b190fb4161c8567810ac748e6a570`），不证明当前可成功安装。原 Qwen 首臂 install RC1／wheel 权限拒绝和原 raw reward 1、40 参考的历史结果继续保留；本轮未取得修权限重grade回执，也未将原分改 0。新私有条件、静态检查和已授权发布流程均不能代替实际验收或模型／任务完成结论。
