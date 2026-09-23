# CPU 机器后续工作：Claude 的设计与对 Codex 建议的核对

> **勘误（2026-09-10，按 [Codex 核查](cpu_followup_codex_review_20260909.md)）**：§2.1 的"约 1 TB"是镜像 SIZE 相加（含共享层），去重外推约 0.6–0.8 TB，且仍是外推；§2.2 变量名应为 `SLIME_AGENT_CC_PLATFORM_TARBALL`；§3.3 "gold 全部参考 case 通过"只适用于 SWE，R2E 按预期状态映射（24 题里 10 题含 ERROR/FAILED 预期）；§4.2 的"扩展回归"与"按函数变异"降为需要显式选择规则与手工校准的诊断；"人力只花在失败题"不成立（Pydantic-5706 在通过组）；"7 个工件再加 MONAI-2454、pandas-48106"重复计数；OpenAI 138 题是"未稳定解决"子集。合并后的分阶段计划见 [cpu_followup_stages_20260910.md](cpu_followup_stages_20260910.md)。

日期：2026-09-09。作者：Claude（B 线）。性质：**建议稿**，供用户决定执行范围；与 Codex 的 [cpu_followup_plan_20260909.md](cpu_followup_plan_20260909.md) 并列，§7 逐条给出同意 / 补充 / 反对。所有数字来自昨夜探针的账本（`ledger/`）与今天对机器的只读测量；没有新起容器、没有付费调用、没有改 rh2 代码。

先回答你的四个直觉，再展开。

| 你的直觉 | 一句话回答 |
| --- | --- |
| 1. 用真实 rh2 判分；怎么保证到训练机也不出问题 | 可以在这台机上独立跑真实 rh2 grader（不需要 learner），但今天还有两个已知接缝挡着 216 题：parser 映射和 mypy/conan 的测试命令。跨机器一致性靠三样东西：身份记录、一套固定的"评分一致性用例"在每台评分主机上先跑一遍、主机事实入 preflight 记录。 |
| 2. 提前装镜像、装 Claude Code、存储多大 | SWE-Gym 216 题镜像落盘约 1.0 TB（不是压缩清单的 480 GB）；R2E 每题约 1.6 GB。Claude Code 用 rh2 现成的原生包离线安装，不用装 Node。建议训练机用本地 registry 镜像 + 按需拉取 + LRU 清理，而不是硬塞全部镜像。 |
| 3. 要不要扩大筛选 | 要，而且比 Codex 建议的 64+64 更大：门是自动的，CPU 便宜，人力只花在失败题上。建议 SWE-Gym Full 同 9 仓库先 256 题（按 78 个 repo/version 工具链分层）、R2E 再 128 题；第三来源只做 16–32 题试接。 |
| 4. 题目问题怎么筛 | 三层配合，顺序是：执行证据（自动、全池）→ 本地 agent 静态审计（全池，按 OpenAI 四分类）→ 模型求解（只对可疑题和随机对照，先把出网通道封住）。DeepSeek 不是筛题主力，它是 harness 级信号。 |

---

## 1. 真实 rh2 判分与跨机器一致性

### 1.1 现在能不能独立跑真实 rh2 grader

能，代码入口是 `SWEGradingManager.grade(workspace=None, frozen_delta=…, spec=…)`（[manager.py](../../../../../rh2/src/repoharness2/grading/manager.py)），配 `GraderSandboxProfile`（deny_all、非 root 54322、cap-drop ALL、2 CPU / 4 GiB / tmpfs 1 GiB）。已有两个真实 Docker 驱动可参考：`tests/grading/test_w3b_grader_profile_docker.py`（fixture 镜像）和 `experiments/s1_7a_t1_regression.py`（8 题 Verified，workspace 导出路径）。不需要 miles、Ray 或 GPU。

**但对 216 题今天跑不通，两个接缝已经在代码里看得见：**

| 接缝 | 代码事实 | 后果 | 修法（T1，A 复核） |
| --- | --- | --- | --- |
| parser | `envpack/scoring.py::parse_official_eval` 调安装的 swebench 4.1.0 `make_test_spec(instance, namespace, arch)` + `get_logs_eval(spec, path)`；4.1.0 的 `MAP_REPO_TO_PARSER` 没有 SWE-Gym 9 仓库 | 216 题解析必 `KeyError`，manager 记 infra 故障整组丢 | 把 fork（pin 242429c1）的 `log_parsers.py` + `grading.py` 像 constants 一样冻结为 vendor 资产（sha256 pin），`parse_official_eval` 按 `spec_vendor_id` 选实现；8 题 Verified 仍走 4.1.0 |
| 测试命令 | `prepared_task_face.py::_v2_candidate_test_lines` = `eval_cmd + 触及的测试文件`；官方 mypy 是 `-k "<case> or …"`（40 题），conan 要先 `export PYTHONPATH`（12 题） | mypy 的 `-k test-data/unit/x.test` 选不中任何 case；conan 视 cwd 可能 import 失败 | 命令生成按 vendor 分派：mypy 用 fork 的 `make_test_command` 规则，conan 注入 `eval_commands`；其余 7 仓库现状已与官方前缀一致 |

这两条不改 reward 语义（只是让评分真的跑起来、跑对测试），属 T1；但因为改的是共享 grading 文件，按协议由 B 写、A 复核，一批一个修改者。

### 1.2 昨夜探针与真实 rh2 之间还差什么（不能把探针结果冒充 rh2 验收）

| 维度 | 探针 | rh2 正式 | 对策 |
| --- | --- | --- | --- |
| 补丁应用 | 官方 `git apply --allow-empty` → 镜像 git 2.34 必退 `patch --fuzz=5` | frozen delta 直写文件（无 diff、无 fuzz） | 同一候选工件两边跑，比逐测试状态 |
| 测试路径投影 | 只去掉与官方 test_patch 精确同路径 | 按 `DEFAULT_SWE_TEST_GLOBS` 排除更多测试路径（Codex 核出 6 题有差别） | 用现成 7 个候选工件对账 |
| 网络 / 用户 / 资源 | 默认网络 + root 为主；离线、54322 各测过一组 | deny_all + 54322 + 2 CPU / 4 GiB / tmpfs 1 GiB / 无 shm 设置 | 见 §1.4 校准 |
| install 步 | 官方脚本含 install | 不重装 | 12 题已证明不影响判定；扩大到全池要靠 rh2 真跑 |

### 1.3 "评分一致性用例"：把昨夜的产出变成可迁移的验收包

昨夜账本里已经有全部原料：216 题 × empty/gold 各 3 次的官方判定与逐测试状态映射、24 个候选补丁、12 题的无关/变异 fixture。建议固化为一个小包（不新建 schema，就是 jsonl + diff 文件）：

```text
conformance/
  cases.jsonl        # (instance_id, 工件类型 empty|gold|candidate|probe, 工件 sha256, 预期官方判定, 预期 F2P/P2P 逐 case 状态, 预期不可判原因)
  artifacts/<sha>.diff
  hosts/<host>.json  # 每台跑过它的主机：kernel/cgroup/docker/storage driver/shm 默认值/CPU 型号/实测每例耗时
```

先选 24 例（每仓库 ≥2，含 modin 网络翻转题、pandas 参考 ID 题、MONAI-2454 同名新文件、MONAI-763 共享内存题、conan、mypy）。**任何一台要承担评分的主机**（这台 CPU 机、将来的 8 卡机或独立评分 worker）在开训前先跑一遍，比对的是逐测试状态而不只是 0/1。这就是你问的"怎么保证到训练机不出问题"的可操作答案：不是保证，是每台机器开工前 20 分钟的证据。

### 1.4 资源与条件校准（在这台机上就能做完）

- **共享内存**：MONAI-763 的 DataLoader 在 64 MiB 默认 `/dev/shm` 下 SIGBUS（Codex 已定位）。rh2 grader/rollout profile 目前没有 `--shm-size` 旋钮，建议 A 加一个字段（T1），数值由这台机实测：MONAI 26 题 + dask/modin 用 1 GiB 重跑 gold 一次。
- **内存上限**：profile 默认 4 GiB；昨夜是 8 GiB 上限、没有记录峰值。补一轮 `docker stats` 采样（每 2 秒）跑 216 题 gold ×1，得到每仓库峰值 RSS，再定 rollout/grader 的 memory_bytes。这决定 8 卡机上能并发多少评分容器。
- **网络**：从现在起把 `--network none` 作为筛选的默认变体（与 rh2 deny_all 一致），全 216 题 empty/gold ×1 离线重跑一遍（约 2.5 小时），把"网络敏感"题列全，而不只知道 modin 两题。
- **超时**：昨夜 gold 单次超过 300 s 的 10 题，超过 900 s 的 3 题（modin）。按仓库给上限（例如 modin/pandas 1,800 s，其余 600 s）比一刀切合理；这是 A 线 wall-clock 决定的输入。

---

## 2. 训练与评测前的环境准备：镜像、Claude Code、存储、流程

### 2.1 实测体积（这台机 `docker system df -v`）

| 项 | 数值 | 推算 |
| --- | --- | --- |
| SWE-Gym 镜像落盘 | 25 个共 118.6 GB，中位 3.2 GB，最大 14.1 GB（MONAI-6975）；共享层只有 1.5–2.3 GB | 216 题约 **1.0 TB**；同 9 仓库 Full 2,346 题约 10 TB（不可能全放） |
| R2E 镜像落盘 | 24 个共 39.5 GB，中位 1.4 GB | 4,578 题约 7 TB（不可能全放） |
| 压缩清单（registry 侧） | SWE-Gym 216 题约 480 GB | 本地 registry 存压缩层即可 |
| 单次拉取 | 中位 22 s（本机 2.6 Gbps） | 按需拉取可接受 |

结论：**训练机不应以"全部镜像常驻"为前提设计**。首训 216 题常驻需要 ≥1.3 TB（含 25–30% 余量、可写层、日志）；若训练机盘不够，改用本地 `registry:2` 镜像仓（压缩约 480 GB）+ 按需拉取 + LRU 删除。训练时每步同一批任务的 8 条 rollout 共用镜像，工作集 = 每步任务数 × 约 4.7 GB。

### 2.2 Claude Code 不用装 Node

rh2 的 `ClaudeCodeDriver._install_native_cli` 已经是离线安装：把 `@anthropic-ai/claude-code-linux-x64@2.1.205` 平台包（含原生 `package/claude` 二进制）上传进容器，`install` 到 `/usr/local/bin/claude`，再核 `--version` 等于 pin（不符即 run-halt）。昨夜我的探针用 Node + npm wrapper 是绕路，正式链路不需要。准备工作只有：下载该平台包一次、记 sha256、放到 `SLIME_AGENT_CC_TARBALL` 指向的位置；grader 容器不装 Claude Code。

### 2.3 建议的准备流程（一次做成"环境包"，任何主机都按它开工）

```text
1. 清单：题单 + 数据 revision + 镜像 ref@digest + spec_vendor pin + rh2 commit + profile digest
2. 镜像：推入训练机本地 registry（或预拉常驻），逐镜像核 digest 与 amd64
3. 工具：Claude Code 平台包（sha256 pin）、relay 镜像（digest pin）、grader/rollout profile 参数
4. 预检：跑 §1.3 的一致性用例（24 例，约 20 分钟）+ rh2 自带 prelaunch probes
5. 记录：主机事实（kernel/cgroup/docker/存储/shm/CPU）写进本次 run 的 startup evidence
```

哪些现在就能在这台 CPU 机上做完：1、2 的清单与 digest 核（已有）、3 的包与 pin、4 的用例包和第一份主机记录。训练机上只剩推镜像和跑预检。

### 2.4 日志与保留

一条 Claude Code 轨迹的 stream-json 约 4.5 MB；216 题 × 8 条 × 50 步 ≈ 400 GB。训练时不能全留原文，按 rh2 现有账本保留摘要与抽样；评测与诊断轮次才留全量。这台机上昨夜 270 MB 原始日志已同步到 `runs/env_probe_20260909_final_sync/`。

---

## 3. 扩大环境筛选：扩多大、从哪扩、怎么分层

### 3.1 为什么可以比 64+64 大

昨夜 216 题 facts/empty/gold 一遍（648 个 job，含 192 次拉取）用了 2 小时 45 分，5 并发，机器费用不到 $1；失败率约 5%，且失败题的归因才需要人。也就是说筛选的边际成本是磁盘时间与拉取限速，不是人力。人力只花在：失败题归因（每题几分钟）和抽样复核。所以规模应由"下一步要用多少题"决定，而不是由谨慎默认值决定。

### 3.2 建议的扩大顺序

| 批 | 来源与规模 | 选题规则 | 目的 |
| --- | --- | --- | --- |
| E1 | SWE-Gym Full 同 9 仓库 **256 题** | 覆盖 Lite 的 78 个 (repo, version) 工具链每组 ≥2，再按仓库配额补；含 hydra 66 题、bokeh 26 题作 L2 保留仓库的可行性检查 | 扩容训练池的最低成本路径，同镜像格式同 parser |
| E2 | R2E Subset **+128 题**（10 仓库各 ≥8，含 tornado/pyramid 保留仓库各 8） | 按仓库 × 测试规模分层 | RL 证据最强的来源；镜像小、测试快 |
| E3 | SWE-rebench V2 Filtered 的 Python 子集 **16–32 题** | 只挑当前 9+10 仓库之外的仓库 | 试第三来源的接入成本与覆盖增量 |
| E4 | SWE-Gym Full 其余（按需，分 200 题一批） | 等 E1 的失败率与 T0 处置定了再扩 | 训练池需要时才扩 |

E1 需要先补 Full 的 11 列原始行（按冻结 revision 重抓）并让 ingestion 构造器接受非 Lite 行（`envpack/ingest_swegym_lite.py` 泛化，T1，数据线代码）。E2 只需扩大候选清单，R2E runner 已可用。E3 需要一个新 adapter（reward = 目标 ID 全 PASSED，parser 按语言），先做 Python。

### 3.3 每题跑什么（比昨夜更省、更对齐 rh2）

| 门 | 次数 | 变体 | 说明 |
| --- | --- | --- | --- |
| facts | 1 | 默认网络 | digest、HEAD、导入位置、未来提交、控制文件 |
| empty / gold | 各 1 | **`--network none`** | 与 rh2 deny_all 对齐；异常题再补默认网络对照 |
| 重复 | 对异常题 ×3；正常题随机 10% ×3 | 同上 | 昨夜 1,296 次里只有 1 次噪声，全量 N=3 不值 |
| 参考覆盖 | 自动 | — | empty 里全部 F2P 出现且失败、gold 里全部参考 case 出现且通过；缺失即标 |
| 耗时/内存 | 自动 | — | 分段计时 + `docker stats` 峰值 |

估算：E1 256 题 ≈ 256 × 3 job × 中位 45 s ≈ 3.5 机时 + 拉取 256 × 4.7 GB ≈ 1.2 TB 下载（本机 2.6 Gbps 约 1 小时，Docker Hub 限速可能拉长到半天）；E2 128 题 ≈ 1 机时。都在一天内。

### 3.4 不建议现在做的

自建 PR 生产线、SWE-smith 接入（测试对 agent 可见，奖励定义不同）、Envs-FORGE/TaskPilot 式合成。FrogNano 新精读的价值是方法论：任务有效性（gold/noop/题意）与策略相对难度分开，题面改写会改变信息量而不是代码难度；它没有可直接接入的任务包。等基座诊断出来再谈难度校准。

---

## 4. 题目问题怎么筛：执行证据、静态审计、模型求解三层

### 4.1 外部资料里的做法（你还没读的部分，只列与筛题直接相关的）

| 来源 | 做法 | 对我们的启示 |
| --- | --- | --- |
| OpenAI Verified 审计（N13a/N13b） | 让 agent 逐题调查失败：把问题分成测试过窄、测试过宽、覆盖不足、题面误导；o3 稳定失败的 138 题里 59.4% 有题目问题 | 筛题要有执行证据，不能只读题；四分类可直接当我们的标签 |
| SWE-rebench V2（O11/O28b） | LLM 给题面打元数据（完整性、难度、是否含外链），gold/noop 验证，flaky 检测，运行后反查 always-fail 题 | 元数据筛 + 执行验证 + 训练后回查三段式 |
| Prime（prime 稿） | Verified = 首检失败再试 10 次有一次过就保留 | "Verified" 不等于稳定，本地必须自验 |
| SWE-smith（E5） | 环境先行、同镜像派生多题；未做题面审计 | 扩容思路可借，筛题不能借 |
| N06 verifier hardening | 收紧 verifier 攻击成功率降，良性通过率也降约 10 个百分点 | 任何加严都要同时报 gold 与合法替代解通过率 |
| FrogNano | 任务有效性与策略难度分开；题面改写改变信息量 | 先对齐题意与测试，再校准难度 |

### 4.2 建议的三层筛查

**第一层：执行证据（自动，全池，已有 80%）**

- 昨夜的门：empty/gold、参考覆盖、网络敏感、共享内存、参考 ID 脆弱（10 题）。
- 新增两项自动检查：
  - **扩展回归**：gold 与候选各跑一次"gold 触及模块的整个测试文件"（不只参考集），报告参考集外的失败差异。Pydantic-5706 那种"候选破坏了 Sequence 行为但官方只跑一个文件"的假阳性就会露出来。这是诊断指标，不进 reward。
  - **语义变异**：把昨夜"机械删末 hunk"换成"按函数逐个还原 gold"（AST 定位 gold 改动的函数，每次只还原一个），变异后仍 FULL 的函数就是测试没约束到的部分；MONAI-6975 的 docstring 误报不会再出现。

**第二层：本地 agent 静态审计（Codex / Claude，全池 216 + 扩容批，每题几分钟）**

固定 rubric，输入 = 题面、base 代码相关文件、公开测试；**先不看 gold**，写出可推导的行为约束；再对照 gold、隐藏测试、F2P 名单，输出 OpenAI 四分类标签 + 置信度 + 一句依据；只标记不裁决。24 题审查已经证明这套流程能发现真问题（Pydantic-8500 官方用例没覆盖题面原例）。产出直接进候选 manifest 的题级字段。

**第三层：模型求解（只对可疑题和随机对照）**

DeepSeek 一题净成本约 ¥0.8，但昨夜证明了两个前提没满足就不能用它筛题：容器可出网（3 条轨迹下载了上游修复）、起始工作区没存快照（镜像预置改动混进候选）。先修这两点：求解容器接 `--internal` 网络 + 一个只放行 `api.deepseek.com:443` 的小转发器（和 rh2 relay 同构），起跑前 `git status` 快照。之后对第二层标记的题 + 10% 随机正常题各跑 2 次，看"官方通过但审计说不对"和"官方失败但修对了原例"两类。**它回答的是 harness 级可解性与评分信号，不是题目质量的主判据。**

### 4.3 处置口径（都是 T0，先积证据）

有执行证据的坏题才排除并记录原因；只有审计标签的题标"待核验"；参考 ID 类先逐类归因（Unicode、反斜杠、空格各一题）再决定改规范化还是排除；修过题面或测试的版本与原指标分开存，reward 定义不悄悄变。

---

## 5. 执行顺序与今晚就能开的任务

| 顺序 | 任务 | 依赖 | 机器时间 | 人力 |
| --- | --- | --- | --- | --- |
| 1 | 216 题 empty/gold ×1 `--network none` + `docker stats` 峰值 + MONAI 26 题 `--shm-size 1g` gold | 无（runner 加两个参数） | 约 4 小时 | 小 |
| 2 | 评分契约修补 B1′（vendor parser + mypy/conan 命令），本地单测 | 无 | — | 半天，A 复核 |
| 3 | 真实 rh2 grader 驱动：12 题 empty/gold + 7 个候选工件 + MONAI-2454，正式 profile，比逐测试状态 | 2；A 确认 frozen delta 入口或用 workspace 路径 | 1–2 小时 | 半天 |
| 4 | 一致性用例包（24 例）+ 本机主机记录 | 3 | 20 分钟 | 小 |
| 5 | E2：R2E +128 题 facts/noop/gold | 无 | 1 小时 | 小 |
| 6 | E1：Full 原始行重抓 + ingestion 泛化 + 256 题门 | ingestion 代码（T1） | 半天机时 | 1 天 |
| 7 | 静态审计 216 题（两个 agent 分半） | 无 | — | 1 天 |
| 8 | 出网受控的 DeepSeek 求解（可疑题 + 对照） | 转发器（半天）+ 7 | 数小时 | 小 |
| 9 | E3 第三来源 16–32 题 | 新 adapter | 半天 | 半天 |

1 和 5 不需要任何决定，机器空着就可以开；2–4 是真实 rh2 判分线，需要 A 参与；6–9 按你对扩容与筛题的决定。

## 6. 需要你决定的

1. **扩容规模**：E1 256 / E2 128（我的建议）还是 Codex 的 64 + 64。
2. **筛选默认网络条件改为 `--network none`**（与 rh2 一致；昨夜默认网络的结果保留作对照）。
3. **B1′ 由 B 写、A 复核**：vendor parser + 命令分派（T1，不改 reward 语义）。
4. **grader/rollout profile 新增 `shm_size` 旋钮**（A，T1），数值由校准定。
5. **DeepSeek 继续用于筛题的前提**：接受"受控出网转发器 + 起始工作区快照"后再跑；预算另定。
6. **10 题参考 ID 处置与 12 题不可判 FULL 的去向**（T0，等归因证据）。

## 7. 对 Codex 建议的核对

| Codex 的点 | 我的态度 | 说明 |
| --- | --- | --- |
| 真实 rh2 评分不需要 GPU，但有 parser、命令、投影、R2E 来源四个接缝 | **同意** | 我补了两个接缝的具体代码位置与修法（§1.1），以及一致性用例包（§1.3） |
| 先用 7 个现成候选工件对账 | **同意** | 加 MONAI-2454、modin-6937 离线、pandas-48106 三个已知反例 |
| 换机器降低漂移：交付身份组 + 每台主机 6–12 个迁移样例 | **同意并加码** | 固化为 24 例的用例包，比逐测试状态，纳入 preflight |
| 准备流程七步、三类东西、容量预算公式 | **同意** | 补实测体积（§2.1）：216 题落盘约 1 TB，Full/R2E 全量不可常驻，建议本地 registry |
| 用 rh2 原生 CC 安装，不重造 Node/npm | **同意** | 昨夜探针的 ccbundle 是绕路，已注明 |
| 并发 1/2/4 再 8 | **部分不同** | 昨夜 5 并发 1,296 次运行只有 1 次噪声（共享内存），并发本身没出问题；更需要的是每仓库峰值内存与 shm，先测这两项再定并发 |
| 第一轮扩 64 + 64 | **反对，建议 256 + 128** | 门是自动的、失败率约 5%，人力只在失败题；E1 还兼做 hydra/bokeh 保留仓库可行性 |
| 第三来源先 rebench Python 16–32 题，暂不接 SWE-smith 和自建 PR | **同意** | |
| 筛题"静态筛疑点 + 执行证据定性 + 少量模型轨迹" | **同意** | 补两项自动检查（扩展回归、按函数变异）和 DeepSeek 的出网封堵前提 |
| 新池先审 24–32 题 | **不同** | 静态审计成本低，建议 216 全审，让标签成为候选 manifest 的字段；执行复核才限量 |
| FrogNano 的启示：先验证题目再校准难度 | **同意** | |
| 不冻结 216 题为正式训练集 | **同意** | |

## 8. 本稿没有做的

没有跑新实验、没有改代码、没有拉新镜像。§2.1 的体积是本机 49 个镜像的实测外推；§3.3 的耗时按昨夜 216 题外推；E1 的拉取时间受 Docker Hub 限速影响，未实测。
