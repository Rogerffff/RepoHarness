# pandas-dev__pandas-56849 — 独立初判，阶段一

审查日：2026-09-21。角色：B2 pandas 独立 reviewer。建议 `disposition.state=needs_review`、`scope=static_review`、`usage.intended_use=development_diagnostic`；原因是正式 actor 开发环境尚未核验，并非已发现题意或 gold 的决定性错误。本次没有执行 pandas、测试、安装、容器或模型，也没有修改 source/test/gold/reward。

本文 `ROOT=.`，`I=ROOT/runs/swegym_quality_batch02_20260921_v2`，`B=I/public/pandas-dev__pandas-56849/base`，`P=I/private/pandas-dev__pandas-56849`。所有源码行号指本次实际读取的静态文件。未读公开读者、主审、其它 reviewer、旧质量结论、批次聚合、manifest、assignments、CPU 计划或方法调整。读取了本题 `environment_record.json` 的原环境摘要，随后用 own `run_refs.json` 的原账本和日志核对；未跟进该摘要的聚合 evidence 指针。三题均独立初判保存后才等待统一开放第二阶段。

## 1. 公开要求、版本与初始问题

公开题面要求恢复 `pd.date_range("2010-01-01", periods=20, freq="m")` 的月末序列。标题说明 `m` 是已弃用 `M` 的别名，历史输出提供了 20 个具体月末。公开 base 的 `c_OFFSET_DEPR_FREQSTR` 已把 `M` 映射到 `ME`；`offsets.pyx:4863–4871` 却在进入 `_get_offset` 大小写归一化之前按原样查弃用表，`m` 没有被转换，随后 `_get_offset` 查不存在的 `M` 前缀而失败。`DatetimeArray._generate_range`（`pandas/core/arrays/datetimes.py:434`）直接调用 `to_offset`，与题面调用栈相符。

base 为 `612823e824805b97a2dbe258ba808dc572083d49`，tree `edb634158e9d744dc86b29409271680833e98e86`。公开包、grading、validation 分别与各自 S2 JSONL 第 156 行相等；未重新做整包 blob 检查。`test.patch` SHA256 `7b0ccd3808139e626fa131ee5eee11bf89153de1fc3067e437efb7b7decd543f`，`gold.patch` SHA256 `161403c2ba4bd4c7dbab449dbd4463ab524fafacf919fc4547af80cccd9fb4da`。原 noop 的实际失败栈进一步确认了初态问题，不能只把 gold 差异当复现。

`public_hints` 的禁止改测试是公开操作约束；本题合理业务修复可全在非测试源码完成，不与之冲突。其中“conda 已激活”和“所有测试修改都会恢复”的解释不是已验证运行事实。`user_prompt.txt` 是当前函数静态渲染结果，不是捕获的模型消息；public bundle 会物化给 actor，不能因 hints 未在 user prompt 中就称其不可见。

## 2. 需求与断言双向映射

| 要求／合理旧行为 | 公开依据 | 实际断言及参考归属 | 判断 |
| --- | --- | --- | --- |
| 小写 `m` 可生成月末日期 | 题面原例；`_generate_range → to_offset → _get_offset` | 唯一 F2P `TestDateRanges::test_to_offset_with_lowercase_deprecated_freq`：两期结果等于含 `2010-01-31, 2010-02-28`、`freq="ME"` 的 `DatetimeIndex` | 覆盖核心；原例 20 期未逐项断言，不由此单独设硬门 |
| 弃用警告指向 ME，保留月末而非分钟含义 | 标题的 deprecated M；base 弃用表及已有 M/SM/BQ/BY 警告测试 | 同一 F2P 匹配完整 `'m' … 'ME' instead.` 的 `FutureWarning`；`tm.assert_produces_warning` 默认检查警告 stacklevel 和额外异类警告 | 警告种类、替代别名可由公开代码推知；确切文案更窄，但与现有统一格式相同，未据此判误拒 |
| 非法组合仍拒绝，包括 `2h20m`、`-m` | `B/pandas/tests/tslibs/test_to_offset.py:47–90` | 官方 patch 仅给现有 `test_to_offset_invalid` 加忽略小写 m 的 FutureWarning；原 ValueError 及 `Invalid frequency` 匹配未变。两节点均在 P2P | 不是削掉非法频率断言；允许先发弃用警告再拒绝组合 |
| 保持合法 tick、倍率、空白、锚定偏移和既有弃用行为 | 全部 `test_to_offset.py`；`test_date_range.py:152–166,779–819` | P2P 的 `test_to_offset`、negative、whitespace、leading_zero/plus、Timedelta、anchored_shortcuts 及日期弃用参数组 | 相关正文已读；保护 `ms/us/ns/min` 等与大小写敏感分支 |
| 不指定内部实现位置 | 题面是用户行为回归 | 测试只调用公开 date_range 或 to_offset，未 mock 内部 helper | 可采用别名表扩充、局部归一化等非 gold 实现；仍需保留公开弃用语义 |

新增/修改内容已全读：一个新测试的警告和 index 等值断言，以及既有 invalid 参数测试的新 warning filter。F2P 无额外 fixture；已读 `tm.assert_produces_warning` 参数及实际匹配逻辑，包括 `_assert_raised_with_correct_stacklevel` 的调用者文件比较。P2P 实际读了全部 `test_to_offset.py:1–173`，`test_date_range.py` 的导入/helper、M/SM/BQ/BY、H/T/S/L/U/N、A/Y 弃用块、`test_date_range_edges` 全部三种起止边界、负非 tick 频率正文，以及 `pandas/conftest.py:1197–1245` 的 TIMEZONES/tz_aware_fixture；未逐字审全部时区、DST、自定义节假日及所有范围生成测试。未审全仓调用者和 period 专项测试。

## 3. 三套测试集合与原始历史实跑

固定评分参考是 **1 F2P + 419 P2P**。实际执行命令是两整个文件：`pytest -rA --tb=long pandas/tests/indexes/datetimes/test_date_range.py pandas/tests/tslibs/test_to_offset.py`，收集 **426** 项；本人的实际正文阅读范围如上，三者不可互换。parser 记录 420 个键，不代表只执行 420 项；当前 `swegym_parsers.py:45–55` 以空白拆分摘要 node ID，参考中确有含空白参数被截短的键。未逐项建立 426 个完整节点到 420 键的映射，不把本题 419 P2P 宣称为完整节点覆盖。

证据根目录 `ROOT/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-3`，仅看 ledger 第 11、12 行以及 own run_refs 指向日志：

| 角色 | 原日志与决定性行 | 历史结果 |
| --- | --- | --- |
| noop | `eval_logs/evallog_replay-f216-baseline01-w_1d6b2dfa.eval.log:3076,3084,3093,3105,3369,3442,3893–3901` | KeyError M / ValueError m，并缺预期警告；1 failed、425 passed；F2P 0/1，P2P 419/419，reward 0，test rc 1 |
| gold | `eval_logs/evallog_replay-f216-baseline01-w_2a3467af.eval.log:3025,3067–3069,3107,3115,3339,3568–3575` | 日志明确 Cython 编译 offsets.pyx、C 编译、链接 offsets `.so`；426 passed；F2P 1/1，P2P 419/419，reward 1，test rc 0 |

两日志字节 SHA 与 run_refs 一致：noop `3388bfd4a7843a041f294fb2a241e884f5ec6bd69347426c6b63a8dd4ae3cffb`；gold `6f86fcee9c19792299128b7c905f912dd7cffc0a397d17f2980c60353b6a5d50`。ledger 记评分镜像 digest `a8a1cad925505ccd8abad28474286566aed5b0ead05b235354c0611228daf13a`，不是派生配方，`image_id_actual=null`；评分身份 rh2grader/54322、deny_all、2 CPU/4 GiB、可写 conda prefix。观测包入口 `/testbed/pandas/__init__.py`、版本 `3.0.0.dev0+91.g612823e824`。gold 安装约 42.278 秒、测试约 6.373 秒、内存峰值约 680.297 MiB；这些仅是该历史 grader 运行数据。

编译链和行为对照支持 gold 源码在历史 grader 中生效；没有单独记录运行时 `offsets.__file__`，不把顶层 `pandas.__file__` 当作扩展加载位置的完整证明。ledger 的 `apply_user=agent/54321` 只表示补丁应用身份，不能当作正式 actor 开发会话已经成功。

## 4. Gold、合理替代和自然部分修复

gold 只在 `offsets.pyx` 的非 period 弃用分支用 `name.upper()` 查键；警告仍保留输入 `name`，再把别名换为规范偏移。不触碰 period 分支，不全局大写 `ms` 等 tick。已读弃用表、`_dont_uppercase`、`_lite_rule_alias`、`prefix_mapping` 和 `to_offset` 后续倍率/组合/异常逻辑；未发现具体旧行为破坏证据。gold 较题面 m 扩及其它表内小写弃用别名，未见不相关改动。

在同一解析入口把 `m` 加入弃用映射、或仅规范化表内别名，也是可接受实现路线，测试没有强制 gold 的三行写法。自然不完整修复“只恢复解析但漏发弃用警告”会被 F2P 拒绝；“把所有频率转大写”会危及 ms/min 等已有 P2P。只修题面 m、未一并修所有其它小写弃用名，不应无依据判为本题不合格。20 期、其它别名、period 路径未全覆盖是限定范围，不是已证明的质量缺陷。

## 5. 具体开发条件与交付边界

| 操作/资产 | 依据及已有证据 | 仍需区分的条件 |
| --- | --- | --- |
| 定位和编辑频率解析 | 公开 traceback 直达 `pandas/_libs/tslibs/offsets.pyx`；源码完整 | 可交付此 `.pyx`，不需改官方测试 |
| 编译并加载修改后的 Cython 扩展 | base `pyproject.toml:1–18` 与 `doc/source/development/contributing_environment.rst:207–230,290–310`；历史 gold 确认 Cython/C/link | 正式 agent/54321 的 PATH、editable loader、编译器、构建目录和 conda prefix 权限未验；Meson 自动重编不等于在 actor 中已经重编成功 |
| 公开复现与窄测试 | 日期是内存内生成；无需数据集、模型权重、数据库或运行期网络服务 | 预装依赖与 compiler 可在准备时固定；不假设 actor 可联网下载安装 |
| CPU/空间 | 当前 rollout 默认 2 CPU/4 GiB、tmp 1 GiB、home 256 MiB；历史 grader 内存如上 | 不是本题 actor 有效 profile 或构建稳定性实测 |

当前 RH2 `prepared_task_face.py:312–335` 使用 `test_globs=()`；官方精确恢复/保护路径仅为 `pandas/tests/indexes/datetimes/test_date_range.py` 和 `pandas/tests/tslibs/test_to_offset.py`。`trusted_projection.py:79–88` 按精确控制面分类，`prepared_task_face.py:185–234` 恢复官方路径并应用 test.patch。gold 的 `.pyx` 在 ledger included_paths，未被排除；未发现合理修复必须写不可提交资产或被恢复文件的冲突，`additional_exclusions=[]`。

源码、构建配置、非官方 fixture 与解释器环境不全部由官方路径保护，不能把现有隔离描述成“任意控制面均不可修改”；本题没有据此构造攻击或新增规则。当前评分由 `scoring.py:190–272` 的段内解析与冻结 F2P/P2P 决定；普通完整 pytest 的非参考失败及 rc 1 不自动 reward 0。全局启动/收集错误仍由 `manager.py:1197–1249,1314–1325` 等路径判断，不能只看 rc 或只看参考通过。

正式 face 的 `rollout_spec_from_view:342–359` 仍消费 public image；不是把其它修复配方自动带进 actor。`sandbox_profile.py` 固定 actor 54321 / grader 54322，rollout init 只明确 chown 工作区/home；`materialize.py:47–52` 的 BASH_ENV 落在 `/root`，当前 rollout hidden_paths 含 `/root`，实际 shell 注入/PATH 要实测，不能据静态路径单独宣布激活失败。已读 generate 写入点与 CC/run_agent 传递点，未捕获模型请求或真实工具调用。

## 6. 关系、限制与唯一优先下一步

本题不是另外两道 pandas 题的同一缺陷。存在具体跨版本答案暴露关系：本题 base 的 `pandas/core/dtypes/cast.py:634–639` 已含 48106 gold 的分类类型处理，`pandas/api/typing/__init__.py` 已含 53958 gold 的类型导出。本 reviewer 为私有诊断同时读过三题；不应把本审查上下文或跨题新版本源码交给独立 solver，也不能只因同仓把三题并成一个问题簇。

**唯一优先下一步（未来 CPU，尚未执行）：**用正式 actor 启动路径，在指定 public image 中以 agent/54321 核对解释器、pandas/offsets 实际加载位置和权限，再以公开 20 期复现验证一份正常 `.pyx` 修复经实际 editable 构建生效；记录修改前/后、编译输出及修复后序列。其作用是消除本题最具体的 actor Cython 开发条件缺口，不是重新证明历史 gold，也不预先要求全仓测试或泛化反例。固定 grader 上的质量诊断可以单独开展，不能用它替代这项 actor 核验。模型能力、求解成功率、费用/token 均未测；成本字段应为 null。

当前 RH2 阅读快照为 ROOT HEAD `e3d120b55a62cca5985f688de8cdd481b12ea6be`，manager 有未提交改动；引用当前源码不声称与 09-19 原 runner 字节相同。关键文件 SHA256：prepared_task_face `31ff5145dfa8b71b2a183b14f8a5fbfe4572b71911af54023c8168e534e4f8a3`；manager `eadaa64acc2e9dc358ad4c7c4f9ad3bb60d81a1c72298a41dabbdf6397ad6342`；scoring `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`。
