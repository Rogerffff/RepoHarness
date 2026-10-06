# MONAI6975 准备超时恢复独立窄审

审查日期：2026-09-29。结论：**当前版本预发接受，未发现阻断；尚未执行，不能声称恢复成功或解释正式得分。** 本审仅本地读取原件、脚本及冻结参数，使用标准库核 SHA/JSON/AST；未运行远端、项目或评分。复用已审 actor/private 范围，不重做目标语义审查。

## 审查版本

- 新脚本：`rh2/experiments/swegym_cpu_preprobe_20260929/monai6975_grade_recovery_v1.py`，SHA256 `6a4b6ca30adb66b8b917bbb0dafddcc1f9dff64dd0d51d36792d3aa2b2f0a35f`。
- 直接父脚本 `monai_reserve_followups_v1.py` SHA256 `32fb723f773569858cdf97d148616a67c43c55bd55aabb2e07649df55e735145`；其固定 `mixed_followups.py` SHA256 `605f4326beb120c00cbbb6a6bbc36f04a03ce6a64f834cd557edc9fba4d799c6`。新脚本未修改二者。
- `runs/swegym_cpu_preprobe_20260929/monai6975_setup1800_approval_v1.json` SHA256 `80e6cc063aabf2d0556bda60a89da47429691dc0155a436b71c2f5de2c240415`；所列旧目录 **67 个文件全部存在、字节数与 SHA 相符，没有漏列或多列**。当前 9 项输入 SHA 与旧 `status.json.inputs` 全同。
- 旧证据：`runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-6975/reserve6-v1/`。新远端结果目录为 `/work/swegym_cpu_preprobe_20260929/results/Project-MONAI__MONAI-6975/grading-setup1800-v1/`，创建采用 `exist_ok=False`，不会覆盖旧失败证据或重新执行 actor/private。

## 原失败的准确解释

`grade_noop/ledger.jsonl` 的真实结果是 `infra_failure` / `failed_to_grade`，detail 为 `grading_control_surface_protect_timeout_after_900s`。reward、F2P/P2P、install、test 都为 null，`execution_failure_stage` 也为 null；因此不能只查后者，也不能记成正常目标 0 或“参考测试不一致”。`grader_trusted_setup=901.136589s`；日志已记录测试文件恢复 2/2、apply rc0、`RH2_SETUP_OK=1`，之后在控制面保护阶段超时，未进入安装/测试。原评测日志 18,091 字节，SHA256 `0209d74891d2ec022d7e78ac90ef597e7fc7f67b933c0538bcb07956c866958d` 与 ledger 相符。

旧父方法先把 null 参考数与 4 个 F2P / 59 个 P2P 比较，才检查基础设施失败，故外层错误 `formal reference counts differ` 是实验诊断顺序错误。旧候选清理 `removed=true`；`grade_noop.log` 唯一 driver footer 中 created=removed=1、containers_open/supply_open/cleanup_failures 均空，final exit0、grader_containers_open 空、cleanup_failures_total=0。旧方法未写 `driver_close_checked.json` 是提前抛错所致，不代表容器泄漏。

内存峰值 4 GiB；原 `resource_facts` 记录 container_oom_killed=false、oom_kill_events=0、pids_events_max=0。这不证明没有回收/IO 压力，也不确定超时根因。准备预算扩大只能作有界复验。

## 新脚本可达流程与守卫

1. **身份及绑定。** 先验固定父脚本、继承固定 helper/评分源码、9 项输入、公开 base/digest、私有完整 base/F2P/P2P/test_patch、prepared gold 字节。随后逐文件核旧证据，要求旧精确准备超时、install/test/reward null、私有矩阵已确认、双层清理完整。原镜像 digest `sha256:0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055`；inspect 必须同时匹配旧 image 及 approval 的 ID `sha256:789cb5d10d9b343a2e8b656581697a7127b56a0d467b1cc5b8779a79a0ff0727`，公开 tag 在启动前及每次 grade 前必须同 ID。无新镜像层、安装配方或 Conan 空绑定的引入。
2. **不重复开发实验。** execute 只遍历 noop/gold/degenerate 的继承 grade；不调用 actor/private/pull/build。要求 MONAI4583 `executed_pending_review`，再检查实际无任何 Docker 容器、无默认三网络以外的网络，满足原队列正常收口后的串行启动条件。此检查遇未知/残留直接停，不自行清理无关资源。
3. **预算只有已授权差异。** 重载 run 在调用父 run 前，精确要求原 setup=900 并改 1800，同时要求 candidate-stage=900、whole=3600。继承 direct CLI、test=1800、cleanup=120、外层4380及2CPU/4GiB/UID54322/deny_all不变；实际预算审计还须 after1800、test_seconds_unchanged1800。冻结 wrapper 只替换 env_reset_timeout_seconds，不改变测试内容或超时。whole3600包含各阶段开销，并不保证准备与测试各自都能用满1800；若触及总时限仍应停止并据实分类。
4. **先判执行有效性，再解释测试。** 父 run 成功返回后，新 run 先要求唯一 ledger、唯一 driver footer，保存 `driver_close_checked.json`，要求候选 removed=true，再保存 `execution_classification.json`。只有 stage_error=None、reward 为0/1且 infra_failure_detail/execution_failure_stage为空，才返回父 grade 比参考。因此已观测的 setup900 超时形态会得到明确 infra 诊断，不能再掉入 null 参考数比较。若子进程非零或取消，父 run 直接停止，不进入后续候选；TERM等待180、升级KILL等待30均有界，未知清理不能解释成成功。
5. **实际候选与完整结果。** 父 grade 仍检查安装 rc0/日志完整、测试段结束、引用不缺失/skip、runner未变、实际import在/testbed、完整日志SHA。gold/退化必须只投影 `monai/transforms/transform.py`，唯一冻结 regular/100644 文件、excluded_pathset_changed=false，源码SHA分别为 `5d8ba724a4e09bdf533c1030e0891a9acfb00a98069ca6586533cddb4e369bb5` / `a8382325df5169732767963fa29553845514fe29b318ce60184bdcc12ddf369a`，与旧 private 实际校验源一致；noop included_paths须空。noop预期0/gold预期1异常立即停；退化得1保留待语义审查，不当成失败或自动通过质量门槛。
6. **双层清理不弱化。** 新 run 要求 manager created=removed=1、open/supply/failures严格为空、outer failures无、halted/aborted无，final exit0、grader containers空、cleanup总数0；继承 grade 再检查。最后再次核实际 runtime 空，才写 executed_pending_review。单一进程 rc0 不能替代上述清理凭据。

## 执行后仍须核的事项

预发接受仅覆盖上述确切脚本、approval和当前输入。执行后须读三方原始日志、逐参考全表、安装/测试段、实际镜像/资源/预算、冻结源码和双层清理，再由 root 冻结 parser 重放及远端/本地 SHA 归档；不能以 campaign 成功代替逐件验收。原 actor/private 的复用范围保持原样。单独运行和 setup 扩大同时发生，应在结果中写清，不能据成功把并发、CPU或内存认作唯一根因；D6正式修订、GPU/模型能力及训练资格均不在本恢复范围。

## 后续队列 gate 补充窄核

另读 `rh2/experiments/swegym_cpu_preprobe_20260929/wait_recovery_then_conan_v2.py`，SHA256 `77302dbd4ffa0d4b5811db16a615d12ec947c75a442686b3a580111417823719`（AST通过）及 `runs/swegym_cpu_preprobe_20260929/queue_reserve_conan_v2.json`。无新增阻断：只接受新恢复目录的 executed_pending_review、无error、三组formal_results齐全，并再次要求4583正常及实际全局容器/非默认网络为空；依据上面已固定恢复脚本，该status只能在逐组双层清理及最终实际清理通过后产生。gate不宣称独立质量审查完成，只放行尚未执行的两Conan实验。Conan与dispatcher SHA分别固定为 `1be9fe84c0a02d7277b3e0950394214ca76734b7dc72f0733805b0e2b66c4693`、`4c8ca3368d9910fd83d69307d29d3f529ef00a33466d3f31c47cdc39ba17090b`，新dispatch目录须不存在，旧等待/dispatch不改。启动顺序须先产生恢复status再启动gate；文件缺失或读到未完整JSON会保守停止，不会错误放行。等待有7小时上限、unit停止即停；SIGTERM也不继续派发。
