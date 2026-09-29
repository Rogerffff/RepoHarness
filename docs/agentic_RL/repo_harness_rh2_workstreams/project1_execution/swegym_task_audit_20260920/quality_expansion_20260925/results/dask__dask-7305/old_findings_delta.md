# dask__dask-7305：旧发现逐项差异

root明确release后完整读refs所列L1_dask记录和09-20 dask_pilot本题记录，两个SHA吻合。未沿其链接扩读raw hints、环境汇总、旧原日志、其它题或reviewer；09-20原日志引用与本次第一阶段已授权核过的同题pair相同。

| 旧主张/来源 | 结论 | 决定性依据与边界 |
|---|---|---|
| L1 checks1/4/17：文件对应但新增large_uint在base过 | 确认并分开字段 | 本次patch/base/投影对应；noop1597、gold1602均PASSED。材料版本对应属1，行为覆盖问题属25/32，不因测试弱就说版本不一致 |
| L1猜“不经过partition_quantiles快路径” | 纠正为先计算再覆盖 | shuffle.py:487–492先算quantiles/min/max，522–530条件成立后以mins+[maxes[-1]]替代quantiles并返回。不是完全没执行quantiles，而是错误结果不决定最终断言 |
| L1 check2：直接题面例未跑，base行为未实测 | 确认范围 | np.percentile线性转换是静态精度风险；本次未执行直接例，不能用另一个set_index通过来否定base bug，也不把准确+1当已复现 |
| L1 checks3/29：hints含三方案、公开没有选方案1线索 | 公开规格部分确认；原hints未核 | 当前prompt确无所有整数nearest要求；私有讨论仅旧转述，actual消息/可见材料未知，check3/29保持unknown。09-20 public_boundary这种分离方式成立 |
| L1/09-20：唯一F2P是小整数{1,2,4} | 确认 | 完整test.patch、expected及noop1511–1515/gold1600；它不直接比较大整数端点。近似算法允许内部选择变化不意味着这唯一集合是公开规范 |
| L1 check24“强制唯一实现最严重”“方案2必整题拒绝” | 收窄；同意09-20 unresolved | 公开允许精度安全分支/精确保留端点的方向，F2P确排除保留原小整数集合的结果；未实现/运行完整替代解，不称已证反例或所有合理实现必拒 |
| L1 check25“只改nearest不碰uint64就是伪修复” | 推翻；同意09-20 refuted | 避免整数浮点插值正是gold局部修复机制。覆盖不足可以独立成立，不能把有效机制本身称完全不修bug。需另有残留行为的明确验证 |
| L1 checks26/27 pass：gold完整且无回归 | 收窄 | 本次完整process_val_weights:337–343仍np.interp，末端astype无法恢复已丢精度，构成未执行完整性风险；nearest第一阶段有正证据。未证新增gold回归，26 unknown，27完整性unknown而非全pass |
| L1/09-20：large_uint只能是回归保护，不是缺陷验收 | 确认并细化 | 新函数只npartitions与set(divisions)，不检查直接Series dtype/name/index/顺序或最终数据范围；同数据形状被单分区min/max替代 |
| L1 checks6/7/11、09-20环境“baseline_pair_no_known_environment_issue” | 确认本次pair范围，非当前actor资格 | 同一RH2pair安装RC0、noop1失败/gold0失败，108collected、3slow skip，expected105项都有状态；actual image ID仍null。旧标注不能变成完整环境/稳定性资格 |
| L1 skip伪键[3]与106结果数 | 仅确认日志形状，未重演parser | 本次原skip摘要[3]、parser106与collected108不同；expected逐ID完整。完整非expected解析正确性仍未证明；skip不能记已执行 |
| L1建议强写“所有整数nearest”进题面/直接reject_revision | 不采纳为唯一处置 | gold不是规格，优先直接验证公开端点与不足唯一值分支，再讨论版本化验收。09-20不为gold写法补题意的限制与初判一致 |
| 09-20 next_action安全转换完整候选实验 | 合理后续但本次不执行 | 本次唯一优先先做公开直接例的1/3输出分区base/gold私有CPU对照，定位核心和np.interp残留；不机械增加第二实验/全仓 |
| L1包内唯一、早期成本minutes24/跨题信息 | 未核、不继承 | 不扩读prescan或其他题，旧成本不能当本次成本；development_diagnostic、needs_review/static_review |

history没有改变封存前稿核心判断。新增明确纠正“完全绕过quantiles”和“nearest是假修复”两种表述；09-20记录已先收窄合理替代解的实证程度，本次独立初稿与其一致。最值得先做的仍是题面直接函数的私有base/gold精确端点对照，覆盖相同两值请求1和3输出分区，不需要原CSV、模型或全仓。未新增CPU/actor事实。


封存初稿：[analysis_before_history.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7305/analysis_before_history.md)（SHA256 `612fe1f394c138a31bb605f397e21499a0763dd844508a48f1ec26232cbe2fd1`）。

本次release后历史读取仅：

- [dask__dask-7305.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-7305.json)；SHA256 `90ff4ee6fa16435c2fbdd0943b906a6a8dec7945352396b653bb4da4d74bb2ca`。
- [dask__dask-7305.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/dask_pilot/records/dask__dask-7305.json)；SHA256 `91582bb64bc8e619458355cc75368f878f4cee2c59d0c727750431b419bad38b`。
