# python__mypy-12417：历史开放前的独立私有分析

本稿于 2026-09-21 完成静态调查后保存；尚未读取本题 `history/.../refs.json`、旧质量记录或其他角色结论。只读本题公开包、已封存 `public_read.md`、私有原件、明确授权的配方及原始运行证据，并引用共用方法。没有执行项目、导入项目、安装依赖、运行 Docker/SSH/模型或编写验证补丁。元数据 Python 只用于 JSON 逐对象核对、文件摘要与文本定位。本稿保存后不回写，历史差异另记。

## 证据索引与版本边界

以下缩写均为本题路径，源码行号均指未经修改的 base 导出。

- `R` = `${REPO_ROOT}`。
- `P` = `R/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-12417`；`S` = `P/base`。
- `D` = `R/runs/swegym_quality_batch01_20260921_v2/private/python__mypy-12417`。
- `O` = `R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-12417`。
- `E` = `R/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-12417`。
- `G` = `E/gold/eval_logs/evallog_replay-er19-iw1-python___e26620f5.eval.log`；`N` = `E/noop/eval_logs/evallog_replay-er19-iw1-python___3aeba4ff.eval.log`。两份账本均为对应 `gold/ledger.jsonl:1`、`noop/ledger.jsonl:1`。

`P/public_bundle.json`、`P/base_identity.json`、`D/grading.json` 一致指定 base `47b9f5e2f65d54d3187cbe0719f9619bf608a126`，导出 tree `3e4b07470568ec645531cdc3ddd5e10abfcdd566`。`S/mypy/version.py:8` 为 `0.950+dev`，grading 声明 Python 3.10、版本 0.950。公开镜像 digest 为 `sha256:44be0de19c2cee6d786ebaad4a3d9058dd003dc207d5b0ea8ac99ab730020d52`，配方 base ID 为 `sha256:c1607f47dfd43c7210103452a0c11711a37b3cb5df72286f6554da09eea5a71d`，派生镜像为 `sha256:854faf11b77e78836444b9be7ef9c2fea5255da422fac6aa07dead9e7a63cca7`。没有把不同镜像 ID 当成材料错配。

按 `D/source_refs.json` 精确读取三个 ingest JSONL 的第 199 行：`public_bundles_v0.jsonl`、`grading_bundles_v2_v0.jsonl`、`validation_bundles_v0.jsonl`，均与本地包逐 JSON 对象相等；未审阅其他行。`D/gold.patch` SHA-256 为 `4dc3dcbd7f5410bca0c9a02e543a32bbdb7dac0ba7c6c0f8933ca7101d618e7b`，与 validation 及 gold 账本一致；`D/test.patch` 为 `17201df496f0010e7629694ee5f1518ac0fd655ae17809abf116d5413a53a0b7`。G、N 完整文件摘要分别为 `1fa9a802251e5bc2d777f6505a98268cf44b0bb0f200a97ed05d910ffddb52bd`、`a95a797671d4c45791c1265b36d26d098bbefcaac580479159421f15caeddf7e`，与 run refs/账本一致。

## 1. 公开需求与初态

`P/user_prompt.txt` 的原例是 `o: object; match o: case xyz(): pass`，其中 `xyz` 未定义。公开 traceback 指向 `mypy/checkpattern.py` 中 `assert type_info is not None`。目标是这类输入不再导致 mypy 内部错误；正常报告未定义名称可以从 base 的语义分析与既有错误约定推断。题面没有要求无效分支的 subject 必须降为 Any、捕获变量必须产生后续错误，或必须用某个 PatternType 构造。

`S/mypy/nodes.py:1606–1626` 的 RefExpr.node 初始为 None；`S/mypy/semanal.py:3788–3803,4356–4362,5083–5102` 查找失败时保留未绑定 node，并产生 `Name "xyz" is not defined`。类模式语义分析先访问 class_ref，再访问捕获项（4288–4293）；捕获名通过 `visit_as_pattern:4259–4263` 建立变量。`S/mypy/checker.py:4111–4123` 在检查 match 时先遍历模式来推断捕获类型；`S/mypy/checkpattern.py:105–110,459–466` 没有处理未绑定节点就断言，因此到达公开错误路径。

原始 N:441–446 先输出两个 `Name "xyz" is not defined`，N:498–532 的堆栈从 data runner/build 到上述 match 第一遍、最后在 checkpattern.py:466 AssertionError；N:443 为 SystemExit 2，N:534–538 是 mypy INTERNAL ERROR。因而 no-op 失败与本题缺陷直接相关。历史记录实际执行的是带捕获的隐藏测试；没有单独执行题面零捕获原例的证据。二者在断言前走同一路径，这是源码支持的联系，不能写成原例已实跑。

公开 `public_hints` 中“conda 已激活”是待核环境声明；“禁止改测试”是否进入真实消息仍未知，其“所有测试修改恢复且不计分”的解释与当前无测试名通配排除机制不完全相符。源码修复可落在 `mypy/checkpattern.py`，不依赖修改受保护测试才能成立；若该指令实际适用，会限制追加回归测试的交付方式。暂记共享输入条件，不能静默忽略提示，也不据此判题无效。

## 2. 全部新增断言与 data-driven runner

test patch 仅在 `test-data/unit/check-python310.test` 新增一个 `[case testMatchInvalidClassPattern]`，未修改生产源码、helper、配置或 stub。插入点紧随另一用例的 `[builtins fixtures/primitives.pyi]`，但该 fixture 不跨 case 继承。新增 case 无专用 builtins/typing fixture，使用 lib-stub 默认内容。

F2P 唯一 ID 为 `mypy/test/testcheck.py::TypeCheckSuite::check-python310.test::testMatchInvalidClassPattern`。其输入为模块级 `m: object` 和两个独立 match：`xyz(y)`、`xyz(z=x)`。共七条实际 expected 输出，非“只要没有 crash 就算通过”。

| 新增断言 | 输入位置/含义 | 公开或旧行为依据 | 证据层次 |
| --- | --- | --- | --- |
| `Name "xyz" is not defined`，两次 | 位置捕获与关键字捕获的类名均不存在 | 公开原例同一未知名称；semanal 既有诊断 | 合理要求；N 已输出，G 的 case 整体通过 |
| `Revealed type is "Any"`，对 m 一次 | 第一个无效分支内 subject 从 object 变 Any | 题面没有要求；gold 的 pattern.type 选择直接造成 | 隐藏验收附加了恢复类型选择 |
| `Cannot determine type of "y"` 加 `Revealed type is "Any"` | 位置捕获变量的附带错误与类型 | 捕获变量已有语义声明，但 gold 返回空 captures；错误恢复策略未公开指定 | gold 特定恢复路径导致；不是单纯文案替换问题 |
| `Cannot determine type of "x"` 加 `Revealed type is "Any"` | 关键字捕获变量的附带错误与类型 | 与 y 同理，覆盖另一种捕获输入 | 同上；第二分支没有检查 m 的 reveal |

`S/mypy/test/data.py:31–81` 按当前 case 处理 `[builtins]` / `[typing]`，读取 fixture 并写入临时路径；178–192 将 inline expected 展开，265 调用 suite.run_case。解析在 406、427 使用 `collapse_line_continuation:452–462` 把反斜杠续行合并；`expand_errors:469–497` 分别将同一行 `# E:`、`# N:` 转为带行号的 error/note，因此 y/x 的两条注释都是正式断言，不是说明文字。case 临时目录与文件 setup、DataSuite/DataFile collector 也已读取（data.py:265–306,550–650），没有 skip/xfail 标记。

`S/mypy/test/testcheck.py:107–108` 只有运行解释器至少 3.10 才加入 check-python310.test。TypeCheckSuite 读取 case、写 main、解析 flags（145–167），`helpers.py:287–300,367–399` 按文件名指定目标 Python 3.10；没有 flags 时 strict_optional=False、error_summary=False。本 case 非增量，cache_dir 为 os.devnull（testcheck.py:177–184）；use_builtins_fixtures=True、show_traceback=True；直接 `build.build(..., alt_lib_path=test_temp_dir)`（197–202），收到 res.errors 或 CompileError.messages，再在227行比较完整 expected 和 actual。`helpers.py:46–120,233–253,303–309` 仅规范路径、尾空白、CR 与 can't/cannot 等，不接受缺失、增加或随意改写诊断。不是 grep gold 实现，也不是未运行测试体的收集检查。

默认 `test-data/unit/lib-stub/builtins.pyi` 全文已读，提供 object/type/int/str/function 等最小定义；typing.pyi 全文提供内部特殊处理的 Any、Generic、Type、Tuple 与 Sequence 等。`modulefinder.py:735–743` 在 use_builtins_fixtures 下将 lib-stub 放在默认库搜索路径最前，并排除第三方安装包候选路径（346–350）。fixture 内容足以支持 F2P，case 不依赖外网或真实执行 `match xyz()`。它执行的是 mypy 静态分析；输入程序本身不会因 Python NameError 而作为测试结果。

## 3. 三个 P2P 全部展开与需求—测试映射

三个 P2P 的 base 用例及 fixture 均完整阅读（`S/test-data/unit/check-python310.test:570–616`）。ID 均以 `mypy/test/testcheck.py::TypeCheckSuite::check-python310.test::` 为前缀。

| 公开要求或合理旧行为 | 依据位置 | 测试与决定性断言 | 覆盖及执行事实 |
| --- | --- | --- | --- |
| 未定义类模式不能触发 INTERNAL ERROR | 题面原例；checkpattern.py:465–466；semanal 名称诊断 | F2P 对 xyz(y)、xyz(z=x) 产生正常输出 | 相关路径覆盖；N 目标断言崩溃，G 通过；原例 xyz() 未单独执行 |
| 未定义名字仍报告错误 | semanal.py:4356–4362,5083–5102 | F2P 两条 Name 错误 | 已覆盖；不能通过全局压制诊断蒙混 |
| 无效类模式体的 subject/capture 恢复方式 | 公开没有唯一约定；相邻已知无效模式使用 early_non_match | F2P 额外五条输出 | 有具体过严疑点；见下一节，替代路线未运行 |
| 默认 dataclass 的位置捕获对应字段类型 | base:570–584，A.a:str、A.b:int | `testMatchClassPatternCaptureDataclass` 的 i=str、j=int | 两端均通过；保护有效类模式及精确捕获，非仅不崩溃 |
| match_args=False 不生成位置模式接口 | base:586–599 | `testMatchClassPatternCaptureDataclassNoMatchArgs`：A(i,j) 报缺失 __match_args__ | 两端均通过；负行为覆盖 |
| init=False 字段不算位置参数，其余位置仍可捕获 | base:601–616，b=field(init=False) | `testMatchClassPatternCaptureDataclassPartialMatchArgs`：A(i,j) 报 Too many positional patterns；A(k) 的 k=str | 两端均通过；同一 case 同时保护错误与后续有效分支 |
| 其他已知无效类模式沿用旧恢复方式 | base:689–703,861–868 | filled generic alias / a=1 模式报主错误，分支内 reveal 不要求输出 | 已实际阅读但不在本次四项评分执行中；支持合理替代路线 |
| 普通/限定类名、keyword、自匹配、NamedTuple、泛型等旧行为 | base:468–568,618–715,794–858 | 相关旧 case 的捕获与错误输出 | 静态阅读；不把同文件其他 10300 deselected 当作通过 |

三个 dataclass P2P 均 `[builtins fixtures/dataclasses.pyi]`，该文件43行全文已读：object、str/int、泛型 tuple、dict 等定义供 plugin 生成成员使用。`lib-stub/dataclasses.pyi` 34行全文已读，包含 dataclass 的 match_args 参数和 field(init=...) 签名。`mypy/plugins/default.py:119–120` 选择 dataclass callback，`plugins/dataclasses.py:514–518` 调 transformer；transform:129–135 读 match_args 默认 True，222–230 只将 is_in_init 字段生成 Literal 名称 TupleType 的 __match_args__；343–349 从 field(init=False) 得到排除标记。`checkpattern.py:499–536` 读取 __match_args__，没有则报错，位置项过多则报错，否则映射为字段 keyword；561–592 分析字段类型并合并 inner captures。故三个 P2P 确实保护本修复所在类模式分支的正负行为。

这里已有有效回归保护。不能因仅三个 P2P 就断言任意错误修复可过，也不能将“同一 .test 文件”代替这条具体调用链。把所有类模式无条件返回 Any/空 captures，会失去有效 dataclass 的 i/j 类型和负诊断，无法满足所读测试。只压制 INTERNAL ERROR 而吞掉正常输出也不满足完整比较。尚无已执行的错误候选获满分反例；本轮不为凑反例制造任意按测试输入分支的补丁。

## 4. 合理替代路线与疑似误拒

gold 只把 None 断言改为 `PatternType(AnyType(TypeOfAny.from_error), AnyType(TypeOfAny.from_error), {})`。这是明确、局部的恢复方案，但不是公开约定中的唯一方案。

可比较的另一条路线：在相同 None guard 返回已有 `self.early_non_match()`。这个 helper（checkpattern.py:669–670）返回 `(UninhabitedType(), 当前 subject 类型, {})`；同一个 visit_class_pattern 对填好参数的 TypeAlias（467–469）、非类型 class_ref（475–481）、缺失 __match_args__（517–520）及过多位置项（525–528）已有类似调用。尤其 base:689–703 的 `testMatchClassPatternCaptureFilledGenericTypeAlias` 与861–868的 `testMatchClassPatternIsNotType`，分支内显式 reveal 却不要求 note，提供了可读的错误恢复先例。

原因链可定位：checker.py:4131–4134 遇到 UninhabitedType 时将分支 binder 标为不可达；visit_block:2139–2151 随后停止检查分支语句。名称错误来自更早的语义分析，仍应保留。gold 的 Any 分支保持可达且空 captures 无法给 y/x 推断类型（checker.py:4166–4198）；checkexpr.py:264–277 对未就绪 Var 调 handle_cannot_determine_type，checker.py:405–419 最终给出既有 HAS_TYPE 错误；Any 的 reveal 则来自表达式类型。这解释了 F2P 五条附带输出对恢复方案的实际限制。

因此替代 guard 静态上可修原例，且只改变原先 None 崩溃入口，未触动三个 P2P；F2P 则预期因缺五条输出而失败。该推断尚未 CPU 验证，也没有据此断言其所有上下文都正确。若最小对照显示它破坏了应保留的后续分支/变量行为，需撤销“合理解”判断。当前问题应记为“公开未唯一指定的错误恢复输出，存在有旧行为依据的替代路线”，而不是泛称所有精确错误字符串不公平。两条 Name 诊断有公开依据，必须保留。

## 5. gold 的完整性与原始执行对账

gold 没有引入新 API、导入、依赖或无关改动。None guard 位于所有位置/keyword/零捕获分歧之前，静态上覆盖题面 xyz() 与两种隐藏输入；原先非 None 的 TypeInfo/TypeAlias/Var 分支保持原代码。返回错误 Any 使主错误之后继续分析分支并产生上述附带结果。未在所读源码与三个真实 P2P 中发现 gold 造成的新旧行为冲突；这不是全仓或完整原例动态验证。

| 条件 | gold | no-op |
| --- | --- | --- |
| install / test 退出 | 0 / 0 | 0 / 1 |
| 实际选中 | 4，10300 deselected（G:448–465） | 4，10300 deselected（N:429–436,539–545） |
| F2P | 1/1 PASSED | 0/1，断言崩溃而非安装/收集问题 |
| P2P | 3/3 PASSED | 3/3 PASSED |
| report / reward | RESOLVED_FULL / 1 | RESOLVED_NO / 0 |
| 缺席、跳过、段外解析 | reference_missing=[]、reference_skipped=[]、num_parsed_outside_segment=0 | 同左 |
| 安装 / 测试秒数（账本） | 6.847 / 3.620 | 6.916 / 3.735 |
| 测试进程摘要 | 4 passed，2.87s | 1 failed, 3 passed，2.81s |
| 记录内存峰值 | 129.238 MB | 134.246 MB |

两端均 `pytest -n0 -rA -k 'testMatchInvalidClassPattern or testMatchClassPatternCaptureDataclass'`；P2P 名称共前缀所以选中三项，原始 short summary 的四个完整 ID 与参考集逐项吻合。`pytest.ini:24` 默认 -nauto，但命令显式 -n0；本次没有另一题的 xdist 多 worker 行为，不能继承其他版本经验。运行平台 Linux、Python 3.10.14、pytest8.3.2、xdist3.6.1（G:450–454/N:431–435）。可预期诊断由 data runner 比较，mypy 报普通输入错误并不要求 pytest 退出非零；N 的失败明确是 INTERNAL ERROR。

两份账本 phase/stage_error 无基础设施错误，cleanup.removed=true，runner_integrity_changed=false；没有重试，缺少同状态重复评分和并发证据。N/G 的 0/1 差分不是 scorer 根据 candidate 类别提前生成：均有安装、四项实际输出及测试结束标记。未读取/运行源码 runner 的来源版本对照，不能将当前日志等同全部 SWE 原始条件。

## 6. 本题开发条件与配方原件

`E/image.json` 的完整 Dockerfile 为 `ARG BASE_IMAGE; FROM ${BASE_IMAGE}; COPY wheels/ /opt/rh2/build-wheels/; ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels`。pins 仅 setuptools72.1.0、wheel0.43.0、packaging24.1，base_layers_preserved=true。`E/build.log` 记录固定 base digest、COPY wheels 和同一派生 image ID；只有 ARG 默认空的 build 警告，构建完成。明确授权的 `R/runs/env_recipe_repair_20260919/install_wave1/run_install_wave1.py:23–58` 显示该波构建离线 wheel 层并直接调用原 replay_grade.py 的 --derived-image；没有采用别的波次 revised_install wrapper。配方未预置目标库修复；wheel 内容未逐二进制审计，不能扩展为泄漏已经全面排除。

G:362–438/N:343–419 实际执行 `python -m pip install -r test-requirements.txt`、`python -m pip install -e .`、`pip install pytest pytest-xdist` 并有成功结束标记；pip 显示 Looking in links，editable build 成功、目标版本为 0.950+dev.base.dirty。typing_extensions4.12.2、mypy_extensions1.0.0、tomli2.0.1 等来自 base 已安装环境。与 `S/CONTRIBUTING.md:20–59` 的开发安装及单测方式一致。`S/pyproject.toml:1–6` 需要 setuptools/wheel；requirements 全部已读，Python3.10 下 typed_ast、pytest及其 plugin 等测试依赖由原日志满足。没有本题必须的模型权重、数据下载、GPU或外部服务；输入与 stub 均本地文件。

必要开发条件是可读生产源码/公开旧测试及 stubs，可写 workspace、home、临时目录及采用 editable 安装时的解释器 prefix；Python 至少3.10才能收集本文件，所用兼容依赖应可离线恢复。最小公开复现可用 `python -m mypy --python-version 3.10 --show-traceback /tmp/repro_12417.py` 检查题面原例；公开回归可用 `python -m pytest -n0 -rA mypy/test/testcheck.py -k 'testMatchClassPatternCaptureDataclass or testMatchClassPatternIsNotType or testMatchClassPatternCaptureFilledGenericTypeAlias'`。这些是建议，未在本轮运行；不要把 hidden F2P 内容提供给 solver。

账本 grader uid54322、deny_all、2CPU/4GiB、PID512、tmpfs1GiB、shm64MiB，prefix owner 54322，candidate writable prefixes 包括 `/opt/miniconda3/envs/testbed`；导入观察 `/testbed/mypy/__init__.py`，package version 单独探针为 `?`，实际安装日志补充了明确版本。公开环境卡计划 actor 为 agent/54321；账本 apply_user=agent/54321 只证明该次补丁应用身份，不能证明 actor 的 shell激活、目录权限、安装、公开测试或真实 Claude 工作流已可用。`D/environment_record.json` 的 `both_roles=true` 指 gold/noop，不是 actor/grader 两个身份。实际模型请求、网络代理、shell PATH、可见挂载与泄漏边界仍待 actor 验证。

已读 environment_record 的总结状态、analysis/history 字段，属于已暴露环境结论；未沿它们读取 `analysis_149.json` 或提前读取旧质量历史。其有关当前配方的关键事实以 image/build/账本/日志独立核对，未把 verified_environment_pair 当作训练批准。

## 7. 交付、官方恢复、评分控制面与暴露

G:185–225/N:166–206 实际将 `test-data/unit/check-python310.test` 从 base checkout 后注入可信 test patch，restored=1、expected/present=1、absent=0、apply_rc=0。这是本次真正执行的官方恢复，不等于全部测试名目录统一排除。`gold/ledger.jsonl:1` projection.included_paths 只有 `mypy/checkpattern.py`，ignored_paths=[]；noop included_paths=[]；两者均有冻结 patch 摘要。合法源码 guard 未被覆盖。test patch 只触碰 data 文件，未出现源码/测试混合职责路径。

三个 P2P 恰位于同一官方恢复文件，确有本次冻结参考保护；另外阅读的 generic alias、non-type、keyword/NamedTuple 等旧 case 也位于该文件，但未被此次选择器执行。默认 lib-stub、dataclass fixture、TypeCheckSuite/data.py/helpers.py、pytest.ini 是本题实际依赖的测试控制面；阅读其源码不等于已经证明 actor 不能篡改，也不等于已执行攻击。没有具体获分伪造证据，additional_exclusions 保持空，不把所有 test-data/或 mypy/test/加入自造规则。

公开导出只提供 base 跟踪文件且无 .git；本调查上下文已见 gold、隐藏测试、相关日志和环境摘要。静态导出不能替代 actor 对真实 Git 对象、预装包、挂载和工具出网的检查；未来 solver 不得收到本稿、card、私有断言或历史分析。没有读取真实模型成功/失败轨迹，不能评价诚实性、能力、token成本或基座难度。

## 8. 关系、暂定处置与唯一优先实验

本题目前没有基于 commit/修复来源确认的跨题重复关系；未查跨题原件，不因同仓/同文件归族。任务是 Python3.10 类模式错误恢复的局部缺陷修复。原始公开例子与 traceback 已给定位线索，但没有给完整 gold；预训练或外部答案是否可达未知。

暂定 `needs_review / static_review`，用途 `development_diagnostic`。当前原件足以确认材料一致、历史 RH2 的 no-op目标失败与gold四项成功、三个P2P的有效正负保护；尚有 F2P 强制恢复附带输出的具体公允性疑点，以及未验 actor 条件。没有证实假阳性、没有判定原题无效，也不将 gold 可跑升级为模型可解。

**唯一优先 CPU 对照（只提出，不执行）**：固定本题 base/digest/离线配方，隔离构造三份实现：base、原 gold、仅将 None 分支改为 `return self.early_non_match()` 的替代实现。输入组为公开零捕获原例；隐藏 F2P 的两种捕获输入（由特权调查侧使用）；三个既有 P2P；另两项公开旧测试 `testMatchClassPatternIsNotType`、`testMatchClassPatternCaptureFilledGenericTypeAlias` 作为恢复惯例控制。检查每次 mypy 原始错误、内部错误/退出、branch reveal 和实际 RH2 四项得分，不能只看总分。预期可区分结果是：base 在公开原例/隐藏F2P崩溃；gold均消除崩溃、四项通过；若替代实现也保留两条未定义名错误、消除公开/隐藏crash、五项旧回归不变，却只因缺五条附带输出被F2P拒绝，则形成窄范围误拒证据。若它损害公开要求或相关旧行为，不能凭风格不同主张放宽断言。实验后才决定保持现有标准、修订错误恢复oracle，或补有依据的公开说明；不要先将gold输出照抄入题面。

actor 基本环境检查仍是未来实际求解前提，但不是本稿捏造的第二项语义实验。container wall/agent tokens/human decisions 无本轮对应计量则填 null；引用历史阶段秒数时保留其历史角色和阶段范围。
