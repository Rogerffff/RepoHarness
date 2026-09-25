# Brief：受控 Python 包供应（候选政策 1A + 2A）——设计稿，未启用

2026-09-24 / Claude（A 线）。**状态：设计稿（2026-09-25 按 [Codex 复核 R4/R5 与接口清单](review_next_slices_20260924/README.md) 修订）；没有改任何运行配置、profile 默认值或生产代码。网关可先开发；grader 联网切片按修订后的 §4.2 实施。** 依据：[第六组 README §3](README.md)（最小供应结构、阶段接缝、验证清单）、[Codex 方向复核 §3–§5](codex_direction_review_20260922.md)（1A/2A 定义与三处接缝）、[README §8.3](README.md)（"写设计无需等确认，不能先把候选政策启用到运行配置"）。用户 2026-09-24 答复"依赖供应两个选择我都同意（1A+2A）"：本文按 1A+2A 写；**启用到正式作业配置仍是单独一步**，等本 Brief 审查后由用户放行。

## 0. 采用的政策（用户已选）

| 项 | 内容 | 本文落点 |
| --- | --- | --- |
| 1A | 默认不提供被测项目自身的远端发行包；本地候选 `pip install -e .` 保留；已验证配方确需某个固定发行包时逐题单列允许；第三方依赖不按题目日期截断 | §3 索引网关的逐题封禁表 + 例外表 |
| 2A | 评分保持"root 可信 setup / 官方测试注入在先"；随后候选安装段可用受控 PyPI；正式测试前撤掉出口；明确接受"私有测试已可读时仍可向供应服务发请求" | §4 grader 的接网—安装 exec—撤网核对—测试 exec 交接 |

不在本文范围（Codex §4 已列）：一般公网、GitHub、conda、apt、上传能力；原容器评分；216 题重跑；防泄漏的完整证明。

## 1. 现状事实（本文只依赖这些）

- **rollout 网络**：每个 attempt 一张 `--internal` 网络（`gateway_mode_ipv4=isolated`，地址池切子网），本 run 一个 egress relay 容器（bridge 网络、nobody、只读根、纯 TCP 转发脚本）以别名接入每张 attempt 网络；relay 监听表 = 模型代理 + `internal_services`（[`RolloutSandboxProfile.relay_listen_map`](../../../../../rh2/src/repoharness2/adapters/slime/sandbox_profile.py)，`RH2_SANDBOX_INTERNAL_SERVICES` 环境变量已有解析入口）。relay 对上游新建 TCP 连接，不带来源身份（Codex §5.1）。
- **grader 网络**：`GraderSandboxProfile.docker_run_args` 写死 `--network none`；`grading/manager.py` 的 lease `network_policy="deny_all"` → `("--network","none")`，启动前核对 `NetworkMode == "none"`。
- **评分脚本**：`_run_eval` 三段——root `trusted_setup_script`（恢复/注入官方测试）→ root `grader_protect_control_surface_script`（/testbed 交候选用户、官方测试文件 root 只读）→ 候选用户 `candidate_test_script`（**同一 shell**：安装段 `RH2_PHASE_START/END=install` + ERR trap + `RH2_INSTALL_RC` → 官方 Start/End 标记 → 测试命令 → `RH2_TEST_RC`；安装段 `export` 对测试有效，见 [`prepared_task_face.py`](../../../../../rh2/src/repoharness2/adapters/slime/prepared_task_face.py) 模块头与 Codex §5.2 的 Bash 探针）。
- **Docker 行为（本机探针，2026-09-24，`rh2/experiments/batch6_network_20260924/`）**：

| 编号 | 事实 | 对设计的意义 |
| --- | --- | --- |
| A1–A5 | 以 internal 网络启动的容器可以 `docker network disconnect` 掉最后一张网络；之后名字解析失败、按 IP 连接 `Network is unreachable`、`NetworkSettings.Networks == {}` | "撤出口"= 断开网络，可核对 |
| B1–B2 | 断开后可再次 connect 并恢复连通 | 阶段只能单向；撤网后不再 connect（§4.4） |
| C1 | `--network none` 启动的容器**不能**再 connect（daemon 拒绝：private (none) mode） | grader 若要在安装段接网，必须以 internal 网络启动，不能先 none 再接 |
| D0–D4 | 断网前已建立的 TCP 连接断网后收发超时；新连接被拒（echo 服务器验证，排除 HTTP 缓冲假象） | 安装段留下的后台进程在测试段拿不到网络 |

## 2. 组件与部署

```text
rollout 容器 ──attempt 内部网络──▶ run relay（新增监听 3141）──▶ 宿主 RH2 索引网关(:3141) ──▶ devpi-server(:3142，本机缓存) ──▶ pypi.org
grader 容器  ──grading 内部网络──▶ run 包供应 relay（只监听 3141）──┘
```

- **devpi-server**：每台训练宿主一份，自持数据目录（作业配置给路径），只作 `root/pypi` 镜像缓存，上游固定 pypi.org；版本钉在作业配置并进 run evidence。候选只经网关取包，不接触 devpi 的管理/上传接口；不给候选挂可写 pip 缓存。
- **RH2 索引网关**（新文件 `rh2/src/repoharness2/adapters/slime/pkg_index_gateway.py`，aiohttp，与 relay 同级的 run 级宿主进程）：
  - 路径 `/a/<token>/simple/<dist>/` 与 `/a/<token>/files/…`；`<token>` 由宿主为每个 attempt / 每次评分随机签发并绑定 `attempt_id / task_id / blocked_dists / phase`，注入到容器环境（`PIP_INDEX_URL`、`PIP_TRUSTED_HOST`）；未知 token → 404。这就是 Codex §5.1 要的**宿主绑定的 attempt/题目视图**：日志按 token 关联，不信任候选自报身份，候选也无法冒用别的 attempt（不知道其 token）。
  - 1A：`blocked_dists`（PEP 503 归一名）命中 → `/simple/<dist>/` 与其文件 404；例外表命中 → 放行。第三方不做日期截断。
  - 只接受 GET/HEAD；只转发归一化后的 simple 路径与文件路径，**丢弃 query string**，文件 URL 改写为经网关；这是缩小出站信息通道，不是"无出站信息"的承诺（Codex §4）。
  - 逐请求 JSONL：`ts, token→attempt_id/task_id, phase, path, dist, filename, upstream_status, bytes, elapsed`；token 进入 `withdrawn` 后一律 403（纵深；真正的隔离是网络断开）。
- **relay**：rollout 复用现有 relay，索引作为一条 `InternalService(listen 3141 → 宿主网关)`；grader 用**另一个** relay 容器（同镜像、同脚本，`RH2_RELAY_MAP` 只含 3141），不把模型代理等端口暴露给 grader（Codex §5.1）。

## 3. 1A 的逐题数据

- `blocked_dists`：被测项目自身的发行包名（来自 B 的逐题事实：派生镜像里项目的 dist-info 名 + 仓库 `setup.py`/`pyproject` 的 `name`，多名并列）；进入评分面（`PrivateGradingBundleV2` 新字段）与公开面（rollout 也封同一表）。
- `allowed_project_releases`：已验证配方确需的本项目固定发行包（当前没有已知条目；MONAI-763 的 `nibabel==4.0.2` 是第三方且来自本地 wheel 目录，1A 下不受影响）。
- 固定与动态：固定的是 B 已验证的环境配方、派生镜像、预置 wheel、devpi 版本与上游；动态的是候选新装的第三方依赖（不锁定，可两次解析不同）。**缓存不是冻结**，逐 attempt 记录实际取得与安装的版本（§5）。

## 4. 2A 的 grader 阶段交接（主要接缝）

### 4.1 网络生命周期

1. 评分前：`create_attempt_network`（复用 rollout 的子网池与取消回收）→ 包供应 relay `connect --alias pkgidx`；grader 容器改以该网络启动（新的 lease `network_policy="supply_install_then_none"`；C1 决定了不能沿用 `none` 再接）。
2. root 可信 setup / 保护控制面：照旧（root 步骤不取包）。
3. 候选脚本安装段：可达 `http://pkgidx:3141/a/<token>/simple`；其余目标无路由。
4. **撤出口**：安装 exec 结束 → `docker network disconnect` → `docker inspect` 核对 `Networks == {}` → 网关把 token 置 `withdrawn` → 核对成功后宿主才启动测试 exec（§4.2）。
5. 正式测试：无网络；结束/取消/超时按现有清理，attempt 网络与 relay 连接走既有 `reclaim_network_after_cancel` 与 label 清扫。

### 4.2 阶段交接：宿主在断网核对后才启动测试段（两次 exec，状态由候选自己携带）

Codex §5.2 已证"机械拆两次 exec"会丢 `export`；R5 又证候选 shell 里的闸门（等 root 文件）不是宿主对放行的控制——候选 `source` 自己可写的激活脚本就能改写 `[`，宿主的文件权限管不到候选 shell 的控制流。因此不再用候选 shell 守卫，改为：

1. **安装 exec**（候选 UID，脚本前半段）：安装段照旧（`RH2_PHASE_START/END=install`、ERR trap、`RH2_INSTALL_RC`），段末由 root 写的脚本尾部（不是候选命令）把可携带状态落到候选自己的目录：`export -p > "$HOME/.rh2/env.sh"`、`declare -f > "$HOME/.rh2/funcs.sh"`、`pwd > "$HOME/.rh2/cwd"`，再打 `RH2_PHASE_HANDOFF=1`。exec 结束本身就是"安装段结束"的信号，不需要 0.5 s 轮询。
2. **宿主**：记录安装 exec 的退出与输出 → `docker network disconnect` → `docker inspect` 核对 `Networks == {}` → 网关 token 置 withdrawn → **只有核对成功才启动测试 exec**。放行事实在宿主手里。
3. **测试 exec**（候选 UID，脚本后半段）：**先保留来源 renderer 的可信前导**（`_V2_ENV_LINES` 的 `#!/bin/bash` + `set -xo pipefail` + 激活 + `cd /testbed` + safe.directory；R2E 用其来源的对应前导），再恢复携带状态——`source` env 与 funcs 文件、`cd "$(cat cwd)"`（cwd 用 `cd` 恢复，不 source）——然后执行既有官方 Start/End 标记、测试命令与 `RH2_TEST_RC`。携带文件缺任一 = 安装段 shell 没走到尾部，按 §4.2.1 第一行处理。**为什么前导必须保留**（Codex NS1 探针，真实 `getmoto__moto-6913` bundle → 当前 renderer → 两段 Bash → 真实 parser）：官方标记是冒号命令 `: '>>>>> Start Test Output'`，只有 xtrace 才进日志——只带 export / function / cwd 的第二段标记全缺、18 项解析成 0 项（`test_log_parse_failed`）；显式恢复 `set -xo pipefail` 后 18 项、manager 接受。不照搬测试夹具的 `set -u`（pandas 激活钩子已证不兼容）。

保证范围（本机 Bash 探针 `rh2/experiments/batch6_network_20260924/env_carry/`）：exported 变量（含 MONAI 配方那类 `OMP_NUM_THREADS`）、PATH、函数、cwd 都能带到测试 exec；shell 选项由第二段自己的可信前导重新设置（不从携带文件恢复）；**不携带**未 `export` 的普通 shell 变量与 alias。代表配方若依赖未导出变量即为反例，届时把该配方列为例外或改配方；不做通用 shell 序列化。携带文件由候选 UID 写、候选 UID 读，只是候选自己的状态，不作为可信的"安装完成"证明；新 HOME 下的状态目录 `$HOME/.rh2/` 由脚本尾部先 `mkdir -p`。日志 = setup 输出 + 安装 exec 输出 + 测试 exec 输出顺序拼接，Start/End 标记与 parser 不变。预算：两段共用同一个 `test_timeout_seconds`，测试 exec 只拿剩余，不扩预算。

#### 4.2.1 三个终点（同一评分 owner 收齐 exec、网络与监控，消费同一实际剩余期限）

| 终点 | 处理 |
| --- | --- |
| 候选在安装段就退出（shell 没走到携带尾部，携带文件缺失） | 等价于今天单 shell 里"shell 已死、测试没跑"：不启动测试 exec，日志无 Start/End 标记，按既有 parser 规则不产生 reward；记事实 `install_shell_exited_early` 与安装 exec 退出码。要与"安装命令非零但 shell 继续（`RH2_INSTALL_RC≠0`，尾部照常写状态，测试照跑）"和"状态写入失败（尾部 `RH2_PHASE_HANDOFF` 缺失 / 写盘报错）"区分记录；归因沿用既有 P-A，携带文件与标记不重新定义 reward |
| 撤网或核对失败 | 宿主直接记 typed infra `grader_supply_withdraw_failed`，不启动测试 exec，不产生 reward，不按离线评分交付；容器、网络、token 按既有清理 |
| 外层取消 / 期限到点 | 同一 owner 终止当前 exec（安装或测试）、网络绑定与 token，收齐 exec 输出与 inspect 事实；未确认放行的作业不得按正常完成交付 |

### 4.3 明确接受的边界

私有测试文件在安装段已被候选用户可读（root 保护只防改写）：安装命令可以把内容编进对网关的 GET 路径。网关丢 query、只转发归一路径并全量记日志，能缩小与留证，**不能**证明没有出站信息（Codex §4）。这是选 2A 时接受的条件，写进 run evidence 的政策字段。

### 4.4 不做的事

不在测试段重新接网；不给 grader 暴露模型代理；不做通用 shell 序列化；不改 deadline、取消与后台进程回收语义；不因阶段化给候选两份超时。

### 4.5 接口清单（Codex 复核补入）

- `contracts/sandbox.py` 的 `NetworkPolicy` 枚举新增 `supply_install_then_none`，"grading 只能 `deny_all`"的 validator 放行该值（1A+2A 已授权的窄契约演进，不再询问同一政策）；旧默认仍 `deny_all`，manager / profile / 契约三处一起迁移。
- 索引入口与文件入口共用同一份宿主绑定政策：验收含已知文件 URL 直接访问、路径归一化（`..`、百分号编码、大小写）、固定 release 例外，不只测 `/simple/<dist>` 404。缓存不等于冻结，下载 / 候选安装观测不等于环境终态精确重建。
- token 与网络绑定在取消、退出、评分结束时都释放，不把每次 attempt 的网关状态留到 run 末尾。
- 归因沿用 P-A 的候选归因条件与资格基线："编译错误归候选"不扩成任何构建失败都给 0；网关自身故障也不能仅凭候选声称取包失败来证明因果；资格与新评分脚本摘要的对应列入 B 接线。
- **观测身份（R4，P1）**：安装后的 `pip list` / 导入观测一律以**候选 UID** 执行（manager 已按 I1 把前后观测改成候选 UID 入口，直接复用）；root 只做可信静态读取、网络与宿主控制操作，绝不以 root 启动候选环境里的 Python / pip。观测只是诊断，不是不可伪造的安装证明；失败不产生新的 reward 判据。
- 信号：安装 exec 的结束就是"安装段结束"，不需要轮询容器内文件。
- **分段验收（NS1）**：用真实 bundle 经当前 renderer 渲染两段脚本、本机 Bash 执行（测试命令替换为确定性 PASSED 文本）、真 `spec.parse_log` / `manager._parse_eval_log`——对照"原单 shell / 只携带状态 / 前导 + 携带"三形态，要求第三形态 Start/End 齐全且解析项数与单 shell 相同；另加 R2E（无安装段）一项正控。

## 5. 记录、失败分类与验证

- **记录**：网关逐请求日志（按 token 归 attempt）；安装后以**候选 UID** 执行 `pip list --format=json`（复用 manager 现有的候选 UID 前后观测入口，不用 root）写入评分 facts `supply.installed`；run evidence 记 devpi 版本、上游、政策（1A+2A）、封禁表摘要。
- **失败分类**（Codex §5.3）：`supply_unavailable`（基础设施）只在网关/devpi 侧对该 token 在安装段记录了连接失败/5xx/超时 **且** 安装段失败文本是取包错误时成立；候选构建/编译错误归候选；判不出的沿用现有"未确定"处理。事后健康检查只作诊断，不改归因。GET 日志不证明装入了哪个解释器（以 `pip list` 观测与导入结果为准）。
- **验证清单**（README §3.3，实现后逐条留证）：缓存冷/热各一次代表安装；agent 与 grader 两种用户/解释器安装成功；候选声明确实被读取；索引不可用 vs 候选安装错误分开归类；封禁的本项目发行包 404、直接 URL 无路由、测试段无网络（inspect + 容器内探测）；超时/取消后网络、relay 连接与容器都清理；1 题冷启动的墙钟与 gate 时间。不做 GPU 作业，不做全池三路评分比较。
- **前置事实待 B**：R2E 48 题中 41 题的 `.venv` 无 pip（B 决定 E11）——供应对它们无效，除非派生镜像补 pip/uv；SWE-Gym conda 环境有 pip。

## 6. 文件归属与顺序

| 归属 | 文件 | 改动 |
| --- | --- | --- |
| A | `sandbox_profile.py` | 包供应 relay 参数、grader 网络策略与启动前核对、撤网核对 |
| A | `grading/manager.py`（B 当前有未提交改动，按 B 落地后顺序修改） | `_run_eval` 两段 exec 生命周期（安装 exec → 撤网核对 → 测试 exec）、三个终点、`grader_supply_withdraw_failed`、facts |
| A/B 单一写入者 | `prepared_task_face.py`（B 当前修改者） | 渲染拆成安装段（含状态携带尾部）与测试段（含来源前导 + 状态恢复）两份脚本；评分面 `blocked_dists` / 例外表字段——由 B 在其在制品落地后按本节接入，A 审 |
| A | `pkg_index_gateway.py`（新） | token 登记、1A 封禁、日志、转发 |
| A | `generate.py` / `bringup.py` | rollout 环境注入 `PIP_INDEX_URL` 等；`InternalService` 条目 |
| B | 逐题 `blocked_dists` 与例外表、派生镜像 pip/uv 可用性、代表题 | 供应定义的数据侧 |

顺序：网关 + relay 变体 + 单元测试（假上游）→ grader 两段 exec 生命周期与三个终点（假 runner 各一次 + 本机 Docker 一次正常交接，验证 §1 的 A/C/D 三类事实）→ rollout 注入 → 代表题冷/热安装 → 用户放行启用。启用前所有默认值保持现状（grader 仍 `--network none`，rollout relay 监听表不变）。

## 7. Codex 设计复核（2026-09-25）

**1A+2A 已批准，不重复请求选择；grader 联网切片先修订 R4/R5，网关可独立推进。** 证据、替身边界和验收见[复核报告 §3](review_next_slices_20260924/README.md)。本轮未启用联网。

- R4 / P1：安装后 `pip list` 必须复用现有候选 UID 的观测入口；root 不能执行候选可写解释器、激活脚本或包。现有 S1-m / I1 已修过此边界，本文 root 观测写法应撤回。
- R5 / P2：root 放行文件不能使候选 shell 的检查不可绕过；本机 Bash 已复现函数覆盖 `[` 后提前进入下一段。`[[ ... ]]` 只修这个例子。保留安装所需 shell 状态的同时，应明确宿主如何在断网确认后交付 / 启动正式测试段，以及 exec 和监控在提前退出、撤网失败、取消 / 期限时由谁终止并收齐。不能依赖 shell 退出 97 作为唯一收口。
- 实施清单补 `contracts/sandbox.py` 的策略枚举与 validator、索引与文件入口同政策核对、attempt 结束时 token / 网络绑定释放；沿用 P-A 既有候选归因条件。这些都是已批范围内的具体接线，无需另立政策决策。

## 8. Codex 修订复核（2026-09-25）

**R4 的候选 UID 观测、R5 的宿主断网确认后启动测试、三个终点与共享期限方向接受；补 NS1 后可实施。** [完整报告 §2](review_followup_e5_20260925/README.md)。1A+2A 与继续推进已获批，不需要再请求“允许实现 grader 联网”；正式作业启用仍按 §6 单独安排，本轮未启用。

- **NS1 / P2 设计补充**：第二个 exec 应保留来源 renderer 的可信 shell 前导。`export -p` / `declare -f` / cwd 不携带 `set -xo pipefail`；真实 SWE 的 Start/End 冒号命令依赖 xtrace 出现在日志中。本机真实 renderer / parser 对照中，缺前导时 18 项变为 0 项并报解析失败，恢复前导后正常。把这个对照加入验收，不照搬夹具的 `set -u`。
- cwd 用 `cd` 恢复，状态目录先建立；状态恢复按候选 UID 执行，不作为可信完成证明。安装命令非零但原 shell 继续、提前退出、状态写入失败分别沿既有 P-A 归因；取消、撤网失败、期限到点不得启动第二 exec。
- 同步清掉正文残留的“单 shell / root 放行文件 / 轮询”旧描述。实现验收沿现有源脚本与 parser，含无安装段正控；不需要通用 shell 状态平台。
