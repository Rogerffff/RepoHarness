# 实现边界与验收口径

整理日期：2026-10-04。代码父版是实际 GPU 作业的 `frozen_code_v8` 文件快照，记录的 Git HEAD 为 `a31cdcd0adb0fab3e681201edfb928653fdf5b3c`；两者不能混为一谈。发布时按文件摘要核对，不在共享脏树上直接套补丁。

## 分段计时与预制环境

性能诊断默认关闭。开启后记录宿主单调时钟区间、四段权限开销、安装与测试事实；排队时间单独计算。嵌套区间不相加，未开始或中断的区间不伪填零。可选计时读回的普通运输／解析失败只记 `permission_readback_error`，不改变评分或覆盖原保护步骤的错误；取消等 BaseException 仍传播。最终诊断在清理后原子写入旁路 JSON；已经形成 `ArtifactRef` 的原始评测日志不再改写。

权限模板从不可变源镜像创建，绑定 grader profile 和准备配方摘要。它只准备固定解释器前缀、可选仓库属主及明确列出的第三方依赖。每次评分仍创建新容器和可写层，运行原 Git 清理、完整基线核对、FrozenPatch 重放、官方测试写入与保护。预制时不执行候选、不植入私有测试、不缓存候选编译结果。

运行期仍遍历需交权的树，只对属主／组不匹配或带 setuid/setgid 的项执行物理 `chown -h`。新增文件、硬链接和软链接本身仍受处理；不沿软链接修改外部目标。官方文件最后恢复 root:root 0644，每级祖先目录恢复 root:root 1777，并执行原有完整自证。GNU 实机权限反控同时比较完整 chown 和条件 chown；修改、删除官方文件和替换其祖先目录均应失败，候选新文件和缓存仍可写。

派生镜像改变环境身份。旧镜像的资格凭据不能直接搬用。Pandas 的第三方依赖模板另跑新空补丁资格检查，并绑定新镜像、同一评分脚本与评分材料；原候选的 FrozenPatch 字节不因此改变。资格检查不是候选正确性的证明。

## 原容器评分

有两种不同证据，必须区分：

1. 固定成果 CPU 原型：manager 自建 grader profile 容器，先封存，再用原 FrozenPatch 模拟 solve 污染。
2. 默认关闭的真实调用链接口：`RH2_GRADING_ORIGINAL_CONTAINER=1` 接入 `bringup → generate → GradingQueue`。在实际 rollout 基线生成及激活检查之后、harness 启动之前封存；此时不要求尚未产生的 FrozenPatch。

真实接口只采用 actor 与 grader 的实际 OCI config ID 相同、资源限制一致、工作目录受支持的容器。原 actor 的 HOME tmpfs 如实进入复用 profile；grader HOME 保持独立目录。profile 摘要因此不同，不能冒充旧 fresh profile。镜像或实际 profile 不兼容、两个复用名额已满时直接走原 fresh 路径，不占用 episode 预算等待复用名额。

采用时在同一 event loop 同步登记删除所有权，随后由 grading manager 独占容器删除。外层 finally 委托同一个 owner，确认删除后再处理原 attempt 网络。提交者取消时，`submit_owned` 等待 worker 完成有界收口；队列强停同时终结执行中、队列中和反压等待中的请求。评分前早退时，无法证明容器停止也必须传播 run-fatal，不能只记普通清理失败。

artifact 持久化、hygiene 分类和可信投影均保留。评分提交时核对 physical attempt、基线摘要和冻结摘要。活文件树从来不是评分输入：先撤网并确认实际网络列表为空，停止 actor 的全部进程并确认归零，核对固定环境内容与权限，校验 root 私有封存摘要，恢复整个工作树和 Git 状态，清空 actor HOME 与临时目录，再运行原完整基线核对和 FrozenPatch 重放。grader 的真实身份、能力、资源和无路由探针仍执行。

候选改写固定环境时，原容器关闭后仅尝试一次 fresh 评分，使用同一个 FrozenPatch、同一个绝对期限、原 fresh profile 和停止谓词。这个分支不复用受污染的解释器。期限耗尽时不再创建容器；停止／基线完整性失败保留既有致命语义。

CPU 接缝探针使用真实 rollout profile、独立 internal 网络、真实撤网和 GradingQueue，但 solve 仍是固定成果夹具，没有真实 Claude Code 或 GPU 模型调用。它不能替代正式 rollout 验收；开关在交付中保持默认关闭。

## 构建结果不能只靠文件清理推断

三个原候选都只改 Python 文件。因此逐测试状态一致不能证明任意 C/C++ 等编译型补丁都已正确重建。

另设独立 Coverage CTracer 反控：修改真实 C 源码的可观察文本，把源码 mtime 设得比已有扩展更旧；旧加载模块不能呈现新文本；强制构建后必须加载另一 SHA 的模块并呈现新文本。它证明“删缓存”和“加载最终源码生成的二进制”是两件需要分别核实的事。该反控不改原 FrozenPatch，也不宣称原官方脚本已普遍强制重编译。编译型任务在推广前仍需按实际配方建立这类证据。

## Prime 后端

实现按固定版本的原生 SDK 接口核对，覆盖创建、就绪、命令、文件传输、资源／网络核对、日志取回和删除确认；不伪造 Docker inspect。SDK 依据为官方仓库 commit `3c7f8bf88df0b0da6c79d0992206cf5fabcf6888`。已在本任务独立环境安装该 commit 对应的 `prime-sandboxes 0.4.2`，锁定本地依赖，用真实 SDK 请求序列化、响应模型和 HTTP MockTransport 验证创建／资源／网络字段及删除后的 404 确认；403 保留未删除状态。配置读取被限定在测试目录，网络连接被禁止；就绪与 guest 通路仍是模拟或未测。该结果不代替线上 SDK 环境及服务验证。镜像引用要求不可变 registry digest，并另记录来源镜像和归档摘要。

创建前登记幂等 key；创建结果未知时保留状态并停止新增资源。新调用进入时和已排队请求取得并发槽后都检查未知状态，后者不再绕过守卫发出请求。删除 API 返回不等于已清理，必须确认对应自有 ID 已终止或结构化 404。权限错误不当作已删除。只处理本实例登记的精确 ID，不做全账户清扫。账户文件显式传入，拒绝隐含 endpoint／team／user 覆盖。

VM 与 Docker profile 不能视为等价。候选使用固定非 root UID、无 capabilities、no-new-privileges 和每 UID 进程限制，另核 VM CPU／内存／磁盘、swap 和服务商实际断网策略；这些事实明确记录为 `docker_profile_equivalence=False`。启动 shell 前固定 BASH_ENV/ENV，清空预加载变量；真实目标镜像的动态库兼容性仍待线上资格验证。

截至本记录，未创建付费 Prime 资源。账户私有 key 文件、费用范围尚未收到；目标镜像上传／转换、实际 guest 行为、线上 gold/noop、日志和删除完整链都未验证。官方 SDK 的私有镜像接口是 Dockerfile 构建上下文上传或受支持的 registry 来源转换，不能把本地 `docker save` 包直接当作已完成的 Prime 上传。本片的静态绑定接口与本地测试不代替真实镜像发布回执。

参考：[Prime Sandboxes](https://docs.primeintellect.ai/sandboxes/overview)、[固定版 SDK 镜像接口](https://github.com/PrimeIntellect-ai/prime/blob/3c7f8bf88df0b0da6c79d0992206cf5fabcf6888/packages/prime-sandboxes/src/prime_sandboxes/images.py)。

## 验证与发布边界

所有 CPU 作业沿用公共 `cpu_slot`：每机最多两个评分／准备作业，准备最多一个且也计入总槽。吞吐协调器自身不运行 Docker，每个评分子进程分别持有一个公共槽，不能以一个作业名隐藏多个容器。原评分预算、资源、官方脚本、逐测试判定均保留。

交付为冻结父版上的可审查补丁、逐文件前后摘要和测试／CPU 证据。共享源码、正在运行的 GPU 默认配置、题主账本和历史 evidence 不原位回写。EA69 的原分只用于性能同输入对照，其既有语义争议不因本次结果一致而消失。
