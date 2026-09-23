# pandas-dev__pandas-56849：历史开放前静态分析

本稿在未读取本题历史调查、旧答案、reviewer 或 B1/B2 聚合材料的条件下保存。仅做文本、JSON 和只读 Git 阅读，没有运行项目、测试、安装、容器、联网或模型，也未修改 source/test/gold/reward。公开视角引用本题 `public_read.md`，本主审已暴露于本题隐藏测试及 gold，不是盲解。

路径缩写均以 `.` 为根：`P=runs/swegym_quality_batch02_20260921_v2/public/pandas-dev__pandas-56849`，`B=P/base`，`V=runs/swegym_quality_batch02_20260921_v2/private/pandas-dev__pandas-56849`，`W=runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-3`，`N=W/eval_logs/evallog_replay-f216-baseline01-w_1d6b2dfa.eval.log`，`G=W/eval_logs/evallog_replay-f216-baseline01-w_2a3467af.eval.log`。RH2 源码读取时根仓库 HEAD 为 `e3d120b55a62cca5985f688de8cdd481b12ea6be`；这是宿主源码身份，不替代历史运行脚本摘要。

## 1. 公开目标、版本与初态

目标是恢复 `date_range("2010-01-01", periods=20, freq="m")` 的日历月末序列；标题说明 `m` 是已弃用 `M` 的别名。当前 base 的规范月末名是 `ME`，不应要求恢复旧版本 repr 中的 `M`（`P/user_prompt.txt:3–7,62–77`；`B/pandas/_libs/tslibs/offsets.pyx:2923–2958`；`B/doc/source/user_guide/timeseries.rst:1239–1266`）。题面足以定位入口，无必需外部数据或服务。弃用类别和一般警告风格可从原代码/旧测试推知；小写警告必须原样显示 `m`、完整措辞及所有同族别名的恢复范围没有明示规格。

精确 base 为 `612823e824805b97a2dbe258ba808dc572083d49`，public image digest 为 `sha256:a8a1cad925505ccd8abad28474286566aed5b0ead05b235354c0611228daf13a`（`P/public_bundle.json:1`）。`V/source_refs.json:2–12` 所指 S2 public/grading/validation 各第 156 行与本题局部 JSON 文本解析值相等；没有重做整包 blob 全检。`P/base_identity.json:3–12` 声明导出无 Git 元数据；真实容器线索不能据此推定不存在。

根因路径可由 base 直接推出：`date_range` → `DatetimeArray._generate_range` → `to_offset`；原样 `m` 未命中只有大写旧名的弃用表，之后 `_get_offset` 才将它转成 `M`，以当前 prefix 表查找时失败（`B/pandas/core/indexes/datetimes.py:1008–1019`；`B/pandas/core/arrays/datetimes.py:425–449`；`B/pandas/_libs/tslibs/dtypes.pyx:248–331`；`offsets.pyx:4656–4691,4755–4773,4855–4871,4927–4939`）。既有 noop 实际出现 `KeyError('M')`、两层 `ValueError`，最后还被 warning helper 的“未见 FutureWarning”断言包装（`N:3090–3122,3360–3444`）。因此初态问题不是仅从 gold 差异猜测。

## 2. 需求与全部新增/修改断言双向映射

冻结 F2P **1**，P2P **419**（`V/grading.json:1`）。唯一 F2P 为 `pandas/tests/indexes/datetimes/test_date_range.py::TestDateRanges::test_to_offset_with_lowercase_deprecated_freq`；无显式 fixture/Mock，调用真实 pandas 日期范围实现。

| 要求或合理旧行为 | 公开依据 | 对应检查、断言及结论 |
| --- | --- | --- |
| 小写 `m` 成功生成日历月末 | `P/user_prompt.txt:7,68–77` | `V/test.patch:9–18` 调 `date_range(...periods=2,freq="m")`，与 `2010-01-31/2010-02-28` 的 DatetimeIndex 比较；覆盖首两个时间点、类型/dtype、长度、顺序、名称。原 20 个点、跨年和闰年没有新增直接检查。noop 失败、gold 通过有真实日志。 |
| 遵循 `M` 已弃用、改用 `ME` 的语义 | 标题；`B/offsets.pyx:4863–4871`；`B/pandas/tests/indexes/datetimes/test_date_range.py:149–166` | F2P 要 `FutureWarning`，`match` 包含整句且必须小写 `'m'`，helper 还检查 warning 指向调用文件、无额外类别（`B/pandas/_testing/_warnings.py:28–35,96–113,128–180,217–230`）。类别和替代名有依据；大小写与完整措辞存在过严疑点。不是字符串严格相等：实现用 `re.search`，末尾 `.` 亦未转义。 |
| 正确频率属性 | 月末别名、`date_range` 固定频率返回约定（`B/pandas/core/indexes/datetimes.py:835–857`） | expected 传了 `freq="ME"`，**不等于实际频率被断言**。`assert_index_equal` 不比 DatetimeIndex.freq；`equals` 最终比 dtype 与 asi8（`B/pandas/_testing/asserters.py:181–349`；`B/pandas/core/indexes/datetimelike.py:141–175`）。此项是具体覆盖限度。 |
| 非法 `2h20m`、`-m` 仍报 ValueError | `B/pandas/tests/tslibs/test_to_offset.py:47–90` | `V/test.patch:23–34` 只给此参数化测试增加忽略小写 `m` 弃用 warning 的 marker，29 个冻结 P2P 键仍检查原异常。没有删断言；gold 在先发 warning 后判非法的时序下能继续测异常。该 marker 也限定 warning 文本大小写。 |
| 正常单位、倍数、组合与锚点不回归 | `B/pandas/tests/tslibs/test_to_offset.py:12–173`；日期范围旧测试 | 已读本文件全部测试：offset 对象/Timedelta、分钟与亚秒组合、正负号、空白、零前缀、非法语法、W/QE/SME/SMS 锚点。日期范围已读 `2M/2ME`、SM/BQ/BY 与 A/Y/H/T/S/L/U/N 弃用、MS 负向范围、ME/YE 负倍数、边界/inclusive、month-start 与 semi-month-end 等相关测试体及 fixtures。有保护，但没有 `2m/-2m` 或直接 `to_offset("m")` 的新例。 |
| MS/ms/min 与 Period 语义保持 | `B/doc/source/user_guide/timeseries.rst:1247,1262–1266,1315–1326`；`B/pandas/tests/scalar/period/test_period.py:31–117` | 所读 P2P 的分钟/亚秒和 MS 路径有保护；Period 测试、offset 名称测试不在本题执行/冻结集合。gold 的 `is_period is False` 条件仍隔开 Period。其他旧小写名仅属共享根因的合理扩展，不能把未枚举大小写全部强加为本题必需目标。 |

全 test.patch 为两处上述变化；没有新增源码、外部 fixture 或隐藏 helper 名要求。全 gold.patch 仅对 `offsets.pyx` 弃用表的条件、replacement 查询和赋值改用 `name.upper()`（`V/gold.patch:5–23`），保留原输入用于 warning。静态上可恢复一般 `m`、倍数及同族旧名，不改 `MS/ms`，也不改变 `is_period=True` 分支。无无关代码或未交付新增依赖。已有 gold 通过不能外推所有同族别名、Period 或全仓回归。

## 3. 合理解、部分实现与误判疑点

合理替代路线：只在 `is_period=False` 且 `name.upper()` 确为旧别名时先规范化名称，再复用现有弃用转换。正确保持特殊大小写（MS/ms）、倍数与非法输入语义，可产生相同月末结果，但 warning 用规范名 `'M'`。题面称其为 M 的别名，公开旧测试未规定这个输入应打印哪种大小写；F2P 的小写文本会拒绝它，非法输入 marker 也不忽略大写 `'M'`。目前这是**源码支持的潜在误拒**，尚无本轮候选运行证据，不能写成已测得的 RH2 假阴性。

自然的部分实现是仅在 `date_range` 入口把字面 `m` 换成 `ME` 并发 warning，未修共享 `to_offset` 或倍数 `2m`。它可能满足唯一 F2P 与全部旧 P2P，却没有完整恢复公开“频率字符串可有倍数”的接口（`B/pandas/core/indexes/datetimes.py:854–857`；`B/pandas/tseries/frequencies.py:30–34`）。另一具体缺口是包装器将正确日期重建为无 freq 的 DatetimeIndex，F2P 不检查该属性。两者均未制作/运行，不声称已证假阳性；不靠任意硬编码来判题无效。

## 4. 三套集合及既有真实运行

| 集合 | 所见范围 |
| --- | --- |
| 实际 pytest 执行 | 两个官方文件，426 collected；noop 425 passed/1 failed、rc=1（`N:3075–3087,3893–3901`）；gold 426 passed、rc=0（`G:3106–3118,3339,3568–3575`）。完整正常收尾与失败 traceback 支持目标测试体确实进入执行。 |
| 冻结评分参考 | F2P=1、P2P=419，账本 parsed=420，missing/skipped 均空；noop reward=0、gold=1（`W/ledger.jsonl:11–12`）。不是“426 个独立评分键”。 |
| 本主审实际读过 | 全新/修改测试、唯一 F2P、全部 `test_to_offset.py` 测试体；日期范围相关片段、参数、fixture/helper，范围见末节。已枚举所有冻结 P2P 函数名及参数数量，但没有逐字审阅其余日期/时区/自定义营业日测试体。 |

本题有可定位的 parser 身份压缩：`swegym_parsers.py:44–55,99` 按空白 split、同键覆盖。原日志 426 条状态变为 420 键；10 个实际节点合并为 4 键，少 6 个身份：custom-business-day 的同一带时区日期两例、`test_to_offset[2h` 的三个组合、`test_to_offset_whitespace[2` 两例、`test_to_offset_whitespace[` 三例（`N:3729–3730,3814–3817,3864–3868`；`G:3404–3405,3489–3492,3539–3543`）。两次这些节点都实际 PASSED，因此**不推翻此对 noop/gold 分差**；但不能把 419 个 P2P 键说成独立保护了每个参数实例。静态可见同键不同状态会后写覆盖，是共享评分限制，未经本题反例运行不扩大为已观测错分。

评分取 F2P/P2P，而非 pytest 总退出码直接决定所有 reward：`rh2/src/repoharness2/envpack/scoring.py:189–309`；manager 对外层正常 pytest rc=0/1 与收尾作区分（`grading/manager.py:1197–1230,3082–3106`）。普通已完成会话的非参考失败不自动 reward=0；本题现有日志没有此类额外失败。

## 5. 开发环境与 actor/grader 边界

`W/ledger.jsonl:11–12` 使用原 public image/digest，`derived_image_recipe=null`、`image_id_actual=null`、`env_qualification=absent`。UID54321 仅是 candidate.apply_user；实际安装和测试为 rh2grader/54322，拥有 `/opt/miniconda3/envs/testbed` 可写前缀、2 CPU/4GiB、deny_all 网络。不能从 apply_user 或 grader 安装成功填 actor 开发通过。

noop 为干净工作树、HEAD=base（`N:1437–1441,1504`）；gold HEAD 同 base，唯一候选源码差分是 offsets.pyx（`G:1437–1446,1509–1532`）。`git show` 中 ci/categorical/plotting 差分是 base 提交展示，不是候选脏文件。原件给出 Python3.10.15、pytest8.3.3、NumPy1.26.4、Meson1.2.1、Cython3.0.5、gcc13.3、Ninja1.12.1 与 editable 安装；gold 实际重新编译 `.pyx`、C 对象并链接扩展（`N:2997–3066,3080–3084`；`G:3025–3075,3082–3115`）。安装末行是卸载 pytest-qt，故只引用 RC=0 不够；此处已经读到 pandas 构建/安装成功正文。峰值约 noop668.891/gold680.297 MiB 为既有 grader 观测，不是 actor 资源保证或新 CPU 测量。

| 开发需求 | 依据与现有适用证据 | 仍待核对及最小验证路径（未执行） |
| --- | --- | --- |
| 导入当前 checkout 的 pandas 与 offsets 扩展 | `B/pyproject.toml:1–38`；以上 grader 安装/版本日志 | 正式 actor/54321 的 shell 中核 `id/pwd/command -v python` 与 `sys.executable,pandas.__file__,offsets.__file__`；不得以当前宿主 Python 替代。 |
| 修改 Cython 后加载新实现 | `B/doc/source/development/contributing_environment.rst:211–230,260–275,292–310`；gold 编译日志 | actor 的 editable loader、build 目录与解释器前缀写权限未知；优先确认既有 Meson import 重建，必要时用已有离线依赖作 `pip install -ve . --no-build-isolation --no-deps --no-index`。这只是建议，不新设必须重装条件。 |
| 本地复现和窄范围 pytest | `P/user_prompt.txt:7,68–77`；`B/pyproject.toml:66,482–525`；`B/pandas/conftest.py:38–60` | 用公开 20 点复现与 ME 比较，再跑相关公开测试；需 pytest/Hypothesis，XML 输出目录可写。业务输入是字面日期，不需外部资产、数据库、GPU或运行期公网。 |
| 合法交付 | gold 仅 `.pyx`，原件投影只包括该源码 | `.so/build` 是派生编译产物；评分重建源码。原“不得改测试”若实际适用仍约束 solver；可在临时脚本核 warning/原例。正式公共镜像、消息注入、激活和工具链仅有说明，尚非本题 actor 验收。 |

## 6. 投影、恢复、控制面与泄漏

精确 official 恢复文件仅 `pandas/tests/indexes/datetimes/test_date_range.py` 和 `pandas/tests/tslibs/test_to_offset.py`，由 test.patch 两条路径得到；没有普通业务源码混入。当前 `test_globs=()`（`rh2/src/repoharness2/adapters/slime/prepared_task_face.py:312–336`）；逐 official 路径从 base checkout、再 apply 官方 patch（同文件 `:187–234`），原日志也见两文件恢复、apply RC0 和 setup OK（`N:1505–1555`；`G:1533–1583`）。`.pyx` 合理解可进入投影，gold 账本 included_paths 也如此。

`trusted_projection.py:1–28,79–88` 表明 official 路径改动被忽略而非一概拒题；不能沿用“所有 tests/testing 文件均不可交付”。本题无需修改恢复文件才可修复。`pandas/_testing/_warnings.py`、`asserters.py`、conftest/pytest 配置未在这两条 official 名单内，确会影响测试可信度；这是可见通用控制面限制，本轮无攻击运行、无新增排除依据，`additional_exclusions=[]`。原公开 hints 的禁止改测试指令是否进入真实消息仍待核，不能借实际渲染未知自行取消指令。

公开包无 gold/F2P/P2P；是否存在真实镜像缓存、Git 可见未来答案或工具出网获取答案，本轮未验证。题面有 issue/用户名定位线索，不等于已获取答案。未读取其他题，不能按同为 offsets 文件自动判断任务同族或数据污染。

## 7. 八方面处置与唯一优先实验

八方面已覆盖：公开规格与层次、初态与版本、全部新增/修改断言及实际/参考集合、合理替代解、相关回归及 gold、开发要求与身份、投影/恢复/控制面、用途与暴露。未查的是正式 actor 全链、完整 P2P/全仓调用者、稳定性重复、模型能力/成本和跨题关系。

暂定保留为 **development_diagnostic 静态候选，needs_review/static_review**：核心题意和 noop/gold 分差可解释，没有把一般 actor 未验直接当坏题。仍有 warning 大小写误拒疑点、m 倍数/共享入口/freq 属性覆盖限度及参数身份压缩，均保留其证据层次；不预先修改原题/参考或批准训练、评测。

唯一最值得先做的实验：在获准的隔离 CPU 条件中验证上述“仅规范化已识别旧别名、warning 保留规范名 M”的非 gold 合理解，先确认公开 20 点、`2m/-2m`、MS/ms、非法语法和 Period 合理旧行为，再通过相同 RH2 条件评分，记录具体 warning 断言拒绝是否是唯一原因。这个实验可直接区分规格自由度与测试误拒；不得只改 warning 关闭全部警告，亦不要求先穷举全部别名或重跑216题。正式 actor 可用性另待共享入口验收，不在本题创造更多硬门。

## 8. 原件实际阅读范围

- 完整：P 的 prompt/bundle/identity/environment brief；V 的 source_refs/run_refs/test.patch/gold.patch/validation/environment_record；grading 全 JSON 经文本解析，完整 F2P、P2P 函数名/参数数量清单及所用字段；本题 S2 精确156行文本比较；本题 public_read（1–174）；W ledger **只第11、12行**。没有打开 reconciliation 聚合表。
- 日志：N 的2990–3125、3360–3455与关键 setup/HEAD/收尾匹配行；G 的3018–3127、3336–3342、3566–3577与对应 setup/HEAD行。两原件全状态行做纯文本整理以核计数/身份合并；未逐字读两个日志全部 conda激活输出。diagnostics 仅键名、task_id和observations，不冒充完整sidecar复核。
- Base：`offsets.pyx`2923–2986、4650–4958；`dtypes.pyx`228–360；`core/indexes/datetimes.py`821–880、1002–1023；`core/arrays/datetimes.py`404–460；`core/indexes/datetimelike.py`135–188；`tseries/frequencies.py`1–45；`_testing/_warnings.py`28–180、217–230；`_testing/asserters.py`181–378。
- 测试及fixtures：`tests/tslibs/test_to_offset.py`1–173全文；`tests/indexes/datetimes/test_date_range.py`1–220、481–501、578–627、700–824、1245–1280、1343–1360、1507–1718；`tests/tseries/offsets/test_offsets.py`748–846；`tests/scalar/period/test_period.py`1–120；`pandas/conftest.py`38–62、260–283、332–345、1200–1284。局部片段边缘未完整的函数不作为已完整覆盖。
- 文档/配置：pyproject1–76、482–525；timeseries.rst1227–1285、1314–1333；contributing_environment.rst211–230、260–275、292–310。未根据 public_read 的未亲读路径代作源码验收。
- 共享机制：scoring.py184–320；swegym_parsers.py1–117；manager.py246–330、558–572、660–696、1195–1238、3080–3132；trusted_projection.py1–155；prepared_task_face.py187–240、300–336；相关路径关键词检索。共享方法/环境卡/模板和40项格式指引；未依本题外旧案例作结论。

保存后等待协调者封存并按本题开放历史；本稿不回写。
