# 单卡探针部署与接入

开始：2026-10-02，Asia/Singapore。用户已交付新GPU机并授权本线程配置、接入和执行。当前执行原件统一写入 `runs/ordinary_gpu_probe_20261002/`，连接信息只放该目录的忽略文件。

## 当前实查

**10月3日新进展：SWE和R2E各一条新模型候选已完成原FrozenPatch直评及清理。** Moto5134 Coder a3为原评分1（2项F2P、12项P2P，实际选定pytest共17项通过）；NumPy18b7 Coder a1为原评分0（11个期望状态匹配10个）。两条都通过完整基线重建，旧a2仍保留infra/无有效成绩。255份已结束证据共152,278,132字节已远端/本地逐SHA核对。评分接缝通过与题目语义正确性分开：Moto候选新发现混合过滤列表回归，CPU已确认，暂不宣布题目或候选合格；NumPy的`p != None`漏修在公开模型轨迹和正式失败中一致。各自完整独立审阅在`runs/ordinary_gpu_probe_20261002/reviews/`。

Qwen3.6已完成BF16单卡加载，实际196608窗口、单请求，KV容量531804 tokens；真实thinking/工具消息往返成功。130038 token输入配65536输出上限、195538 token输入配1024输出上限均返回成功，210010 token输入被400拒绝；这不证明生成满65536 tokens或所有长负载稳定。独立真实CC压缩恢复检查已通过：一次400后摘要、继续真实Bash并退出0，清理正常；这是32K机制验收，与196K长输入证据分开。非作者已复核，没有新增运行阻塞。新接收的Pillow2d01、aiohttp4075仍由原题主持有，先核材料/构建，再进入同一串行队列，不等待整仓完成。

已通过SSH和免密sudo进入x86_64虚拟机。实际GPU是 RTX PRO 6000 Blackwell Server Edition，显存97,887 MiB；驱动580.173.02，宿主显示CUDA兼容上限13.0。24逻辑CPU、约214GiB内存，Ubuntu24.04.5、内核6.11.0-1016-nvidia、Docker29.8.0、overlay2及cgroup v2，metacopy=N。NVIDIA容器运行时已配置，真实容器内 `nvidia-smi` 成功；初查没有运行中的模型或题目容器。

**外挂卷已于2026-10-03 00:36 SGT挂载并验证。** 这台实际为Spheron ES，共享卷使用virtiofs；初查只看块设备/NFS不足，不能据此推断未attach。启动日志已包含virtio2，`/sys/fs/virtiofs/2/tag`实际为volume1，按官方供应商说明挂到`/mnt/volume1`后显示1000GiB。4096字节写入、fsync、读回通过，fstab加入`rw,nofail`并校验，未重建卷、未重启VM。在用模型和Docker暂保留本地ext4；模型缓存和证据后续有序迁移，已运行工件路径不热换。证据：`runs/ordinary_gpu_probe_20261002/remote/bootstrap/volume_mount_20261003.json`；[官方挂载说明](https://docs.spheron.ai/connecting/volume-mounting/spheron-es)。

已按冻结 `uv.lock` 安装RH2评分运行环境（不装无关dev组）。复用先前成功的SGLang镜像 `lmsysorg/sglang@sha256:06e4f2ed21afde4ff513cda65070124e727ba23ccaeff7712b8c40e1097d611f`，对应历史v0.5.20，已拉取并启动。Claude Code继续固定2.1.205，通过npm发布的integrity核验后使用，不顺便升级。

## 2026-10-03 00:06 SGT 验收进度

Coder固定HF revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120` 已下载并逐文件SHA归档，约61.08GB。BF16服务使用196608上下文、单请求、静态显存比例0.90；实际分配303543 token的KV缓存，GPU驻留约89,933MiB。此为新部署参数，不冒称与首轮服务argv完全相同。

真实GPU完成两轮工具消息往返：工具调用解析正确、返回内容被下一轮使用；首请求输出上限65536。真实token计数210009的请求得到既有共享逻辑产生的400溢出响应。原件在 `runs/ordinary_gpu_probe_20261002/remote/validation_v1/gpu_smoke/`。这证明adapter消息往返及400，工具结果由夹具提供，正式CC工具执行和压缩恢复仍另验。

首波Moto5134 actor/grader与NumPy18b7 R2E派生镜像均构建成功，实际新ID写入远端 `config_v1/identities.json`，不用历史ID代填。Moto四个兼容wheel与旧SHA逐字一致；NumPy消费当前摄入和修订，hidden tree摘要一致。新独立入口的本地11项检查及队列8项窄检查通过，远端Moto输入核对也通过；这些都不代替非空候选直评验收。

## 本次接入与运行边界

- 用户确认的题目持续负责人、两款BF16模型、首轮次数及受托宽预算，以[统一约定](gpu_coordination_decisions_20261002.md)为准。
- 本线程唯一远端执行者。两位 `gpt-6.1-sol/high` 子agent分别负责实验入口接入、首波材料与历史部署核对；均不操作远端或运行模型。
- 新入口复用正式actor隔离、解释器激活、五工具和冻结收尾；评分直接消费原actor的baseline与FrozenPatch。宿主diff作为审阅附件，不再靠fresh replay重新导出替代直评验收。
- 公开说明只交付当前有效、经题主确认的中性开发指引；隐藏测试、gold及私有调查材料不进入solver。
- 先冻结代码与输入，完成SWE/R2E非空往返和模型工具、上下文恢复检查，再逐题串行运行。既有CPU实验按适用范围复用，不统一重跑。
- 通用测试控制保护仍按用户决定延后。已知失真的原评分与语义审计分列，不能转成训练资格或普通正确率。

## 正式CC校准与开始求解

宿主评分venv补装锁定Torch 2.13.0的CPU构建，SGLang引擎容器保持2.13.0+cu130。排空使用已有 `RH2_PROBE_GATEWAY_CONTROL_URL` 指向宿主docker0；没有扩成公网监听。第一次合成校准在CC发起模型请求前因缺依赖退出，排空地址也失配，清理已确认；证据保留，不计题目尝试。

32K旁路的六段大输出压力测试出现4次400，前三次各完成摘要和工具继续，随后触发CC的反复压缩保护；exit1且is_error=true，不能用subtype=success记通过。窄验收改为两段大输出后完成标记：实际53368 token超窗→摘要29801 token（生成997）→新的普通请求与Bash标记→exit0/is_error=false，日志、会话排空和清理均完整。非作者reviewer已核原件。两条证据分别保留在live_c2_a2/a3，不把失败压力测试重写为通过，也不将窄32K恢复称196K触顶或训练capture验收。

Moto首派在模型调用前因`queue.py`遮蔽标准库而归档失败，清理成功；原`code_v1/queue_v1`保留为infra，不记模型0。队列改名`serial_dispatch.py`，12项本地检查及远端全新Python进程线程池回归通过，非作者复核无新增阻塞。新`code_v2`仅作这一改名及回归增量，服务包装源字节不变；`queue_v3`于00:31 SGT重新派发Moto5134，实际正常196K/64K/240回合/3小时配置。完整结束、非空原FrozenPatch直评和逐题语义审阅仍待返回，下一条为NumPy18b7。远端准备脚本缺pytest时的停止与空队列也保留，不算模型尝试。原评分、候选行为和用途验收分开报告。

**已知等待限制：**网关与CC HTTP等待设置1800秒，但现有adapter到SGLang仍是900秒无数据等待。不能称全链1800；若长prefill或长响应因此中断，按infra处理，不能记模型0。本次Coder短请求未触及该限制。部署成功、消息验证、直评与题目最终验收分别记账。


## 00:48 SGT 首条模型返回与恢复

Moto5134 Coder a2真实求解155.135秒、CC退出0、43个CC回合，原非空FrozenPatch已保全。首请求实际65536输出上限，五工具；模型自然结束，没有预算截断。尚未评分：Docker在收到task-delete后删除actor/relay延迟，原cleanup=false导致入口停止，队列attention保持原状。现场kernel/journal/进程/容器证据已保存；之后确认两个容器和原网络不存在，两次窄生命周期检查约0.47/0.46秒均正常。根因仍未确定，不将其归因于内存、共享卷或模型；删除开始早于卷挂载。恢复只补原候选的直评，原失败与清理异常不回写、不重新求解。

Qwen3.6固定revision权重已下载并逐文件SHA归档，71.93GB；尚未启动或GPU验收。模型/镜像仍暂存系统盘（约63GiB剩余），卷已可用，迁移将在无在途文件依赖时进行。共享卷已有一份小证据快照，未把模型/本地Docker正在使用的路径热迁移。

## 01:04 SGT 原工件评分的窄阻塞

`recovery_moto_a2_grade_v1` 在全新输出目录复用原冻结补丁，原件摘要前后相同。模型、公开提示、补丁和原清理失败记录均未改写。评分在基线重建阶段拒绝，尚未开始安装或验收测试，因此没有有效的0/1成绩；评分容器1次创建、1次移除，manager两层收口为空，无残留。

实际比较发现：1613个评分文件的路径、类型、模式和内容摘要全部一致；24条排除区路径仅有`.git/objects/pack/`下的`.idx`和`.pack`文件名不同，造成`excluded_census_digest`及整个manifest摘要不同。共享Git清理脚本已包含在两侧；执行环境差异与repack稳定性还在用无模型的小实验定位。此时不放宽摘要校验、不生成替代baseline，也不把模型成绩补成0。后续模型派发暂停至影响范围明确，原轨迹和补丁可继续语义审阅。

原件：`runs/ordinary_gpu_probe_20261002/remote/recovery_moto_a2_grade_v1/`；当前状态：`runs/ordinary_gpu_probe_20261002/orchestration.json`。这是评分接入问题，与已经完成的volume挂载分开记录。

**01:12 SGT补查结束：**两个pristine镜像分别连续清理两次，同容器也会改变pack文件名；四次评分文件和Git对象集合都相同。28条Docker操作退出0、两个容器清理正常，非执行者已复核四份原件。已将[具体复现与修复边界](git_pack_baseline_handoff_20261003.md)通知分类二协调线程，公共初态修复前不再花GPU重复生成同类候选。不自行绕过完整摘要校验；R2E影响范围与3.6 GPU验收仍未完成。

## 01:26 SGT 公开路径补查与卷复制

Moto5134原候选的 null→Logs mock 路径在断网、UID54321、同镜像下补查通过：只提供公开示例区域，精确测试结果1 passed、退出0；原三文件字节未变，诊断容器已清理。这补上负责人审计所缺的路径证据，不改写原模型两次 NoRegionError，也不替代尚被公共 Git 初态问题阻塞的正式 grade。原件与范围见 `runs/ordinary_gpu_probe_20261002/reviews/moto5134_a2_public_path_followup.md`。

外挂卷持续可读写。Qwen3.6权重正由持久化单元 `rh2-gpu1002-copy-qwen36-volume-v1` 复制到卷并逐文件核SHA；进度以 `remote/storage_copy_qwen36_v1/status.json` 为准。原系统盘副本保留，当前模型服务路径未改，不能宣称系统盘已释放空间。完整校验前不使用卷上部分副本，不重复启动复制；后续模型验收仍可使用已核验的原副本。

## Git修复接入 code_v3，恢复两来源首波

2026-10-03。总协调派出的 `git_init_determinism` 是本修复唯一实现者，材料发布线程不是该实现者。其窄修与59项检查、非作者审查已交付。GPU机从code_v2另建code_v3，仅共享sanitize、两份生成快照和新回归测试四路径变化；生成脚本SHA与真实验收版一致，旧版本不改。部署核验初次误用系统Python缺pydantic，未启动作业；随后用固定RH2 venv完成全部源摘要和生成脚本回读。

GPU机实际Moto actor/grader派生镜像各两轮准备，四份完整manifest一致，1613评分条目不变，两个诊断容器清理正常。复用原诊断脚本及明确的诊断身份，未生成供旧候选改绑的评分基线；原a2工件前后摘要不变。

新queue_v4使用config_v4允许列表与独立services_v4网关日志，code_v3正式入口：Moto5134 Coder a3，然后NumPy18b7 Coder a1，串行运行，任一infra/清理异常停止。Moto为新版本新求解，NumPy此前从未派发；两条均按既有probe-wide-v1预算，各自原生生成新的baseline/FrozenPatch，不是旧a2恢复直评。初态检查通过尚不代表两条完整评分通过，以实际result/manager_close与独立审阅为准。

## 首波结束后的实证与题级回流

Moto a3求解276秒，实际92个CC回合／92个生成请求；网关共93条记录另含1次count_tokens，早先口头将93条称为93回合已纠正。新原工件6文件直接投影评分，安装0、测试0、完整日志17通过，无参考缺失，actor及manager清理正常。正式链独立审阅35项通过，见`reviews/moto5134_a3_formal_chain_review.md/json`。

语义审计随后发现：候选把含字符串和`exists`字典的合法过滤列表传给只处理字典的函数。原镜像同命令CPU两侧对照中，base两项通过；原候选control通过，但混合列表抛出`AttributeError`。实际源码及六文件工件摘要相同、断网、UID54321、两容器清理成功，结果见`remote/diagnostics/moto_a3_mixed_filter_v1/`。该诊断核评分文件树，不冒作额外完整baseline直评；原正式评分1不回写。下一步由本题负责人建立有效正对照并补有公开依据的窄回归验收，当前不再用GPU重复确认这个已知漏洞。

NumPy a1完整直评为10/11、testRC1，唯一失败是`p != None`返回False。模型自己的公开测试已经显示该错误，仍保留只改`__eq__`的候选；原`__ne__`对`NotImplemented`取否。这一失败有公开行为支持，不记作基础设施错误或预算截断。独立原件复核继续核完整材料身份和轨迹，不因单个失败推广到模型能力排名。

两条完成后才停止Coder服务并保留可恢复容器/配置，切换Qwen3.6。首次transport准备脚本误读新版server_info为嵌套server_args，在启动adapter前停止；独立v2读取实际顶层字段后继续，原脚本与记录保留。这是部署脚本错误，不是模型失败。新工具、长prefill和溢出证据位于`remote/validation_v2/qwen36_smoke_v1/`。

## 02:16 SGT Qwen3.6 首波启动

`queue_v5`已由持久化单元开始串行处理NumPy18b7、Pillow2d01，仍使用code_v3及probe-wide-v1。Pillow题主请求、完整材料和CPU原件已核，新GPU镜像实际构建并读回，未沿用旧CPU image ID。题目结果仍由原题主继续审计。

启动脚本v1错误地将gateway的脱敏审计封装与原config逐字比较，在dispatcher前停止；没有模型调用。v2按既有日志格式核内部脱敏config及监听/健康接口后启动，旧脚本保留，运行入口未改。校准专用32K adapter/gateway已清理；当前只用正式196K服务。

DataLad6b6请求已接收但题主确认gold仍破坏公开路径和模板query行为，主动保留不派发；由原题主窄修后另交新版本，未花GPU重复已知漏洞。aiohttp4075材料核验完成，独立准备镜像在构建；仍需读回正常actor/grader环境下C parser不可导入这一真实评分条件。

公共Git初态问题由“梳理分类二处理背景”协调单一代码实现者；本线程负责GPU复现、接入、验证及最终运行收口。SWE题级测试修订由材料发布者统一登记，本线程继续负责Moto5134这道题，避免并发修改共用类型。

## 02:26 SGT 新一轮结果与按题回流

NumPy18b7 Qwen3.6首轮求解23.472秒，正式11/11、reward1；Pillow2d01首轮49.725秒，正式60/62、reward0。两条都完成原FrozenPatch直评、完整基线核验、actor与manager收口。NumPy候选同时处理eq/ne的非poly1d操作数，正在独立语义核查；Pillow完整原件已通知其原题主继续分析。评分不是最终语义结论。260份已结束证据215,135,636字节已远端/本地SHA对齐，包含12份原同步排除的约97KB文本构建材料；大镜像/权重未回传。

aiohttp4075采用单独r069准备快照，实际新镜像9a9a39c…完整性通过；普通UID54321与54322导入均确认C扩展不可用、Python alias有效、没有设置AIOHTTP_NO_EXTENSIONS。这个窄读回不冒称完整actor自验。正式Qwen3.6首轮已进入queue_v6，原配方及136键状态映射不改，ALT2正/原gold负的题级依据保留，结果回原题主。

Moto5134原gold又经单臂私有CPU检验：mixed与控制都通过，source SHA490468fc…，真实UID54321/断网/原profile/清理正常。复用已完成base/a3，不重复求解；新D6正式0/1/0仍等待共用发布者的有界登记，不用私有预检冒充正式验收。

题主不必为原公开说明已足够的题制造新brief。本地实验入口已支持显式unchanged并通过两来源测试、非作者核查；原brief行为不变。作者两文件共17测、reviewer单文件16测，范围不同。当前code_v3保持不变，新模式需另冻结部署才生效。
