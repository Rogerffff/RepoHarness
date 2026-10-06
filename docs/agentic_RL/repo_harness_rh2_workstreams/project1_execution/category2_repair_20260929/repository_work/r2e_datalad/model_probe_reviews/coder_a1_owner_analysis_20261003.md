# DataLad088：Coder 首次探针的题主分析

2026-10-03。题目 `datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb`，模型路由 `Qwen3-Coder-30B-A3B-Instruct`，作业 `gpu1003-datalad088-coder-a1`，材料 `r2e-mr-088`，预算 `probe-wide-v1`。

**本臂正常完成，修好题面例，但一个新增分支漏设本地默认 scheme，候选不正确。** raw reward=0；17 个 expected 状态键匹配 16 个，唯一偏差为 `test_url_samples`。实际断言是转义冒号本地路径的 scheme `'' != 'file:implicit'`。固定 `~` 兼容失败匹配 expected，不是另一个新增回归。

题主只读完整原件，没有 SSH、运行候选、补评或重新 solve。用途仍限固定版本基座诊断，未授训练／留出或通用模型比较资格。最新[覆盖优先规则](../../../overnight_watch_20261003.md)暂缓未开始的普通追加采样，不以旧每模型三次作为本题待办。

## 原件与评分依据

固定 snapshot 为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-datalad088-coder-a1/`。题主重核其 manifest 的 492 成员 SHA／大小，共 45,488,623 字节，包含前序接续和代码身份文件，**不等于 492 份本题新输出**。manifest SHA 为 `1d1abbfae6509be88de2db2eb8783b46da6f3e9bd5ee6a6c8e5e97e5a7ca9740`；[指标与完整工具时间线](../../../../../../../../runs/category2_repair_20260929/r2e_datalad_model_probe_20261003/coder_a1/owner_original_metrics.json) SHA 为 `69147f0348e90c3b667d3312acb97277519fc0c549883293c039fb9eb07e6617`。

直接从[完整正式日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-datalad088-coder-a1/queue_v29/results/gpu1003-datalad088-coder-a1/grading/eval_logs/evallog_gpu1003-datalad088-coder_e526cbc1.eval.log)读回 15 PASSED、2 FAILED、1 XFAIL，17 个不重复评分键与 expected 集合相同，只有 `test_url_samples` 不匹配。日志 8,404 字节，SHA `0bb28e54d225e839cb320537720fbf54abcc7564c2b4e500c8e3cac546a493ec`。实际 test RC=1、入口正常 RC=0，安装在现有环境 skipped，不能声称又完成一次安装；无 infra failure/stage。

[执行者窄回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-datalad088-coder-a1_execution_receipt_v1.json) SHA `17f49918008a51b311b46cdfd9a60e844a22e4771a551fbdae6052cbeb9cd3d3`；决定性原件另由[非作者核查](coder_a1_independent_review_20261003.md)支持。非作者已接触私有材料，不是 fresh 公开盲读。

## 方法与根因：拆分失败后未恢复本地默认分支

[原候选 diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-datalad088-coder-a1/queue_v29/results/gpu1003-datalad088-coder-a1/attempt/candidate/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb.diff) 只改 `datalad/support/network.py`，没有改公开测试。新增逻辑为：

```python
elif fields['path'] and ':' in fields['path'] and not fields['path'].startswith('/'):
    parts = _split_colon(fields['path'], 1)
    if len(parts) == 2:
        fields['hostname'] = parts[0]
        fields['path'] = parts[1]
        fields['scheme'] = 'ssh:implicit'
```

Coder正确复现了下划线 hostname 不被 `urlparse()` 认作 scheme、旧逻辑因而落入本地默认的局部原因。它排除以 `/` 开头的 path，调用现有 `_split_colon()` 后再设置 host/path，比直接把任意冒号判成 SSH 更有边界意识。原例及常见 host/path 实际通过。

失败是控制流：对于 `example.com/path/sp1\:fname`，新增外层 `elif` 成立，而 `_split_colon()` 只拆未转义冒号，返回一段。内层 `if` 不赋值；因为已经选择了这个外层分支，后面的 `else: file:implicit` 不会执行，scheme 留空。完整正式日志在直接字段比较处报 `'' != 'file:implicit'`，与冻结源码完全一致。它与 Qwen3.6 的“选 SSH 后在字符串重建处失败”是不同机制；不能只按同一个失败 key 合并原因。

该转义 case 在065已存在，不是088新加的两项。088 query 的整个 `test_parse_url_opts` PASSED；转义失败之后的 round trip 与 `/some/dir:x` 断言没有执行到。虽然候选静态排除了绝对路径，不据此填该断言的动态通过。这里不要求改变 hidden 对未转义 slash 前缀 URL 的分类约束，也不追加新评分语义。

## 定位和纠错

行号指[完整 harness trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-datalad088-coder-a1/queue_v29/results/gpu1003-datalad088-coder-a1/attempt/harness/trajectory.jsonl)。时间从首 HTTP 请求 `20:39:18.661812 SGT`（原件 `12:39:18.661812 UTC`）起算，到工具结果记录，包含生成、工具和调度开销。

| 回合／原件行 | 动作与可得结论 | 累计工具次数／时间 |
| --- | --- | --- |
| G1，10→14 | 直接整读题面给出的 `network.py`，含目标方法 | 1 次，0.550s |
| G2，23→27 | 整读公开 `test_network.py` | 2 次，1.292s |
| G3，36→40 | 原例在 baseline 是 file／空 hostname／原 path | 3 次，2.839s |
| G4，49→53 | 定向再次读 `_set_from_str` | 4 次，3.780s |
| G5，62→66 | 直接 `urlparse` 确认无 scheme／hostname | 5 次，6.175s；首次运行证据确认局部原因 |
| G6–G7，75→92 | 重复 scheme 和常见 SSH 对照 | 7 次；没有转义路径 |
| G8，101→105 | 一次源码编辑 | 8 次，12.623s |
| G9，114→118 | 原例与常见 SSH／本地字段正常 | 9 次，14.368s；证明局部修复 |
| G10–G12，127→157 | 相关1项、3项、再完整18项公开 pytest | 12 次，19.359s；完整文件只有已说明的`~`兼容失败 |
| G13–G15，166→196 | 自选断言及两次原例／原有示例断言 | 15 次；均避开转义冒号，未纠正新增控制流 |
| G16，205 | 正常 completed 终点 | 无新工具；没有完整正确修法 |

文件由题面提供，不能把直接读取速度外推为复杂仓库搜索能力。本臂无误定位或搜索循环；一次编辑后没有返工。但一次编辑并不证明修法完整，首次完全正确的解决方案未出现。

## 工具与并行机会

共15次工具：3 Read、11 Bash、1 Edit。工具错误1次是 G12 完整公开 pytest 的 RC=1，原 footer 和 brief 共同指向已知 `~` 兼容项；不是坏命令、环境中断或候选本次新增问题。三个pytest均未用管道隐藏退出码，完整结果可读。

G1整读源码后G4又读目标方法，G5／G6分开做近似scheme比较；G10单项和G11三项测试后马上G12整文件测试包含前面函数，存在重复。G13已用 assert 核多种 host/path和普通路径，G15也断言题面字段，强于只打印OK；但边界只选无冒号的普通本地路径。G14复查的是原有 `weired:/`，不能代替下划线或转义case。未检查“进入分支但 `_split_colon` 不拆分”的输出不变量。

使用 `python` 而非brief建议的显式解释器和 `-B`；本臂公开pytest实际显示 `/testbed/.venv/bin/python`，激活已核，不能据简写判错环境。未加 `-W ignore` 产生较多依赖告警输出，`-B`缺失也可能生成再生缓存；具体排除路径变化依原census／独立核查，不据旗标猜测。下一轮若有明确校准需求，可优先合批比较及相关测试、缩小阅读窗口、补控制流边界，而非重复原例。

两份只读文件、scheme比较和修改后独立行为检查有合批或并行机会。本臂每个有工具的生成只有1个调用；全部结果先于下一请求，未观察到重叠。多工具执行能力未在本臂触发或独立核验，模型的稳定并行能力为**不可判断**，不据串行样本判不会并行。

## 验证：真实断言增加了，但本地边界仍缺

有效部分是先复现、编辑后字段检查、真实相关和整文件pytest，以及最后多输入assert。公开 `test_url_samples`仍注释题面例、也没有本次转义case；模型额外断言验证了原例，却未新增公开持久测试。正式hidden同名函数包含更强的保留case，所以两者结果不同不意味着评分矛盾。

最后文字准确说明了公开文件的已知`~`失败，**没有像Qwen3.6最后文字那样声称全绿**。但声称“maintaining backward compatibility with all other URL types”超出实际覆盖：实际转义本地路径已经破坏。没有检查scheme默认值、从字段重建和 `_split_colon` 返回一段的分支，导致错误修法通过它自己的自选验证。

## 效率：求解约35秒，准备耗时独立记录

实际gateway／adapter／CC终点计数一致：16次生成，累计输入297,378、输出3,328；单次最大输入24,309、输出628。累计输入包含每次重复发送的历史，不能理解为一次297k上下文。CC报告cache读／写均为0，不据此推断底层缓存性能。

| 原计时口径 | 数值 |
| --- | ---: |
| 首HTTP请求至末adapter响应，包含工具往返 | 31.775s |
| CC duration／API duration | 31.839s／27.651s |
| HTTP response耗时总和，含传输／网关／推理 | 27.201s |
| driver solve | 35.238s |
| actor整体attempt／其中trusted init | 179.321s／119.217s |
| grader trusted setup／test phase | 111.414140s／1.462457s |
| 正式pytest正文 | 0.82s |
| 作业资源观测窗口 | 326.004s |

口径相互包含，不可相加。精确工具执行时间和入队等待没有对应证据，不填估计；准备的119秒／111秒不计模型定位或求解耗时。整读源码／测试后下一请求输入由4,103→11,634、11,634→16,265增长，包含工具结果与消息封装；之后重复相关pytest输出也被带入历史，是累计输入较高的具体因素。

预算仍为context196,608、实际每请求max_tokens65,536、240回合、wall10,800s。无预算截断，CC UI的maxOutputTokens32,000不替代真实请求上限。CC costUSD1.57009为兼容元数据估计，不是租GPU实付费用。不能因这一个样本比另一模型少约10秒，就下模型效率排名或稳定性能结论。

## 终止、身份与用途

完整205记录，末result为success／is_error=false／end_turn／completed；16 HTTP均200、无stream error，harness RC0。solver、grader及gateway清理闭合，原FP重建成功，无重评。原FP `193740cb…`只有源码一项，实际GPU baseline `ee60bf13…`、246项，与Qwen3.6相同image `c5d39040…`和base；原FP的excluded_pathset_changed=true与projectable分类如实保留。冻结契约明确该旗标记录排除区路径集合变化，不单独据此判篡改；本臂reason_codes为空，非作者窄核未发现材料阻断。不能宣称排除区不变，也不推广成训练资格。

单模型原预算完成率1/1、raw成功率0/1、完整样本语义正确率0/1；截断／infra无效0/1，没有同条件重复稳定性结论。baseline环境包字段仍null。实际模型路由与冻结运行配置支持本次诊断身份，不等于独立证明GPU驻留权重；本题也不构成两个模型的一般能力排序或来源训练价值结论。

双模型当前首轮结果已齐，[成对汇总](pair_first_round_analysis_20261003.md)已完成；题主核收执行回执并已用工具ack（请求revision5）／清活动指针（progress revision9）。当前没有新增题级材料阻断或CPU修复依赖。保留两份失败原候选；暂缓本题普通追加采样，不重复solve求通过，资源动作服从最新用户安排。
