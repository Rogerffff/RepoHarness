# python__mypy-11236 — reviewer 独立初判

2026-09-21。`disposition.scope=static_review`，`state=needs_review`，`usage.intended_use=development_diagnostic`。建议为静态诊断候选：公开目标与新增正负断言有实质联系，已有指定 gold/noop 对照可解释；正式 actor 条件及题面原例尚待验证，不能标 `ready_for_probe`。

根目录为 `.`；`P=runs/swegym_quality_batch02_20260921_v2/public/python__mypy-11236`，`Q=.../private/python__mypy-11236`，`W=runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-11236`。源码行号均相对 `P/base`。`G=W/gold/eval_logs/evallog_replay-er19-iw1-python___74f1c394.eval.log`；`N=W/noop/eval_logs/evallog_replay-er19-iw1-python___32643f4f.eval.log`。

## 公开目标、根因与版本

原例返回 `Union[Tuple[str], Tuple[Literal[1]]]`，分支分别返回 `("a",)`/`(1,)`；后者错误被推成 Tuple[int] 而拒绝。要求在联合元组上下文中保留正确字面值信息，并保持不匹配的值/类型被拒绝。题面 expected 小节虽留空，前后原例和报错已经明确。Python-version=3.7、strict 等原 flags 是复验条件，不能用测试默认选项冒称已完整复现。

base=`209a7193feb4bbfa38d09232b0a5a916e9d2e605`。`checkexpr.py:3301–3315` 仅在 Union 里有唯一合适元组时选择上下文，多候选便不给元素精确上下文；`infer_literal_expr_type:2088–2113` 此时生成带 last_known_value 的 Instance。`subtypes.py:243–297` 却没有将这种 Instance 与目标 Literal 比较的分支，tuple subtype 又逐项调用它（332–355）。`Instance` 文档:809–851、`docs/source/literal_types.rst:90–164` 已解释隐式 Final/常量与普通变量的区别，目标可从公开材料推出。N:564–580 在正确 True/False 返回和 Final 元组返回多报错，和根因一致。

精确核对 S2 public/grading/validation **第 187 行**与本包 JSON 一致；未重做整包 blob 审计。test.patch SHA256=`28cffeeb62663944e97404f843da295041b62cc544362293f521a061b5edd087`，gold=`96d1a2e3a08c9f52d7a7ce94fa2de15ee638beba3817cc14394b9426d3f17dc1`，对应指定 ledger。

## 全部新增/修改断言映射

| 公开目标/合理回归 | 具体断言 | 覆盖与证据 |
| --- | --- | --- |
| 联合元组内正确 Literal 分支接受 | 新 F2P `TypeCheckSuite::testLiteralAndInstanceSubtyping` 的 f：`(True,5)`、`(False,'oops')` 均无 error；reveal 为 `Union[Tuple[Literal[True],builtins.int],Tuple[Literal[False],builtins.str]]` | 原例的同根变体，测试“能通过”与返回签名；G:560–572 通过，N:572–573 多报错误。原始 str/int 单元素组合未直接执行。 |
| 隐式 Final 元组与显式 Literal 元组 | `does_work`: `x: Final=(1,)` 返回 Tuple[Literal[1]] 无错；`also_works`:显式 x:Tuple[Literal[1]] 无错 | 有公开 Final 语义和 Instance.last_known_value 注释依据，非隐秘 API。noop 对 does_work 多错（N:575），显式旧路线未额外失败。 |
| 错误字面值不能接受 | `invalid_literal_value`: Final (2,) 返回 Literal[1]，要求 Tuple[int] incompatible return | 阻止“任何保留值都算匹配”的错误修复。 |
| Python 值相等不代表同一 Literal 类型 | `invalid_literal_type`: Final (True,) 返回 Literal[1]，要求 Tuple[bool] incompatible return | 阻止仅比较 `True == 1` 的错误实现。 |
| discriminant 与 payload 必须共同匹配 | `incorrect_return1`: `(False,5)`、`(True,'oops')` 两支各报与完整 Union 不兼容 | 阻止只按分量分别匹配 Union 后忽略跨元素关联的修复。 |
| 普通 bool 不能当已知 Literal | `incorrect_return2`: `(bool(),5)`、`(bool(),'oops')` 两支均报错 | 拒绝没有 last_known_value 的非字面量；fixture bool 继承 int，但无已知 Literal 值。 |
| 旧 Final 嵌套元组调用行为更新 | `testLiteralFinalGoesOnlyOneLevelDown`（base:2677–2696）保留 a/b 的 `Literal[1]?`、`Tuple[Literal[1]?,Literal[2]?]` reveal，删去 force1(reveal_type(a))/force2(reveal_type(b)) 的旧输出/旧错误，改成 `force1(a)`、`force2(b)` 均无错 | 已逐项读，但**未被执行、未在冻结奖励引用**。这是原先标注 TODO 的行为修订，符合新子类型关系；不能把“测试补丁修改了它”当运行保护。 |

F2P 共 1、P2P=0；一个 F2P 内有上述多个正/负例，不能按“只有 1 条”或 P2P=0 判空洞。`test-data/unit/README.md:28–46` 定义 no-error、E/N、out 语义；`mypy/test/testcheck.py` 运行 build 并比较诊断。已读 fixture `bool.pyi:1–19`、旧 case 的 tuple fixture指令，未假定真实 Python 执行这些片段。N 的 diff 显示 `...` 是 helper 输出截断，不代表最后两条负例被删；本次以完整 test.patch 判断其断言，以完整 case PASS 判断历史结果，不反推出逐子断言运行事件。

执行选集与阅读范围不同：vendor 用补丁中的 `[case]` 名拼 -k；修改旧 case 的第一 hunk 没带其 `[case]` 头，因此 G:560 / N:546 **仅选 `testLiteralAndInstanceSubtyping`**，G:565 9846 collected / 9845 deselected / 1 selected。G/N `ledger.jsonl:1` 分别 F2P 1/1 与0/1，P2P=0、reference_missing/skipped为空，reward 1/0。上述旧修改断言、额外阅读的 mutable/Final 回归不属于该事实。

## gold、合理替代与回归范围

gold 仅在 SubtypeVisitor.visit_instance 中遇右 Literal 且左 last_known_value 非空时，将比较委托给该 Literal。`visit_literal_type:397–401` 走 Literal 等价，`LiteralType.__eq__:1628–1631` 比较 fallback 和值，故不会把 True 当 Literal[1]；没有值的 int/bool 仍走旧拒绝分支。`checker.py:2227–2231` 在非 Final 变量推断时擦除 known value；`erasetype.py:134–151` 递归清除。已读旧 `testLiteralFinalErasureInMutableDatastructures1/2`（2618–2645）、`testLiteralFinalMismatchCausesError`（2647–2675）、`testLiteralFinalCollectionPropagation`（2698–2725）：普通 list[int] 不能转 List[Literal[1]]、Final 也不应让 mutable 容器永久保留字面值。未见 gold 破坏这些的直接静态证据；指定运行未执行它们，proper subtype、enum、overload、缓存/增量与全仓调用未穷查。

合理替代可在 tuple subtype 比较时，对待匹配 Literal 的元素按已知字面值比较，仍保持值与 fallback 两者等价；它解决公开 tuple 需求且处理 Final 元组，不必把变更放在 gold 的通用 Instance 分支。也可改善 Union 元组的上下文推断，但若只照顾现场 tuple expression，会漏掉 F2P 的 Final 变量返回；不能因修好原例就宣称完整测试行为已满足。测试没有内部 helper/mock/顺序要求。错误字符串精确属于仓库既有诊断约定，暂未发现合理实现被错拒的具体证据；替代路线未执行，特别是错误类型打印是否保持需验证。未经对照不能把全局“都保留 Literal”或 Python 值相等判断当有效替代解。

## 安装、开发条件、交付边界

W/image.json + build.log（实际完整阅读）确认 public digest `6b6a59…9cc9e` 派生 image=`sha256:853ffff2219f5167a87f7f310b17b8362d098f66745c20d0406c44c2c708edd0`。通用 `install_wave1/run_install_wave1.py:24–47` 仅把 setuptools75.1.0、wheel0.44.0、packaging24.1 wheels 复制并设离线环境变量；没有强制安装 pins 的 Docker RUN。G:472–548 / N:458–534 的实际 install 则明确 requirements 和 editable 安装成功：Python3.9.19、types-typing-extensions3.7.3、typing_extensions4.12.2、mypy_extensions0.4.4、setuptools75.1.0、pytest6.2.5。base test-requirements 没有最前 pin；G:286–294 的初态 diff 和实际安装显示镜像已有 test-requirements 的 pin 改动，不能将“静态 base 完全干净”外推到真实镜像初态。该变动不是本题 test.patch 修订。

ledger 的实际身份为 rh2grader/54322，deny_all、2 CPU/4GiB，解释器 prefix 可写；import observation 为 `/testbed/mypy/__init__.py`，gold 投影只含 `mypy/subtypes.py`。apply_user=agent/54321 只是应用补丁，未验 actor 的真实 shell/CC/PATH/依赖权限。正式 face 根据 public bundle 使用原镜像，本次 install_wave1 派生镜像的环境成功不能自动算 actor pass。

| 开发操作/资产 | 依据与证据 | 缺口与最小验证（未运行） |
| --- | --- | --- |
| 定位与调用工作区 checker | 公开原例；checkexpr tuple 路径；`test-data/unit/README.md:47` 的 `pytest -n0 -k` | 正式 agent 身份打印 UID/HOME/cwd/PATH、sys.executable、mypy 与 subtypes.__file__，确认工作区 `.py` 生效。 |
| requirements、纯 Python 源码及 fixtures | setup.py:77 起默认 USE_MYPYC=False；typeshed 位于仓库；bool/tuple 和 typing_extensions stub 为受控静态输入 | grader 的 editable 安装可解释，actor 激活与依赖仍未知；一般无需本题专用编译器/数据集/服务。离线准备即可，不要求运行期联网。 |
| 原例与回归验证 | 题面 Python3.7/strict 配置；Final、mutable 公开旧测试 | `python -m mypy --python-version 3.7 --strict --warn-return-any /tmp/issue11236.py`；窄跑 `pytest -n0 mypy/test/testcheck.py -k 'testLiteralFinalGoesOnlyOneLevelDown or testLiteralFinalCollectionPropagation or testLiteralFinalErasureInMutableDatastructures'`，分别保留 base/gold/candidate 结果。 |
| 提交和恢复 | 合理源码改动可位于 subtypes 或 checkexpr | 官方仅恢复 `test-data/unit/check-literal.test`。`test_globs=()`；不把所有测试文件一概剔除。修复本身不需要改被恢复文件或系统包。 |

当前 RH2 `prepared_task_face.py:185–234,312–338` 精确恢复官方文件，再以 grader 安装/测试；G:295–335 的原始自证确认本题 1 文件。`manager.py:962,1197–1230` 区分普通 rc=1 与全局失败，未引用失败不会仅凭 rc=1 自动改为 reward0。P2P=0 的限度是冻结回归面窄；本报告没有据此新增文件排除或给通过解开绿灯。public_hints 的“所有测试修改永不计分”是共享说明偏差，实际消息投递尚未核；source-only 合法路线仍可遵守禁改测试要求。

题目关系：本题 base `subtypes.py:543–550` 已有10308成员预检；17071 base `subtypes.py:621–622` 已有本题 gold 的核心分支。记录同仓跨版本答案接触，不据此判同问题重复。题面未给 gold 修法；真实镜像祖先、可见源码副本/安装缓存的答案可达性未验，静态导出无 `.git` 不能代表无泄漏。

优先后续：统一 actor 条件验证时，用题面原例和少量 Final/mutable 旧用例作正负对照，尤其补查已修改却未执行的 `testLiteralFinalGoesOnlyOneLevelDown`；已有 F2P 负例有实质约束，无需机械造额外攻击或把全仓通过设成前置门槛。

## 隔离、暴露和证据层级

未读 public_read、主审 analysis/delta/card/screening、I2/history、B1/B2 汇总/manifest/method_adjustments/CPU 队列或其他题结论。environment_record 仅读取顶层键名，未读取其摘要/analysis/history内容。读取本题完整公开包/patch/grading/validation/source_refs/run_refs、上述必要源码文档旧测试，以及 W 的 image/build 和 G/N 对应原账本日志。已看到本包另两题的 gold/隐藏测试；10308 获准 materials 条目的 fixture decision 摘要在同上下文暴露，未用于预设本题结论。所有运行结果为 09-19 既存 RH2 证据重读，本次仅静态和元数据/哈希检查，未运行项目/测试/安装/Docker/联网或模型。未穷尽所有合法解与回归，不称盲解或正式训练/评测批准。
