# Dask7138 Qwen3.6 首轮：非作者候选与轨迹核查

2026-10-04。对象 `gpu1003-dask7138-qwen36-a1`。**本候选满足当前 array-like 正确展开、返回 Dask Array 与旧 `array=` 兼容要求；正式原分为 `reward=1 / resolved`，470 项参考全部通过。本核未发现候选语义阻断、当前评分误收／误拒或测试控制污染证据。** 完整封包运输、实际 code9／R25 绑定、资源清理、ack 和总账由父线程验收；本报告不代替这些工作，不授稳定能力或训练资格。

依据[三方现行协作授权](../../../coordination_workflow_20261003.md)安排的首次本臂非作者窄核。已读题卡、修订、矩阵、固定探针申请和既有 Coder／同原 FP CPU 实证，非 fresh 全题盲审。本轮只读本地原件、做数据解析与内存重放；没有 SSH、容器、CPU／GPU、模型、pytest 或候选执行，没有重跑已有矩阵或 CPU。只新增本报告及同名 JSON。

## 当前目标与实际候选

[原 FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/attempt/frozen/frozen_patch.json)规范摘要为 `e1f8877dfc4c912f3fc79bd4e25a4e6e5cc912da9e9920811bb7470e55f2f068`；含生产文件与公开测试文件两项。[实际 baseline](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/attempt/frozen/baseline_manifest.json)规范摘要为 `1bb7df741c80d1271ab92408e0277d129c0b866011b218b79a8295bc38ad49b2`，base 为 `9bb586a6b8fac1983b7cea3ab399719f93dbbb29`。425 对象在 tar 与 manifest 一一对应：424 普通文件内容／类型／mode 和 1 symlink 目标摘要均核过；symlink 的 Git `120000` 是对象类型，不与 tar 权限 `0777` 作普通文件比较。没有解包到磁盘或执行成员。

生产改动只有 `routines.py:1198`：`return asanyarray(array).reshape((-1,))`，保留 `def ravel(array)`。实际 baseline L29 已导入 `asanyarray`；`core.py:4058–4095` 将标量及 array-like 转成 Dask Array，L4085–4086 对既有 Dask Array 直接返回，再接原 reshape 路径。它与既有 `compatible_ravel` 正对照的生产修法相同。旧关键字兼容由保留参数名解释，并得到当前正式新增 P2P 的实际通过支持。

完整轨迹 L113／117 的生产 Edit、L173／177 的公开测试 Edit 均从真实 baseline 在内存顺序重放；old_string 各唯一，最终字节与两项 FP 完全一致。生产内容 SHA 为 `5d245e5166c7b026b1d67cc943419c62dce98401f782dd684ea639df44fe96b6`。不以 source gold 的标签代替正确性，也不新增零拷贝或全部 NumPy 参数要求。

## 正式测试与评分边界

[正式报告](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/grading/report.json)为 raw1／resolved，infra detail 为 null。独立读取[完整正式日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/grading/eval_logs/evallog_gpu1003-dask7138-qwen36-_a2437547.eval.log) 1,215 行，计得 **562 个唯一 PASSED 节点**，全部位于测试起止 marker 之间，没有 FAILED／ERROR／SKIPPED 等节点。逐参考与实际 private prepared 和 diagnostics 的 references／success 列表严格相等：

| 分区 | 参考 | 成功 | 失败／缺席／skip／unaccounted |
| --- | ---: | ---: | --- |
| 原 F2P | 1 | 1 | 全部 0 |
| 原 P2P | 468 | 468 | 全部 0 |
| 新增旧关键字 P2P | 1 | 1 | 全部 0 |
| 合计 | 470 | 470 | 全部 0 |

日志 L1092 是 `test_ravel_with_array_like`，L1093 是 `test_ravel_keyword_array` 的 PASSED。实际私有 patch 与当前 effective patch 字节相同、SHA `2f3c5c539816149a06b6c460b5d79d6b3223f452cd5862bcdbac41faf76bc44a`。F2P 保留标量／list／tuple／混合嵌套并追加含非零、负数输入与类型断言；新增 P2P 直接调用 `da.ravel(array=array)`。这些不是模型自行执行过的所有用例；其运行实证来自 trusted 正式测试。完整模块 562 项与评分参考 470 项是不同范围。

模型确实改了公开测试并新增 `test_ravel_array_like`。但[实际评分投影](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/grading/projection.json)只保留 `dask/array/routines.py`；正式日志 L352–364 将测试恢复到 base、核 base SHA、再应用 trusted patch，L385–397 的 setup attestation 成功。正式日志没有模型新增节点，不能把公开自测冒作正式 F2P。report 的 `test_files_modified=false` 仅指评分投影。FP 没有 conftest／fixture／runner 改动；diagnostics 的相关路径数组为空，control protect 成功，未见评分绕过证据。

安装 L567–598 实际完成固定 pytest7.4.4 和 editable 安装；测试 L608–614 执行完整模块，L1208–1215 为 562 passed／92 warnings、test RC0。diagnostics 记录 install RC0／1.569s、test RC0／7.222s、candidate segment 完整且非 partial；外层 shell exit0不是单独接受依据。`runner_integrity_changed=true` 与 `resource_facts=null` 如实保留。日志能看到 pytest8.3.2→7.4.4，但缺逐文件 runner diff，只能作有限归因推断，不能认定唯一原因或写成 runner 未变。

## 方法、验证与最终说明

[完整轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/attempt/trajectory.jsonl)293 行、227,942 B，与 harness 副本逐字节相同。20 个模型请求／CC 回合，19 次工具：12 Bash、5 Read、2 Edit。唯一工具错误为 L95／99 修前 list 的真实 `AttributeError`，不是基础设施失败。

| 轨迹行 | 实际行为与证据 |
| --- | --- |
| 11–85 | 定位两处 ravel，局部读实现和公开测试，确认现成 asanyarray。 |
| 95／99 | 原 `[0,0]` 缺 reshape 实际复现。 |
| 113／117 | 一次生产编辑加入转换，保留参数名；没有二次源码纠错。 |
| 127／131 | 修后平面与嵌套 list 打印值匹配 NumPy；这些打印不等于分支断言。 |
| 173／177 | 新增公开 `assert_eq` 测试，正式评分排除。 |
| 187–219 | 原 ravel、新公开 array-like、1D no-op 三个单节点各 1 pass。 |
| 229／233 | 同模块筛选 11 pass／550 deselected，包含上面三项；不能相加为 14 个独立测试。 |
| 243–261 | 核 Array.ravel 委托并打印二维 Dask 方法与 NumPy匹配。 |
| 275／279 | 查看两文件最终 diff。 |
| 289／293 | 最终说明只列改法、两类公开新测试和 11 项相关测试通过，与轨迹一致。 |

模型没有显式自测 `array=`、标量／tuple 的类型；正式当前参考补足本候选的实证范围。pytest 自测使用 head／tail 管道，不能从工具 `is_error=false` 单独推出 pytest 成功；本轮有明确 PASSED 和完成汇总。与 Coder 的“全部既有测试／完整向后兼容”过度声明不同，本轮最终说明没有扩大成完整仓库测试或全部 NumPy API 验收。

实际求解 26.193s，CC 22.627s、API 16.008s；累计提示 126,475 token、输出 2,505 token，提示累计含重复上下文。三个单节点随后被筛选运行重复覆盖，可合并重叠验证，并在同一窄范围显式核旧关键字。所有响应最多单个工具，没有可见并行；该臂不能证明执行入口支持或不支持多工具并行。独立局部读取有批量机会，复现→编辑→修后验证仍有顺序依赖。

正式评分共 487.486s，trusted setup 464.814026s，约占 95.35%；安装和测试成本分别见上文。grader queue wait0只对应其记录范围，外部派发等待未知。不要将准备成本归给模型，也不要据这一个样本／耗时推出稳定性能优势。实际所有 20 请求 `max_tokens=65536`，model_sent 为 Qwen3.6-35B-A3B；CC 32000 是客户端 metadata。gateway 的 `checkpoint_identity_verified=false` 仍保留。

## 公开输入与既有两臂结果

实际首 HTTP user 仅有日期 reminder 与原题面；saved prompt 和 solver_prompt 相同，首 task text 与 prepared spec.prompt 相同，24 个 CRLF 规范化后等于 saved prompt。首 system 是通用 CC 与环境说明；完整可见轨迹只操作公开仓库。20 请求 body 未见私有 keyword 节点、effective patch、正对照名称、revision／materials 标识。字符串检查与可见轨迹支持本范围无私有输入证据，不代替全环境隔离审计。

原题面本已指明转换位置与方向，甚至给出带 `asasanyarray` typo 的示例；**引导属性必须保留，快速定位不代表无引导能力**。prepared 另含旧通用 public_hints，但实际首请求未交。依据[已有 GPU 公开范围澄清](../../../../../../../../runs/category2_repair_20260929/swe_dask/model_analysis_20261003/dask7656_qwen36_a1_v1/public_hint_scope_GPU_clarification_v1.json)和题主现行 preparation 的有效范围，`unchanged` 保持绑定 spec.prompt，不把旧 hints 自动追加；这是复用已澄清范围，不是新 pending alignment、违令或重跑依据。本轮未发现具体必要开发说明缺失。

既有 Coder GPU 准备300超时／None 与同原 FP CPU setup900 raw0各自保留；CPU实际只失新增关键字 P2P，原1F／468P通过。本 Qwen生产补丁保留参数名且470全过，不回写原 Coder 分数，也没有新 Coder求解或已有效CPU重跑。

## 限制与停止条件

本语义窄核无待修阻断。父线程完成完整封包／机械身份与运行绑定后，可按本范围登记 Qwen 成功诊断。稳定能力、正式训练资格、typed训练 actor和通用安全审计均未由此授予；runner 归因与资源 null边界保留。公开候选测试的注释有 `issues/XXXX` 占位引用，属于后续交付洁净度事项，未进入正式评分，不阻断当前语义结论。

题卡／revision／acceptance 中部分字段保留准备时期 draft／pending／null。本核以实际 prepared、FP和正式 log 判断观察结果，没有用旧状态否定已有实证或篡改历史字段。到此已足够停止本核；额外理论反例、已有有效 CPU 和未交旧 hints不触发追加重跑。

## 读件身份

完整 43 份读件的路径、SHA／大小与读取范围见[同名 JSON](non_author_7138_qwen36_a1_candidate_review_20261004.json)；以下只列关键原件。本审查未复算全部139份封包，完整闭包由父线程负责。

| 原件 | 大小 B | SHA256 |
| --- | ---: | --- |
| [frozen_patch.json](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/attempt/frozen/frozen_patch.json) | 142936 | `b2fa13f401f61cadcccb96c77d34c5f83fdf17c041dca72d0fad4d0180eac1b4` |
| [baseline_manifest.json](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/attempt/frozen/baseline_manifest.json) | 99708 | `65c898817a5017b5d3f8f5085cef04250a7d1696504231247e1c5d92bb5c253f` |
| [baseline.tar](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/attempt/frozen/baseline.tar) | 8816640 | `0c73c83a30c4b01781b9fc49b5c720422e0875fdb25fb057964b050b1aba05da` |
| [trajectory.jsonl](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/attempt/trajectory.jsonl) | 227942 | `17c6eb5a8bf96a448ee5efcc204041ce4bde78bc637fb3a89a4989ed96708fba` |
| [dask__dask-7138.diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/attempt/candidate/dask__dask-7138.diff) | 1156 | `46b40f501a73269aeb49bc47eee8a02290ab920a9678762687b960ba5996a5f1` |
| [evallog_gpu1003-dask7138-qwen36-_a2437547.eval.log](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/grading/eval_logs/evallog_gpu1003-dask7138-qwen36-_a2437547.eval.log) | 74281 | `15dc1a0d53748ea766697b299bf2c1c9ad33b35a1e785a4f1bd2f3c73134b165` |
| [evallog_gpu1003-dask7138-qwen36-_a2437547.diagnostics.json](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/grading/eval_logs/evallog_gpu1003-dask7138-qwen36-_a2437547.diagnostics.json) | 80857 | `43d6db6432eacb09bec46c9e0a89d5c35204cb97580b7c56752267749c523a50` |
| [report.json](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7138-qwen36-a1/grading/report.json) | 1801 | `231a9fec57acdc79e9b97d8fb5f4a46c24b59b199f4287406cf811bd842002ef` |
| [host_grading_views.jsonl](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/prepared_dask_four_r25_code9_v1/dask7138/private/host_grading_views.jsonl) | 75877 | `865452a80389ee3975faa5ffbd1a5a101f7039e7a3a5a704e5964acc44fe1e79` |
| [requests.jsonl](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/dask4-r25-code9-v1/gpu1003-dask7138-qwen36-a1/requests.jsonl) | 492682 | `28f98f11c02c4381e88bc11057e27facfc72629bbbb1ef1f6f79fd62be40a28c` |
| [probe-swe-dask-7138-20261003-v1_pair_execution_receipt_v1.json](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/probe-swe-dask-7138-20261003-v1_pair_execution_receipt_v1.json) | 9691 | `15eadf0d511bc3bd1da2bef73a9b30a307b68c93c6289725cafdb07b8f1f5bfb` |
