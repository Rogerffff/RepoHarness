# pandas-dev__pandas-53958 — 独立初判，阶段一

审查日：2026-09-21。建议 `state=needs_review`、`scope=static_review`、`intended_use=development_diagnostic`。本题有具体质量疑点：官方唯一 F2P 只检查 namespace 名称，不验证两个名字代表所需类型；公开题面还保留“补到 _libs”与“补到 api.typing”两种位置选项。gold 实现合理且历史运行通过，但这些事实不足以证明测试对合理替代解和自然错误解均能正确区分。未执行新反例，不能宣称误判已实跑确认或原题无效。

`ROOT=.`；`I=ROOT/runs/swegym_quality_batch02_20260921_v2`；`B=I/public/pandas-dev__pandas-53958/base`；`P=I/private/pandas-dev__pandas-53958`。本次仅静态文件/JSON/hash/只读 Git；未导入/执行项目、测试、安装、联网、容器或模型，未改 source/test/gold/reward。未看 public_read、主审、其它 reviewer、旧质量结论、B1/B2 聚合/manifest/assignments/method_adjustments/CPU计划。看过本题授权 `environment_record.json` 的 baseline 摘要，未跟进聚合 evidence；以下使用 own run_refs 原 ledger/log 核实。三题初判统一保存后等待封存开放。

## 1. 公开目标、材料与初态

题面要方便用户为 NA/NaT 做类型标注，指出当前 `from pandas._libs import NaTType` 与 `from pandas._libs.missing import NAType` 位置不一致，询问是否把 NAType 补到 `_libs`，并把 `pandas.api.typing` 列作另一种方案，未给出已决位置。base `doc/source/reference/index.rst:12–25` 把 api.typing 定义为用于类型提示的公开类命名空间；`pandas/api/typing/__init__.py` 也采用实际类 re-export + `__all__`。这些公开材料支持选择 api.typing，是很强的工程路线提示，但没有明确撤回题面同时提出的 `_libs` 共置方案。不能读了 gold 后再把唯一位置说成题面明确规定。

base `1186ee0080a43a08c3431a5bfa86898f6ec3b54d`，tree `0fe5a870217e5ac80b2cc5508a40b2b9f4afa85d`。public/grading/validation 与对应 S2 JSONL 第155行相同；未重复整包机械检查。test.patch SHA256 `598ef5ed62657055f34a89729483b08f82bc4c4cd9bd3e8045f05df72aa7d610`；gold.patch `ac43e453848274035149bb10d0a41826c433fce9bdf706101227725d73d8b1c3`。base 的 `_libs/__init__.py` 已导出 NaTType，missing.pyi/pyx 定义 NAType；api.typing 仅16个名字，没有这两类型，与公开问题相符。原 noop 的目录差异失败也证实了该初态。

公开 non-test 修复限制不妨碍改 api.typing 或 _libs 的源码导出文件。hints 的 conda 激活声明仍须实测；当前 `render_user_prompt` 只渲染题面，公开 bundle 又会物化进 actor，不能说 hints 一定成为 system message，也不能说其不可见。

## 2. 需求—断言双向映射及测试范围

已逐行读 `B/pandas/tests/api/test_api.py:1–373`，包含唯一 F2P、全部10个P2P和 Base.check helper。test.patch 仅向 `TestApi.allowed_typing` 加入字符串 `NaTType` 和 `NAType`；没有新 helper、fixture或运行时类型断言。

| 公开要求／旧行为 | 依据 | 官方测试实际要求 | 判断 |
| --- | --- | --- | --- |
| 在统一且适合类型标注的位置取得两种类型 | 题面；公开 api.typing 文档与类导出惯例 | 唯一 F2P `TestApi::test_api_typing` 调 `Base.check`，比较经过过滤的 `dir(api_typing)` 与18个期望名称 | 检查固定 api.typing 位置的名字；不检查对象身份、是不是类、能否作为类型标注/运行时类型参数 |
| 固定选择 api.typing 而非仅补 _libs | 题面开放两选项，文档支持 api.typing | 同一 F2P 强制 api.typing 两个新名字；只在 _libs 共置会失败 | 有具体规格二义性；未凭此直接判题不可用，需保留公开方案范围 |
| 保持已有公开 namespace | base 既有 API清单 | P2P `TestApi::{test_api,test_api_types,test_api_interchange,test_api_indexers,test_api_extensions}` 与 `TestPDApi::test_api` | 主要是名字集合回归，不验证各导出对象语义 |
| 保持 top-level `pd.__all__`、既有测试工具和弃用接口 | base `test_api.py:215–243,358–373` | P2P `TestPDApi::{test_api_all,test_depr}`、`TestTesting::{test_testing,test_util_in_top_level}` | pd.__all__ 有缺失/多余集合断言；不是 api.typing.__all__。test_depr 在此base三个列表为空，循环无实际对象 |
| 新导出就是现有 NaTType/NAType，旧导入不破坏 | 题面明确要“types”；missing.pyi、nattype.pyi及pyx class定义 | 11个测试均无 `is` / isinstance /类型标注使用断言 | 具体核心语义缺口；测试名字存在不等于类型正确 |
| api.typing 的星号导出保持一致 | base源码中显式 __all__ 惯例 | Base.check 排除所有双下划线名字；没有 api.typing.__all__测试 | 忘记更新 __all__ 的自然部分实现可静态预测通过本套测试；单独星号导出是否题目硬要求不扩大判定 |

三套集合：冻结参考 **1 F2P + 10 P2P**；历史实际整文件 `pytest -rA --tb=long pandas/tests/api/test_api.py` 收集并运行 **11** 项；本人已读该文件全部正文及导入/helper，因此本题这三套在测试函数覆盖上相合，仍不能扩大到所有类型用户或全仓回归。未运行类型检查器，未审 pandas-stubs 外部仓库，也未穷举 scalar NA/NaT 操作测试。

## 3. Gold、合理替代与自然不完整实现

gold 在 api.typing 导入 `pandas._libs.NaTType` 与 `pandas._libs.missing.NAType`，并加两个 __all__ 元素；保持旧导入位置不变，是符合公开 type-hinting 用途的类再导出，不含测试改动或额外依赖。已读 api.typing、api、_libs 三个初始化文件，missing.pyi 全文、nattype.pyi 类型入口、_typing.py 的 TYPE_CHECKING 导入，及 pyx 中真实 NAType/NaTType 类定义位置与 sentinel 赋值位置。未发现 gold 类型接错或删除旧接口。

合理非 gold 路线可从 `pandas._libs.tslibs.nattype` 直接 re-export 同一个 NaTType，再由 missing 导出 NAType；只要不泄漏额外名字，既有断言不限制 import 文本。另一个公开提出的合理路线是把 NAType 补入 `_libs/__init__.py`（包括 __all__），形成共同 `_libs` 导入；它保持两类本体，静态预测会因 api.typing 未增名而被 F2P 拒绝。公开文档让 api.typing 更合适，但不能消除题面的所有二义性，故保留而非下最终误拒结论。

**具体自然错误候选（未创建/未执行）：**在 api.typing 中误把 singleton 当类型导出，例如 `from pandas._libs import NaT as NaTType`、`from pandas._libs.missing import NA as NAType`，同时补同名 __all__。这种 type/value 混淆使名字列表完全正确，却无法提供题面要求的两个类型；已有11测试只比名字，静态预测仍可通过。不是修改测试或伪造日志的攻击，也不依赖隐藏函数名硬编码。独立行为 oracle 可检查 `NaTType is type(pd.NaT)`、`NAType is type(pd.NA)`，或 `isinstance(pd.NaT, NaTType)` / `isinstance(pd.NA, NAType)`。前两条对应“现有类型的再导出”，后两条能直接揭示 singleton 被误用为类型参数。本轮没有用静态推断冒充 RH2 实得分。

## 4. 原始 baseline 环境与执行证据

证据根 `ROOT/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-2`；仅查本题 ledger 第11 noop、第12 gold 行以及 own run_refs 两原日志。

| 角色 | 原日志与关键行 | 历史真实 RH2 结果 |
| --- | --- | --- |
| noop | `eval_logs/evallog_replay-f216-baseline01-w_a8d9ae3e.eval.log:2967–3036,3046,3059,3190–3195,3214–3222` | 正常安装后跑11项；`dir`左16右18、diff为NAType/NaTType；1 failed/10 passed；F2P0/1、P2P10/10、reward0、rc1 |
| gold | `eval_logs/evallog_replay-f216-baseline01-w_eed61475.eval.log:2995–3064,3074,3087,3101,3108–3115` | 整文件11 passed；F2P1/1、P2P10/10、reward1、rc0 |

两日志 SHA 与 run_refs 匹配：noop `89f991e7fdacc8888fe6f671bb9c6b05cbe4ce8037208a786227cbb5a5fbdc64`；gold `6e54d2d10fd1c91b26c14a094a46f32e018e68a5fa92c3aa5ea2919359925acc`。ledger 镜像 digest `b45817ed11542705d541028f48e9ce8026e783feb14440454141fc6d8129df21`，derived_image_recipe=null、image_id_actual=null。评分身份54322、deny_all、2 CPU/4 GiB、可写 conda prefix。安装命令为 `numpy<2`、editable pandas、卸载pytest-qt；日志正常构建/安装并在测试导入时调用 ninja。观测包入口 `/testbed/pandas/__init__.py`、版本 `2.1.0.dev0+1120.g1186ee0080.dirty`；runner digest 前后相同，cleanup removed=true。gold 安装约8.073秒/测试约4.535秒，峰值约324.66MiB；noop约9.152/4.616秒、622.656MiB。数字属于该历史 grader，不是 actor 性能保证。

gold 改 Python 导出且唯一目录断言从失败转通过，支持修改确实影响了历史 grader；日志没有单独打印 api.typing 或两个扩展类所在模块的 __file__，不把 pandas 顶层入口当作所有模块来源认证。apply_user=agent/54321只是补丁应用身份，不能冒称正式 actor 开发已成功。两个 ledger 记 num_parsed_outside_segment=1；当前评分只消费标记段内状态，这个段外数量不是另一个执行测试或额外通过证明。

## 5. 具体开发条件与评分边界

| 操作/资产 | 公开依据和历史证据 | 待核条件 |
| --- | --- | --- |
| 修改导出并导入本地 pandas | API init文件、题面两个旧导入可直接定位；gold为纯Python改动 | 正式 agent/54321 的 shell、sys.executable、pandas/api.typing模块来源及源码生效未实测 |
| 已有 NA/NaT 扩展可导入 | base pyproject 使用meson/Cython；贡献文档:210–229说明editable构建；历史安装/导入成功 | 修复不需改Cython；基础扩展/loader仍必须可用，actor可能触发自动重编，权限/工具链不能由grader推定 |
| 验证类型API | `python -m pytest pandas/tests/api/test_api.py -q` 是公开窄测试入口；独立直接导入可检验类本体 | 原base公开测试仍期望16名字，正确添加后该旧清单会报差异；这是API清单需随正式patch更新，不能要求模型编辑受禁止测试来得分 |
| 资产/网络/资源 | 无数据集、权重、服务或运行期公网需求；只需预置pandas依赖与构建环境 | 当前rollout默认2CPU/4GiB、tmp1GiB/home256MiB不是本题实测有效profile；不要求无目的新下载 |

正式 `rollout_spec_from_view` 使用 public image，当前 actor54321/grader54322两套身份不能混用；rollout init 明确工作区/home可写，grader另给conda prefix写权限。`materialize.py:47–52` 的 BASH_ENV在/root，rollout hidden_paths包含/root；实际CC extra env、工具shell和image PATH未捕获，不能只按这个路径判定失败或通过。

当前 `prepared_task_face.py:312–335` 为 `test_globs=()`；唯一官方精确恢复/保护文件 `pandas/tests/api/test_api.py`，不包含 api.typing 或 _libs 的业务导出源码。gold included_paths 只有 `pandas/api/typing/__init__.py`，ignored_paths为空。没有合理修复被投影丢弃的证据，`additional_exclusions=[]`。test.patch未混入普通源码。非官方 fixture、包初始化与构建配置仍是可执行面，不能将官方路径保护说成整个验收控制面均不可干预；本题具体不足来自真实断言语义，未造额外绕过手段。

评分仍由当前 `scoring.py:190–272` 的段内解析及冻结参考决定；完整pytest的非参考失败/普通rc1不自动reward0，manager的全局错误检查另有条件。本题所有11参考恰好覆盖本文件运行项，但仍不能把测试文件整体成功解释为类型身份被检验。

## 6. 关系、用途及唯一优先下一步

本题与48106/56849是不同API问题；有具体版本暴露：56849公开base的 `pandas/api/typing/__init__.py` 已完整包含本题 gold 两import与两个__all__名字；本题base的cast.py:626–631又已含48106的分类类型处理。共同reviewer见过这些原材料仅能用于私有诊断，不应给独立solver继承，也不能因同仓将三题当同一变体。

**唯一优先下一步（未来固定-grader CPU语义诊断，尚未执行）：**比较 gold 与上述“误导出 NA/NaT singleton”的自然错误候选，在保持同一官方test.patch/参考/镜像条件下同时记录RH2结果和独立类型身份/用法oracle。若错误候选仍reward1而类型oracle失败，则确认该具体漏测；再依据公开types目标增加最小语义断言并检查合法直接re-export仍可接受。该实验不依赖先完成正式actor启用，实验结果也不能替代actor核验。题面位置二义性仍单列保留，不因优先验证漏测而删去。未测真实模型成功率、学习价值或token/费用，成本null；不提供本报告给solver。

当前ROOT HEAD `e3d120b55a62cca5985f688de8cdd481b12ea6be`，manager有未提交变动。prepared_task_face SHA256 `31ff5145dfa8b71b2a183b14f8a5fbfe4572b71911af54023c8168e534e4f8a3`；manager `eadaa64acc2e9dc358ad4c7c4f9ad3bb60d81a1c72298a41dabbdf6397ad6342`；scoring `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`。这是本次当前静态源码标识，不认证09-19 runner字节。
