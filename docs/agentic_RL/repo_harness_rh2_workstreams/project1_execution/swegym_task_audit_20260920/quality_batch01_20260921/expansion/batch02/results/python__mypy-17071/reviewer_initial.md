# python__mypy-17071 — reviewer 独立初判

2026-09-21。`disposition.scope=static_review`，`state=needs_review`，`usage.intended_use=development_diagnostic`。公开 bug、源码缺口和 2 个 F2P 的因果关系清楚，建议为静态诊断候选；剩余关键条件是正式 actor 开发入口验证，未验证不标 `ready_for_probe`。

根目录 `${REPO_ROOT}`；下文 `P=runs/swegym_quality_batch02_20260921_v2/public/python__mypy-17071`，`Q=.../private/python__mypy-17071`，`W=runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-17071`。源码行号均相对 `P/base`。`G=W/gold/eval_logs/evallog_replay-er19-iw1-python___9334e4a9.eval.log`；`N=W/noop/eval_logs/evallog_replay-er19-iw1-python___2965a84e.eval.log`。

## 公开需求与初态

题面重复两遍，示例缺 imports/TypeVar 定义且 return 缩进错；目标仍可由签名和明确错误信息确定：`Callable[[Any], TypeGuard[T]]` 参数中的 T 应计入函数的类型变量来源，不能报 “A function returning TypeVar should receive at least one argument containing the same TypeVar”。补齐普通 imports/缩进即可复现，不能把这些排版遗漏算成只能靠隐藏答案解题。公开版本报告 1.4.1，指定 base 为 `4310586460e0af07fa8994a0b4f03cb323e352f0`（1.10 开发版本），不假定版本号差异已修复。

`checker.py:1422–1439` 用 CollectArgTypeVarTypes 遍历形参；该类只覆盖 visit_type_var（7389–7396），继承的 `TypeTraverserVisitor.visit_callable_type` 仅遍历 arg_types/ret_type/fallback（`typetraverser.py:83–87`）。`CallableType` 注释明确 TypeGuard/TypeIs 的目标另存 `type_guard/type_is`，ret_type 为 bool（`types.py:1802–1803`），因此 T 被漏读。N:500–529 两个 case 都因同一额外 UNBOUND_TYPEVAR 错误失败，推理与原始运行吻合。

S2 public/grading/validation 只读精确第 212 行，各对象与本包相等。test.patch SHA256=`3bd1f0adaf901bb07a24fed9578779b45deac88e565f46977997a34bace12c8e`；gold=`fcc697876239908bf4070a03921326432d564c54da43073587fec909aae0467b`，匹配 ledger。未重做全部 blob 审计。

## 需求—断言、选集和回归

| 要求/相关旧行为 | 测试的全部关键断言与公开依据 | 覆盖、结果与限制 |
| --- | --- | --- |
| TypeGuard[T] 出现在 callback 中是合法 T 来源 | F2P `check-typeguard.test::testTypeGuardTypeVarReturn`：`main(x: object, Callable[[object], TypeGuard[T]]) -> T`；负 guard 分支 raise，随后 return x 无错误；`reveal_type(main("a", is_str))` 精确为 builtins.str | 不仅消除报错，还检验 narrowing 与实参推断。object 比题面 Any 更能暴露 return 类型错误。G:522 通过，N:516–529 多 UNBOUND_TYPEVAR。 |
| TypeIs 对应行为 | F2P `check-typeis.test::testTypeIsTypeVarReturn` 同结构，改用 TypeIs[T]，同样推断 str、无多余错误 | issue 未点名 TypeIs，但 base 有相同 CallableType 表示及 `check-typeis.test:85–105,124–133` 的泛型/高阶回调用法；对称要求可从公开源码发现，未见强制 gold 内部细节。G:523 通过，N:500–513 同因失败。 |
| TypeGuard 在普通参数/变量/属性位当 bool | P2P `check-typeguard.test::testTypeGuardIsBool`（base:57–66）三个 reveal：函数参数 bool、变量 bool、成员 bool | G/N 均通过。保护普通 TypeGuard 表示，但不保护“真正缺 T 的返回值仍须报错”。 |
| TypeIs 正负分支 narrowing 保持 | P2P `check-typeis.test::testTypeIsUnionIn`（base:95–105）：str 分支、int else、离开分支回到 Union[str,int] | G/N 均通过。 |
| 真正未绑定的返回 TypeVar 仍拒绝 | 公开 `check-generics.test::testSubtypingWithGenericFunctions`（1593–1621）中 `f2(x:A)->B`、`f4(x:int)->A` 明确要求同条错误 | 已读、未纳入奖励/本次指定运行；这是具体未受保护旧行为，不把普通覆盖缺口直接升级为拒绝题目的理由。 |

读完两个新增 case 的每个语句、全部隐含“无额外输出”要求与 `[builtins fixtures/exception.pyi]`（含 object/int/str/bool/Exception）。`mypy/test/testcheck.py:108–109,163–183` 将片段交给 build.build 并比较诊断；片段 **不作为 Python 执行**。源码 `test-data/unit/lib-stub/typing_extensions.pyi:36–37` 明列 TypeGuard/TypeIs。其它已读旧行为为 `testTypeGuardWithTypeVar`、`testTypeIsWithTypeVar`、两文件 basic/arity/representation 及 TypeIsHigherOrder 的起始用例；未穷读整文件。

执行选集、冻结引用在本题恰为同 4 项：vendor 对 patch 全部 `[case]`（含两段上下文中的 P2P）提取 -k 名称；G:509–526 记录 11 workers [4 items] 和 4 passed。G/N `ledger.jsonl:1` 分别 F2P 2/2 与 0/2，P2P 均 2/2、reference_missing/skipped 空，reward=1/0。没有把 parser 计数当唯一执行证明；同时检查了选集、失败差异与实际 PASSED/FAILED 行。

## gold、替代方案和未覆盖风险

gold 只给通用 TypeTraverserVisitor 增加两个非 None 字段遍历。它修复收集 T 的真实路径，没抹除 checker 的未绑定检查，未见违反本题需求的改动。已追到其他调用者：`FreezeTypeVarsVisitor`（checkmember:847–855）、`TypeVarLikeNamespaceSetter`（tvar_scope:21–37）、`LocationSetter`（types:3486–3495）与 `CollectAllInstancesQuery`（messages:2684–2700）。这些通用访问者也会多遍历 guard/is 目标，符合“遍历全部组成类型”的公开类说明，但现有四项没有专门保护其 namespace、freeze、消息重名及递归边界，不能称全部回归已证明。

合理替代路线是在 `CollectArgTypeVarTypes.visit_callable_type` 局部调用 super 后遍历两个字段，或在此 collector 复用覆盖 guard/is 的完整查询；无需扩大所有 TypeTraverserVisitor 调用者的行为。本题测试不检查类名/文件/调用次数，没有静态误拒证据；该替代未执行。自然但过窄的修复是“见到任意带 guard 的 Callable 参数就跳过 UNBOUND_TYPEVAR 检查”，它会放行 `Callable[[object], TypeGuard[int]]` 搭配不相关返回 T；冻结 4 项不含这个负例。另直接删除整个未绑定检查也可能消掉两个失败，却破坏上述公开 generics 旧断言。应在候选补丁回看或定点 CPU 中检查，不能只凭这类常见漏洞宣布题目无效；没有当前候选实际误评分证据。

## 真实安装、actor 开发与评分边界

`W/image.json` 和 build.log 与 `install_wave1/run_install_wave1.py:24–47` 证实以 public digest `ffc5cb…ed99` 为父，派生 image=`sha256:65be15358f008d20c0dd256c9e70e3f09c85154113ea04875f1a71e98ed751fe`。Dockerfile 只 COPY wheel 并设置离线源；pins 是可用 wheel 清单，**不是强制已安装版本声明**。这里 G:436–495、N:414–473 实际 `pip install -r test-requirements.txt` 后 editable 安装成功，明确使用 typing-extensions **4.8.0**、mypy-extensions 1.0.0、setuptools 68.2.2、types-psutil 5.9.5.17、types-setuptools 68.2.0.0。Python 为 3.12.4、pytest 8.1.1；并行来自 `pyproject.toml:108–111` 的 `-nauto`，日志为 11 workers。不能把推荐/较新版本或“TypeIs 在 4.8.0 运行时不可导入”的推断混入本次环境事实：测试使用源码内静态 stub，且本次真实 4 项已执行。

G/N 各 `ledger.jsonl:1` 的运行身份是 **rh2grader/54322**，网络 deny_all、2 CPU/4 GiB、可写解释器 prefix；observations 导入 `/testbed/mypy/__init__.py`，安装 rc=0。gold 投影仅 `mypy/typetraverser.py`，ignored_paths 空。**apply_user=agent/54321 仅证明补丁应用身份**，未覆盖真正 CC actor 的 shell、工具、激活、权限和可见资产。正式 rollout 仍按 public bundle 取原镜像，不能默认消费这份派生镜像。

| 开发需要 | 公开依据与现有证据 | 缺口/最小验证（未执行） |
| --- | --- | --- |
| 导入工作区 mypy，进入 checker/traverser | traceback 文案；CONTRIBUTING:39–44 的 requirements/editable 安装；实际 grader editable 成功 | 正式 agent shell 打印 UID/HOME/cwd/PATH、sys.executable、mypy 与 typetraverser.__file__；不能只查包版本。 |
| 窄跑类型片段与公开回归 | CONTRIBUTING:65–77 推荐 `pytest -n0 -k`；typing_extensions stub、exception/tuple fixture 都在 base | 运行修正 imports/缩进的题面复现，`python -m mypy`；再 `pytest -n0 mypy/test/testcheck.py -k 'testTypeGuardWithTypeVar or testTypeIsWithTypeVar or testSubtypingWithGenericFunctions'`。隐藏新增 case 不必给 actor。 |
| 准备、安装、资产、资源 | pyproject build-system 和 test requirements；静态片段不需数据库、数据集或服务 | actor 的依赖/激活/离线安装资产未验；无需运行期公网。2 CPU 条件是否沿用 -nauto 要记录实际值，既有 11-worker 单次成功不证明所有 actor 资源档。 |
| 交付源码 | 可在 typetraverser 或 collector 源码修复 | 原官方精确恢复 `check-typeguard.test`、`check-typeis.test`，不覆盖上述源码；`test_globs=()`，无新增排除建议。 |

本题恢复 2 文件的原始自证在 G:249–299。当前机制 `rh2/src/repoharness2/adapters/slime/prepared_task_face.py:185–234,312–338` 是精确文件恢复而非按测试名通配；manager:962,1197–1230 不把普通 rc=1 自动改 reward。源修复不需改被恢复文件，旧 public_hints 的禁改测试不妨碍该路线；其“所有测试改动永不计分”说明及实际消息投递是共享待核项。未做 runner 可写面攻击；没有证据支持本题专门新增路径排除。

关系/泄漏：17071 base `subtypes.py:621–622,1133–1135` 已含本包11236/10308的核心修复，记录为同仓版本交叉暴露，不合并为同题。自身公开 issue 未给 gold 代码，真实镜像可见历史/安装资产的答案内容未核验。推荐用途只限 development_diagnostic。

唯一优先后续：在统一正式 actor 验证中先运行题面复现，并窄查“合法 guard/is T 来源”和“无关 T 仍报错”的正负对照；同时记录实际镜像、解释器/模块来源及资源。无需因四项覆盖有限先要求全仓绿。

## 隔离与阅读范围

本次未参与公开阅读或主审；未读 public_read、主审 analysis/delta/card/screening、I2/history、B1/B2 汇总/manifest/method_adjustments/CPU 队列或其它题结论。environment_record 只见顶层键名，未读摘要/analysis/history 值。已读本题公开包、必要源码/文档/旧测试、完整私有 patch/grading/validation/ref 与指定 image/build/ledger/log。已读同包三题 gold/隐藏测试；10308 的获准 materials 条目含 fixture 修订 decision 摘要，属于本上下文暴露，未据它推断本题。仅静态文件/源码/日志读取、JSON/哈希处理；本次未运行项目、测试、安装、Docker、联网或付费模型，所有 pass 均注明为既有运行。
