# D6 两题 actor 窄验收工具独立审查

2026-09-29。结论：**未发现阻塞执行的问题，可以按已批准范围，在六行 CPU 矩阵收口后串行执行两题。** 本报告审的是工具与实际被调生产 API；真实 CC、屏障、冻结与清理结果尚待原始运行证据复核。没有运行 Docker、远端作业、CC 或评分，没有改生产代码。

后续状态：本工具两题已实际执行，公开开发／冻结子链通过；独立跨路径初态比较发现fresh grader重建的F1阻塞，见 [actor证据审查](d6_actor_evidence_review.md)。本文的“可执行”属于当时入口审查，不能解读为最终actor评分接缝通过。

## 版本与核对范围

审查对象为 `runs/category2_repair_20260929/tools/d6_actor_acceptance_v1/actor_acceptance.py`、README、delivery manifest，以及冻结树中实际被调用的 `acceptance_startup_2.py`、driver、sandbox、baseline、quiescence、exporter、prepared/assignment 和 manager 绑定检查。

- actor 脚本 SHA-256：`96eabc4dc4d0a419c0f263c9a20bb4d97e8b5535fd4ca83dee7f6ef3b4fc9a8a`，40249 字节。
- 冻结代码清单 SHA-256：`43186d0d85f1eb4e7d28e51b92a9a2c82bf1d4ff178d785d8d4846795300460e`。
- 独立重算 delivery manifest 中四个文件的 SHA/字节数，全部匹配；再次调用清单核验函数确认冻结输入完整。
- 独立本地调用两题 `load_task`，得到材料身份分别为 `sha256:087c7e478009b03857ca0d241f04400dadbe596ef93e37843190024c0564da0b`、`sha256:8eedaba78b0b93dabfa3f2618bec38be69514907724a579c44dab8d8959de90a`。逐题错 task/public/env 回显与释放后解析共八个负例全部以对应契约原因拒绝。该检查只读实际本地 prepared，未调用容器。

按审查标准，本片重点覆盖 A/D/E/F/G/H/I/L/M/N。B 不改变训练采样或奖励；C 沿用已批准的先矩阵后 actor 次序，不新增授权闸门；J/K 在这个一次性有界工具范围内未发现需先修的问题。生产机制独立结论仍见 [实现审查](d6_implementation_review.md)，本片不重复扩大审查其他线程在制代码。

## 调用链与材料边界

1. `PreparedTaskFace.load` 验 manifest 外部摘要、private host 文件摘要与逐题环境身份；正式 mint 与 `AttemptAssignmentRegistry.bind` 将本次 attempt 绑定到 prepared 原分派。rollout spec 的 `grading_spec` 必须为空，宿主单独解析私有 grading spec。prompt 要求逐字等于公开 prepared 行。
2. 容器启动使用正式 profile、relay、网络、物化检查、可信 Git sanitize/init、prelaunch 与 activation 检查。派生镜像固定到本批已用 ID，并核父层；正式 relay 镜像按 digest 核对。profile 无宿主 bind mount。镜像缺失即停，不隐式拉取。
3. 调用的是继承的 `Runner.solve`，其实际进入 `ClaudeCodeDriver.run`，由生产 Engine API 启动真实 CC 并保存同一次 exec 的轨迹、stderr 和可信退出事实；没有复用旧 `Runner.run/collect` 的候选后 root Git 流程。
4. 三条桩命令只读公开身份、工作区源码来源和已存在的公开测试。没有给 CC gold/C1/test patch/私有 grading 文件；宿主只写公开 bundle、激活脚本和工具命令。私有材料只用于宿主侧关联。运行后的实际请求体、容器初态和命令仍须独立复核，静态审查不替代无泄漏证据。
5. 先生成 baseline，CC 返回后完整回收三份日志，再关闭桩和唯一 relay，随后生产 `DockerQuiescenceBarrier.establish` 真正执行终止 agent 进程、归零和双读 census；`export_frozen_patch` 使用同次 baseline 和注册的 execution/physical attempt 身份。工件落盘后立即删除 actor，再从磁盘重读、classify、构建 trusted projection。
6. 冻结身份与注册 assignment 逐项相等，`face.grading_spec(resolved)` 重新得到本次有效材料；manager `_verify_frozen_delta_binding` 重算工件/baseline/projection 摘要并核 task/base/workdir 与投影路径集。这是正式 manager 起容器前的纯检查，没有启动 grader。`frozen_material_join.json` 保存环境分派、材料身份和工件摘要，不能误写成 frozen 本体新增了环境摘要。

正常 imports 缺 `miles` 时，fallback 仅按冻结清单加载两个既有零依赖 leaf，并检查真实来源路径；没有伪造 miles 包或复制绑定规则。本地首题实际经过该 fallback；同进程次题复用已载入的同源模块。远端每题独立进程的实际模式须看 `input_check.json`。

## 失败、资源与证据判据

命令全文由 agent 身份读取，校验 rc、声明/实际字节数并保存 SHA；首命令失败仍继续收取其余已有输出，最终拒绝验收。命令只回显结束状态不会影响完整 `.full` 留存。CC 缺 result、流不完整、公开 case 集合不完全匹配、解释器/模块来源错、控制文件可写、屏障拒绝、冻结留下非缓存 delta，均不能获得通过状态。

异常和取消由外层捕获并保留首因，尽力取回命令输出，finally 做受保护且有总时限的清理。容器、relay、网络、桩分别收口；再按**本 run 的精确标签**查询容器和网络，查询失败与残留都计清理错误并返回非零。不会移除同台其他线程的评分容器。登记 attempt 最后释放并验证不可再解析。启动 helper 的失败回滚及最终标签复查共同覆盖句柄未返回的失败情形；清理超时明确写 `cleanup_unconfirmed`，不假报成功。

资源范围为两题串行、每题三条有时限命令。真实 CC 版本由 driver 检查，tarball SHA、镜像、profile、命令、原始轨迹、清理与文件清单都有记录。README 对源码检查、安装与奖励证据的职责划分符合当前 Brief：本工具不重复六行安装/奖励矩阵。

## 适用边界与剩余项

没有本片必修 finding。以下是结果使用边界，不是新增阻塞或建议加字段：

- `session_plane_drained` 只由这个独立直连桩的关闭事实支持；没有训练 capture、队列或完整 orchestrator drain receipt。不能据此宣称 miles 训练端到端通过。
- 固定公开命令的输出和源码摘要足以验本窄场景，不是对任意恶意候选的证明。
- 工具自身退出 0 仍须独立核真实 CC 轨迹、三份全文、baseline/frozen、注册材料关联和本 run 最终清理；不能替代六行评分复核。
- 真实结果到齐后补到独立证据报告，旧失败原件保持。两题转类仍按题级验收结论处理，不自动授予训练资格。
