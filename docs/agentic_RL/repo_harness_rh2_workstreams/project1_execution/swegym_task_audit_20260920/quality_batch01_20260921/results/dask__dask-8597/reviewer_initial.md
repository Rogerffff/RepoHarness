# dask__dask-8597 独立复核初判

记录时间：2026-09-21。阶段：读主审前的独立静态初判。用途：development_diagnostic；不是 actor 验收或训练/评测批准。

公开目标、base、唯一新增 F2P 与 gold 对得上；新增断言不要求 gold 的具体写法。初判可作为**静态探针候选，保留条件**：真实 actor 的解释器及兼容配方消费仍未验；评分只明确列出 116 个 P2P，不能把整文件 119 pass 等同于全部旧行为均被计分。优先后续是定点检查“只在启用切块时做大小计算”这种不完整修复，联合判断公开行为、完整退出码与实际 reward。

## 阅读与暴露

- 已读指定 reviewer 角色卡、actor_environment_card.md、record_template.md、quality_review_protocol_20260920.md。
- 已读本题 public 的 prompt、bundle、环境说明、base_identity；private 的 test.patch、gold.patch、grading、validation、source_refs、run_refs、environment_record。
- environment_record 是已见的结构化环境汇总，含末尾 history 来源引用；已向协调者报告，协调者确认该文件属允许元数据。**没有沿其 analysis/history 引用打开旧总结**。
- 未读 public_read、主审产物、质量 history、主计划、manifest、method_adjustments 或其它题结论；未列读 OUTPUT_DIR 中其他文件。
- 已逐段读完整 base 的 dask/array/tests/test_slicing.py（1–1067）、新增测试全部 4 行有效代码、assert_eq 及其直接 helper、conftest 与 pytest 配置；已读主调用链、相关 take 调用者和公开切片说明。
- 已复读 run_refs 指定的 gold/noop 原始 ledger、eval log 的安装、实际测试、失败栈、总结/退出码，以及 recipe 原件；补读 gold diagnostics 的控制面与 setup 字段。没有执行项目代码、安装、Docker、SSH 或模型；这是独立复读日志，**不是独立复现**。

路径缩写（以下行号均属于这些固定原件）：

- PUB = runs/swegym_quality_batch01_20260921_v2/public/dask__dask-8597
- BASE = PUB/base
- PRV = runs/swegym_quality_batch01_20260921_v2/private/dask__dask-8597
- RUN = runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-8597
- GOLD_LOG = RUN/gold/eval_logs/evallog_replay-er19-cv1-dask__da_cb209d73.eval.log
- NOOP_LOG = RUN/noop/eval_logs/evallog_replay-er19-cv1-dask__da_50713119.eval.log

## 公开需求与材料身份

题面标题说“0-D”，但原例 `numpy.zeros((3, 0))` 是二维、一个轴长度为零；需求是 fancy indexing `[[0]]` 能正常构造并得到 NumPy 对应的空数组，shape=(1, 0)、dtype=float64。该术语误用能由题面原例直接消除，不构成隐藏规格（PUB/user_prompt.txt:3–22）。公开切片文档支持单轴整数列表/数组以及布尔索引，并明确多轴列表不是已支持能力（BASE/docs/source/array-slicing.rst:4–22）；不能借标题扩张为要求所有真正的标量 0D 索引。

base_commit 为 c1c88f066672c0b216fc24862a2b36a0a9fb4e22，public、grading 一致。base_identity 记录 base_tree bd0e4fc24106244ba2713e90efa250b78210d1e4、451 个跟踪项、无 .git、blob 已验证（本 reviewer 未重建 export）。gold 日志 219 行、noop 214 行的 git show 指向同一 base。gold 工作区差异在 GOLD_LOG:351–363 仅为 take 的零元素 guard，与 PRV/gold.patch 一致；测试补丁在 GOLD_LOG:366–371 与 NOOP_LOG:348–353 被恢复后 cleanly apply。

本轮静态 SHA-256 核对：

- gold.patch = e1ed047ba04029e62bc4fb82b16717dc7d6f7f7ce03ac859c2e0bb5e6aec22e4，与 validation、gold ledger 一致。
- test.patch = 472ecb0eaf0dd9dd1e8820784c5354ed711f9fccd1a9de82c0d15dd5d55223c7。
- gold/noop eval log hash 分别为 4ada7bf0ddf6c18c4cda78ca70e91426f95c57fe42c08b2b7ada896381a944cb / 523554351e52e3593ea705193878caaaa4e5e8281dd78afe6ee14683c78d8e4e，匹配 run_refs。

## 需求—断言双向映射

| 需求/合理旧行为 | 公开或 base 依据 | 测试与决定性断言 | 独立判断 |
| --- | --- | --- | --- |
| 原例正常返回 shape=(1,0)、float64 的空结果 | prompt:9–21；core.py:1832–1855 | 唯一 F2P `test_slice_array_null_dimension`：`assert_eq(array[[0]], np.zeros((3,0))[[0]])`（PRV/test.patch:10–13） | 直接覆盖题面，无异常字符串、helper 名或 gold 行形状要求 |
| 真正计算、shape、dtype、块/图元数据自洽 | utils.py:196–258、261–339 | assert_eq 对 Dask 输入 validate graph、persist/compute(sync)、校验块 shape/dtype、最终 shape/dtype/type 与 meta ndim | 不是仅检查能构造对象或双方同异常；对空数组数值比较本身平凡，但 shape/dtype 非平凡 |
| 非空列表索引、不同轴、分块及排序行为保留 | slicing.py:585–621；公开切片说明:51–65 | P2P test_take、test_take_sorted、test_take_semi_sorted、test_slicing_chunks；前两者检查具体图与 chunks | 有公开旧测试支持这些内部约束；没有发现新增误拒。未证明所有可行重构均被接受 |
| 非空大块配置 True、chunk-size 生效 | slicing 文档:88–95；slicing.py:638–676 | P2P test_take_avoids_large_chunks、test_take_uses_config：chunks=(1,1,51,50,1) 等；10GB 不切分 | 保护对应分支，不能代替零长度轴与配置的交叉覆盖 |
| 未知非索引轴大小不切大块 | slicing.py:644–645 | P2P test_getitem_avoids_large_chunks_missing[chunks0]，使用 NaN chunks 并 assert_eq | gold 保留原 NaN 分支；chunks1 是既有 XFAIL，不是本题需要转绿 |
| 默认大块警告、False 静音、True 切块及结果 | slicing 文档:67–95；test_slicing.py:875–903 | test_getitem_avoids_large_chunks 运行且通过，但不在 P2P；test_slicing_integer_no_warnings:784–790 也不在 P2P | 已确认的评分集合覆盖缺口；需实际错误候选确认是否会出现 reward=1 但完整测试失败，不能仅从清单断言已观测误判 |
| 空 index、空 slice、负索引、越界、布尔 index 与 newaxis 旧行为 | test_slicing.py:447–542、616–625、651–739、751–824 | 对应 P2P 均列入且运行通过；大多对比 NumPy，越界明确 raises | 已读相关断言；这些用例大多是非空输入，不能宣称覆盖了本题全部零轴组合 |
| 零轴的非默认配置、其他轴/shape/dtype、重复与负索引、混合切片 | 同一公开 NumPy 语义和相关 base API | 新增 F2P 只有默认配置、shape=(3,0)、[[0]]、默认 dtype/chunks | 覆盖有限。可构造合理的定点补充；没有据此直接宣布题目无效 |

全部 F2P 已读：1/1。P2P 清单 116 项；逐段通读该测试文件，重点追踪上表受影响断言。对 gold 日志的 PASSED 集合与 grading 中 F2P/P2P 做静态集合差，恰有上述两个非参考通过测试；不将“同文件运行”冒称“全部进入 reward 参考集”。

## 根因、gold 与可接受替代解

调用链：Array.__getitem__（core.py:1832–1847）→ slice_array（slicing.py:174）→ slice_with_newaxes（196）→ slice_wrap_lists（260–263）→ take。混合整数/切片与列表还有 slicing.py:265–281 的第二条 take 调用；routines.take:1945–1951 也委托数组索引。真正 Dask 整数索引走 slicing.py:994–1113 的独立 blockwise 路径，不能与此题 Python 列表索引混为一谈。

take 的 `other_numel = np.prod([sum(x) for x in other_chunks])` 对 chunks=((3,),(0,)) 得 0，而 base 只检查 NaN，随后 `math.ceil(nbytes / (other_numel * itemsize))` 除零（slicing.py:640–648）。NOOP_LOG:777–863 给出同一调用链、输入和失败行。pytest 的 warnings-as-errors（setup.cfg:46–52）使该运行先以 RuntimeWarning 失败，而题面普通 REPL 报 OverflowError；这不是版本错配证据，二者属于同一分母为零路径。

gold 仅让零值与 NaN 一样使用无限 maxsize/warnsize。对实际零元素块，不会产生数据大小超限，所以跳过警告/切分符合公开语义；索引计划、块图、dtype 与越界检查保持原路径。其他正元素值未改，NaN 旧行为保留。静态未发现 gold 漏修题面或引入具体回归；日志只支持所跑文件，不是全仓正确性证明。

可行的非 gold 路线是先给 maxsize/warnsize 默认无限，仅在 other_numel 为正且已知时算大小；或对零非索引轴独立处理，保留现有计划和输出图。新增测试没有锁定 guard 顺序或 `math.inf` 写法。无需为完成此题修改测试或引入新依赖。

一个值得验证的不完整修复是将原 guard 改为“NaN **或未启用 split-large-chunks** 时不计算大小”。它修复默认原例，也可能保住已列 P2P 的非空显式 True 路径，却取消公开承诺的默认大块警告，且在零轴+True 下仍除零。此为**静态错误候选**，本轮未写入/运行，不能声称已拿到满分。

## 既有运行证据及开发条件

两个 ledger 均为 compat-v1:dask__dask-8597，实际派生镜像 sha256:065c32c154a13335b5363bd7969d0c79bd19f7dee23b9a1000b5650ac9cd78e0。candidate apply_user=agent/54321，实际测试 policy=user rh2grader/54322、2 CPU/4GiB、network=deny_all、允许写 /opt/miniconda3/envs/testbed；这不是 agent 在正式工具 shell 中完成开发的证据。

- 配方：RUN/gold/recipe/recipe.json:3–8，离线从 /opt/rh2/compat-wheels 安装 pytest==7.4.4，再 `python -m pip install --no-deps -e .`。GOLD_LOG:619–649 与 NOOP_LOG:601–631 实际从 pytest 8.3.2 换到 7.4.4、editable 安装成功、install rc=0。
- 执行：GOLD_LOG:659–666 与 NOOP_LOG:641–648 明确 Python 3.9.19、pytest 7.4.4、/testbed、收集 123 项；不只是 parser 产生了名称。
- gold：GOLD_LOG:790、932–944，F2P pass；119 passed/2 skipped/2 xfailed，test rc=0。ledger:1，F2P=1/1、P2P fail=0/116、reward=1。
- noop：NOOP_LOG:772–863、1008–1016，唯一 F2P 在 take 除零；118 passed/2 skipped/2 xfailed、test rc=1。ledger:1，F2P=0/1、P2P fail=0/116、reward=0。
- 两个 ledger reference_missing_count=0、cleanup.removed=true。gold/noop 记录 mem_peak_mb=1536.57/1609.496；不能移植为当前 actor 实测。
- runner_integrity_changed=true 在两个 ledger 都出现；原件同时记录预先声明的 pytest 降级。未把该布尔量单独判为候选篡改，也未独立核定 digest 覆盖范围。gold diagnostics 原件显示 trusted setup restore/apply 成功、保护文件完整；共享完整性机制仍以协调者验收范围为准。

| 需要的操作/资产 | 公开依据 | 现有证据与适用范围 | 缺口与最小验证 |
| --- | --- | --- | --- |
| 从实际工作区导入 Dask、NumPy，编辑 slicing.py | core.__getitem__、slicing.take；setup.py:12–39 | grader ledger import path=/testbed/dask/__init__.py；editable 安装通过 | actor shell 打印 UID/cwd、sys.executable、dask.__file__、NumPy/pytest 版本，确认编辑生效 |
| 运行原例和少量公开切片测试 | prompt；test_slicing.py；setup.py:25–29 | 兼容 grader 的 pytest 7.4.4/xdist 可运行 | actor 是否收到同一 pin/离线 wheel、能否写解释器前缀未知；应在准备时固定配方，不让 solver 用业务补丁修 pytest API |
| 必要依赖及资产 | setup.py：NumPy、Dask 核心依赖；测试 importorskip NumPy，sanitize 测试可用 pandas | 原例无数据文件、模型权重、外部服务；全部可准备为本地依赖 | 无运行期公网需求；不要求全仓所有可选依赖 |
| 最小验证路径 | 原例 + 公开旧测试 | 题面规模极小，历史同文件执行在给定资源内结束 | actor 先跑公开原例，再 `python -m pytest -n0 dask/array/tests/test_slicing.py -k 'empty or take or getitem_avoids_large_chunks'`；候选加入后原例应得到 (1,0)/float64 且 compute 成功 |
| 可提交修复与文件规则 | gold 只修改 slicing.py；公开操作指令禁止改测试 | ledger projection.included_paths=[dask/array/slicing.py]；eval recipe:10、49 恢复 test_slicing.py | 合法源文件修复不冲突；public_hints 的“所有测试修改永不计分”不推广为当前事实。本题不依赖修改测试，因此其适用性待验未形成题目特有阻塞 |

## 八方面覆盖与独立处置

| 方面 | 本轮覆盖/结论 |
| --- | --- |
| 公开需求 | 原例与文档已核；标题术语可消歧。实际 CLI 消息渲染仍未知 |
| 材料与初态 | commit/patch/原始失败路径匹配；日志及 gold hash 已核，无具体材料错配 |
| 测试是否测到 | 全新增断言、全部 F2P、相关 P2P/helper 已核；原例完整覆盖，零轴组合覆盖有限；两项运行测试不在参考集 |
| 误拒合理解 | 未见新增测试强绑实现；已提出非 gold 等价 guard；不声称穷尽合法实现 |
| 回归/gold | 主链、混合 take、routines.take、Dask index 分流、配置/NaN/空索引已核；无已证 gold 回归；未查全仓/其它后端全矩阵 |
| 开发条件 | 定位和所需依赖明确；旧 compat grader 通过；正式 actor 的实际镜像、PATH、激活、pin 权限与代码生效未知 |
| 交付/评分 | 源文件可投影，官方测试恢复；test.patch 未夹带普通源码；reward 集合与整文件不同；未审完整隔离/清理实现 |
| 题目关系/用途 | 仅本题，没有因同文件推断题簇；公开没有给出 gold 修法；镜像可见资产/祖先历史未查。已暴露 gold/隐藏测试，不能作为盲 solver |

建议：保留为静态开发诊断候选，不写 ready_for_probe；没有当前证据要求改题面或否定 gold。唯一优先后续：在授权 CPU 的相同配方下用上述不完整 guard 做 base/gold/candidate 对照，同时跑题面原例、零轴+split=True、公开默认警告测试及实际 RH2 评分，区分“覆盖边界”与已发生的误评分。随后使用共用真实 actor 入口核对开发环境；本轮不代替这一步。

第一阶段到此，等待第二阶段 S2/S3 与旧结论变更记录。

