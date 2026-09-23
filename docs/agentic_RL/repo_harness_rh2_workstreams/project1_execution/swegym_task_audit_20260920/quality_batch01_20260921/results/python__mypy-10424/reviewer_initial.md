# python__mypy-10424：独立复核初判（第一阶段，冻结前稿）

日期：2026-09-21。角色：`/root/review_mypy10424`，未参与本题主审。范围：静态阅读、原始日志复读与材料哈希/补丁上下文校验。**没有运行历史项目、测试、安装、Docker、SSH 或模型；本记录中的新增 CPU 实验全部未执行。**

初判：本题有明确、合理的公开修复目标；现有 F2P 确实检查了目标类型行为，gold 与该目标相符，未发现必须依赖隐藏规格的要求或具体误拒证据。可保留为有条件的 `development_diagnostic` 静态候选，不能据此批准训练/最终评测，也不能标为 actor 已验。主要评分限制是：五个断言全要求“保持原类型”，没有同时约束普通实例必须继续收窄；有具体、可区分的过宽修复候选值得先做 CPU 对照。它不是由“P2P 为空”单独推导出来的。

## 阅读顺序与暴露

先读指定的 [reviewer 角色卡](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/roles/reviewer.md)、[环境卡](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/actor_environment_card.md)、[记录模板](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/record_template.md) 和共用 [方法协议](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_review_protocol_20260920.md)，再读本题公开材料、公开源码/旧测试，随后才读私有补丁与运行原件。

已暴露：本题 test.patch、gold.patch、grading.json、validation.json、run_refs.json、source_refs.json、environment_record.json，以及指定 09-19 原始 noop/gold 日志和账本。`environment_record.json` 的 `verified_environment_pair`、checks、observations 和 history 字段已经看见；**没有沿 analysis/history 链接读取汇总**。没有读取本轮 public_read、主审前稿、recipe_before_history、old_findings_delta、card、screening_record、任何 review、质量历史、manifest、主计划、method_adjustments；没有读取其他题。source_refs 只读索引，没有沿其路径读取整批 ingest。目录枚举只用于找本题原件。

因此本稿是主审结论开放前的独立判断，但已经看过答案和隐藏测试，不可作为公开 solver 输入。

## 公开目标、材料身份与初态

[公开题面](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/user_prompt.txt:3) 的核心是：`t: Type[C]` 可以是 `C` 的子类对象，子类可以采用元类 `M`；在 `if type(t) is not M: return` 后，不能把 `t` 变为 `<nothing>`，应保留 `Type[C]`。题面包含 `D(C, metaclass=M)` 和 `f(D)`。这是保留类对象类型的修复，不是禁用所有类型收窄。公开文档 [类对象的类型](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/docs/source/kinds_of_types.rst:577) 明确 `Type[C]` 包含 `C` 和其子类，公开 [元类文档](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/docs/source/metaclasses.rst:17) 提供语法、继承和冲突约束；开发者可仅据公开材料理解原因。

公开 bundle 和私有 grading 的 base 均为 `4518b55663bc689646280a0ab2247c4a724bf3c0`，版本为 0.820。以标准库读取文件、按 Git blob/tree 格式重新计算完整公开 base tree，得到 `195a4e235fdf7ff797e6b2e38178a99dd6edd651`，与 [base_identity](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base_identity.json:4) 一致；1485 个文件、12259324 字节亦一致。原题文本 SHA、grading 内嵌 test patch 与单独 test.patch、validation 内嵌 gold 与单独 gold.patch 均一致；两个补丁全部旧 hunk/context 与 base 相符。本地 gold SHA 为 `0bc6c39bdd85a3ddd99913d868e153bcf3a3292f90ac35e577b4bcc2712bba23`，与 validation 和原始 gold 账本一致。以上是材料校验，不是项目执行。

初态因果链已读：

- [checker.py:3960](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/checker.py:3960) 的 `find_type_equals_check` 收集 `type(t)` 的实参和待比较类，调用 `conditional_type_map_with_intersection`。`is not`/`!=` 由 [4232 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/checker.py:4232) 交换两侧映射。
- `get_isinstance_type` 将元类名对应的 class callable 转成 `Instance(M)`（[5309 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/checker.py:5309)）；条件映射使用重叠关系，并写入 binder。`visit_if_stmt`、`visit_return_stmt` 分别消费分支映射和标记返回路径不可达（[3243 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/checker.py:3243)、[3157 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/checker.py:3157)）。
- 名称/成员/下标读取经 `narrow_type_from_binder` 调用 `narrow_declared_type`（[checkexpr.py:4170](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/checkexpr.py:4170)）。base [meet.py:53](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/meet.py:53) 对 `Type[C]` 与 `Instance(M)` 会落入 `meet_types`；其 [visit_type_type](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/meet.py:630) 只直接保留 `builtins.type`，其他元类最终在 strict optional 下得到 `UninhabitedType`。
- 历史 [noop 原始日志](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/noop/eval_logs/evallog_replay-er19-iw1-python___bbc494ef.eval.log:489) 确实执行本题用例，实际 main:11 和 main:17 为 `<nothing>`，其余三处已为 `Type[__main__.C]`。这是目标行为失败，不是导入/收集错误。未自行重现题面完整早退原例，也未另核“自 0.812 回归”的历史起点。

## 全部新增断言、runner 与需求对应

[test.patch](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/private/python__mypy-10424/test.patch:1) 仅向 `test-data/unit/check-narrowing.test` 追加一个 case，没有修改普通源码、helper 或 fixture；[grading](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/private/python__mypy-10424/grading.json:1) 唯一 F2P 是 `mypy/test/testcheck.py::TypeCheckSuite::testNarrowingUsingMetaclass`，P2P 列表为空。已读完该 case 的全部 5 个断言。

| 需求/行为 | 对应断言及公开依据 | 覆盖判断 |
| --- | --- | --- |
| 正向 `type(t) is M` 时保留 `Type[C]` | test.patch:20，运行 main:11；题面否定检查早退后即处于这个条件 | 直接覆盖核心错误；noop 在此失败，gold 通过 |
| 同一 `is` 检查的 else 不错误收窄 | test.patch:22，main:13；`C` 和不同元类的子类仍可能存在 | 直接覆盖另一侧；noop 已通过 |
| `type(t) is not M` 的 if 保留 `Type[C]` | test.patch:24，main:15 | 直接覆盖否定侧；noop 已通过 |
| `is not` 的 else 保留 `Type[C]` | test.patch:26，main:17；与题面早退后的真假条件相同 | 直接覆盖核心错误的反向写法；noop 失败，gold 通过 |
| 两个条件之后仍保持 `Type[C]` | test.patch:27，main:18 | 覆盖分支汇合；noop 已通过 |
| 题面完整 `D` 声明、`f(D)`、早退控制流 | 公开题面:14–21 | 测试没有逐字复现；类型检查函数体不依赖实际调用，且相应 binder 路径已读，语义覆盖较强；完整 CLI 原例仍应在 CPU 核对 |
| 普通实例应继续收窄（包括 `Any`、union、final） | [check-isinstance.test:2577](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/test-data/unit/check-isinstance.test:2577) 起 10 个既有 case | 公开旧行为明确；这些不在评分选择中，F2P 内也没有正向对照 |
| `issubclass` 对 `Type[C]` 继续有效；`isinstance(x, type)` 保留类对象类型 | [1596 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/test-data/unit/check-isinstance.test:1596)、[1811 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/test-data/unit/check-isinstance.test:1811) | 相关调用者/旧行为已读，未参与此次评分；没有发现 gold 静态破坏证据 |
| `==`/`!=`、assert/while、非 strict optional、泛型/联合/有自定义元类的类对象 | 同一 checker/meet 分派及公开类型体系 | 隐藏 case 不覆盖这些组合；只作边界未知，不自动扩大本题要求或据此宣布 gold 错误 |

这不是只校验注释或结果文件：

1. [testcheck.py:51](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/test/testcheck.py:51) 把 `check-narrowing.test` 加入 `TypeCheckSuite.files`；[data.py:550](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/test/data.py:550) 按 `[case ...]` 分割，pytest collector 创建真实 case。前一 case 的 `[builtins fixtures/dict.pyi]` 不会渗入新 case。
2. [data.py:445](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/test/data.py:445) 把每条 `# N:` 转成包含文件、行号、severity 和类型文本的 expected 输出；`setup` 创建独立临时目录（[262 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/test/data.py:262)），case 无自定义文件/fixture。
3. [helpers.py:372](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/test/helpers.py:372) 解析 `--strict-optional` 并加 `--no-site-packages`。`TypeCheckSuite.run_case_once` 将源码作为 `BuildSource`，关闭本 case 增量缓存，调用真实 `build.build`，捕获诊断后用完整数组比较（[testcheck.py:138](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/test/testcheck.py:138)、[205 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/test/testcheck.py:205)、[235 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/test/testcheck.py:235)；[helpers.py:117](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/test/helpers.py:117) 对差异 raise `AssertionError`）。空输出、漏掉 reveal、额外错误都不能通过。
4. 已读默认 [builtins.pyi](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/test-data/unit/lib-stub/builtins.pyi:1) 与 [typing.pyi](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/test-data/unit/lib-stub/typing.pyi:1)：前者含 `type`，后者含经语义分析特殊处理的 `Type`。默认 fixture 的加载见 [modulefinder.py:676](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/modulefinder.py:676)。这是类型检查测试，不执行被检查的 Python 程序；注解函数无 `f(D)` 调用也会被检查，见 [checker.py:722](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/checker.py:722) 和 [4719 行](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/checker.py:4719)。

精确类型字符串是 mypy 现成的 `reveal_type` 公开输出形式，且 issue 明确要求 `Type[C]`；没有要求 gold 函数名、私有 helper、实现步骤或内部调用序列。目前无具体的合理解误拒证据。可行的非 gold 路线是仅在 `find_type_equals_check` 中避免对已知 `TypeType` 与元类目标进行不安全收窄，同时保留普通实例分支；其构造、完整回归和 RH2 接受情况未执行，不能提前标为通过。

## gold 与回归限制

[gold.patch](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/private/python__mypy-10424/gold.patch:4) 只在 `narrow_declared_type` 的 `TypeType`/`Instance(metaclass)` 组合返回 declared；前面的相等、union、非重叠、Any 和 TypeType–TypeType 处理均保留。`TypeInfo.is_metaclass` 的判定包括 `builtins.type` 的子类等（[nodes.py:2547](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/nodes.py:2547)）。它保留类对象已知的 `C` 信息，避免要求本实现尚不能表达的交叉类型。依据已读分派，普通 Instance 收窄和 `issubclass` 的 TypeType–TypeType 路径不会被这个新条件笼统关闭；没有发现 gold 混入另一需求、不可提交依赖或明显破坏上述旧行为。该结论是静态范围内未发现，非全仓回归证明。

**具体漏测候选：**在 `find_type_equals_check` 入口直接 `return {}, {}`，就会全局关闭 `type(x)` 比较收窄。它静态上应满足本题五处“保持 Type[C]”断言和题面原例，却破坏公开旧测试 `testTypeEqualsCheckUsingIs`（`y: Any; if type(y) is int` 应得到 `int`）、`testTypeEqualsNarrowingUnionWithElse`、`testNarrowInElseCaseIfFinal` 等。因此得分可能不能区分针对元类的修复和明显过宽的修复。**未制作/运行这个候选，未观察其实际 reward；此处是有具体触发点和旧语义的静态假设。**这限制 reward 的解释，不足以凭空否定本题所有诊断用途。

还读了 `TypeType` 的语义和规范化（[types.py:1870](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/types.py:1870)）、TypeType/metaclass 的重叠与子类型处理、`narrow_type_from_binder` 在名称、成员、下标和 union 方法调用的入口，并抽查 `testtypes.py:943–989` 的 type/meet 与 literal 测试。直接 `meet_types` 的单元测试不等于验证 `narrow_declared_type` 新分支；这些旧测试也都没有被本题命令选中。

## 原始运行与开发条件

两份 [原始账本](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/gold/ledger.jsonl:1) / [noop 账本](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/noop/ledger.jsonl:1) 均为本题单次 09-19 RH2 replay。重新计算 eval log SHA 与 `run_refs`、账本一致：gold `6249d8819b8af31e58b986ebdf746e156f4dee8a7a28355d6d10f240e9d34d73`，noop `536f23ae33f9a4b1a09f2cf5a720d2516d726cdb1a2b86dc1e2fe5e09b2a28a5`。

[image.json](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/image.json:2) 的上游 digest 与 public bundle 一致，修复镜像 ID 为 `sha256:362a2da70c5f90f6b7909ed92a8a8bceb9d9377cf822c0b170f45bc48f3e2a08`。完整 Dockerfile 只复制 wheels 到 `/opt/rh2/build-wheels` 并设置 `PIP_NO_INDEX=1 PIP_FIND_LINKS=...`；pins 是 setuptools 75.1.0、wheel 0.44.0、packaging 24.1。共同脚本 [23–58 行范围内的构建/重放逻辑](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/run_install_wave1.py:24) 选择这个派生镜像并核保留 base 层；[build.log:27](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/build.log:27) 与该 ID 一致。这不是已将配方选入正式 actor 的证明。

原始 gold 日志显示 HEAD 正是 base（[142 行](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/gold/eval_logs/evallog_replay-er19-iw1-python___6bca9f92.eval.log:142)），除 gold 外还有环境保留的 `test-requirements.txt` 一行 `types-typing-extensions==3.7.3`（[222 行](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/gold/eval_logs/evallog_replay-er19-iw1-python___6bca9f92.eval.log:222)）。随后只恢复并加补丁到官方 `check-narrowing.test`，安装测试需求和 editable 项目。候选只投影 `mypy/meet.py`，ignored_paths 为空；没有要求 solver 交付环境改动。

[gold 实际测试段](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/gold/eval_logs/evallog_replay-er19-iw1-python___6bca9f92.eval.log:497) 是 `pytest -n0 -rA -k testNarrowingUsingMetaclass`，Python 3.9.19 / pytest 6.1.2，9493 collected / 9492 deselected / 1 passed，test rc=0，reward=1；noop 同命令 1 failed，test rc=1，reward=0。`full_test_exit_zero` 只能理解为这条选中一个 case 的命令退出零，不能说全仓测试通过。两账本均记录 grader 为 rh2grader/54322、deny_all、2 CPU/4 GiB、安装完成、`/testbed/mypy/__init__.py` 导入路径、清理 removed=true；gold 约 124 MiB 峰值是这个历史 grader 运行的观测，不是 actor 资源验收。两 driver.log 的收尾没有记录 cleanup failure。

| 开发需要 | 公开依据与已有证据 | 当前缺口 / 最小后续验证（未执行） |
| --- | --- | --- |
| 定位源码与离线复现 | README 测试节、[test README:126](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/test-data/unit/README.md:126) 允许工作区 `python -m mypy`；路径已定位至 checker/checkexpr/meet | 在实际 agent shell 记录 UID/HOME/cwd/PATH、`sys.executable`、`mypy.__file__` 和 `mypy.meet.__file__`，确认导入工作区源码 |
| 解释器、依赖与必要工具 | setup.py 默认 `USE_MYPYC=False`；已读 requirements/pyproject，现有 grader 的 3.9/pytest 6.1.2/xdist 可执行本 case | 不需要为该小题默认要求编译器或 Python 2 全套；actor 的 conda 激活、依赖可读和是否加载旧 `.so` 仍待核 |
| 安装准备、离线资产 | 仓库含类型 stub/fixture；修复配方提供构建 wheel，评分 editable 安装成功 | 标准源代码复现不天然要求联网/服务/新权重；如果 actor 真需重新安装，需确认 wheel 目录权限和可写安装方案，不能套用 grader 的可写 conda 前缀 |
| 最小公开验证 | 精确题面临时文件 + `python -m mypy --no-incremental /tmp/issue10424.py`；旧 `testTypeEquals*` 和 final case 可通过 pytest 精选 | 对照 base/gold/候选；期望原例 `Type[__main__.C]`，旧实例收窄仍正确；不要求运行隐藏测试或全仓测试作为 solver 前提 |
| 交付文件 | 合理修复是普通源码；gold 的 meet.py 实际可投影并生效 | 不需改被官方恢复的 `.test` 文件，也不需提交 `/opt` 包环境；原 public_hints 禁止改测试不妨碍本题合理路线 |
| 资源与临时文件 | runner 每例临时目录，关闭非增量缓存；历史所选测试轻量 | 正式 actor profile 与进程/磁盘权限仍未验，不能把历史 grader 低内存转换成实测保证 |

## 八方面覆盖结论与未知

| 方面 | 实际核查及边界 |
| --- | --- |
| 公开需求 | 已读题面、bundle/hints、环境 brief、Type[C]/元类公开文档及相关旧测试。目标可由公开材料解释；实际模型消息/CLI 自动附加信息未捕获。 |
| 材料与初始问题 | 完整 base tree、补丁上下文和哈希一致；原始 noop 明确目标断言失败。尚未新跑完整原例；0.812 历史版本未查。 |
| 测试测到要求 | 全部 5 个断言、唯一 F2P、data-driven collection/parser/build/assertion、默认 fixture 已核。用例真实检验行为，但缺普通实例正向回归及若干相邻组合。 |
| 误拒合理解 | 输出要求有公开依据，没有锁定 gold 结构；提出限定 checker 路线，未执行替代解。不能声称穷尽所有合法实现。 |
| 回归与 gold | 已追 meet/checker/checkexpr/type/subtype 路径，读普通 `type` 检查、final、issubclass、TypeType 与部分 meet 旧测试；未见明确 gold 回归。过宽修复的静态候选存在，实际 reward 未验证。 |
| agent 开发条件 | 入口、依赖、stub、临时文件和安装路径明确；原始派生 grader 已验。actor 镜像消费、shell/解释器/源码生效、权限和工具交互未知。 |
| 交付与评分边界 | test patch 只加测试；官方恢复路径、gold 投影路径已由原始日志/账本核对。没有针对本题发现必须改被恢复文件的冲突；未复审共享 parser/安全隔离，也未查看真实镜像全部可见资产，答案泄漏不能静态排除。 |
| 关系与用途 | 这是类型检查回归修复；题面给期望行为与原因，未给 gold 代码。遵守单题范围，未读其他任务，因此重叠/派生关系未知；没估计模型成功率、训练价值、token 成本。 |

## 唯一优先新增实验与用途条件

优先做一个三组 CPU 对照（本轮仅设计）：base、gold、以及上述“`find_type_equals_check` 总返回空映射”的过宽修复。每组检查题面完整早退原例、官方唯一 F2P，再运行公开旧测试 `testTypeEqualsCheckUsingIs`、`testTypeEqualsNarrowingUnionWithElse`、`testNarrowInElseCaseIfFinal` 和 `testNarrowInIfCaseIfFinalUsingIsNot`。精选命令可为：

```sh
python -m pytest -n0 -rA mypy/test/testcheck.py -k 'testTypeEqualsCheckUsingIs or testTypeEqualsNarrowingUnionWithElse or testNarrowInElseCaseIfFinal or testNarrowInIfCaseIfFinalUsingIsNot'
```

预期区分：base 在目标 F2P 失败；gold 通过目标且保留旧行为；过宽修复若得到 RH2 reward=1 却失败旧对照，则证实当前评分无法约束这一合理回归。必须同时保留标准 RH2 得分和直接行为日志，不把局部运行当 RH2 结果。若预期不成立，按实际输出修正判断，不能预写实验结论。

进入模型开发诊断前还必须使用协调者统一入口补 actor 环境事实，尤其正式 face 是否消费上述派生镜像、实际解释器和工作区源码。若仅保留原 F2P，可作带补丁审读及旧行为复查的探索性诊断，reward=1 不直接视为完整修复；若需要独立依赖 reward，先用上述 CPU 结果决定是否在独立评分修订中加入已存在的普通实例/union/final 回归。这些语义来自公开旧测试，不需扩写成隐藏新需求。当前不改题、不新增排除路径、不自行宣告 ready_for_probe。

第一阶段到此冻结；等待协调者明确开放 S2/S3 与旧结论变更记录后，只另写 review.md，不回写本稿。
