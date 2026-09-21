# pandas-dev__pandas-50319 — 独立复核初判（封存版）

2026-09-21。角色：fresh B3 reviewer；本包只含 50319、51605 两题，先读原件后形成判断。状态 **needs_review / static_review**；用途 **development_diagnostic**，不是训练/评测准入。本文件保存后不回写；与主审、公开读者和旧结论的比较另写 review.md。

**独立结论：题面与新增断言存在直接的接受范围差异，应先做窄 CPU 误拒诊断。** 题面明确允许原例返回 `None` 或猜到格式，但新增测试只接受 `"%d.%m.%Y %H:%M:%S.%f"`。已有 API 文档和公开调用者也容许猜测失败时返回 `None`，不能把更强的隐藏断言反称为公开唯一要求。gold 的 token 分类修复本身有源码和原重放成功支持，尚未发现其破坏本次已查旧行为；这不消除对合理非 gold 路线的误拒风险。

## 阅读与暴露边界

只读共用 reviewer/environment/template/protocol 四份方法文件；自己的 I3 public/private 原件；inventory 的 common、reference_v1/baseline01 及本包 exact-id 项；它们精确指向的原日志、账本行、输入与原运行代码。未读 public_read、主审稿、delta/card/record、B3 assignments/聚合、其它题结论、独立 history/旧质量报告或 analysis_reference 目标。

**已见私有暴露：** 本题 gold、test.patch、完整 F2P/P2P；environment_record.json 自带 `verified_environment_pair`、`reference_id_pandas`、gold=1/noop=0、安装/清理摘要及内嵌 history 定位字段，已全部看到，未追其 analysis/history 文件。随后用原日志核对，不把这些摘要当独立质量结论。另一题 51605 的私有材料同样已读，见本包另一份初稿。没有承担“仅公开材料”角色。

全部操作为静态文本/JSON、stdlib hash、tarfile.extractfile 读历史字节；未解包、import/执行项目、测试、安装、联网、Docker、SSH、模型调用、quota/reset、修改源/tests/gold/reference/reward/expected 或提交推送。

路径缩写：`ROOT=.`；`I3=ROOT/runs/swegym_quality_batch03_20260921_v1`；`P=I3/public/pandas-dev__pandas-50319/base`；`Q=I3/private/pandas-dev__pandas-50319`；`R=ROOT/runs/env_recipe_repair_20260919/reference_v1`。下列相对引用都以这些明确根为基准。

## 八方面覆盖与需求—断言映射

| 方面 | 已查事实、结论及边界 |
| --- | --- |
| 公开需求 | public_bundle、user_prompt 全读。原例为 `guess_datetime_format('27.03.2003 14:55:00.000')`，目标“不 error”，明确接受 None 或格式串。parsing.pyx:862–879 的公开 docstring 同样写 str 或 None；core/tools/datetimes.py:129–146 在 None 时告警并走逐项解析，:435–461 接受该 fallback。 |
| 材料与初态 | base `1613f26ff0ec75e30828996fd9ec3f9dd5119ca6`，tree `51c401ff1bb51e8a235a0f6777f209d8f671da77`。原题 traceback 的调试 print 不在 base，关键路径仍吻合。parsing.pyx:810–815 将点分日期分为数字/分隔符，:965 无异常保护调用 _fill_token；:1019–1023 把单独 "." 当小数，int("") 抛 ValueError。原 noop 栈证实相同异常，并非仅由 gold 反推初态。 |
| 测试测到要求 | test.patch 只增加一个参数；已读 test_parsing.py 全 327 行，包括全部现有参数、关键断言与 helper。新增参数进入 :184–186 的 `assert result == fmt`，不只检查“不抛错”。F2P 全部 1 个，P2P 全部 109 个参考键已逐项核对；实际文件执行 114 个 node，参考键与节点数量不可混写。 |
| 误拒合理解 | 存在具体非 gold 路线：在 guess_datetime_format 的 token 填充失败处局部捕获 ValueError 后返回 None，保留先前成功路径及错误类型检查。它满足题面原例与文档 fallback，却会违反新增相等断言；本轮未执行该候选，其他回归是否全部保持须实验确认。不同的正确数字 token 判断也合理，测试没有要求必须用 gold 的 regex 或 helper 名。 |
| 回归与 gold | 全读 _timelex、guess_datetime_format、_fill_token、dayfirst 告警和唯一业务调用者。gold 将条件改为 `re.search(r"\d+\.\d+", token) is None`，只对真正小数 token 分拆秒/小数，数字与分隔符走 zfill；源码没有新增依赖，文件顶层已有 re。原毫/微/纳秒、非填充、时区、locale、dayfirst 旧测试均在实际运行文件内。原例之外的点分日期、dayfirst=True 点分原例、to_datetime 端到端不在新增验收中；未穷举所有日期语法或性能。 |
| 开发条件 | 可定位 Cython 入口和公开构建文档，修复 .pyx 必须重编译。历史 grader 安装与实际编译成功，正式 actor 的解释器、编译工具、可写 build 路径及候选扩展加载尚未知，详见开发表。 |
| 交付/评分边界 | gold 仅改 parsing.pyx；test.patch 仅改 test_parsing.py，无普通业务源码夹入测试补丁。冻结 harness 仅恢复/保护这个 official test 文件，gold 源路径已投影 included、ignored=[]。没有证据要求写无法提交的文件；C 扩展产物是验证所需构建产物，提交源 .pyx 即可。公共 hints 的 blanket “所有测试修改不计分”不等于实际机制；本题合法源修复不依赖改测试。 |
| 关系与用途 | 51605 的公开 base 在 parsing.pyx:1009–1023 已含本题 gold 条件，这是本包可证的跨版本答案暴露关系，不是同一问题的重复题；后者修 MultiIndex。两题求解上下文不应复用本次答案知识。不推断模型成功率、学习价值或真实消息工具渲染已通过。 |

| 公开需求或合理旧行为 | 依据 | 测试及关键断言 | 覆盖结论 |
| --- | --- | --- | --- |
| 原例不抛异常，None 或有效格式均可 | user_prompt 最后一句；parsing.pyx:875–879 | 新参数完整 node `test_guess_datetime_format_with_parseable_formats[27.03.2003 14:55:00.000-%d.%m.%Y %H:%M:%S.%f]`；result == fmt | 原错误路径覆盖；接受范围冲突，None 路线被排除。 |
| 保持已支持的格式、时区与英文月份 | test_parsing.py:144–207 | parseable_formats、locale_specific_formats；逐个 exact fmt/None | 已查全参数，历史实际通过；exact fmt 有既有格式接口依据。 |
| 保持小数秒推断 | :315–327 | test_guess_datetime_format_f 的 .123/.123456/.123456789 均等于 %S.%f 格式 | 3 个 P2P 键，覆盖旧小数分支。 |
| dayfirst、非补零、类型/无效字符串 | :189–193、210–265 | True/False 格式、warning helper、8 个无效字符串 None、2 个错误类型 TypeError | 旧行为有覆盖；新点分日期的 dayfirst=True 未增测。 |
| pandas.to_datetime 能处理猜测失败 | core/tools/datetimes.py:129–146、435–461 | 评分仅 test_parsing.py，无 to_datetime 端到端新断言 | 调用者表明 None 有意义；端到端状态未知。 |

新增用例继承 `@td.skip_if_not_us_locale`；已读 util/_test_decorators.py:124–128、202–205，只有 en_US 才不 skip。历史日志确实执行该 node，无 reference_skipped；未来复现仍须记录 locale，不能以“收集到了节点”代替执行。相关 P2P 的 assert_produces_warning helper 已读，它还校验多余告警/stacklevel。新增用例没有 fixture、Mock、额外 helper 或隐藏内部调用约束。

## 原运行证据与评分口径

原始记录来自 R/runs/pandas-dev__pandas-50319-{gold,noop}/ledger.jsonl 各第 1 行。run_refs 指定的 ledger 行 hash（去换行）与 log SHA 已逐一复算一致：

| 角色 | 完整测试、关键原日志行 | 账本评分 | 安装/资源（原字段单位） |
| --- | --- | --- | --- |
| gold | eval_logs/evallog_replay-er19-ref-v1-panda_c332d5e5.eval.log:4913 命令；:5007 新 node PASSED；:5057 **114 passed**；:5065 RH2_TEST_RC=0 | F2P 1/1、P2P 109/109、reward 1、resolved；parser 键 111 | install_seconds=731.263；mem_peak_mb=902.945；resource_facts=null |
| noop | eval_logs/evallog_replay-er19-ref-v1-panda_55456694.eval.log:4889 命令；:4954–4960 _fill_token/int("")；:5089 新 node FAILED；:5090 **1 failed, 113 passed**；:5098 RC=1 | F2P 0/1、P2P 109/109、reward 0、tests_failed；parser 键 111 | install_seconds=701.046；mem_peak_mb=838.82；resource_facts=null |

两次命令均为 `pytest -rA --tb=long pandas/tests/tslibs/test_parsing.py`。完整命令 RC 与 reward 分别记录；冻结 prepared_task_face.py:147–156 / manager.py:908–936 明确 RC 只进诊断，评分走 reference F2P/P2P 和 parser，不由“文件整体返回零”直接定义。

**安装不是靠末命令 RC 推定。** gold 日志:3149–3152 为 numpy<2 与 editable install，:3159–3160 明确因变化重新 Cythonize parsing.pyx，:4009 复制 parsing.so，:4888/4898 显示 Successfully built/installed pandas；noop :4864/4874 同样成功。:4899/:4875 的 `pip uninstall pytest-qt -y` 是 install 串末命令，故 RH2_INSTALL_RC=0 只代表它；独立成功行与编译行支持本题实际安装。两次 Python 3.8.20、NumPy 1.24.4，观测包源 /testbed/pandas/__init__.py；观测未给 parsing.so 独立 hash，不冒称正式 actor 二进制加载已验。

**reference_v1 不是原 parser 原样结果。** 已核 R/run_reference_cases.py:23–39 → replay_with_install_recipe.py:61–78 → frozen scripts/replay_grade.py 的调用链和 status.json 本题 gold 命令。真正输入是 R/reference_bindings_v1.json 顶层 `version/decision/tasks` 中本题键；运行目录的 bindings/reference_bindings.json 只是所选 entry 审计输出，不能当 --bindings 输入。无 install recipe、materials 或 derived image 覆写。

本题只有 1 个显式绑定：冻结 P2P 键 `test_is_iso_format[%Y\%m\%d` 对应 pytest 显示转义后的完整反斜杠 node。reference_bindings.py:14–32 对完整 node 查状态、缺成员不补 pass，:49–67 只替换指定 alias，保留 F2P/P2P；两份 .reference.json 原始 raw_node_states 都是 PASSED。未绑定前该 P2P 缺席，gold original 为 108/109、RESOLVED_NO；绑定后 109/109、RESOLVED_FULL。它不改变本题新 F2P 的业务断言。

实际 114 node，经原 whitespace split 得 110 个键；两个碰撞组为 parseable_formats 的空格日期 2 node，以及 no_padding 的空格日期 4 node。绑定再补 1 个旧反斜杠 alias，得 111 个解析键；冻结参考共 1+109=110。**不能把 109 P2P 说成 109 个实际节点，或把 114 passed 当 114 个独立参考。** 已逐行计数原 -rA 状态并核两个碰撞组；本次成员全通过，未因此观察到错误通过，但单条 binding 不等于全面修复所有碰撞语义。

## 身份、材料和冻结调用链

- 原输入 manifest tasks[152] 的 canonical hash 为 `0cc90516446875d958d89d7f1449065d8aae1e3f2ae07ae762e158e887d4fc11`；host_grading_views.jsonl:153 原行 hash `709886ccb6dacfcf2acf43e1989af007ce6bd7d7fb1503136fa38e094a4a5cec`，grading 等于 Q/grading.json。
- source_refs 指定的原 ingest public/grading/validation 第 153 行和各导出 SHA 均核对；test.patch 等于 grading.test_patch；gold 等于原 gold candidate，SHA `70ca3fa70b50975e2fe34f0f790e66f9f7c7a1453220c0bf6d69d30d145214ec`。stdlib Git blob hash 核得源码 old blob `614db69425f4c6cd8e7a7454569e9471a7dbff31`、测试 old blob `a4c79e77d2eed12426eba2d9af9be16c70f4aa1a`，与补丁 index 匹配。
- 原 image_ref 为 xingyaoww/sweb.eval.x86_64.pandas-dev_s_pandas-50319:latest；expected/identity `sha256:e645e4346df9200174e8b879ad8fb7a09f64f91c7375311e2569596d054ba21e`；**image_id_actual=null**，image_local_build=false，不补造实际 ID。script digest `sha256:eca150e1e393c221f3b9822665a12965d35c956f87e3693efa8f61692dfd3058`。
- 只从 ROOT/runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz 的 exact members 读取历史代码。scripts/replay_grade.py SHA `6115714639d677a7a2b116738507d8adf8fc9f5a4f4059ff7f792360359a0311`；adapters/slime/replay_grade.py `b8f1fbe2f37032e52b496f2eb9296c8a647a3072af2b7def600809544c9999fb`；prepared_task_face.py `3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27`。已追 spec_vendor、scoring、swegym_parsers、manager、trusted_projection 的相关调用链。
- ReplayGrader 候选应用身份 agent/54321，只是机械应用补丁，不是模型开发；评分安装/测试用户 rh2grader/54322，network=deny_all，cpus=2.0，memory_bytes=4294967296，pids_limit=512，shm_bytes=67108864，tmpfs_bytes=1073741824，candidate_writable_prefixes=["/opt/miniconda3/envs/testbed"]。budgets 秒数为 900/120/3600/1800（candidate/cleanup/grading/image pull）。env_qualification=absent。两次 trusted_setup 恢复/应用 1 文件、control_surface 保护 1 文件成功，账本 cleanup.removed=true。
- 冻结 prepared_task_face.py:298–331 从 test.patch 得 exact official 文件，test_globs=()；trusted setup :194–211 恢复它并重施 test patch。gold 的 parsing.pyx 在 included_paths，ignored_paths=[]。没有证据要加额外排除规则。
- 原 prepared summary 仍指向 /work/full216_20260919/replay/{prepared,private}。未来需另建重定位副本、独立 candidate/output/run_id，验证 runtime 镜像和依赖；本轮没有改原 prepared 或任何 /work 路径。

## 逐题开发条件

| 必需操作/资产 | 公开依据 | 已有证据范围 | 当前缺口 | 未来最小验证 |
| --- | --- | --- | --- | --- |
| 定位并导入本工作区 pandas/parsing | traceback；P/parsing.pyx；公开 base | 源文件齐全；grader 包源观测为 /testbed | 正式 agent 实际 PATH、Python、parsing.__file__、初态 HEAD | 用 agent 实际 shell 记录 id/cwd/解释器和 pandas/parsing 来源，再运行题面单例。 |
| Cython/C 工具链与构建写权限 | pyproject.toml:1–9；doc/source/development/contributing_environment.rst:191–212 明示改 _libs 要重编译 | grader 实际 Cythonize/复制 .so 成功 | actor 的编译器、Cython<3、NumPy headers、build/tmp 可写性与构建产物生效 | 在未来重定位工作区按公开构建入口窄验证，记录源码修改后扩展加载和公开测试；不以系统包可写作为当然条件。 |
| 核心依赖与 narrow pytest | pyproject.toml:24–30；test_parsing imports；locale decorator | 历史已安装/执行，114 node 不 skip | actor pytest/dateutil/NumPy、英文 locale 与离线预装资产是否齐全 | `python -m pytest -q pandas/tests/tslibs/test_parsing.py`；记录 skip 与编译加载，不跑全仓。 |
| 网络/外部资产 | 原例与被测路径仅字符串、stdlib、dateutil/NumPy/pandas | 无业务外部服务或下载数据的需求；grader deny_all 成功 | 如工具链缺失，应准备阶段固定补齐 | 不给运行时公网作为默认前提。 |
| 可交付源修复 | public_hints、gold path 与投影 | .pyx 可投影，测试受保护 | 模型侧实际 hints 消息与工具渲染未捕获 | 验证源改动能进入评分；不要求提交 .so 或修改官方测试。 |

正式 actor 的身份/交互/开发环境是未来模型开发门槛；**不是固定 grader 语义诊断必须先跑模型的理由**。本题静态争议应先在相同冻结 grader 条件作 CPU 实验，actor 条件另验。

## 唯一优先后续实验（未执行）

在新重定位副本、原 reference_v1 wrapper + 原 bindings 输入、固定 grader/profile 下，只构造一份**对 _fill_token 的 ValueError 作局部 None fallback**的非 gold 候选；保持业务成功路径和官方 test/reference 不动。核题面单例确实返回 None、不抛错；记录现有 P2P 与新 F2P 的完整 node、解析键、RC/reward；同时核公开 to_datetime fallback 及旧小数/dayfirst 回归。预期若候选满足公开要求、P2P 保持而新 F2P 仅因 None 被拒，即确认误拒。

未来修订应从原“不 error、None 或格式”要求出发，允许 None 或可验证的正确格式，保留旧成功格式保护；不能只为保住 gold 改写题意。这里只列未来窄建议，未写候选、未改测试、未改参考。当前保留 needs_review；静态已发现的接受范围差异不随环境 pair 成功变成 pass。审阅 token/费用无观测，均 null；上表耗时全部为历史原运行，非本轮重跑。
