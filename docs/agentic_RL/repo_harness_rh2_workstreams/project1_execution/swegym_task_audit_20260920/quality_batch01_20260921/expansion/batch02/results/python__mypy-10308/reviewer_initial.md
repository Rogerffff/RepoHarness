# python__mypy-10308 — reviewer 独立初判

2026-09-21。`disposition.scope=static_review`，`state=needs_review`，`usage.intended_use=development_diagnostic`。建议保留为 **materials-v2 明确版本的静态诊断候选**；原始 S2 材料与已引用运行不是同一 grading digest，正式 actor 消费该版本尚未证明。不能标记 `ready_for_probe`。

本文路径均相对 `.`（ROOT）。`P=runs/swegym_quality_batch02_20260921_v2/public/python__mypy-10308`，`Q=.../private/python__mypy-10308`，`M=runs/env_recipe_repair_20260919/materials_v2`，`W=runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10308`。源码行号均为 `P/base`。`G=M/runs/python__mypy-10308-gold/eval_logs/evallog_replay-er19-mat1-python__e8bba825.eval.log`；`N=M/runs/python__mypy-10308-noop/eval_logs/evallog_replay-er19-mat1-python__4cc880f8.eval.log`。

## 公开目标、材料与初态

公开题面要求处理两个递归泛型 Protocol 的 `__add__` 时不再 INTERNAL ERROR；原例有 `__len__`、`bound=float`、联合参数/返回、自类型标注及完整 strict 命令。没有要求特定内部 helper 或采用 gold 算法。公开 traceback 已指向 `constraints.py:437` 的缺失成员断言。base 的 `is_protocol_implementation` 在逐成员比较中先接受递归假设（`subtypes.py:503–582`），`infer_constraints_from_protocol_members` 又假定两个成员必定存在（`constraints.py:378–440`）。`TypeInfo.protocol_members` 排除 object，收集协议父类并排序（`nodes.py:2492–2501`）；先检查成员 `a` 的递归比较可能在发现缺少 `b` 前重新接受假设。已有 N:694–728 恰好在该断言失败，不是凭 gold 差异推测初态。

S2 的 public/grading/validation **仅精确第 179 行**与本包对应 JSON 逐对象一致；base 标识为 `1567e36165b00d532f232cb3d33d1faf04aaf63d`。本次未重做整包 blob 审计。原 test.patch SHA256=`17e5df4826ca8f10bc17381a85a2f539c6001eee5a959dab39bd13c45423a42f`；gold=`4d9843b52d969a2d73a05a4a00e6c5639a4d49706add7f11a6a2aa1321a3672e`，与指定账本一致。

## 需求—断言与实际覆盖

| 要求/旧行为 | 公开依据与对应断言 | 判断及运行证据 |
| --- | --- | --- |
| 不崩溃并保留结构子类型检查 | F2P `TypeCheckSuite::testTwoUncomfortablyIncompatibleProtocolsWithoutRunningInIssue9771`：P1 多 `b`，P2 的 `a` 接收 P1/P2 联合；四个赋值中 p11、p22 无错误；p12 报缺 `b`，p21 报 `a` 签名不兼容 | 测到同一递归/缺成员根因，且不能靠吞掉所有错误通过。G:552–565 通过；N:718–728 崩溃。题面完整 `__add__`/float/strict 组合未直接执行。 |
| 错误信息可解释 | F2P `[out]` 精确要求 2 条 assignment error、缺成员 b 说明、泛型签名 Expected/Got 多行 notes | 与现有协议诊断格式一致，未约束内部实现。`p12`、`p22` 的裸 `# E` **没有冒号，不是断言**；真实 `[out]` 报 main:14/15，p22 正常。不能按注释位置误判测试要求相矛盾。 |
| 不能将任意 Iterable 当 Hashable | 新 `testHashable`：`g(Iterable[str])` 内传给 `f(Hashable)` 必须报参数不兼容；object fixture 显式有 `__hash__`，协议 Iterable 自身未保证它 | 源码的 protocol_members 排除 object 为此提供公开语义线索。G 通过；N:729–742 Actual empty。它在执行选集中，**不在 F2P/P2P 奖励引用中**。 |
| 合法递归协议、普通类动态属性、hash=None 继续工作 | 已读旧 `testRecursiveProtocols2`、`testRecursiveProtocolSubtleMismatch`、`testMutuallyRecursiveProtocols` 及两个 mismatch case（791–887）、`testClassesGetattrWithProtocols`（1902–1936）、`testPartialTypeProtocolHashable`（2593–2608） | 阅读过且与修改面相关；既有本题运行均未执行这些，P2P=0，不能称回归已验，也不因 P2P=0 自动判坏。 |

完整读了 test.patch 两个新增 case、全部 `[out]` 和 fixture 指令；`testWeirdRecursiveInferenceForProtocols-skip` 只是补丁上下文中的 case 名。vendor 从补丁所有 `[case …]` 拼 `-k`（`rh2/src/repoharness2/envpack/spec_vendor.py:183–190`）；G/N 实际仅选 2 项，未把该 skip case 算为通过证据。冻结奖励为 F2P 1 / P2P 0；实际执行 2；本次静态阅读范围大于二者。

## 修订材料、gold 与合理路线

原补丁只改 `check-protocols.test`，却引用 base 不存在的 `fixtures/object_hashable.pyi`，且 base `fixtures/typing-full.pyi:1–70` 没有 Hashable。`mypy/test/data.py:31–80,238` 在**单 case setup**读 fixture，因此原件存在辅助 case 材料缺口；不能直接推断 F2P 未执行或奖励必为 0，更不能把任意完整 pytest 的 rc=1 当全局失败。

指定 `M/materials.json` 顶层 version 为 `materials-v2`。本题条目在原断言不变下增加 object_hashable fixture、typing-full 的 Hashable 协议及 `test-requirements.txt` 的 `types-typing-extensions==3.7.3`。核算如下：

- 原 grading digest：`sha256:868b96a8cb7abe13a644884c99dcb33fb85f893865968526b64ad4520f6fb221`。
- 修订 test_patch SHA256：`e139b55e06645736212fa707a276588537373d6b01be3d16d45532155d6c90ed`。
- 修订 grading digest：`sha256:6fe0fad6693159c8f245f5627888efa35053e56843240729e971f9640fd331d4`。

两个逐运行 `materials/materials.json` 的本题条目及原/修订 digest 均核对一致。它们是**审计输出**，没有 `tasks` 映射，不能作为 `--materials` 输入。真实通路是 `run_material_cases.py:27–54` 取 install_wave1 本题 image_id、向 wrapper 传顶层 `M/materials.json`；wrapper `replay_with_install_recipe.py:42–60` 断言原 patch hash，替换 `test_patch`，重建 trusted setup/eval/hygiene，断言 candidate test script 未变，附加 `+materials-v2`。parser/F2P/P2P 仍绑定原 grading。run_id/recipe 中 `mat1`/`materials-v1` 字样不代表真正材料版本。G:257–325 证实恢复 3 个既存文件、保护 4 个文件并成功应用修订。

gold 先比较双方声明的协议成员集合（排除 `__init__`/`__new__`），再进入递归假设和成员类型检查；只在左侧为 Protocol 时使用早退，普通类 `__getattr__` 路径仍在 `find_member:617–628`。它保留原构造器忽略约定、协议依赖记录和后续类型检查；文档拼字修改无语义。未发现 gold 需要额外业务改动。可行替代路线是两阶段成员校验：先用协议声明/继承成员进行存在性预检，再递归比较每个成员，不必采用 set-subset 写法；测试没有引用 helper/操作顺序。另一条在约束生成处处理缺失成员的路线必须同时保持赋值拒绝语义，不能仅把断言改成跳过。仅吞异常或无条件接受协议不会满足 F2P 负例。未实际构建或执行替代解，不声称穷尽误拒。

## 开发条件、投影和用途

`W/image.json`/`build.log` 与通用 `install_wave1/run_install_wave1.py:24–47` 表明基于 public digest `820409…69c3` 构建 `sha256:9acbdc2f996afc47c0f85a9b3f6cb67d62055a22bf1545d29f26e44ee1a8b51d`，仅 COPY 离线 wheels 并设置 `PIP_NO_INDEX/PIP_FIND_LINKS`，没有在镜像构建中强制安装 pins。G:462–525 的真实安装记录为 Python 3.9 环境、types-typing-extensions 3.7.3、typing_extensions 4.12.2、mypy_extensions 0.4.4、setuptools 75.1.0，editable 本题 base 源码安装完成。G/N 所在目录各 `ledger.jsonl:1` 记录 rh2grader/54322、deny_all、2 CPU/4 GiB、导入 `/testbed/mypy/__init__.py`、安装 rc=0，reward 为 1/0；apply_user=agent/54321 只是候选应用身份，不能当 actor 开发验收。

| 开发需要 | 公开依据/已有条件 | 未验与最小验证（均未执行） |
| --- | --- | --- |
| 定位并运行类型检查器源码 | traceback；README:209–216；`test-data/unit/README.md:28–47` 说明静态类型检查和 `pytest -n0 -k` | 正式 public image、agent shell 下打印 `id`、cwd、PATH、`sys.executable`、`mypy.__file__` 与 `mypy.subtypes.__file__`，确认候选源码生效。 |
| 解释器、依赖、fixture | 公共测试 helper 与 requirements；指定 grader editable 安装已见日志 | actor 的 conda 激活、prefix 写权限、依赖/离线轮子可见性未知；不能借 grader 可写 prefix 填 pass。必要时准备阶段固定资产，不要求运行期公网服务。 |
| 原例与窄回归 | 题面完整原例及 strict flags；旧 recursive/getattr/hash=None case | 先用 agent 执行题面复现（无 INTERNAL ERROR），再窄跑上述公开旧 case；隐藏测试无需提供给 solver。Python 3.8/Windows 与 grader 3.9/Linux差异未独立复验。 |
| 可提交修复 | 业务修复在 `mypy/subtypes.py` 或相关源码 | 原版仅恢复 check-protocols；修订版精确恢复/保护 4 文件，包括 test-requirements。合理业务修复不需要写这些文件；`test_globs=()`，不是所有测试路径都统一剔除。 |

当前 `prepared_task_face.py:312–338` 以精确 test.patch 路径定义 official 文件；`:185–234` 恢复后运行安装/测试。manager:962,1197–1230 区分常规 rc=1 与全局失败。测试 runner、非 official fixtures 可写这一共享边界未做攻击实验；无题特有证据支持新增排除项。公开 hints 的“所有测试修改永不计分”说明过宽，实际是否作为 CLI 消息仍未知，但本题 source-only 修复可遵守禁改测试指令。

关系：本包 11236 base `subtypes.py:543–550` 已包含本题成员预检，17071 base 也有；这是同仓版本答案可达关系，**不是三题同问题重复**。本题题面给 traceback、没有给 gold 实现。静态包无 Git，真实镜像可见祖先/安装资产是否有答案未查，不能写无泄漏。

优先后续：由统一 CPU 负责人固定 **materials-v2 输入＋该派生镜像** 的实际消费路径，在正式 agent/public-image 条件跑原例与少量上述公开回归，同时对齐 grader 材料；无需先扩大全仓测试。本次只静态阅读及 metadata/hash Python，未运行项目/测试、Docker、联网或模型。

## 阅读隔离与证据强度

未读任何 public_read、主审 analysis/delta/card/screening、I2/history、B1/B2 汇总/manifest/method_adjustments/CPU 队列或其他题结论。environment_record 仅查看顶层键名，未读 analysis/history/摘要值。本题读取公开题面/bundle/base_identity/environment_brief、私有全部 patch/grading/validation/source_refs/run_refs、上述原始 image/build/ledger/log、精确材料条目和通用路由。**已暴露** materials 条目的 `decision` 摘要（称恢复遗漏 fixtures、断言不变）和上游 fixture patch/commit；本文用 base 缺件、补丁差异、运行自证重新核实，没有打开它链接的旧质量报告。另已看同包三题 gold/隐藏测试，非 solver/盲解上下文。记录中的执行结果均为 09-19 已有 RH2 原始运行重读，不是本次重跑；最终建议为静态推断。
