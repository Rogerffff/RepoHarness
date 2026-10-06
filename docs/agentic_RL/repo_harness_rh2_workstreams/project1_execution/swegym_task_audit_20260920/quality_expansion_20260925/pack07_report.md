# Dask 第七包静态收口

6801、7138、7305 三题均优先处理质量问题（quality_first）；全部仍为 needs_review/static_review、development_diagnostic、ready_for_probe=false。本包不新增开发候选，不授actor、训练或正式评测资格。

| 题目 | 决定性证据 | 唯一优先后续 |
| --- | --- | --- |
| 6801 | 4个F2P只验列裁剪图；没有共享delayed次数。gold保留HLG但Arrow infer初始化仍compute | 私有base/gold公开例普通/infer分阶段计数 |
| 7138 | gold把ravel(array)更名为ravel(array_like)；derived_from不补关键字别名，旧array=绑定破坏 | 维护者处理参考兼容；无新增CPU |
| 7305 | 唯一F2P锁小整数{1,2,4}；大uint新测试属于P2P但noop已过，quantiles随后被min/max覆盖 | 私有直接partition_quantiles两值、1/3输出分区精确端点对照 |

6801 的普通共享图修复有局部依据。infer采样是未修改的残留，不列为gold新引入回归；tokenize漏写选项仍只是条件性碰撞疑点，同路径并发写语义需先界定。read-parquet前缀/BlockwiseParquet要求可能误拒不同正确图，未执行完整替代解。旧scheduler测试只记flag和结果，旧graph_size测读取图，kwargs_pass为新建局部字典；相应历史说法已纠正。公开例显式meta排除了from_delayed自动探测；不得用私有旧维护意图静默豁免题面infer目标。

7138 的新输入转换是实质正证据；旧非零Dask、未知长度1D及图长度P2P也有作用。新增四组非Dask样本全零，不能验证一般内容/顺序；no_op没有身份或共享内存断言，不能宣称零拷贝。保留26/27 issue基于具体旧关键字绑定，并非因影响面大而判回归。公开题面含修法仅是引导属性，模型难度/训练收益未知。

7305 reviewer在cross release前主动报告初稿P2P归属错误，review首段已更正且初稿SHA不变。该测试确在104 P2P中，先算quantiles、再被单分区min/max覆盖；不能说完全没执行quantiles。nearest避免第一阶段浮点损失是有效局部机制；唯一值不足时np.interp仍有精度风险，27unknown、26unknown。小整数固定集合的误拒风险未由完整替代解实证，不将其写成所有合理解必拒。

历史原命令与结果逐题保留：6801 parquet文件371 collected，noop8fail/355pass/1skip/7xfail，gold363pass/1skip/7xfail；7138 routines文件561 collected，noop560pass/1fail，gold561pass，均92warnings；7305 shuffle文件108 collected，noop104pass/1fail/3slow skip，gold105pass/3slow skip。expected分别4+169、1+468、1+104，全有状态且无expected跳过；P2P语义为风险抽查，不是全数通读。6801旧缺fastparquet及7138旧pytest8故障不适用于所引修复pair。安装末命令RC0、测试RC1→0；actual image ID分别83edfe…、281a1a…、null，完整摘要见逐题record/review。历史grader成功不等于当前actor初态/权限/依赖/资产可用。

五个审查角色均显式gpt-6-astra/high/fork_turns=none；不声称后端验真或OS隔离。独立初判先封存，主审history与reviewer cross均在工具接受后记录release。六份主审card/record先核交付SHA再归档，见[修订链](coordinator_revisions/pack07_dask/revision_log.json)；仅root改这六份最终材料，初稿/delta/review和原件不变。root核读范围与未读边界见[记录](reserve20_coordinator_read_notes.md)。结构/hash/时序校验见[输出检查](pack07_output_verification.json)及[修订来源检查](pack07_revision_provenance_verification.json)，不把这类检查当作语义或actor资格认证。

[后续提案](pack07_followups.md)只有两项私有CPU诊断和一项参考兼容审查，均未执行或派发；任务二由Claude B负责。新增累计9/20、总21/32完成，继续冻结剩余任务，无需逐包等待。
