# Reserve6 Pydantic8567／9066 正式结果独立复核

2026-09-29。接续 [actor/private 复核](reserve6_pydantic_behavior_review.md)，跨包独立、非 fresh-blind。先读正式原件，再与题主最终用途卡核对。**两题本次正式 noop/gold 均为 0/1；安装、实际导出、来源参考及清理证据支持真实评分结果。gold 得 1 不消除前段已实测的兼容回归。**

## 正式运行与身份

审查目录为 8567 的 `reserve6_v1_20260928T205304Z-725caa`、9066 的 `reserve6_v1_20260928T205304Z-4f3c46`，各 `grade_noop`／`grade_gold`。四次均使用冻结 code_v1、安装配方入口和原来源测试；仅本实验 setup 预算从300升900秒，test1800／whole3600秒不变。策略为2CPU／4GiB、UID54322、deny_all 网络，没有生产默认或权限改动。

实际 grader 镜像分别为 `b11ee14bd5a90957da5bcb6ef7e09d9ae4db6421b9b8ec36cfdd1b98f43299e9`、`53b96f8194676b2732552c3196debd32c02984797a90cb1cfe4a78fbd0c414f0`。两份 inspect 的原13层逐一等于新14层的前13层；Dockerfile／实际构建日志仅 `COPY wheels/ /opt/rh2/build-wheels/`，另设 `PIP_NO_INDEX=1`、`PIP_FIND_LINKS`。八个公开 wheel 的下载记录列明尺寸和SHA，与冻结清单对应，没有预装候选代码或改变 core 的 RUN 层。ARG 无默认值的构建 warning 不影响本次明确传入 immutable base digest 的成功构建。该层恢复评分所需离线 build 资产；原 actor 已成功，不能称修复了原 actor。

四次真实执行 `pip install -e .`、从候选 pyproject 读取 testing／testing-extra 并安装，均 install_rc0、failed_commands空、未跳过。安装后导入 `/testbed/pydantic/__init__.py`；8567版本2.6.0a1／core2.15.0，9066版本2.7.0a1／core2.16.3，与各自私有行为 core 一致。runner digest 前后不变。未另做安装后 pip check，不宣称全环境包依赖皆已验收。

## 测试与逐参考

| 题目／候选 | 完整选定文件测试输出 | 来源参考逐项结果 | reward |
| --- | --- | --- | --- |
| 8567 noop | 165 collected；1 failed、164 passed；test_rc1 | F2P 0/1；P2P 158/158通过 | 0 |
| 8567 gold | 165 collected、165 passed；test_rc0 | F2P 1/1；P2P 158/158通过 | 1 |
| 9066 noop | 384 collected；2 failed、380 passed、1 skipped、1 xfailed；test_rc1 | F2P 0/2；P2P 367/367通过 | 0 |
| 9066 gold | 384 collected；382 passed、1 skipped、1 xfailed；test_rc0 | F2P 2/2；P2P 367/367通过 | 1 |

独立从每份完整测试日志抽取原始 node 状态，再与本批 `private/reserve6_v1/host_grading_views.jsonl` 逐名比较：8567的159×2、9066的369×2个参考状态齐全，全部符合上表；无缺失、参考skip或参数键误配。9066 的非参考 `test_literal_types` 为skip，`test_get_pydantic_core_schema_calls` 为xfail，不能写成384项全通过。冻结 parser 统计9066为376个键，与原始384节点计数不同；该差异没有吞掉来源参考，本次未修改 parser。root 的 [8567 parser 重放](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/pyd8567_final_v1.json) 与 [9066 parser 重放](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/pyd9066_final_v1.json) 也一致。

8567 noop 唯一失败是 `test_plain_validator_plain_serializer` 的 `isinstance(True,str)`；9066 noop 两个失败分别为 IPv4、IPv6 默认值进入 `to_jsonable_python` 的 SerializationError，随后 `non-serializable-default` warning 在 pytest 中作为错误报告。均为目标行为，非导入／collection／安装／超时伪装的0。四份测试起止标记、安装起止标记齐全，log_partial=false；本地完整日志 SHA 与各自 ledger 匹配。

## 实际候选与清理

两次 noop 的 frozen entries 空；两次 gold 各仅导出一个普通100644源文件，projection只包含该文件、excluded_pathset_changed=false、classification projectable、stage_error空。将 frozen `content_b64` 解码并独立计算整文件SHA，得到：

- 8567 `pydantic/functional_validators.py`：23,628 B，`cbdbf0cf4557b0a2012621781a6a3c6e375d6821b12e939e5f6f6cb35363a5dd`。
- 9066 `pydantic/json_schema.py`：103,620 B，`1dcdfe4f2143ae0b089030c5bc98332f99fd0d686cffa23a9cbeb2ce51126c80`。

两者与前段 private 实测源文件以及公开base+正式gold纯文本重建完全匹配。因此本次得1的 gold 与出现已定位回归的私有 gold 是同一目标源码，不只凭 patch输入或 git apply rc0 推断。正式 trusted setup 恢复并应用各自来源测试，apply_ok=true、测试文件无缺失／异常，候选没有测试／fixture路径修改。

四个 ledger 的 candidate cleanup 均 removed=true、steps=`rm:ok`、detail空；四份 manager_close_checked 已与各自原driver末尾JSON逐结构核对一致，均 created_total=removed_total=1，containers_open／supply_open／cleanup_failures空，final_status exit0，halted／aborted空。两层清理分别有证据，不以外层脚本rc0代替。

setup耗时8567 noop/gold294.625／299.456秒，9066为296.099／300.853秒；安装4.683／4.325、4.927／4.620秒，测试3.497／3.423、7.150／6.218秒。ledger peak分别821.629／805.301／824.445／811.203 MiB；resource_facts为空，不能据此断言全程无OOM或给出最低内存需求。准备耗时与测试耗时不能混用。

## 质量结论与用途边界

8567支持 **S1／T2a**：题面原例明确要求 JSON 序列化结果与两种排列一致；正式新增参考只调 `model_dump()` 并断言两个结果是str，既不检查 JSON 路径，也不核字符串值。这个独立的核心覆盖缺口已经足以判断S1，不需要把 Custom 出现频率推定为常用程度。Custom+PlainValidator 回归另记为实测G1；不据此声称题目无解，也没有新造退化候选或退化正式分数。

9066支持 **S1／T2，按标准§4第4步**：本轮 gold 得1，却破坏默认配置下标准 dataclass 实例默认值的 schema生成。stdlib dataclass 与BaseModel组合是公开文档明确支持的能力，默认值编码属于通用 schema API；`D(1)` 无特殊配置或异常输入，具体base成功／gold抛配置错误与代码路径一致。因此并非仅因“gold有bug”自动升级，也不是边缘自定义协议推断。新增参考含IPv6 `::1`，超出公开IPv4原例，不能归为只复制原例的T2c。[公开 dataclass 组合说明](../../../../../../runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-9066/base/docs/concepts/dataclasses.md)。

两题可保留CPU诊断证据；如另行开展受限比较，必须明确固定环境／参考版本及语义复核，原始reward不能单独代表完整修复或判胜负。修订参考／补充兼容控制所需的完整正对照仍待修复gold或独立验证替代解；不能以有回归的gold充当全面语义正对照。D6未实施，不授予训练或留出资格，actor桩也不证明自主模型能力或完整题面交付。

最终卡窄对照完成：[8567 result.md/json](../tasks/pydantic__pydantic-8567/result.md) 与 [9066 result.md/json](../tasks/pydantic__pydantic-9066/result.md) 的实际结果、分级、条件用途与剩余项均与本复核一致，无新增阻断。root 的 [传输SHA总账](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_reserve_pyd_v1.json) verified=true，156件／1,361,362字节远端与本地一致；[四容器资源采样](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_reserve_pyd_v1.json) 各20–21样本未观察OOM／PID拒绝，非全生命周期证明。已完成actor/private的历史部分记录保留；本篇取代其中“正式结果尚待完整复核”的阶段状态。
