# pandas-dev__pandas-50319：读历史前的私有独立初稿

状态：`needs_review / static_review`；用途：`development_diagnostic`。本稿在读取本题旧单题记录前保存，封存后不回写。2026-09-21。权威根目录为 `${REPO_ROOT}`；默认 worktree 未作证据源。

**暂定判断：存在明确的公开允许结果与隐藏断言冲突，先保留语义争议；已有 reference_v1 环境对照支持原 bug 和 gold 生效，但不能据此准入正式模型开发。** 题面明说可返回 `None` 或有效格式，新增测试只接受 `%d.%m.%Y %H:%M:%S.%f`。优先未来实验是保持旧行为、仅在无法安全处理点分日期 token 时返回 `None` 的一般化替代路线，分别核公开复现与原评分；本轮未写或执行候选。

## 证据边界、暴露及材料对应

以下简称 P=`runs/swegym_quality_batch03_20260921_v1/public/pandas-dev__pandas-50319`，Q=同一输入根的 `private/pandas-dev__pandas-50319`，R=`runs/env_recipe_repair_20260919/reference_v1`，G=`R/runs/pandas-dev__pandas-50319-gold`，N=`R/runs/pandas-dev__pandas-50319-noop`。所有相对路径均从权威根解析。

已读共用角色卡、环境卡、记录模板和八方面协议；本题公开包、自己的 `public_read.md`、Q 七原件；inventory 仅 common、families.reference_v1、tasks 本题项；精确指向的本题原始账本、日志、诊断、绑定输入与输出；以及原调用链所需的历史 harness 归档成员。**Q/environment_record.json 自带 gold/noop 和旧环境修复摘要，初稿前已暴露，不能称全盲审。** 其 `analysis_20.json` 聚合及其它题内容未读；历史单题记录、reviewer、B3 assignments/聚合未读。公开初读是另一新上下文完成，当前主审不是公开盲读者。

| 原件 | 对应事实/断言及核查 |
| --- | --- |
| P/public_bundle.json、user_prompt.txt、base_identity.json | base=`1613f26ff0ec75e30828996fd9ec3f9dd5119ca6`，tree=`51c401ff1bb51e8a235a0f6777f209d8f671da77`；图像引用及 manifest digest；issue 接受两类返回。导出无 .git/gitlink/LFS 缺件是导出声明，不是实际容器完备性验收。 |
| Q/source_refs.json | public/grading/validation 原 jsonl 精确第153行，分别复核 raw SHA `0a9b3105…`、`1762e9b7…`、`089b0e78…`，与导出对象相等；未打印其它行。 |
| Q/grading.json、test.patch | base 一致；一个官方测试文件，新增一个参数，F2P=1/P2P=109 个冻结参考键；eval_cmd=`pytest -rA --tb=long`。完整展开如下。 |
| Q/validation.json、gold.patch | gold 仅改 `_fill_token` 的小数识别条件及注释；patch SHA=`70ca3fa70b50975e2fe34f0f790e66f9f7c7a1453220c0bf6d69d30d145214ec`，与 G/ledger 第1行候选摘要一致。 |
| Q/environment_record.json、run_refs.json | 是索引与已有结果摘要；结论另以 G/N 的 log、ledger、diagnostics、driver.log 及 binding audit 核对，不仅引用摘要。两 ledger 与两 log 全文件 SHA 均与 run_refs 相符。 |
| 原 prepared manifest 本题项、host_grading_views.jsonl 第153行 | task/source、environment digest、grading digest 与库存一致，host grading 与 Q/grading 对象相等；host 行 SHA=`709886cc…`。prepared 原 `/work` 路径不在本机，后续重定位须另建文件，本輪未改。 |
| R/reference_bindings_v1.json 的 tasks[本题] | 原输入含顶层 version/decision/tasks；只取本题一个绑定。run 下 `bindings/reference_bindings.json` 是选中项审计输出，`.reference.json` 是应用结果，都不是原 --bindings 输入。 |

## 1. 公开需求与初态

`user_prompt.txt:5-24` 的直接入口是 `guess_datetime_format('27.03.2003 14:55:00.000')`，结果可以是 `None`，也可以是有效格式，不能抛所报空字符串转整数错误。`parsing.pyx:862-879` 的公开 docstring 同样允许无法推断时返回 `None`。题面 traceback 带调试 print、行号略偏，给定 base 无这些 print，但符号和语句路径匹配。

实际初态链：`du_parse`（906-910）成功后 `_DATEUTIL_LEXER_SPLIT`（915-916）按 `_timelex.get_tokens:789-832` 分离日期中的 `.`；`guess_datetime_format:953-970` 对每个 token 调 `_fill_token`；base 的 `1017-1028` 对任何含点号 token 都走 `token.split('.')` 和 `int(seconds)`，单独 `.` 导致秒字符串为空。**这不止是静态推演：** N 原日志 4901-4960 展示同一输入、函数调用及 pyx:965→1023 的 `ValueError`，N:1420-1423 的 git 状态为 clean/base commit；不是 collection/import 错误。

`public_hints` 的非测试源码操作要求与 issue 语义分开；其“conda 已激活”及“所有测试修改都会恢复”不当运行事实。当前静态渲染未捕获真实 CLI/system/tool 消息，bundle 字段未出现在 user_prompt 不等于 actor 不可读。禁改测试若适用，业务 `.pyx` 仍可合法修复；若不适用，合理新增回归测试可提交，但当前官方 test_parsing.py 会恢复。

## 2. 完整新增测试、helper、F2P 与双向映射

官方 test.patch 只有一个 hunk：在公开 `pandas/tests/tslibs/test_parsing.py:144-186` 的 `string,fmt` 参数表加入 `('27.03.2003 14:55:00.000', '%d.%m.%Y %H:%M:%S.%f')`。没有新源码、Mock、fixture 或文件名测试。测试函数直接调用 Cython 导出函数，随后 `assert result == fmt`。它继承 `@td.skip_if_not_us_locale`；该装饰器的 `_skip_if_not_us_locale` 在 `pandas/util/_test_decorators.py:124-128,202-205` 读取 locale，仅 en_US 执行。Pandas conftest 的 autouse `configure_tests:250-255` 仅设置 chained_assignment；collection hook `139-187` 处理 slow/network/db、doctest 及警告，没有对此 F2P 替换目标函数。pytest 配置 `pyproject.toml:287-318` 含严格配置、no capture、JUnit、asyncio=strict。

唯一 F2P 的**冻结键**为 `pandas/tests/tslibs/test_parsing.py::test_guess_datetime_format_with_parseable_formats[27.03.2003`；**实际节点**为 `pandas/tests/tslibs/test_parsing.py::test_guess_datetime_format_with_parseable_formats[27.03.2003 14:55:00.000-%d.%m.%Y %H:%M:%S.%f]`。旧 parser 在空白处分割造成短键，不能将短键直接当可运行 pytest nodeid。当前日志显示这个具体测试体确实执行，N 失败、G:5007 通过，均非 skip。

| 公开要求/合理旧行为 | 公开依据 | 测试/决定性断言 | 覆盖及反向依据 |
| --- | --- | --- | --- |
| 目标输入不抛异常，可返回 None 或有效格式 | issue 末句；parsing.pyx:877-879 | 唯一 F2P 直接调用并精确 `== '%d.%m.%Y %H:%M:%S.%f'` | 不抛异常及成功推断路线已覆盖；**拒绝明确允许的 None 路线，冲突**。精确结果是隐藏新增要求，旧格式测试不取消 issue 对新输入的显式让步。 |
| 已支持的紧凑、年月、日期、ISO/空格时间及时区形式保持原结果 | test_parsing:144-186 | with_parseable_formats 的32旧实际节点/31 P2P键 | 每个旧参数都要求原 fmt（含14种时区格式/精度组合附近的 None 分支）；这些精确断言有公开依据。新目标不是既有参数。 |
| dayfirst 偏好及旧警告 | :189-193、240-265；parsing.pyx:902-904,1031-1051 | with_dayfirst 两节点；no_padding 12节点/9键；结果相等，tm.assert_produces_warning 校验类别、regex、stacklevel、额外警告 | 有依据、相关保护。`_testing/_warnings.py:19-204` 已展开；None/False 要求无警告，指定 UserWarning 要求出现且文本匹配。目标 F2P 本身未断言无警告，G 警告正常存在。 |
| 月名及 locale 特定格式 | :196-207 | 3 locale 节点直接比较 fmt | 有公开依据；在本历史环境执行通过，非 en_US actor 可能 skip，待核。 |
| 无法猜测值返回 None；错误类型抛 TypeError | :210-237 | invalid_inputs 的8字符串 `is None`，wrong_type 的9、datetime 两节点 `pytest.raises(TypeError, match=...)` | 有依据，限制“全返回固定格式/全吞异常”的部分实现；不要求任意类型都不报错。 |
| 小数秒3/6/9位保持猜测 | :315-327 | 三 `test_guess_datetime_format_f` 均 `== '%Y-%m-%dT%H:%M:%S.%f'` | 直接保护 gold 所涉秒补齐分支；不会证明所有点分日期均已支持。 |
| 上层数组推断和 to_datetime 回退保持 | datetimes.py:129-146,432-462；test_to_datetime.py:2294-2340 | 公开 TestGuessDatetimeFormat 检查首个非空项/全空；TestToDatetimeInferFormat 比较显式格式与推断 | **不在本题 P2P/实际命令内**，仅静态阅读。None 被上层接受并逐项解析，进一步支持合理回退；整体调用者回归未实测。 |
| 同模块季度、月频、日期识别、ISO格式及 try_parse_dates | test_parsing.py:18-141,268-312 | 20测试函数族的剩余参数、异常/数组/格式判断 | 全文件已读、均在实际命令；多为旁路，不把数量算成对点号问题的额外覆盖。 |

合理非 gold 路线：在格式匹配遇到无法安全归类的纯点分隔 token 时停止猜测并返回 `None`，保留既有 ISO 小数秒/非点分日期路径；也可用基于 token 结构的判断成功猜出格式，未要求必须调用 `re.search`。前一类与 issue 一致但原 F2P 按源码必不接受；是否具体实现保留所有旧行为需要未来 CPU 对照。无条件 `return None` 会被大量已有 P2P 拒绝，不能作为合理修复。只特殊处理题面单一字面量的实现可能过测试，但 issue 只明确给一例，不能仅凭没有同类额外参数就证明漏判；更广覆盖只能列建议，不把 gold 的实现范围偷换成完整规范。

## 3. 回归范围、实际节点与解析键

已全文读 test_parsing.py:1-327。受影响的猜测函数族共62旧实际节点，对应58 P2P键：parseable 32/31、dayfirst 2/2、locale 3/3、invalid 8/8、wrong_type 2/2、no_padding 12/9、fraction 3/3。其余51 P2P节点/键为时间/季度/月频/类型/ISO/try_parse_dates 的旧行为。gold 下另有1新F2P，共114实际节点。全部参数表已展开阅读，相关 warning helper 与 locale helper 已展开；未展开整个 pandas 全仓/所有间接调用者，未把非受影响 helper 的每个内部实现作全仓审计。

**五层数量分开：** G/N 都 `collected 114`；G 114 passed、N 113 passed+1 failed；摘要按空白拆分只产生110原始键；固定 F2P/P2P 参考为1+109=110；reference_v1 补回反斜杠 alias 后111解析键（包含原双反斜杠额外键），命中110参考，missing/skipped=[]。这些数量不是互相矛盾。

原 `baseline.tar.gz!src/repoharness2/envpack/swegym_parsers.py:44-56` 以 `line.split()[1]` 作键，后出现状态覆盖前值。本题两个旧 alias 仍合并：

- `with_parseable_formats[2011-12-30`：完整 `2011-12-30 00:00:00` 与 `.000000` 两节点（G:4980,5004）。
- `no_padding[2011-1-1`：`0:0:0` 和 `00:00:00` × dayfirst False/True 四节点（G:5029-5030,5033-5034）。

本题原 bindings 只覆盖 `test_is_iso_format[%Y\%m\%d` → 日志中转义为双反斜杠的完整 node；**未把上面2/4成员 alias 改成全部成员必需**。当前 G/N 六成员均实际 PASSED，所以不能据此推翻现有结果，也不能直接声称某失败必被末值掩盖（`-rA` 的失败摘要顺序也会影响）；能确定的限度是成员缺席未被该 alias 的存在检查单独保护。未来若做解析诊断，应使用固定日志成员缺席/skip 对照，保留真实 `-rA` 顺序；本轮未运行任何 parser 或合成实验。

## 4. gold 完整性

gold 将 `_fill_token` 的 `if '.' not in token` 改为 `if re.search(r'\d+\.\d+', token) is None`。纯 `.`、非小数标点走 zfill 路径，数字小数仍补齐秒至两位、小数右补再取六位。`re` 在原 parsing.pyx:4 已导入，无新依赖；lexer 810-815 已限制数字小数 token 形状，故不能单凭 search 非 fullmatch 断言多点拆包回归。只改一个业务文件，未混入其它功能、测试 helper 或预期更新。原目标在 G 实际通过；相关62旧节点亦过。未测更广 dateutil/locale 输入空间、调用者回归、性能，不能声称 gold 全正确或唯一合法实现。

## 5. 历史真实 RH2、环境与开发需求

调用入口经 R/run_reference_cases.py:25-39，`replay_with_install_recipe.py --code-root /work/full216_20260919/code/rh2 --bindings R/reference_bindings_v1.json --audit-dir <run>/bindings -- run --prepared-summary ... --task-ids pandas-dev__pandas-50319 --candidate noop|gold-dir:...`。wrapper:61-78 仅替换本题 parse_log，追加 grader_version 并调用归档 `scripts/replay_grade.py`；本题未传 recipe/materials/derived-image。archive 是 `runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`，仅 tarfile.extractfile 读取，无解包/导入/执行。已核 driver、ReplayGrader、prepared_task_face、spec_vendor 归档 SHA 与 inventory 四条相符；**当前生产源码不是这些历史字节的替代。**

原 vendor `swegym_specs_242429c1.json[pandas-dev/pandas][2.0]` 安装串为 `python -m pip install 'numpy<2'; python -m pip install -ve . --no-build-isolation -Ceditable-verbose=true; pip uninstall pytest-qt -y;`；pre_install 的 git fetch 是原准备阶段说明，本次 candidate 安装串不执行它。`RH2_INSTALL_RC=0` 仅最后 uninstall 的退出码，不能单独证明 editable 构建；本次另有实际 built/installed 输出（G:4885-4898，N:4861-4874）、源码包版本/导入路径及预期行为翻转支持候选生效。

| 层次 | G / N 事实及原件 |
| --- | --- |
| 初始/投影 | G ledger:1 仅 included parsing.pyx；N 无候选路径；log G:1428、N:1423 显示 base commit。 |
| 安装/测试 | G 731.263秒安装、5.252秒测试，N 701.046/5.424；为**既有账本**计时，本轮成本未知。G:4913/N:4889 真正命令都是 `pytest -rA --tb=long pandas/tests/tslibs/test_parsing.py`。 |
| 普通 pytest | G:4920/5057/5065 为114收集、114 passed、rc=0；N:4896/5090/5098 为114收集、1 failed+113 passed、rc=1。pytest 8.3.3/Python3.8.20；无本题 skip。 |
| 原 parser/修订 | G binding audit original 为F2P1、P2P108/109、missing反斜杠键；revised F2P1、P2P109/109、resolved；N revised F2P0/P2P109、unresolved。binding 函数:14-32 对列出的完整成员要求全部出现并取最坏状态。 |
| 评分与rc | G reward1/N0 由冻结参考解析而来，archive scoring.py:250-269,291-309；test rc仅诊断（prepared_task_face:147-156），两者在本次恰好一致，不可泛化为 rc=0 必然 reward1。 |
| 身份/资源 | grader rh2grader/54322、conda prefix 可写、2CPU/4GiB/PID512/tmp1GiB/shm64MiB/network deny_all；候选 apply=agent/54321。两者均不是正式 actor 的 CLI 开发验证。峰值G902.945MB/N838.82MB来自账本，resource_facts=null。 |
| 镜像/清理 | 镜像 tag 与预期 digest=`sha256:e645e4346df9200174e8b879ad8fb7a09f64f91c7375311e2569596d054ba21e`；**image_id_actual=null**，没有派生 recipe；当前可用性未知。ledger cleanup removed=true，driver.log第3行没有 open containers/cleanup failures；env_qualification=absent。 |

| 开发操作/资产 | 公开依据 | 已有证据范围与缺口 | 未来最小验证（未执行） |
| --- | --- | --- | --- |
| 定位入口、源码与依赖导入 | parsing.pyx:1-66,862；pyproject:24-30 | grader 导入 `/testbed/pandas/__init__.py`；正式 actor PATH/解释器/扩展来源及编译产物新鲜性未知 | 实际 agent shell `id; pwd`，分别打印 Python/pandas/parsing 路径和版本，再直接调用题面。 |
| Cython重建及可写安装 | pyproject:1-10 的Cython>=0.29.32,<3、setuptools/wheel/NumPy/versioneer；setup:398-425 | 历史 grader editable build成功；actor 未证明有编译工具、合适权限/空间；正式默认资源不能从grader成功代填 | 在预置工具链条件下 `python setup.py build_ext --inplace -j 1`，新进程复查扩展与题面。不以预装wheel代替候选源码。 |
| 窄公开回归与locale | test_parsing:144-265,315-327；conftest:37-48 | 历史pytest/Hypothesis/asyncio等存在，en_US相关测试执行；actor依赖/locale/JUnit可写待验 | `python -m pytest -q -rs pandas/tests/tslibs/test_parsing.py -k guess_datetime_format`；另以公开题面验收允许None。 |
| 调用者 | datetimes.py:129-146,432-462 | 只做静态追踪，本题历史命令未覆盖 | 窄跑 `pandas/tests/tools/test_to_datetime.py::TestGuessDatetimeFormat`，必要时原例的to_datetime链。 |
| 业务资产、网络、服务 | 输入是内联字符串，源码无新业务文件；base_identity无gitlink/LFS | 无需GPU/外部服务/下载数据；依赖需准备期预置，不默认actor能公网pip | 导入/编译探针先列具体缺件；无需外部答案/运行期服务。 |
| 可交付文件 | test.patch仅官方test_parsing.py，gold仅业务pyx | 业务源可投影；编译产物/系统包不是必要提交物，测试文件官方恢复 | 提交源码并验证重建生效；无证据添加额外排除路径。 |

正式 actor 验证是后续模型开发的门槛；此处优先语义定点诊断可以独立验证 grader，不把正式 actor 设为每个固定诊断的必需先验。本轮不安排执行顺序的额外审批。

## 6. 交付、评分控制面、关系和用途

历史 `prepared_task_face:194-220,305-333` 从 test.patch 收集官方路径，恢复到base并应用官方 patch；`test_globs=()`，没有按测试文件名一刀切排除。日志 G:1685-1725 与 N diagnostics 核1个恢复、1个保护文件、apply_rc0；业务 parsing.pyx 没被恢复。当前 test.patch 未夹带业务代码；源码、conftest/pytest配置/安装控制面其它可写性是共享边界，未运行注入、绕过或安全实验；不可将无异常观测当成防操纵证明。runner digest前后相等是此次观测，不是候选任意行为的保证。

无须题目特有 exclusions，保持 `additional_exclusions=[]`。仅从本题可确认 issue 目标、GH50317注释与任务50319之间是材料内引用关系；未检索其它题/未来修复，不能从同文件推断跨题簇。提示有精确错误栈但未给 gold 修法，公开base不含未来Git元数据；真实镜像隐藏资产/历史的答案泄漏未验。审查者已见私有测试/gold/环境摘要/绑定，产物不可给 solver；不推断模型成功率、训练价值或费用。

## 7. 暂定问题、下一步和未查项

1. **S50319-1 规范冲突（直接文本/静态断言证据）**：None合法而F2P必拒。最优先未来实验采用窄、一般化的安全回退候选，独立核题面、旧62个猜测节点和原reference_v1得分；期望公开目标满足而原F2P失败。实际替代实现尚未执行，不把结果写成已证明的CPU误拒。若修订测试，应以原公开需求为准，同时保持错误格式拒绝，不为保gold唯一化而篡改题面。
2. **S50319-2 解析覆盖限度（归档源码+真实摘要证据）**：一个反斜杠键已修复，但两个多成员 alias仍合并。当前114实际节点全有证据，不能把这项当成本次gold失败；未来固定日志缺席对照可确定具体计分风险，未执行。
3. **S50319-3 开发运行条件未知（现有grader证据不外推）**：原镜像实际ID未知、当前镜像/路径未就绪，正式agent编译和源码生效待验。不能因而宣判题不可解，也不能标 actor pass。

八方面均有实际阅读：①公开要求及消息未捕获；②对应材料/真实noop初态；③完整新增F2P和62受影响P2P节点、旁路51；④None替代路线及精确断言冲突；⑤gold与调用者静态链，未验全仓；⑥开发依赖/权限/编译/网络分阶段；⑦官方恢复与解析适用边界；⑧仅本题关系与暴露用途。未读旧单题结论，未读reviewer；未运行项目、导入项目、测试/构建、安装/下载、网络、Docker/SSH、付费模型、quota/reset；未修改源/test/gold/reference/reward/expected、未提交推送。本轮仅stdlib文本/JSON/hash和归档成员只读，加本稿写入。
