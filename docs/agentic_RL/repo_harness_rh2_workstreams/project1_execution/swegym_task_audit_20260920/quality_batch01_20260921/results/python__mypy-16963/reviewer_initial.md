# python__mypy-16963 — reviewer 独立初判（封存）

日期：2026-09-21。范围：static_review / development_diagnostic。本文件在读取任何本轮其他角色结论及质量历史之前写成；写成后不回写，后续分歧另记 review.md。

**初判：needs_review。有可用的历史 grader 正负对照，但暂不把本题作为“完整公开需求已覆盖”的优先模型探针。** 唯一 F2P 有实质的正负行为保护，不因 P2P 为空判题无效；更重要的缺口是未观察构造结果的返回类型、未覆盖题面 Union/传参/完整 Car–Boat–Truck 复现。gold 对 total=True 的 Type[TypedDict] 调用有合理修复路径，但原题 Boat 的推断路径及非必填字段存在具体静态疑点。优先做原题完整复现的 base/gold 定点对照，再决定原需求是否已修完。

## 暴露、执行与材料身份

- 我是独立 reviewer，未参与两题主审。在同一上下文读 python__mypy-16963、python__mypy-12417 的原始公开与私有包；两题全部初判封存之前，不读任一题主审/公开读者/历史结论。
- 已读本题 user_prompt.txt、public_bundle.json、base_identity.json、environment_brief.md；全部 test.patch、gold.patch、grading.json、validation.json、run_refs.json、source_refs.json、environment_record.json。environment_record 中的 verified_environment_pair、reward 汇总和 analysis/history 路径已暴露；**未沿这些链接打开旧汇总**。
- 已读角色卡、环境卡、记录模板、共用协议；按下文列出的源码、旧测试与 fixture/helper 抽查。未读 public_read、analysis_before_history、old_findings_delta、card、screening_record、其他 review、质量 history、manifest、主计划或 method_adjustments。查找配方脚本时只列过 runs/env_recipe_repair_20260919 中文件名，未读其他题 build.log。
- 本轮只执行文件读取、JSON/文本一致性、SHA-256 元数据核对及本文件写入；**未执行 mypy、pytest、安装、Docker、SSH、模型或任何新反例实验**。下文“历史运行”均为重读冻结的 09-19 原件。
- public/base_identity 与 grading 的 base 一致：f19b5d3a026319687dd81a5c7c976698bbe948a8，版本 1.10；导出 tree dcd12f0f6cf5c8364b6081eac627a7a926d12b48，无 .git。issue 自报 0.910/Python 3.9.7，是原报告年代，不能借此直接判材料错配。
- 当前元数据核对：test.patch 等于 grading 嵌入 test_patch；gold.patch 等于 validation 嵌入 golden_patch，gold SHA-256 等于 a720daacbae641e02da46ff5589db942622c393497b92fd7a763857be085050d；两个原始日志哈希同时匹配 run_refs 与各 ledger。未重新验证整个导出 tree，blob_bytes_verified 是材料自报。

## 公开需求与初始问题

公开目标不只是让一个调用不报错。题面小例（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/user_prompt.txt`）要求把 TypedDict 类传入 type[D] 参数后调用，返回值仍是 D；Union 小例（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/user_prompt.txt`）要求 type[Union[int,D]] 同样工作；完整复现（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/user_prompt.txt`）把 dataclass 与 TypedDict 构造器用于 Car 显式参数、Boat 条件表达式推断、Truck 显式属性注解，使用 --warn-return-any，期望全部无错误。题面后段只把 NamedTuple 替换后的另一个返回值问题称为“可能另一 bug”，并未明确删除原 TypedDict Boat 目标。

base 中 check_call(TypeType)（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/checkexpr.py`） 调用 analyze_type_type_callee（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/checkexpr.py`）；已有 Any、Instance、Union 递归、TypeVar、NamedTuple 分支，TypedDictType 落入 unsupported_type_type 并返回错误 Any。这与历史 noop 具体失败相符，不是只由 gold diff 倒推 bug。

传入类对象的另一部分已有公开代码基础：TypedDict 类对象识别（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/checkexpr.py`）返回带 builtins.type fallback 的 callable；Callable 到 Type 子类型关系（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/subtypes.py`）比较返回类型与 Type.item，is_type_obj/type_object（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/types.py`）支持 TypedDict fallback。这说明不能假设题面 0.910 的全部传参错误在当前 base 都仍存在；是否已消失须实际复现。

## 测试执行链与全部新增断言

test.patch 只向 check-typeddict.test 增加 testInitTypedDictFromType，一个 F2P，P2P=[]。完整新增 case（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/private/python__mypy-16963/test.patch`）没有调用 func(Point)，也没有检查 cls(...) 的结果。runner 链已读：

- TypeCheckSuite 收集（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/test/testcheck.py`）从 check-*.test 收集；DataFileCollector（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/test/data.py`）拆成 pytest item。无 skip/xfail 或外部服务。
- fixture 装配（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/test/data.py`）将 typing-full.pyi、tuple.pyi 复制为临时 typing/builtins stub；已读两文件全文（201/55 行）。TypedDict、Type 是 mypy 特殊形式，_TypedDict fallback 为 Mapping[str,object]，不是伪造 mock 结果。
- setup（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/test/data.py`）创建临时目录；expand_errors（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/test/data.py`）把 E/N 注释转成带行号的期望诊断；run_case_once（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/test/testcheck.py`）实际 build.build，再于第 195 行比较整个诊断数组。无注释的合法调用也受“不得额外报错”保护。这里执行的是 mypy 对片段的静态检查，不是运行片段中的函数。
- parse_options（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/test/helpers.py`）未设置 warn_return_any，使用默认目标 Python 3.8（测试默认版本（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/defaults.py`）），而历史 runner 自身是 Python 3.12.4；必须区分运行解释器与被检查语言版本。

| 需求或旧行为 | 公开依据 | 测试及决定性断言 | 覆盖与证据层次 |
| --- | --- | --- | --- |
| 保留参数 cls 的 Type[TypedDict] 类型 | 题面 type[D]；既有 Type[C] 行为 | F2P reveal_type(cls) 必须含 Point 的 x/y:int（test.patch:17） | 覆盖参数注解展示；不观察构造结果。noop 原本已满足此行。 |
| 合法 keyword 调用 | 题面 Car/Truck；typed_dict 文档构造器 | F2P cls(x=1,y=2) 无额外错误（:18） | 正行为覆盖；历史 noop 此处 Cannot instantiate，gold 通过。 |
| 拒绝两个位置参数 | 旧 check-typeddict.test:47–50 | F2P cls(1,2) → Too many positional arguments（:19） | 负行为覆盖；防止把整个 callee 直接降为 Any 的无约束修法。 |
| 必填 y 不可省略 | typed_dict.rst:115–121；旧测试 :66–69 | F2P cls(x=1) → Missing named argument “y”（:20） | 负行为覆盖；仅 total=True。 |
| 不接受额外 key | 旧测试 :60–63 | F2P 多传 error → Unexpected keyword argument “error”（:21） | 负行为覆盖；无具体 helper 名/Mock 绑定。 |
| 结果仍是 D、可返回 D 而不触发 no-any-return | 题面 f 与 --warn-return-any | 无返回值 reveal/赋值约束，也无该 flag | 缺失；保持参数诊断但把新 callable.ret_type 改为 Any 的错误候选，静态预计仍满足唯一 F2P，未执行。 |
| 真实传入 D、Union 构造与原例三类 | 题面 f(D)、g(int/D)、Car/Boat/Truck | 无对应输入 | 缺失；gold 通过不能证明这些整体要求。 |
| 错误字段值类型、empty D、可选字段、单 dict 参数构造 | 公开旧构造测试和 totality 文档 | F2P 均未覆盖 | 有来源的边界，不是为测试凭空加规格；需区分题面直接目标与合理扩展/旧行为。 |

F2P 不只是一个“无崩溃”检查：它有合法调用、三个不同参数错误、一个类型展示。其保护范围仍不足以推出返回类型、Union 或旧 Type 语义均正确。

## gold、替代实现与回归

gold（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/private/python__mypy-16963/gold.patch`）仅为 TypedDictType 接入已有 typeddict_callable_from_context。该 helper（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/checkexpr.py`）保留字段类型、字段名、返回 TypedDict 类型，生成全部 ARG_NAMED，再由正常 callable 参数检查执行。它未改其余分支、runner、fixture 或安装文件；未见“还需另一个未交付源码改动”才能过给定测试的证据。

独立核出的具体限制：

1. **原例 Boat 高可信静态漏修疑点。** 条件表达式（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/checkexpr.py`）在没有 Union 上下文时用 join；dataclass 必填字段（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/plugins/dataclasses.py`）为 ARG_POS，TypedDict 类对象的字段在 checkexpr.py:938 为 ARG_NAMED。min_args（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/types.py`）只数 ARG_POS，两构造器的 min_args 不同，is_similar_callables（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/join.py`）不接受，join fallback（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/join.py`）会退到 type；type.__call__（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/typeshed/stdlib/builtins.pyi`）返回 Any，再由 warn_return_any（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/mypy/checker.py`）报错。gold 只改 TypeType 调用，不改这条推断路径。预期原例 Boat 仍有 no-any-return；这是完整链条静态推断，尚无本题原例的执行对照，故不写“已证实 gold 错”。
2. **非必填字段支持不完整。** helper 不检查 required_keys，故 type[PartialTD] 的 cls() 静态预计仍被要求传入所有字段；gold 从完全不支持进入“只支持全字段”的状态。total=False（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/docs/source/typed_dict.rst`）、混合必填字段（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/docs/source/typed_dict.rst`）和 旧 constructor 测试（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/test-data/unit/check-typeddict.test`）允许省略非必填字段。应称新支持范围不足，不声称把 base 原本已成功的 Type[PartialTD] 用法回归坏。NotRequired/继承混合项亦未测，未执行。
3. **返回 Any 的得分缺口候选。** 在新增分支保持 helper 的名字/种类/参数类型，只把返回类型换为 Any，会保留本 F2P 的四条输出，却违反题面“不要 no-any-return”的目标；需要同一候选的公开复现与 RH2 得分对照，静态不能填“已获分”。
4. **替代解接受性尚未证毕。** 可以在 TypeType 调用处重用 TypedDict 专用参数检查，或构造等价 callable，而不强制调用 gold helper。后者满足同样输出无需相同内部结构。前者可能对错误参数沿用公开直接构造器的 Missing key/Extra key 文案，因精确字符串被拒；尚未制作/执行完整替代解，不据此直接判误拒。已有文案约定支持参数错误本身，不能把所有精确诊断都算过严。

实际抽查旧行为：check-typeddict.test:1–76 的 keyword/dict/empty 构造与错参、1072–1095 的 total=False、1511–1530 的类对象 callable 展示、1533–1554 的 **TypedDict、2621–2655 的泛型；check-classes.test:3272–3333 的普通 Type/TypeVar 构造、3390–3443 的 Union/Any、3524–3581 的 tuple 拒绝和 NamedTuple 参数检查。**这些旧 case 均不在本题 P2P，未在所读历史命令中运行。** gold 的分支局部性给出有限回归信心，不能替代回归执行。没有穷举所有公共调用者、插件生成 TypedDict 或泛型边界。

## 环境证据与开发条件

配方 image.json（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963/image.json`）从 public digest 81e0da8d…52f8c 派生 ab5d4a17…71add；只复制离线 wheel 并设置 PIP_NO_INDEX/PIP_FIND_LINKS。逐题 pins：setuptools 68.2.2、wheel 0.43.0、typing-extensions 4.8.0、mypy-extensions 1.0.0、tomli 2.0.1、types-psutil 5.9.5.17、types-setuptools 68.2.0.0、packaging 23.2。未借用 12417 的 setuptools 72.1.0 配方。共用构建段 23–58（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/run_install_wave1.py`）核 base image ID、保留原 layers、将 derived image 显式交给 replay_grade；build 原件（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963/build.log`）记录同一 digest、wheel COPY 和最终 image ID。

- 冻结 noop ledger 第 1 行（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963/noop/ledger.jsonl`）：rh2grader/54322、2 CPU/4 GiB、deny_all、可写 conda 前缀；安装 rc=0，test rc=1，reward=0，F2P 0/1，P2P 0；runner integrity 未变。noop 原始测试段（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963/noop/eval_logs/evallog_replay-er19-iw1-python___45f93b0f.eval.log`）实际运行 1 item，诊断显示四个调用均 Cannot instantiate，不是依赖/收集故障。
- 冻结 gold ledger 第 1 行（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963/gold/ledger.jsonl`）：相同 image/profile，安装 rc=0，test rc=0，reward=1，F2P 1/1，P2P 0。editable 安装及测试段（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963/gold/eval_logs/evallog_replay-er19-iw1-python___152064d5.eval.log`）安装 /testbed 本题版本，实际 pytest 7.4.2/xdist 3.3.1、Python 3.12.4，11 workers 跑 1 item，1 passed。账本 import_path=/testbed/mypy/__init__.py；gold 仅 checkexpr.py 投影入评分。
- 历史峰值内存约 821/836 MiB、测试 15.003/16.859 秒是该 grader 记录；11 workers 来自 -nauto，不等于当前 actor 的 2 CPU 配额内一定相同。没有新资源测量或真实模型成本。
- **actor 未验**：正式 public image 仍不同于上述 derived image，未证明这份离线 wheel 配方被本次 actor 消费；agent/54321 的 PATH、Python、可读资产、安装可写前缀、可见 git/环境提交均未知。environment_record 的 verified_environment_pair 不外推为 actor pass。

| 必需开发操作/资产 | 公开依据及已有范围 | 当前缺口与最小待验 |
| --- | --- | --- |
| 定位并编辑源码 | 题面复现；check_call→analyze_type_type_callee；贡献说明（仅本地运行证据：`runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963/base/CONTRIBUTING.md`） | 入口可静态定位；实际 shell 中 cwd、源码权限待验。 |
| 当前工作区导入、运行复现 | CONTRIBUTING 的 editable install；setup.py:88 默认纯 Python、:221 runtime deps | 用 agent 实际 shell 打印 sys.executable、mypy.__file__，确认修改会生效。无需假设必须编译 mypyc。 |
| 测试工具与资产 | pytest、xdist、仓库 fixture/typeshed；gold 历史离线安装已完成 | 准备阶段固定依赖即可；未发现此复现需公网、服务、权重或数据库。actor 的离线 wheels/依赖可达性未知。 |
| 最小公开验证 | 题面 --show-error-codes --warn-return-any；CONTRIBUTING:74 可 -n0 | actor 上先运行原题复现，再跑选定公开 TypedDict/Type case。隐藏 F2P 不需提供 solver。 |
| 可交付修改 | mypy/checkexpr.py 已在历史 gold projection；官方恢复仅 test-data/unit/check-typeddict.test | 修业务无需改会被恢复的测试/系统文件。临时复现与 cache 非交付项；不要用改变 runner 代替语义修复。 |

## 八方面结论与边界

| 方面 | 实际核查与结论 | 未知/未执行 |
| --- | --- | --- |
| 公开需求 | 全部 issue、公开 hints/环境说明及相关文档；多目标明确 | 真正 CLI system/user 渲染及 hints 应用未知。 |
| 材料/初态 | base 元数据、补丁嵌入、hash、noop 具体诊断相符 | 未重跑原题全部复现，未逐 blob 验证。 |
| 测试测量 | 全新增 case、runner、两 fixture；正负行为逐项展开 | 返回类型/Union/完整复现、错误字段类型和非必填项缺测。 |
| 合理解接受 | 未绑定内部 helper；比较精确诊断的可接受范围已查 | 专用 TypedDict 检查路线可能文案误拒，待完整替代解验证。 |
| 回归/gold | 读局部调用链和上述旧测试；Boat、可选项具体疑点 | P2P 空不等于坏题，也不提供上述回归的执行保护。 |
| 开发条件 | 逐题 recipe/build/ledger/日志与公开入口核对 | actor 派生配方、解释器、权限、资源待验。 |
| 交付评分 | test.patch 纯 .test 数据；gold 纯业务源；恢复/投影原件一致 | 未重新审整条 parser/隔离/清理机制、未查真实镜像全部答案资产。 |
| 关系/用途 | 16963 base 的 checkpattern.py:520–522 已含 12417 同形修复，属版本继承线索；两题目标不同，不据同仓合并 | 无 git 祖先证明，不推断训练收益/基座成功率；本审查上下文已见 gold，不可作盲 solver。 |

公开 hints 的“所有测试修改都会恢复”与本批环境说明指出的当前边界不完全一致；本题业务修复不依赖改测试，因此不构成已知阻塞。官方恢复的准确路径见 恢复日志（仅本地运行证据：`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963/gold/eval_logs/evallog_replay-er19-iw1-python___152064d5.eval.log`）；无法据此宣称全部其他 runner/config 路径都冻结或都可安全改动。

**最小后续实验（均未执行）：** 在本题同一 pinned 配方下对 base/gold 运行题面原始小例及完整 Car–Boat–Truck，保留 --warn-return-any；同时记录每个报错位置和返回类型。若 Boat 仍错，再核这是任务需补齐的原目标，还是需明确收窄公开目标。其后才比较“仅把新 callable 返回类型改成 Any”的候选在公开复现与唯一 F2P 上的差异；total=False/NotRequired 为下一组有公开依据的边界。实际模型探针另需共享 actor 身份验收，不把以上静态条件写成 ready_for_probe。

