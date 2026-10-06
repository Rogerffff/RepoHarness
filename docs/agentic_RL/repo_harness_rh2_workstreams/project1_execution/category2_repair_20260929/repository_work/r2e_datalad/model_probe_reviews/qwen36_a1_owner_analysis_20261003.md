# DataLad088：Qwen3.6 首次探针的题主分析

2026-10-03。题目 `datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb`，模型路由 `Qwen3.6-35B-A3B`，作业 `gpu1003-datalad088-qwen36-a1`，材料 `r2e-mr-088`，预算 `probe-wide-v1`。

**这是正常完成、修好了题面例但引入回归的失败样本。** 正式 raw reward=0；17 个 expected 状态键中匹配 16 个，唯一偏差是 `test_url_samples`。模型把含转义冒号的本地路径误判为 SSH，已有隐藏断言实际失败。题主和非作者直接核原件后，未发现新增题级或评分材料阻断，无须为这次失败修材料或重跑求通过。

本报告只收口 Qwen3.6 首臂的行为分析。Coder 首臂尚未返回，双模型请求仍 `claimed`；同条件重复采样待 GPU 批次安排，不能从单样本推稳定能力。用途限 `versioned_baseline_diagnostic_only`，训练／留出资格未取得；GPU baseline 内环境血缘字段仍为空。

## 判断依据

题主只读原件，重核封存清单全部 80 文件的 SHA／大小，共 8,320,041 字节；直接从正式日志复算 17 键状态，从完整轨迹、18 次实际请求／adapter 记录复算工具及 token 计数。没有 SSH、CPU、模型或候选重跑。读回见 [原件指标和时间线](../../../../../../../../runs/category2_repair_20260929/r2e_datalad_model_probe_20261003/qwen36_a1/owner_original_metrics.json)，SHA `1173f6ae46fca152fb7adcd0f2e3f12e36f738dc76e17e7747a4e0a372c70c7a`。

非作者 [独立关键原件核查](qwen36_a1_independent_review_20261003.md)（SHA `48a21481eec2a0d05bf0ca2c479ab75e95a915b519b74ffaff587d5a0ab3e937`）独立核了实际 baseline 源码、原 FP／diff／projection、完整正式日志、首请求、终点和双侧清理，结论相同。审查者已接触私有材料，不是 fresh 公开盲读。执行者的 [全链执行核查](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/q15_datalad088_qwen36_a1_execution_semantic_review_v1.md) 继续作为代码／镜像／运输身份及有限资源观测的证据。

## 方法与根因：局部诊断准确，判别条件过宽

实际 [候选 diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v15/results/gpu1003-datalad088-qwen36-a1/attempt/candidate/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb.diff) 只有两份文件修改。源码在 `URL._set_from_str()` 无 scheme／hostname 的分支增加：

```python
elif fields['path'] and ':' in fields['path']:
    fields['scheme'] = 'ssh:implicit'
```

模型用 `urlparse()` 观察到：下划线不被当作合法 scheme 字符，`weired_url:/` 因而进入 path，再被旧逻辑判为本地文件。这个局部原因正确。新增分支依靠后面的 `_split_colon()` 识别 host/path，实际把原例修成 `ssh:implicit`、hostname=`weired_url`、path=`/`，`is_url()` 也变为 True。

但“path 含冒号”不能充分区分 SSH 分隔符与本地文件名。正式 `test_url_samples` 在保留用例 `example.com/path/sp1\:fname` 失败：新分支选 SSH，而原 `_split_colon()` 明确只拆未转义冒号，所以 hostname 保持空；最后重建字符串进入 `__str_ssh__()`，在 `url.startswith('ssh:implicit://')` 断言失败。原调用栈和候选源码一致。该转义用例在 065 已存在，**不是 088 新增的绝对路径／query 两项之一**。

模型还取消公开 `test_network.py` 中题面例的注释。两项修改都在原 FrozenPatch 和 projection 中保留，可信恢复的是三个 hidden 文件及 runner，未丢掉公开测试修改。不能把 report 的 `test_files_modified=false` 解释为没有公开测试改动。

| 正式行为 | 实际动态证据 | 本报告结论 |
| --- | --- | --- |
| 原例与前面的 SSH 字段检查 | 已执行，通过到较后的转义路径 | 局部问题修好 |
| 转义冒号本地路径 | 实际抛 AssertionError | 候选回归，支持 raw 0 |
| 088 crawler query 断言 | 所在 `test_parse_url_opts` PASSED | 此增量通过 |
| 转义用例之后的无转义 slash 前缀 round trip、088 `/some/dir:x` 断言 | 函数提前失败，未执行到 | 不声称动态通过或失败；绝对路径静态上仍会进入过宽分支 |
| `test_get_local_file_url_linux` | `~` 编码 FAILED | expected 本就为 FAILED，非新增回归 |
| nose yield 用例 | XFAIL | 不属于 17 个评分键 |

完整 [正式评分日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v15/results/gpu1003-datalad088-qwen36-a1/grading/eval_logs/evallog_gpu1003-datalad088-qwen3_563e2914.eval.log) 为 15 PASSED、2 FAILED、1 XFAIL，test RC=1；wrapper 正常退出 RC=0。17 键 expected 为 16 PASSED、1 FAILED，因此本臂唯一状态偏差为 `test_url_samples`。不是 infrastructure 失败或缺评分产生的 0 分。

## 定位与纠错：题面已给文件，确认局部原因只需少量调用

以下行号均指完整 [harness trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v15/results/gpu1003-datalad088-qwen36-a1/attempt/harness/trajectory.jsonl) 的原 JSONL 行；时间从首个实际 HTTP 模型请求 `02:49:53.132826 UTC` 起算，到相应工具结果被记录为止，包含模型、工具与调度开销，不能称为纯工具时间。

| 回合／原件行 | 实际动作与证据 | 累计调用／时间 |
| --- | --- | --- |
| G1，11→15 | `ls /testbed`，确认目录 | 1 次工具 |
| G2，25→29 | 直接整读 `datalad/support/network.py`，含 `URL._set_from_str`；题面已给导入路径 | 2 次工具，1.170s |
| G3，43→47 | 原例在 baseline 上为 file／空 hostname／原 path，`is_url=False` | 3 次工具，4.756s |
| G4，57→61 | 直接 `urlparse('weired_url:/')` 确认无 scheme、原串在 path | 4 次工具，5.627s；首次用运行证据确认局部原因 |
| G5–G9，71→135 | 多组 scheme／SSH／本地输入比较，G8 整读公开测试 | 9 次工具；没有验证转义或路径内部冒号边界 |
| G10，149→153 | 加入宽泛冒号分支 | 10 次工具，22.131s |
| G11，167→171 | 原例字段及 `is_url` 修正 | 11 次工具，25.544s；只证明局部修复 |
| G14，221→225 | 公开 pytest 到完整 footer，16 PASS／1 FAIL／1 XFAIL | 14 次工具，30.205s |
| G15–G17，239→275 | 自选字段／字符串／`is_url` 比较均打印 OK | 17 次工具，遗漏决定性边界 |
| G18，285、289 | 最终说明和正常 completed 终点 | 无新工具；没有进一步纠正过宽条件 |

本臂未出现误找文件、循环搜索或工具报错；但文件和示例由题面提供，所以不能用快速直接读取来推断复杂仓库的搜索定位能力。首次完整正确的判别条件／修法**未出现**，局部原因确认时间不等于正确解题时间。

## 工具质量与并行机会

工具共 17 次：13 Bash、2 Read、2 Edit，原工具错误计数为 0。使用已有 `.venv` 与 `-B`，源码和测试编辑位置正确，没有安装依赖或改无关编码行为。两次整文件读取有助于了解上下文，但没有据此覆盖 `_split_colon()` 已表明的转义语义。G5／G6／G9 多次重复 scheme 对比，G11／G12 重复原例；这些调用可以合批，节省往返并把注意力留给边界检查。

G14 用 `pytest ... 2>&1 | head -100`，没有 `pipefail`，工具成功不代表 pytest 成功。本臂实际输出包含完整 footer，不能称为截断。G15–G17 只打印 OK／FAIL／DIFF，不以断言或非零退出传递失败；G16 使用 `str(URL(input))`，原 `_str` 缓存会保留输入，弱于从解析字段重建字符串的检查。正式 hidden 恰好检查了更强的字段／重建行为。

存在独立只读文件、scheme 对比，以及修改后字段／字符串／`is_url` 验证的合批或并行机会；依赖同一修改的编辑和后续验证应保持顺序。本臂每个有工具的生成仅请求一个工具，结果记录后才开始下一个请求，**没有实际工具重叠**。这条样本未触发、也未独立核定执行层多工具并发能力，故模型稳定的并行能力记为**不可判断**，不能从串行样本推出模型不会并行。

## 验证质量：公开回归测试有做，语义边界漏测

先复现原例，修改后再次读字段和 `is_url`，取消注释原例并运行完整相关公开文件，是有效的局部验证。公开文件不包含本次失败的转义路径 case，所以公开 `test_url_samples` 通过与正式 hidden 同名函数失败并不矛盾；两个文件的断言集不同。

验证不足在于：自选本地输入均没有路径内部／转义冒号；没有核 `_split_colon` 与新增条件的一致性；round trip 依赖缓存原串；未验证从字段重建的本地边界。正式 query 通过只能证明该输入，不能概括冒号规则安全。最后说 “All tests pass” 与已观察到的公开 1 FAILED footer 不一致；该 `~` 兼容项在 brief 中已明确，不应改成新回归，但最终说明应准确报告已知失败和验证范围。

## 效率：模型约 45 秒，环境准备另计

计数由原 gateway、adapter 和 terminal result 三方一致读回。输入 token 是 18 次请求累计输入，含重复发送的历史上下文；**不是一次 307k 的上下文**。原计数 cache read／creation 均为 0，不据此估计底层推理缓存或吞吐。

| 指标 | 原件数值／定义 |
| --- | --- |
| 模型生成／CC 回合 | 18；不是 289 条 JSONL 记录或 45 个分段 assistant event |
| 累计输入／输出 token | 307,203／6,283 |
| 单次最大输入／输出 token | 24,589／775 |
| 实际预算 | context 196,608；每请求输出上限 65,536；240 回合；wall 10,800s |
| 首 HTTP 请求至末 adapter 响应 | 41.604s；包括工具往返区间 |
| CC duration／API duration | 41.658s／39.008s；CC 原计时口径 |
| 全部 HTTP response 耗时之和 | 38.529s；包含网关／传输／推理，非纯模型计算时间 |
| driver solve | 44.995s；主求解区间，含工具与 harness 开销 |
| actor 整体 attempt | 173.103s；另有 trusted init 105.363s |
| grader trusted setup／test phase | 106.362448s／1.436084s |
| 正式 pytest 正文／runner test marker | 0.84s／1.262s；与上述 wrapper test 口径不同 |
| 作业资源观测窗口 | 314.490s；不是模型解题时间 |

这些时间口径相互包含，不能相加。工具精确执行时长和入队前等待没有直接证据，均不填估计值；约两次 105–106 秒的 actor／grader 准备不能算作模型定位慢。整文件读取后下一请求输入分别由 4,141→12,035、14,187→19,294 增长，包含读回内容和消息封装；同一历史反复输入是累计 token 较高的具体因素。可以考虑一次读相关函数与测试、合批现有比较，但本臂没有另一个同条件优化样本，不能量化改进收益。

全部实际请求的 `max_tokens=65536`，adapter 上限同值；CC UI 元数据的 `maxOutputTokens=32000` 不替代实际参数。无 length／context／turn／wall 截断证据。CC `costUSD=1.69309` 是兼容元数据估计，不是本次租 GPU 的实付成本。

## 结束、分母和后续

完整 289 记录终点为 `success`、`is_error=false`、`stop_reason=end_turn`、`terminal_reason=completed`；harness RC=0。18 请求均 HTTP 200、无 stream error；模型正常停止后仍需独立判断候选是否正确，本臂是正常停止但解错。solver residual=0、网关 revoked／drained／active=0；grader created／removed=1／1，清理无失败，重评次数 0。

| 当前范围 | 分母与结论 |
| --- | --- |
| Qwen3.6 首轮原预算完成率 | 1/1 正常完成；截断／infra 无效样本 0/1 |
| Qwen3.6 首轮 raw 成功率 | 0/1 |
| Qwen3.6 完整样本语义正确率 | 0/1；决定性旧行为回归已独立核查 |
| 本题首轮双模型覆盖 | 已收到 1/2；Coder 尚缺，不把它计作失败或完成 |
| 同条件稳定性 | 每模型多次样本尚缺，不下稳定结论 |

本臂真正使用的 GPU image 为 `sha256:c5d390400a668256e8946daeefe9758a9064f64d518418727cdb013a907ec346`，不能以 CPU 镜像替代。baseline 为 `ee60bf13…`，246 项；原 FP 为 `b9845649…`。baseline `environment_package_digest=null` 的 formal gate 限制没有闭合。真实请求／配置与执行者冻结身份支持本臂模型路由诊断；没有独立的 GPU 驻留权重哈希证明。资源有限采样不证明连续峰值或最低资源需求，代码／预算实际身份和其它链路限制沿用执行者核查。

下一步保持 088 固定请求和全部原件，接收 Coder 首臂并做同范围行为分析。按多数题修好后的统一计划安排同材料／模型／设置／预算重复采样；只有新增题级或评分缺陷才修订材料、CPU 复验并另交请求。当前没有新增 CPU 修复依赖，不清活动请求，不据 raw 或空闲自行退租。
