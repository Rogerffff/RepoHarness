# 8511 FieldInfo 保留 v2：非作者材料静态窄核

材料日期：2026-10-03；审查保存日期：2026-10-04（Asia/Singapore）。对象：`pyd8511-behavior-v2` 私有草稿。审查者已接触本题旧私有材料、参考、对照及模型分析，**不是 fresh 公开读者**。本次仅本地读取、hash、严格内存应用补丁、Python3.8语法AST及既有CPU直接诊断原件；没有SSH、Docker、安装、pytest、模型或作者helper执行，仅读原件并写本报告及同名JSON。

## 结论与允许用途

**材料静态核查通过，没有发现阻碍正常新版本发布的材料缺陷或合法修法冲突。可继续正常冻结发布，并在新正式consumer下验收177参考的四行矩阵；无需新增模型求解。** 新增四项都是已有字段行为与 `repr=False` 的组合保护，不要求基线先修好repr，也不要求内部FieldInfo/schema实现。原Qwen四项实际失败的直接诊断为补充材料提供了依据，但它不是pytest或正式评分。

新矩阵 `noop/gold/narrow/qwen_original` 的预期 **0/0/1/0仍未在177参考下实测**。本报告不签发正式CPU已通过、GPU可派发、重复门槛或训练资格。旧R14三行173参考结果0/0/1、Qwen旧173全过/raw1、原FrozenPatch、两模型首次执行及旧请求ACK都保留；不将新材料静态或直接诊断结果回写为历史新分数。

## 冻结字节、完整应用与旧材料保留

| 对象 | 字节 / SHA256 |
| --- | --- |
| 新revision | 33,236B / `717aa36445b6a8eaafb256e187c31a5a1d583d8c4080c1d828a4efb3f549ad92` |
| 新effective_test.patch | 4,083B / `6f7360d58088c01d59ac51133758ee2404ad21725d859144a14c58765b670125` |
| 新extra_tests.py | 1,268B / `9e64865715dd39e6862598d781a81421e59f27aca2074b361f23dc17068ae7c7` |
| 父revision | 29,677B / `9b0dd24d100e5251ab5d2e4c9b1d522ca5f8e04ca60a7113c7bf960d739aca00` |
| 父effective_test.patch | `3354d6d39957611a8385eb80bf1bfe622386143e3f3cdd3deff03ef5ad3908b6` |
| 原测试patch（不变） | 1,729B / `d43f43c16b25d5286a20bb745e3500b139c9c2caf91603f5330130b44695c06c` |
| E10安装recipe（不变） | 958B / `0ea729756104ca11861412113ab512a624787b6235444fbdd406f69645c35a8e` |

基线来自缓存公开base `e4fa099d5adde70acc80238ff810c87a5cec7ebf` / tree `f6b994800d90c9fd0671ac000b4aa5cfaa9a52f7`。新目录public_tests中的原test_dataclasses.py为72,672B/SHA `ca0aeebd83f995c08159e247c6505d54eee75af00b94cb634d5a65b0c043e2a3`，与父目录和source_cache逐字相同。原public/grading/env来源绑定、base、source_cache、原测试patch、E10、eval_cmd和Python3.8版本均与父revision相同；公开题面、hints及公开基线没有新增要求。

对原test patch、父effective patch、新effective patch分别做严格内存完整应用：每个hunk的路径、旧上下文、旧/新行数及行位置均准确，无fuzz、忽略或局部截断。父有效文件为74,279B，新有效文件为75,547B。解析后的**整个父模块AST在新模块前缀逐节点相同**，不只是检查参考列表；新后缀恰好等于extra_tests.py的四函数AST，没有改旧fixture/import/测试/参数化。基线、原测试应用结果、父/新有效文件以及四个候选应用后的生产文件均通过 `ast.parse(feature_version=(3,8))`。这是语法检查，不冒充真实Python3.8导入或pytest收集。

原F2P列表、原P2P列表、旧新增参考及旧173有效参考原序完整保留。新有效P2P仅在父列表尾部追加四个唯一ID；共1F+176P=177，无重复/遗漏/改分区。每个参考的基础函数名在有效AST中存在；参数化旧AST完整保留，但未运行pytest收集确认新版本的实际nodeid。

## 四项为何属于最小P2P

| 新节点 | 断言与旧行为依据 | 最小性 |
| --- | --- | --- |
| `test_repr_false_field_preserves_default_factory` | 两次HiddenFactory()各得空list且不是同一对象；Field default_factory本来是调用工厂，而不是把字段变必填。直接base检查已成立 | 只保护隐藏字段的工厂和值独立性，不查repr或内部字段 |
| `test_inherited_repr_false_field_preserves_default_factory` | 无本地注解的Pydantic dataclass Child继承同一工厂；旧v1已保护继承工厂，新项再覆盖repr=False交叉点，直接base检查已成立 | 工厂值传递经过继承是独立失效路径；没有新增多继承/一般MRO矩阵 |
| `test_repr_false_field_preserves_gt_constraint` | 显式字符串2转换为2，显式0抛ValidationError，公开错误type=greater_than/loc=('x',)；base旧constraint测试及FieldInfo metadata路径支持，直接base成立 | 不验证default=1是否自动校验，不要求完整错误消息、URL或schema |
| `test_repr_false_field_preserves_alias` | Aliased(y='2').x必须为2；base已有Field(alias=...)输入行为，直接base成立 | 默认1与输入2区分“别名被忽略”而不依赖内部alias存储或repr文本 |

四项都只用公开构造、属性读取或ValidationError.errors()；没有repr调用、`__pydantic_fields__`、`__dataclass_fields__`或schema形状断言。它们是**既有base行为的保护**，不声称原公开issue恰好提供了四个组合示例。FieldInfo公开属性说明和base源码将repr与default_factory/alias/metadata分别保存，`collect_dataclass_fields` 与 `FieldInfo.from_annotated_attribute` 会保留完整FieldInfo；仅修repr不能丢掉其他字段语义。

旧base文件中 `test_can_inherit_stdlib_dataclasses_default_factories_and_use_them` 讲的是BaseModel继承stdlib dataclass且明确标为不支持工厂，**不把它当作新Child(Parent)的正例**。本材料测试的是Pydantic dataclass之间的继承；依据是对应旧v1继承节点、base收集路径与实际直接检查。新增四项各覆盖已经证实的不同字段保留通道，没有扩大到一般dataclass/约束/别名组合穷举，也不绑定narrow的内部写法。保留原行为的其他合法实现同样能满足这些断言。

## 正负对照源码及原Qwen运输

noop/gold/narrow补丁与父目录逐字相同；四补丁都能完整应用于公开生产基线，并通过Python3.8 AST。主要机制与适用结论：

- noop保持原repr缺陷，因此177正式预期0；新四项本身是P2P，不能把它们当成新增F2P。
- gold保留完整FieldInfo作为stdlib default，但在Python3.8使用 `getattr(cls, '__annotations__', [])` 会处理继承的注解；旧正式173矩阵已证明必填、隐藏、工厂三类继承回归，因此新矩阵预期仍0。没有新跑gold或断言它在新四项的具体逐项结果。
- narrow使用 `cls.__dict__.get('__annotations__', {})` 限制本地注解，并以完整FieldInfo作为stdlib default，给repr/kw_only单独传参；它保留工厂/alias/metadata而避免旧继承回归。旧173通过及直接新增四项4/4支持正对照，但**不能由这些证据称177正式已经全过**。
- 原Qwen在reprFalse（或高版本kw_only）转换时只取 `field_value.default` 或MISSING，再构造普通dataclasses.field；没有传default_factory/alias/约束metadata。Py3.8隐藏工厂变成必填，gt与别名丢失的源码预测和实际直接检查相符；新正式预期0仍待真实评分。

新 `controls/qwen_original.patch` 为3,087B/SHA `aa39b79e68b110ebedbb5fdb72bdf4fe23438d021cff194bde3204a42a9b4fbc`。它只是运输diff，没有改模型答案：对公开base完整应用后13,034B生产源码，逐字等于保留的原FP单成员，SHA `161678b86e6cdde428771594d2c5e2d4f1016108a2c9fa9b7d900bc0fb28401d`。严格base64解码、成员path/type/operation及内容digest均核齐；保留FP JSON与权威closed snapshot原件逐字相同，canonical digest仍为 **`sha256:4c305765cca042e14a8b79ebafa304394739f982b0eb68a471a47efbf92b3da1`**。生产应用基线dataclasses.py也与原GPU baseline.tar对应成员逐字相同，不靠相似diff或重构的等价源码替代原答案。

## 已有实际直接证据与本报告边界

已读 `actual_v3_readback.md`、三份实际retention_probe的stdin/stdout/exec、对应source_identity前后原件，并独立核题主readback列的154大小/SHA绑定。题主readback为61,484B/SHA `0bfd332e191bd1528a28c9ca6903f23a2c32e53c5271694fdd9faa4d96f00972`；actual results为521,626B/SHA `3ae7bffa90ba3263bd70355f5e4e088acd21684dae75e28ad4111b962bfb377f`。

实际job `pyd8511-retention-20261003T153716Z-v3` 的baseline/narrow各四项通过且exec RC0；qwen_original四项失败且exec RC1：直接/继承工厂均missing ValidationError、gt0错误接受、alias仍得默认1。三份stdin逐字相同，实际argv为候选容器内Python stdin，**不是pytest**，results明确formal_reward_produced=false/model_calls=0。

每个variant的452源码对象在行为检查前后内容SHA/执行位相同，三variant只有预定dataclasses.py不同；其SHA分别等于本次静态应用的noop/narrow/原Qwen源码。实际导入/testbed、UID54321、Python3.8.19、Pydantic2.6.0a1、core2.14.5与输出相符，实际镜像为 `sha256:df6c3affb7ea6fd826f44863ec92926f7b52558dd0f1b42e05f97aec9fe8ca68`。这些支持四项的基线/候选关系，不是以源码模拟替代依赖实测。本报告只核与材料有关的来源和行为连接；完整命令、资源、PID1、清理及前两次失败的执行验收由现已通过并获题主核收的[实际v3独立报告](non_author_8511_fieldinfo_retention_v3_cpu_review_20261003.md)负责，本审不重复签发其全部结论。其MD为16,111B/SHA `c56ad7dfdde67aaaf209e5e104c32ff0435476fe62b1345bc6e8dbaa4c98bf64`，JSON为74,110B/SHA `a067eadfe16c97e45b0f141d5fb010fb60ae4e297504c7afc5c8cef6988ef8b0`；通过范围仅直接行为诊断，new177_reference_grading_performed仍false。

## 私有边界、封包与下一步

目前新revision明确runtime_registration=false、public_material_changed=false，内容是私有草稿。新增断言只在effective patch/extra_tests，复制的public_tests仍是原公开base；缓存public_bundle不含新增节点或测试代码。没有模型调用交付新私有测试；原公开prompt/hints未改。此本地材料检查支持当前分离，**未发布的新consumer实际public/private分流尚不存在，须由正常发布原件核收**，不能现在冒称未来solver输入已经实验验收。

draft_manifest明示 `private_draft_not_publication_or_cpu_acceptance`，12列成员大小/SHA全部吻合。README和清单自身未在12成员内，不是所列测试/修订字节失配，也不将这个draft当完整publication清单。正常正式封包可纳入现有14成员（12 payload＋draft_manifest＋README）及本材料报告/实际v3独立报告，并另列原件证据绑定；发布者须固定新的完整清单与当前字节，并核受信评分替换与公开入口保持原值。该同步条件不构成材料阻断，不要求重审或回写已封旧版本。

随后需要新正式consumer的177参考四行实际安装、收集、逐参考分区和普通test失败判定，再做非作者原件验收。源等价CPU负对照不能冒称旧GPU原FP已经补评分；旧GPU补评分应另用原FP和原baseline在同版本实际安装/评分，不重采Qwen，不删除或改旧结果。任何新正式输入/版本/清单需要按实际发布核收，本报告不预审不存在的内容。当前材料没有需要改题面、扩预算、加新模型求解或额外一般性质矩阵的阻断。

同名JSON保存材料/旧版本/原FP绑定、177参考原序、四候选应用后源码SHA、四项最小性和实际直接输出来源。结论为材料可正常发布，不等同正式177CPU或GPU验收。
