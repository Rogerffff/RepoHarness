# Conan 13403 GNU baseline actor：非作者运行证据审查

日期：2026-10-03。角色：Production Tracer。结论：**当前 v3 开发诊断具有可解释的真实 Claude Code、agent UID、testbed Python 和 GNU CLI 执行证据；本切片未发现需要重跑的执行阻塞。它只支持开发基线诊断，不证明完整 solver、修复实现、正式 CPU 评分或训练资格。**

## 上下文与范围

本审查由主线程指定，配置为 `gpt-6.1-sol/high`，来源是本次 spawn 明确指定，非继承。审查者未编写被审查脚本或原件；获得的上下文包括项目 AGENTS.md、当前任务范围和具体证据路径，未获得预设修复方案。遵循 [review-standards.md §10.4/10.5](../../../../../review-standards.md) 与 [当前协作流程](../../../coordination_workflow_20261003.md)。此报告是该批次 Production Tracer 的子报告，主审查者仍应独立核对关键证据并综合另一角色的反证结论。

只读取本地原件，不访问远端，不运行容器、实验或旧测试，不修改材料、runner 或共用账本。唯一写入是本报告。另读当前 `devcheck.py` 了解返回码和截尾机制；当前源码不当作远端冻结源码的独立身份凭据，其行为以轨迹中的实际 Bash wrapper、capture 和 attempt 交叉核实。

证据根为 `runs/category2_repair_20260929/conan_cpu_20261003/`。下文 V3/V2/IMAGE 分别指：

- `baseline_actor_13403_r5_gnu_v3_evidence/baseline_actor_13403_r5_gnu_v3/`
- `baseline_actor_13403_r5_gnu_v2_evidence/baseline_actor_13403_r5_gnu_v2/`
- `image_prepare_13403_gnu_v2_evidence/image_prepare_13403_gnu_v2/`

对应 `*_audit.json` 的作者结论只用于对照，事实依据为执行脚本、rc、原始 stdout、Docker inspect/receipt、轨迹及请求。remote_audit 是运输校验清单，不是第三方签名或主机真实性认证。

## 已核事实与可达性

| 事实 | 原件依据与范围 | 可达性 |
| --- | --- | --- |
| SHA/大小运输一致 | 按三个 remote_audit 的 `files` 在本地逐文件重算：V3 34/34、V2 52/52、IMAGE 17/17 全匹配，无额外文件；合计 103 个登记文件。 | 开发证据事实 |
| 第五版可信读回与 fresh prepare | V3 `run_actor.py:14–23` 在启动前逐成员检查普通非 symlink 文件、SHA 和大小，并断言 837 成员；manifest SHA 为 `80ee228d…ed42f9`。`release_verify.rc.json` 返回 0，stdout 记录 `checksummed_files=837`。`preflight.json` 记录通过及派生 image ID；`prepare.rc.json` 返回 0，prepare argv 指向独立 V3 目录，manifest 时间为 `2026-10-02T20:44:17.409026Z`。 | `test_only`：本次实际开发入口执行 |
| prepare 身份相连 | V3 summary SHA `e4ac5fd7…55df05`、prepared manifest SHA `10b80977…76899` 均重算匹配；manifest 中 prompts/rollout SHA 匹配文件。V3 的 prompts、rollout views、private host grading 与 V2 字节相同，但 summary、时间和输出目录独立。 | 开发消费事实；并非 solver 题面交付证明 |
| 真 CC 与 actor 身份 | V3 CC observed 文件及轨迹第 1 行共同记录 `2.1.205`；轨迹实际 Bash identity 返回 UID 54321、Python `/opt/miniconda3/envs/testbed/bin/python`、3.10.14、Conan 2.1.0-dev，并从 `/testbed/conan` 和 `/testbed/conans` 导入；HEAD `55163679ad1fa933f671ddf186e53b92bf39bbdb`，STATUS 空。activation/prelaunch 亦给同解释器和 UID。 | `test_only`：真实 CC 工具执行实测；桩模型 |
| 当前调用链 | 已存 `run_actor.py` → 第五版 `replay_grade.py prepare` → `devcheck.py --image sha256:b408…ff4ff` → CC 2.1.205 → 预设两次 Bash → testbed Python → `subprocess` GNU/Conan CLI。两个 tool_use input 与已存 stub_script 一致。 | `test_only`；不能标成完整生产求解实测 |
| 真实 GNU | capture 记录 `/usr/bin/autoreconf` / `autoconf` 2.71、`automake` 1.16.5。命令脚本直接在含 `configure.ac` 的 build 目录调用 GNU，rc=0，并断言生成 configure；随后 Conan install rc=0。带显式 host/build profile 的 Conan build 到达 `Calling build()` 和 `RUN: autoreconf --force --install`，GNU 报 `'configure.ac' is required`，CLI rc=1。 | `test_only`：当前开发路径观测到原缺陷表现 |
| 轨迹及输出 | V3 原轨迹 30 行、26055 字节，全部可解析，2 次 Bash、3 个 message_start、3 次请求、最终 success result；请求中的 tool_use_id/content/is_error 与对应轨迹 tool_result 一致，仅请求新增 cache_control 元数据。harness stderr 为空，attempt 记录 exec exited、log_complete、无 stream_error。 | 只证明此次正常返回的完整事件流 |
| 清理 | V3/V2 attempt 均记录 container_rm=0、网络/relay 失败空、stub_rc=0、标签容器/网络残留空、residual_after_force 空；post_run 记录 agent 进程 0、git status 行数 0。V2 identity 的两个容器各 rm/query=0 且 remaining 空。IMAGE downloader 与最终标签查询也返回 0、无残留；build log 记录移除 intermediate container。 | `test_only`：正常收口已观测；未覆盖取消/崩溃清理 |

第五版读回结论限于已保存脚本的强制检查、成功 supervisor 状态及 readback 原始输出；指定三组证据没有完整 837 成员 release 树或 manifest 原件，因此本审查**未在本机独立逐成员复算第五版 release**。已保存原件足以解释本次启动前如何 fail-stop，不把它扩大成当前部署或所有 release 的独立验收。

## 逐命令判定

| 层级/命令 | 实际返回码 | 解释 |
| --- | --- | --- |
| V3 identity wrapper | 0 | 身份断言完成；capture 326 字节。 |
| V3 public_gnu_cli wrapper | 0 | 验证脚本的预期包含 build 返回 1；capture 3118 字节。 |
| 直接 `autoreconf -f -i` | 0 | build 目录里的 GNU 正对照成功。 |
| `python -m conans.conan install . -pr:h native-profile -pr:b native-profile` | 0 | profile、依赖图和生成器完成。 |
| `python -m conans.conan build . -pr:h native-profile -pr:b native-profile` | 1 | 到达 Autotools.autoreconf 及真实 GNU；原缺陷表现被诊断脚本接受。 |
| V3 harness / stage / supervisor | 0 / 0 / 0 | CC/诊断/编排正常完成；不是题目评分 0/1。 |

原始输出与脚本共同支持“build-folder 场景未按用户所需位置处理”的诊断：同一临时项目 build 目录有 configure.ac，直接 GNU 成功，而 Conan build 的 Autotools 调用失败。没有 syscall/cwd 探针，故不声称原件直接打印了内部 autoreconf 进程的工作目录。输出证明了目标调用已到达，具体内部 cwd 由场景与已知调用行为推断。

V2 的 GNU/安装成功后，`build .` 漏 profile，报 default build profile 缺失，随后脚本 AssertionError，wrapper rc=1；V2 **未到达目标 autoreconf**。V3 只修复公开诊断的 profile 参数并复验两条命令，不改候选源码。V2 原公开 `test_source_folder_works` 的 1 passed/0.22s 仍以原件保留；V3 不重复，也不把它计成额外通过。旧 v1 缺工具仍保留为历史失败，本次未重核或重跑。

## 镜像、source/Python 复用边界

IMAGE 的 Dockerfile 只有固定 base、复制 deb、离线 dpkg 安装及删除 deb。build log 和 receipt 对应五个包：autoconf 2.71-2、automake 1:1.16.5-1.3、autotools-dev 20220109.1、libsigsegv2 2.13-1ubuntu3、m4 1.4.18-5ubuntu2。base config ID `sha256:dffa4bbc…7c383`，derived config ID `sha256:b40849e1…ff4ff`，V2/V3 plan、preflight、container inspect 和 IMAGE receipt 一致。

V2 identity 原始 stdout 两边字节相同；create/inspect/exit 证明分别从上述镜像、无 mounts、network none、root UID 0、同 testbed 解释器正常完成。比较覆盖：

- 960 个 git tracked 文件内容聚合 SHA：`ea1a479dc6dd1d0dd3518f775e96c3ab97108b34766f6de99b8ffdd970768e98`。
- `pip freeze --all` 聚合 SHA：`db12cb8fcc4a16153a0c100d97788a2633ffd0e9a575d556572385d82aa2ed1d`。
- 固定 HEAD、空 porcelain、Python 路径。

这支持同一不可变 derived ID 下复用上述比较及旧公开测试。它没有逐文件证明所有 Python 安装内容、untracked/ignored 文件、OS 全树或全局权限不变；root identity 不能替代 actor UID。V3 单独身份与 activation 已补足实际 UID/解释器，未重新执行完整 960 文件比较。prepared public view 仍指原始镜像，实际执行明确使用 derived override；`formal_environment_registration=null`，因此该 override 不能自动当成正式环境身份。

## Findings、范围与仍未知

**没有当前开发切片的 P0/P1 执行阻塞。** 以下为已有边界或证据限制，均不是要求增加 runner 状态机或重跑旧测试的理由。

1. **正式准入证据缺口，`conditional_future`，对开发诊断不阻塞；若直接启用为正式求解/评分则构成 P1 gate。** 当前行为是 CC 真运行、桩按清单下发工具，首请求公开正文只有“Devcheck run: execute exactly the tool calls you are given, then stop.”，没有 issue/hints；没有源码修复或正式评分。违反的不变量只会在把诊断 success 当 solver/修复/评分成功时出现。证据为 V3 `output/stub/requests/messages_000.json:1`、`public_commands.json`、`plan.json` 与 `output/attempt.json`。影响是资格误判；建议在正式 CPU/探针请求前由题主/发布/GPU按既有流程补对应正式环境登记、公开完整输入、受影响正负对照与评分运输证据。最小本地核验是解析首请求 messages 与读取三条内部返回码；验收不能仅看外层 0。本次不新增审批闸门。

2. **host 完整输出与 actor 可见输出不同，`test_only`，P2 证据解释限制。** wrapper 先截取最多 200000 字节给 host capture，再只回显最后 1500 字节给 CC；V3 GNU capture 3118 字节与记录 output_bytes 完全一致，所以本次 host 输出未截断，但 trajectory/tool_result 没有 GNU 输出前段。文件证据为 V3 `output/stub_script.json`、轨迹第 15/21 行、`output/captures/public_gnu_cli.out`、attempt commands_result。影响仅在宣称“actor 看到了全输出”或复用为真实模型读日志测试时出现；开发诊断依靠 host 原件可验收。最小核验比较 capture 文件大小、output_bytes 与 tool_result 尾部；未来若要验证模型日志消费，应按那一目标另验输入范围。当前无需修复或扩展本轮。

3. **两项 generic marker false 保留，`test_only`，非当前身份失败。** attempt 的 `interpreter_in_tool_result=false` 和 `bashenv_denied_for_agent=false` 没有被默默改成 true。identity 实际 tool_result 明确报告正确解释器；prelaunch 明确 activation 可读、不可写、root:644。这只支持本切片身份和激活文件写保护，不能外推“agent 所有环境路径不可读/所有权限检查通过”。最小核验读轨迹第 10 行与 prelaunch probe_facts；建议保持原值及其范围说明，不据 generic false 强制重跑。

清理结论只限原件所记标签与正常结束时点；本次未独立查询现场，未测试 SIGTERM、OOM、日志断流或孤儿进程异常分支。文件 SHA 一致证明传输一致性，不消除证据产生主机自身被篡改的理论风险；本任务没有要求另建认证机制。

## 停止条件与推荐

本轮停止条件已满足：真实 CC/UID/解释器、fresh prepare 与第五版启动前读回、GNU 正对照及原缺陷调用、逐命令结果、轨迹/输出边界和正常清理均有相互对应的原件。推荐使用该证据进入下一段题级修复与正式验收准备；仍未知内容按上述 gate 保留。没有依据要求重新跑 V2 已过公开测试、扫描全部 cloud41 候选、新平台或重构统一 runner。

## 固定审查输入 SHA-256

| 文件（证据根相对路径） | SHA-256 |
| --- | --- |
| baseline_actor_13403_r5_gnu_v3_remote_audit.json | eb6f50814aa75d13691238975e1a532d346c57a5386078cd06e5f00d24ed62eb |
| baseline_actor_13403_r5_gnu_v3_audit.json | cabe6bbf21a1f7eb2caf313aa7efbfe3b3dd23ff097a37ae8caabe43a1867dd2 |
| baseline_actor_13403_r5_gnu_v2_remote_audit.json | c148ee86735dd64fe1221599ecdcbfc64e597dd41d99886eab07c8b5f0b32b5f |
| baseline_actor_13403_r5_gnu_v2_audit.json | d66b4626b92bc8d9b6153f9d785db14866f3a28d386e13809ae1c47e3c1cdfad |
| image_prepare_13403_gnu_v2_remote_audit.json | ace43db1e7444d4f01c4476e1988344a11725b8826163164265bc7b182ff7218 |
| image_prepare_13403_gnu_v2_audit.json | d2635c02d9d214c38aece1615ed434b77de03626eca5b274453d81e09693b6df |

