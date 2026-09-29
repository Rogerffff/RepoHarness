# A 线四个待审提交：独立复核

日期：2026-09-28。Codex；检查基准 HEAD `23f5586d`。入口为 [A 线当前状态](../../a_line_status.md) 的 A-N1。

## 1. 结论与下一步

**四个提交已完成本轮复核，但不能整体标为通过。** 发现两项资源所有权问题：AR1 影响当前共用的中转启动函数；AR2 只在尚未正式接线的包供应模式下发生。另有一条供应收尾事实未落盘的观测尾项 O1。

- **先修 AR1**：第二次同名启动失败，不能删掉第一次仍在运行的 relay。属于本次修复引入的回归，不需要新决策。
- **AR2 与 O1 随包供应接线前收口**：取消不能让 token、网络和子网槽位失去清理责任方；收尾事实要能回读。这不阻塞 B 继续按默认离线链筛查。
- **可通过的部分**：PC1 异常判定收紧、评分侧可信 root 前缀、离线路径 E4a/CR1、E2a 批量扫描的本机正确性，以及两段执行的正常顺序和三个结束形态。
- **未完成的仍是未完成**：bringup/rollout 的供应接线、逐题 supply_policy、真实 x86 镜像与已落盘基线对账、代表题安装、GPU 验收。不能概括为“本地全部收尾，只等八卡”。

本轮无新 T0，不重开 1A+2A、I01 B 或评分政策。未修改生产代码、维护测试和 oracle；未提交、push、通知 B 或登录远端。仅使用本地 CPU、Docker 与 localhost 假上游，没有请求公共包源。

## 2. 范围与逐项裁定

| 提交 / 切片 | 裁定 | 依据与适用边界 |
| --- | --- | --- |
| `0adac07d` / NG1 | 原反例已修；留 AR2 | 普通 release 会切断在途下载、收齐事实，后续请求 404；但 release 调用者被取消时状态卡住 |
| `0adac07d` / NG2 | 原取消漏收已修；留 AR1 | readiness 取消会回收；新增无条件按名回收却会删除另一启动者的活容器 |
| `0adac07d` / PC1 | 通过 | 仅捕获异常本身包含路径错误时才走 unsafe；混合的我方契约错误仍按原 ValidationError 暴露 |
| `5b00a091` / E2b | 通过 | 候选执行后的 root 读取使用清空环境和系统 PATH；两处明确的 image_env 例外保留现状，不扩张安全承诺 |
| `5b00a091` / E4a | 离线模式通过 | 按确认删除的完成序号裁剪、遍历快照、累计数不随裁剪缩小；新增供应资源不能沿用“容器删掉即全部完成”，见 AR2 |
| `5b00a091` / CR1 | 通过 | exec 已交付输出在后续 inspect await 前保存；较短 tee 不覆盖较长输出，取消保留证据 |
| `8f31caee` / 两段评分 | 主顺序通过；留 AR2、O1 | 真实 manager + 本机 Docker 的安装→宿主断网核对→测试正控通过；不能据此声称所有取消位置都完成清理 |
| `23f5586d` / E2a | 本机正确性通过 | 冻结旧脚本与新脚本差分、root/非 root、回退和特殊路径通过；真实 x86 镜像/持久基线一致性与收益仍留 A-C1 |

`83760b15`（G1）及 B 线 `1ca4703a` 的既有结论不在本轮重审范围。新两段代码消费它们时只检查相关接缝。

## 3. AR1 / P1：第二次同名启动失败，删除了仍在服务的中转容器

**可达性：`production_reachable`。处置：`accepted`，先修。**

### 事实与触发条件

`adapters/slime/sandbox_profile.py:1116–1119` 对所有非零的 `docker run` 调 `_fail()`；`1107–1114` 不核对本次创建事实，直接按预选名字 `rm -f`。名称冲突也是非零，因此发生：

1. 启动 A 成功，relay 在运行。
2. 启动 B 用同一个 run_id，Docker 因容器名已存在拒绝。
3. B 的失败清理把 A 的活 relay 删了。

不变量是：**只回收本次启动实际拥有的资源；预选名字不是所有权证明。** 旧分支在 run 非零时直接抛错，此误删是 `0adac07d` 新引入的回归。

### 实证与影响

[主审真实 Docker 探针](main_gateway_relay_probe.py) 的供应入口及 [默认 egress 入口探针](main_egress_collision.py) 都复现：第一次 `Running=true`，第二次返回名称冲突，第一次随后 `inspect` 为 `no such object`。结果分别在 [组件 JSON](main_gateway_relay_probe.json) 与 [egress JSON](main_egress_collision.json)。只创建并清理了随机命名的探针容器，无残留。

默认入口不是未来供应功能：`bringup.py:1779–1782` 用 `MILES_RH2_RUN_ID` 或 `local-<pid>` 调 `start_egress_relay`，与 supply 共用该 helper。重复/并发同名启动、相同 run_id 下旧进程仍活着时重启会触发；单实例首次启动不触发，实际发生频率未知。

损害是已有 run 的模型连接中转被移除，可能造成在飞执行失败和整组损耗；未证明奖励污染。第二次进程 fail-fast 无法补救已经删除的第一次资源，所以需改清理归属，不能仅增加报错。

### 最小修法与停止条件

- 已明确名称冲突时，报告启动失败但保留已有对象；一般取消/异常回收也需能证明对象由本次创建。
- 保留“本次确已创建、尚未交出 handle 就被取消”时的有界回收。不要为此引入多 relay 管理平台、自动接管或训练准入闸门。
- 验收仅需：egress 与 supply 同名冲突均保留第一个活容器；本次新建后 readiness 取消仍能清理；本次创建失败留下 Created 容器的既有清理正控保持。

正常训练表示、奖励和分布不变；修复成本限于现有启动 helper 的归属与测试。通过这些对照即可关闭 AR1，不要求实跑八卡。

## 4. AR2 / P2：第一次取消可让供应收尾永久失去 owner

**可达性：`conditional_future`。处置：`accepted`，供应启用前修；不阻塞默认离线链。**

### 三个位置，同一类问题

| 位置 | 先写下的状态 | 取消发生后 |
| --- | --- | --- |
| `pkg_index_gateway.py:345–357` | `releasing=True`，随后 await 在途请求 | 此后 release 总是返回 None，token 留在表中，拿不到终态摘要 |
| `manager.py:3448–3449` | 正常阶段先把 `record.supply_token` 清空，再 await release | finally 没有 token 句柄可重试；容器和网络虽收回，token 仍留在网关 |
| `manager.py:2164–2189` | finally 先设 `supply_released=True`、清 token，再 await release / 拆网 | 一次取消可跳过剩余收尾；`gc():2208` 跳过已删除容器；E4a `2523–2554` 又允许裁剪这条记录 |

不变量是：**完成标志只能代表完成；尚未回收的资源要保留责任方或明确的失败事实。** 容器已删除不等于它的 token、独立网络和子网槽位都释放了。

### 主审复现与正控

- 真实 localhost HTTP：取消 release owner 后，在途下载已经被截断；token `withdrawn`、`releasing=True`、inflight=0，重试 release 仍为 None，签发表留 1 条。普通正控正常移除 token，摘要记录 5 个已转发字节。[证据](main_gateway_relay_probe.json)。
- 实际 manager + 实际 gateway、Docker 替身：正常评分与安装超时正控都清到 0；正常 release 处取消留下 1 token；超时后的 finally release 处取消留下 **1 token / 1 网络 / 1 子网槽位**。随后 `close()` 无重试，报告无容器残留、无清理失败。[探针](tracer_supply_cancel_probe.py)、[结果](tracer_supply_cancel_probe.json)。
- 独立反例把首次取消放在正常评分之后的网络 teardown：token 已释放、容器已删除，但网络和子网槽位各留 1；close 仍给空失败清单。[探针](falsifier_supply_cleanup.py)、[结果](falsifier_supply_cleanup.json)。

主审已独立复跑后两份探针（`main_replay_tracer.log`、`main_replay_falsifier.log`）。替身只控制 Docker 返回与暂停点；另在真实 gateway 的 inflight 中注入一条延迟结束任务，确定性命中取消窗口。它们不是全链真实 Docker 故障实验。正常两段 Docker 用例另行通过。

### 影响、修法与停止条件

`bringup.py:1472–1477` 当前没有注入 supply，只有显式 `GradingManagerConfig.supply` 的组件调用可走这些分支。因此本轮没有证明正式作业已经泄漏。token 已撤销，新请求仍拒绝；容器已删除，不能描述为候选继续联网或奖励被污染。真实风险是长 run 的资源/内存积累与“看似清理完成”的误报，发生频率未知。

最小改法是让既有有界收尾在取消下完成，或保留尚未释放的句柄并明确报告失败；release 中断不能永久锁住状态，token 收尾失败不能跳过网络收尾，record 退役/close 不能忽略未完成的供应资源。取消仍应传播，不新增通用恢复平台、无限重试或新的样本拒绝规则。

关闭条件就是上述三个取消位置与正常、安装超时正控：最终资源为 0，或存在可回收 owner 和明确未完成事实；重复 close/release 不假称完成。修后只对照这些反例，不以新一轮全库测试替代边界证据。

## 5. O1：finally 才补的供应摘要没有进入已写出的 sidecar

**P2 观测尾项，`conditional_future`；`deferred_with_owner_and_gate`：A 随 AR2 修，供应启用前核对。** 不另阻塞默认路径。

`manager.py:2076–2077/2114–2115` 写诊断文件，`2130` 之后才做容器与供应收尾。普通安装超时正控中，record 在 finally 里取得了 gateway 摘要，但落盘 `*.diagnostics.json` 的 supply 块没有；网络 teardown 的最终事实同样晚于写文件。这和网络 Brief §13.3 的全终点事实表述不完全一致。

这是实际落盘缺项，不是奖励判定错误。修 AR2 时复用现有 sidecar 出口补足最终事实即可；不要建立另一套日志协议。验收读取落盘文件核对正常、提前结束、超时/取消路径，区分摘要已完成、未收齐和根本没有签发 token。

## 6. 验证范围

主审从 `rh2/` 跑以下聚焦集合，**127 passed in 20.77s，无跳过**：

```bash
PIP_EXTRA_INDEX_URL='' .venv/bin/pytest -q \
  tests/adapters/test_pkg_index_gateway.py \
  tests/adapters/test_supply_relay.py \
  tests/adapters/test_patch_export_path_names.py \
  tests/adapters/test_e2a_batched_census.py \
  tests/grading/test_e2b_grader_trusted_root_exec.py \
  tests/grading/test_e4a_history_and_cr1.py \
  tests/adapters/test_supply_two_exec_renderer.py \
  tests/grading/test_supply_two_stage_manager.py \
  tests/grading/test_supply_two_stage_docker.py \
  tests/contracts/test_sandbox.py
```

包括本机真实 Docker 的批量/回退差分与两段安装交接。包源是 localhost 假上游；没有复跑作者的公共 PyPI/devpi 冒烟、216 题、真实 CC、双 lane、全库或 GPU。E2a 未重做性能测量，不据本轮测试给吞吐改善数字。

被审生产文件的 ruff 检查通过；生产源码与维护测试无未提交 diff。同步的状态 HTML 已在浏览器检查桌面与 390px 窄屏（页面无横向溢出），键盘展开/收起正常，11 个本地链接目标存在；临时预览服务和标签页已关闭。

遵照审查标准 §10.4，本次新增网络 owner 边界使用一对 Production Tracer 与 Falsifier；主审独立复跑、合并为 AR2，未按子报告数量重复列问题。[Tracer 记录](tracer_findings.md) 保留追踪边界。子审的 23 / 19 项 CPU 测试与主审集合重叠，**不累加为更多独立覆盖**。

探针复跑（仓库根；`$R` 是本目录的相对路径）：

```bash
R=docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch6_efficiency_20260921/review_a_remainder_20260928
PYTHONPATH=rh2/src rh2/.venv/bin/python "$R/main_gateway_relay_probe.py"
PYTHONPATH=rh2/src rh2/.venv/bin/python "$R/main_egress_collision.py"
rh2/.venv/bin/python "$R/tracer_supply_cancel_probe.py"
PYTHONPATH=rh2/src:rh2/tests:rh2/tests/grading rh2/.venv/bin/python "$R/falsifier_supply_cleanup.py"
```

这些脚本断言的是本轮缺陷仍可复现；修后需更新审查副本的预期，不能把“旧探针断言失败”直接当修复失败。

## 7. 当前排程

1. Claude 修 AR1；A 可继续其余已授权的本地工作，B 离线环境处理无需等整个网络功能。
2. AR2/O1 和既有 A-B1 接线一起进入供应启用前的收口清单；仍采用已批 1A+2A，不新增审批。
3. A-C1 在 B 下次 x86 CPU 作业时复用机器对账，A-C2 在接线和题级政策就绪后验证。
4. GPU 作业仍按 I18 与运行方案安排。本轮两个局部修复不需要租 GPU，也不改变正式训练语义。

本轮审查到此停止。没有新证据，不扩展到网络平台重设计、B 数据资格重审或默认全库压力测试。
