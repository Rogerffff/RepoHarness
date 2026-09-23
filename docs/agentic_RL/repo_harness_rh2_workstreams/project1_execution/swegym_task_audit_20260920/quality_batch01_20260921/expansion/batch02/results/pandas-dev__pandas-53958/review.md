# pandas-dev__pandas-53958：独立复核

2026-09-21，B2 pandas reviewer，第二阶段。**建议保留受限静态候选：`state=needs_review`、`scope=static_review`、`intended_use=development_diagnostic`。** 同意主审保留目标命名空间未定和导出对象身份漏检两个独立问题；历史 grader 的正常 0/1 对照不消除它们。下一步优先级与主审不同：本 reviewer 优先验证把单例值误导出为类型是否仍能得分，理由见末节。不是正式训练、评测或 actor 启用批准。

`ROOT=.`，以下相对路径以 ROOT 为根；`I=runs/swegym_quality_batch02_20260921_v2`，`B=I/public/pandas-dev__pandas-53958/base`，`P=I/private/pandas-dev__pandas-53958`。第一阶段初判 SHA256 `37a082fbe5196cde0fcb56636246c63a68b6f77a6d362decc358874f5e7707b3` 保持不变。全部三题封存后才读本题五份主审/公开成品和 history/refs 所指唯一旧记录。仅静态文件、JSON、文本核对；未项目导入、测试、安装、容器、联网、模型，未改 source/test/gold/reward。

## 主审决定性论据的独立核对

| 主张 | 原件核对及判断 |
| --- | --- |
| 公开材料允许两个候选位置，没有公开最终选择 | `user_prompt.txt:3–14` 先问向 `_libs` 增加 NAType，随后以 Another option 提出 api.typing。`B/doc/source/reference/index.rst:21–25` 支持 typing 作为公共入口的适宜性，但没有撤销题面明确提出的另一选项。同意保留规范选择疑义。 |
| 唯一 F2P 只接受 typing 方案 | `P/test.patch` 仅向 allowed_typing 增加两名字；`B/pandas/tests/api/test_api.py:18–30,342–343` 比较去掉双下划线/annotations 后的 dir 名称。`_libs` 单独补真类导出而 typing 不变，静态上仍缺两名字。运行可确认后果，不能替代“该方案应否被接受”的规范判断。 |
| 名称相等未验证导出的是类型 | helper 只收集字符串，没有读取新属性对象。第一阶段已完整读全部 11 个测试、typing/_libs 导出、missing/nattype 定义及 pyi、相关注解调用者；无新类身份或类型用途断言。确认具体观察缺口。 |
| 精确名称比较不是隐藏的新内部实现限制 | 同一 Base.check 和旧名称表已在公开 base。可从不同模块重导出相同真类，gold 不是唯一导入写法。旧报告说 solver 看不到这项约束不成立；无需仅因精确比较就改成包含关系。命名空间选择争议另列。 |
| Gold 自洽 | 只在 `pandas/api/typing/__init__.py` 重导出已有真类并加入 __all__；原定义、单例和旧入口保留。历史 11 项通过支持可运行，未发现具体循环导入或旧行为回归。它实现一个合理方案，不证明该方案是题面唯一选项。 |

公开目的是类型注解所需的真实类型，不是两个可见字符串。`missing.pyx:370` 定义 NAType、`:543–544` 构造 NA；`tslibs/nattype.pyx:359` 定义 NaTType、`:1417–1418` 构造 NaT，pyi 与现有 `_typing.py`/cast.py 注解支持这一解释。在选定入口直接检查 `NAType is type(pd.NA)`、`NaTType is type(pd.NaT)` 不扩大成外部 stubs/checker 的新要求。

本 reviewer 初判已提出的自然错误候选仍有效：typing 把 `pandas._libs.NaT` 重导出成 NaTType，把 `pandas._libs.missing.NA` 重导出成 NAType，导出名单完整保留。它混淆值与类，名称表却仍可能完全满足。没有修改 helper、伪造状态或硬编码节点的必要；本轮没有写/运行该候选，不能填“已证 reward1 假阳性”。漏填 typing.__all__ 是另一个自然部分实现，但其影响不如把实例当类型直接，不作为独立必测。

## 三套集合与旧回归

| 集合 | 本题范围 |
| --- | --- |
| 实际历史执行 | `pytest -rA --tb=long pandas/tests/api/test_api.py`，11 collected。noop 10 passed/1 failed；gold 11 passed。 |
| 冻结参考 | 1 F2P + 10 P2P，恰为这 11 项，无参数化别名碰撞，missing/skipped 为空。 |
| 本 reviewer 实际阅读 | 第一阶段完整读 test_api.py 全文、全部 11 方法、名称表及 helper；类型定义、导出和注解调用者的范围见 reviewer_initial。第二阶段复读 Base.check、_libs 初始化及 `test_na_scalar.py:1–48`、`test_nat.py:96–101` 参数/断言。没有全仓测试阅读或执行。 |

10 P2P 保护顶层 pandas、api 子包、types/interchange/indexers/extensions/testing 等名称和顶层 pd.__all__；后者不是 typing.__all__。test_depr 的三组列表为空，实际不执行弃用断言，不把它记作新类型旧行为已验证。新补读的 scalar singleton/NaT identity 检查旧对象，根本不读取 api.typing 的新名字；即使这些额外测试通过，也不能替代新入口身份检查。它们没有在本次历史评分命令中执行。

以上既足以识别具体漏检，也保留界限：没有主张本题必须通过全仓缺失值运算、全部类型检查器或文档构建。其它普通未覆盖边界不自动构成坏题。

## 原始运行与开发条件

原始证据为 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-2/ledger.jsonl` **第 11 行 noop、第 12 行 gold**，对应同目录日志 `eval_logs/evallog_replay-f216-baseline01-w_a8d9ae3e.eval.log`（N）和 `...w_eed61475.eval.log`（G）。第一阶段已核完整 11 条状态、目标失败/通过、源码投影和收尾；不是重读主审总结就算独立验证。

N 的 F2P 失败直接报告 typing 名称 16 对 18、缺 NAType/NaTType；gold 全 11 项通过。两账本 F2P 0/1→1/1、P2P 10/10，reward 0/1。这只说明该 oracle 正常接受 gold，不是对两个质量疑点的回答。没有参考 ID 修复需求；段外 parsed=1 与段内 11 分开。

主审新增的依赖元数据边界有原件支持，本轮复读 G:3034–3069：Meson 增量仅生成 version，editable wheel 构建安装完成；G:3057–3058 同时有 xarray 2024.9.0 要求 pandas>=2.1、当前 dev 版本不满足的 resolver ERROR，随后 Successfully installed 和安装 rc0。它不阻断本题运行，但不能称整个环境 pip check 健康；该安装段 ERROR 也不是第 12 个目标测试。当前 v2 只解析测试标记段，当前机制源码不被用作旧 runner 的同字节认证。

历史安装约 gold 8.073/noop 9.152 秒、测试约 4.5 秒只是这两段和已有缓存条件，不是完整评分总时长、actor 冷构建成本或模型成本。原镜像 identity 使用公开 digest，image_id_actual=null，不补写实际 Docker ID。运行身份是 grader/54322、deny_all，有其安装/build 权限；apply_user/54321 只表明候选应用，不是开发会话。

正式 public-image actor 需在真实 shell 核解释器、checkout 来源、原 C 扩展导入以及 editable loader/build 目录权限。该修复是 Python 重导出，已有扩展健康时不必完整重建 Cython；若 loader 触发 ninja，仍要实际验证写权限和加载来源。题目本身不需 GPU、数据、远程服务或外部 checker 资产；pandas-stubs 是动机，不是已指定验收环境。

## 交付、控制面与历史差异

当前 `prepared_task_face.py` 用官方 test.patch 精确路径、`test_globs=()`；只恢复 `pandas/tests/api/test_api.py`，再应用两名字的官方更新。typing 或 _libs 的正常源代码路线可提交，`additional_exclusions=[]`。公开旧测试会因正常增加 typing 名字而暂时失败，官方恢复后的新名单才是该历史验收；这不证明必须让 solver 修改受保护测试。harness 禁改测试指令及实际消息/工具仍需在启用时核实，不因渲染未含全部 hints 就认定它不可见。

普通完整 pytest rc1 不自动 reward0；本题预期 `_libs` 方案会令唯一参考 F2P 失败，分数推断来自这个参考失败，不能只靠总退出码。共享 stdout 伪状态等控制面没有本题攻击运行；名称对应对象漏检是正常断言观察不足，不与 parser 注入混为一谈。零解析、全参考缺席或全局故障按 scoring/manager 另判。

旧记录只读 `env_overnight_20260916/L1_modin_pandas/records/pandas-dev__pandas-53958.json`。另按本题引用精确提取 `s2/raw/swe_gym_lite_full_f70b1a29.jsonl:169`，hints 为 `Adding to typing makes sense to me.`；这比题面多一个赞同意见，却既未进入当前 public_hints，也不是明确排除另一方案的最终决定。主审不把它冒充 actor 已知，正确。

同意不采纳旧“给出两条 import 就是严重答案泄漏、训练价值极低”的结论：这两条是描述现有工作入口的必要内容，方案方向明确和补丁小不等于未来答案污染或已测模型容易。也不倒过来宣称真实镜像/Git 或预训练绝无泄漏。旧相邻 scalar/dtypes 建议不能填成实际运行回归，且即使运行也未必检查新导出身份。

阅读/暴露边界：第一阶段已读授权 environment_record 的环境摘要，未跟进其聚合质量历史；第二阶段才读本题旧质量正文和主审产物。没有读批次聚合，未把另题主审的有界阅读偏差归给本题新主审。本 reviewer 的三题原件范围还确认 56849 base 已含本题类型导出，本题 base cast.py:626–631 已含 48106 的分类分支；这是具体跨版本暴露关系，三题不是同一缺陷。主审未核跨题关系的范围可由此补充，不能反推其已知。本上下文已见 gold、隐藏测试、历史及跨版本答案，不得交给盲解 solver。

## 保留分歧与唯一优先下一步

主审优先 `_libs` 单独真类重导出对照，本 reviewer **继续优先固定 grader 的 singleton 误导出对照**。原因有二：`_libs` 导出正确但 typing 名称仍缺的验收结果已能从唯一断言直接推知；即使实际得 0，也不能用分数裁决题面是否应接受该公开候选。规范选择仍需依据当时公开决定或清晰、版本化的任务定义。相较之下，把单例当类型若能得分，会直接证明同一 typing 方案中一个不依赖命名空间争议的错误实现被接受，信息增量更高。

**唯一下一实验（未来 CPU，未执行）：**固定同一 grader、官方 test.patch 和冻结参考，对 gold 与“typing 名单/__all__ 齐全但两个名字绑定 NA/NaT 单例”的自然错误候选取实际 RH2 分数，同时在新入口直接核两个真实类型身份和基本类型用途，记录加载来源。若错误候选官方通过而身份检查失败，才确认该具体假阳性；若运行暴露额外失败，按实际结果修正静态判断。随后是否补最小身份断言及版本化验收由该证据决定，本轮不修改测试或 reward。

保留 `_libs` 方案规范争议，暂不把它追加成第二个必测补丁；正式 actor 启用核验也保持独立前置条件，不拿 grader 语义对照代替。历史实跑、当前静态预测、未来拟议 CPU 和真实模型表现四层分开；本轮没有新运行或模型 token/费用，成本 unknown/null。受限静态候选结论不等于题目质量完备或正式准入。
