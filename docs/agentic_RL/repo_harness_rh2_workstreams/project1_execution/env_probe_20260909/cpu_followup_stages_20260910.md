# CPU 机器后续工作：分阶段实施计划（逐阶段确认）

日期：2026-09-10。作者：Claude（B 线）。性质：把 [Claude 建议](cpu_followup_claude_20260909.md)、[Codex 建议](cpu_followup_plan_20260909.md)、[Codex 核查](cpu_followup_codex_review_20260909.md) 合并成可逐阶段确认的计划。**每个阶段单独确认后才开始；阶段内的小步不再逐条申请。** 本稿没有新实验、没有改代码。

## 0. 对 Codex 核查的回应（先把分歧清掉）

| Codex 的点 | 回应 | 落到哪个阶段 |
| --- | --- | --- |
| R2E 的 expected 含 ERROR/FAILED（24 题里 10 题），不能统一要求全 PASSED | **accepted**。我 §3.3 那行只适用于 SWE 的 F2P/P2P；R2E runner 本来就是预期状态映射匹配，文档表述错了 | 阶段 4 的门定义按来源分开写 |
| 1 TB 是 SIZE 相加（含共享层），不是去重落盘量 | **accepted**。按 UNIQUE 之和（25 题 66.5 GB）加每工具链共享层外推，216 题约 0.6–0.8 TB，仍是外推。结论从"必须 registry"改为"先固定 digest 预拉工作集、按清单清理；训练机盘量知道后再定" | 阶段 3 |
| 扩展回归的"源码→测试文件"映射不可靠；Pydantic-5706 漏的在别的文件 | **accepted（收窄）**。改为显式选择规则：候选轨迹里自己跑过且失败的测试 + 同包目录测试；base/gold/candidate 三方对照，区分原有失败与新增回归 | 阶段 5 |
| 逐函数还原 gold 后仍通过不是测试不足的充分证据；不先造通用变异系统 | **accepted**。先手工构造少量"明确违反需求"的补丁与合法替代解校准 | 阶段 5 |
| 5.6% 不是坏题率；"人力只花在失败题"不成立（5706 在通过组） | **accepted** | 阶段 5 的抽样含通过题 |
| `docker stats` 是采样峰值 | **accepted**。改用 cgroup v2 `memory.peak`（宿主可读）为主，采样为辅，记录口径 | 阶段 1 |
| 24 例 20 分钟未实测；`216×8×50` 日志公式无依据 | **accepted**。用例包分"完整风险集"和"短启动子集"，耗时实测；日志量按实际 attempts 算 | 阶段 3 |
| 不要四组 216 题轮都跑 | **部分不同**。真实 rh2 路径要等阶段 2 的代码修补，而 216 题离线 empty/gold 一轮只花 4 机时、不改代码，直接给出全池"网络敏感题"与内存峰值；它是诊断数据，不是第二套评分器。保留在阶段 1，MONAI 只跑短对照 | 阶段 1 |
| 上限 256/128，首段各 32–64，上限内不再逐批申请 | **accepted** | 阶段 4 |
| hydra/bokeh/tornado/pyramid 是评测候选资格检查，与训练候选分开计数 | **accepted** | 阶段 4 |
| 审计分深浅：全池轻量 + 首批 24–32 深审再扩 | **accepted** | 阶段 5 |
| 复用 rh2 rollout 的 internal 网络 + relay，不另造转发器；`git status` 不够，要复用基线机制 | **accepted**。relay 上游改指 API 主机是最小适配；起始工作区用 rh2 基线 manifest | 阶段 5 |
| 变量名 `SLIME_AGENT_CC_PLATFORM_TARBALL`；七个工件重复计数；OpenAI 138 题是"未稳定解决"子集；Prime 十次规则只是 R2E 卡；前缀一致 ≠ 等价 | **accepted**，见我建议稿顶部勘误 | — |

剩下没有分歧。下面每阶段列：目标、做什么、产出、开始前需要你确认的、机器与人力成本、停止条件。

---

## 阶段 1 · 诊断补测（不改代码，只用昨夜的 oracle runner）

**目标**：把昨夜没测的三个条件补齐，全部是后面阶段要用的输入：全池网络敏感题、每仓库内存峰值、共享内存影响。

**做什么**

| 项 | 范围 | 条件 |
| --- | --- | --- |
| 1a 离线 empty/gold | 216 题各 1 次 | `--network none`（与 rh2 deny_all 一致）；官方脚本原样 |
| 1b 内存峰值 | 与 1a 同一批容器 | 宿主读 cgroup v2 `memory.peak`，辅以 2 s 采样；记录口径与 OOM 事件 |
| 1c 共享内存 | MONAI 26 题 gold 各 1 次 | `--shm-size 1g`，离线；MONAI-763 设 1,800 s 上限，超时即记，不追完整长测试 |
| 1d 汇总 | — | 网络敏感题清单（默认网络 vs 离线判定翻转）、按仓库内存峰值分布、shm 影响题清单、与昨夜结果的一致性 |

**产出**：`ledger/` 追加三份账本 + 一页汇总；这些数字是阶段 2 的 profile 校准输入和阶段 4 的门默认条件依据。

**需要你确认的**：只有"开始"。runner 加两个参数（shm、cgroup 读取），不进 rh2。

**成本**：约 4–5 机时（$1 以内），人力半小时看汇总。

**停止条件**：离线判定翻转的题超过 20 题（说明参考集生成条件与假设不符，要先归因再扩容）；或内存峰值普遍超过 4 GiB（rh2 默认上限要重新讨论）。

---

## 阶段 2 · 真实 rh2 评分接通与对账（代码 T1，B 写 A 复核）

**目标**：让真实 rh2 grader 能对 SWE-Gym 216 题评分，并用现成工件证明它与官方 oracle 逐测试一致或差异可解释。

**做什么**

| 步 | 内容 | 谁 |
| --- | --- | --- |
| 2a 评分契约修补 | vendor fork（pin 242429c1）的 `log_parsers.py` + `grading.py` 为冻结资产，`scoring.parse_official_eval` 按 `spec_vendor_id` 选实现；候选测试命令按 vendor 分派（mypy `-k` 表达式、conan `eval_commands`）；单测覆盖 9 仓库各一题的命令与解析 | B 写，A 复核共享 grading 文件 |
| 2b 薄驱动 | 用真实 `SWEGradingManager` + 正式 `GraderSandboxProfile`（deny_all、54322、2 CPU / 4 GiB）评分；优先走 frozen delta 路径（需要 A 确认可在无 miles 下调用的 finalize/投影入口），否则先用 workspace 导出路径并注明差异 | B 写；A 提供入口 |
| 2c 对账 | 12 题 empty/gold；7 个现成候选工件（含 MONAI-2454、pandas-48106）+ modin-6937 离线 + 昨夜 12 题无关/变异 fixture；比逐测试状态、应用方式、耗时 | B |
| 2d 校准输入 | 用阶段 1 的内存峰值与 shm 结果，给 A 一份 profile 参数建议（memory、shm 旋钮、按仓库超时） | B → A |

**产出**：对账表（逐题逐测试）、差异清单及原因、2a 的代码与测试、给 A 的参数建议。

**需要你确认的**：
1. 2a 归属：B 写、A 复核，一批一个修改者（T1，不改 reward 语义）。
2. 2b 路径：等 A 的 frozen delta 入口，还是先用 workspace 路径（结果标"S1 路径"）。
3. 给 A 的新增请求：profile 加 `shm_size` 字段（T1）；按仓库超时属 A 线 wall-clock 决定的输入。

**成本**：代码与单测约 1 天；对账运行 1–2 机时；A 复核半天。

**停止条件**：真实 grader 对 gold 的逐测试状态与 oracle 不一致且无法归因于已知差异（fuzz、投影、install）→ 停下出根因，不扩题。

---

## 阶段 3 · 环境包与迁移预检

**目标**：把"在任何评分主机开工前 20–40 分钟内证明评分链没漂"变成一个可执行的包。

**做什么**

| 项 | 内容 |
| --- | --- |
| 3a 一致性用例包 | 从阶段 2 对账结果选"完整风险集"（约 24 例：网络翻转、参考 ID、同名新文件、共享内存、conan、mypy、慢题）和"短启动子集"（约 8 例、每例 <2 分钟）；格式 = cases.jsonl + diff 文件 + 预期逐测试状态 |
| 3b 主机记录 | kernel / cgroup 版本 / docker / 存储驱动 / shm 默认 / CPU 型号 / 冷热拉取耗时；先在这台机产出第一份，并实测两套用例的耗时 |
| 3c 工具 pin | Claude Code 平台包（`SLIME_AGENT_CC_PLATFORM_TARBALL`，sha256）、relay 镜像 digest、profile 参数 digest |
| 3d 镜像与存储 | 固定 digest 预拉工作集的清单与清理清单（不建 registry / LRU）；报告 216 题去重后的实际落盘量（拉齐一次、`docker system df` 去重口径）；训练机盘量拿到后再定常驻还是分批 |

**产出**：`conformance/` 目录、主机记录、pin 清单、落盘量实测。

**需要你确认的**：训练机（8 卡机）的盘量与是否允许在其上装本地 registry，这决定 3d 的方案；其余是实现选择。

**成本**：半天人力；机器约 2 机时（含拉齐 216 题量落盘）。

---

## 阶段 4 · 扩大环境筛选（上限内分段推进）

**目标**：形成后续基座诊断可选的环境候选池，覆盖表按实际候选建立；训练候选与评测候选分开计数。

**做什么**

| 段 | 来源 | 首段 | 上限 | 前置 |
| --- | --- | --- | --- | --- |
| E2 | R2E Subset | 32 题（10 仓库各 ≥3） | +128 | 从冻结 revision 取回新增题完整行（gold/expected），沿用 R2E runner；门 = facts + noop/gold（预期状态映射匹配）离线 ×1，异常题 ×3 |
| E1 | SWE-Gym Full 同 9 仓库 | 64 题 | +256 | 按冻结 revision 重抓 Full 11 列原始行；用 Full 实际候选建 repo/version 覆盖表（不照搬 Lite 的 78 组）；ingestion 构造器泛化（T1，数据线代码）；门 = facts + empty/gold 离线 ×1，异常题 ×3，正常题随机 10% ×3 |
| E-eval | hydra 66、bokeh 26（SWE-Gym）、tornado / pyramid（R2E）各 8–16 | 同门 | — | 只作"评测候选环境资格检查"，单独计数，不进训练池 |
| E3 | SWE-rebench V2 Filtered 的 Python 子集 | 16 题 | 32 | 新 adapter（目标 ID 全 PASSED、pytest parser）；只挑现有 19 仓库之外的仓库 |

每段结束出一页：覆盖增量、失效率与原因分类、单位成本（机时、拉取量、去重落盘量）；在上限内继续不再申请，超上限或失效率异常再回来。

**需要你确认的**：
1. 上限 256 / 128 / 32 与首段 64 / 32 / 16（Codex 已同意）。
2. E1 的 ingestion 泛化是数据线代码（T1）。
3. E-eval 现在做还是等基座诊断后做。

**成本**：E2 首段 1 机时；E1 首段约 2 机时 + 拉取约 300 GB；人力主要在失败题归因，每题 5–15 分钟。

**停止条件**：某仓库/版本整体失效（parser 或依赖），先修接缝再继续；Docker Hub 限速使拉取排队超过跑数时间，改为分批预拉。

---

## 阶段 5 · 题目质量筛查（需要你仔细审设计后再开）

**目标**：在 empty/gold 之上，识别测试过窄 / 过宽 / 覆盖不足 / 题面误导 / 环境与 parser 类问题，产出带证据的题级标签，不自动裁决。

**做什么（三层，都先小批校准再扩）**

| 层 | 内容 | 首批 | 扩大条件 |
| --- | --- | --- | --- |
| 5a 结构与执行证据（自动） | 全池：参考覆盖、网络敏感、共享内存、参考 ID 类；加"扩展回归"（显式规则：候选轨迹自己跑过且失败的测试 + 同包目录测试，base/gold/candidate 三方对照，分开原有失败与新增回归） | 昨夜 24 个候选 + 13 个通过题 | 规则跑通且误报可解释 |
| 5b 本地 agent 审计 | 轻量：全池按固定 rubric 出标签（OpenAI 四类 + 环境/parser/其他），先不看 gold 再对照；深审：首批 24–32 题（含已知反例、正常通过题、随机未报警题），测漏检/误报/耗时 | 24–32 深审 + 全池轻量 | 深审的漏检率与耗时可接受 |
| 5c 手工反例与替代解 | 对首批题手工写"明确违反需求"的补丁与合法替代解，跑 grader 看误奖/误杀 | 8–12 题 | 校准 5a/5b 的标签 |
| 5d 模型求解 | 只对 5a/5b 标记题 + 10% 随机对照；前置：复用 rh2 rollout 的 internal 网络 + relay（上游改指 API 主机），起始工作区按 rh2 基线 manifest 记录 | 待定题单与预算 | 前置完成后单独申请 |

**产出**：旁路审查账本（范围、理由、证据、不确定性），不写进生产 manifest，不自动排题；处置建议按题分类交 T0。

**需要你确认的（这是你说要仔细审的部分）**：
1. rubric 与标签集；2. 首批 24–32 题的组成（反例 / 通过 / 随机的比例）；3. 两个本地 agent 的分工与交叉核验方式；4. 5d 的网络方案、题单、次数与金额；5. 标签的存放与使用边界（只作诊断，不进 reward、不自动剔题）。

**成本**：5a 自动约 2 机时；5b 深审每题 20–40 分钟人机时间（未实测）；5c 半天；5d 按题单。

---

## 阶段 6 · 处置决策（T0，等阶段 2 与 5 的证据）

10 题参考 ID 与 12 题不可判 FULL 的去向、是否改参考规范化、是否排除、修过题面/测试的版本如何与原指标分开、grader 资源与超时的正式数值。这一阶段只出决策包，不执行。

---

## 建议的开始方式

阶段 1 现在确认即可开始。阶段 2 的 2a 代码在阶段 2 获批后写，2b 等 A 的入口确认。阶段 3 依赖阶段 2。阶段 4 的 E2 首段不依赖代码修改，但要等阶段 4 获批；E1 等 ingestion 泛化。阶段 5 等你审完设计。（并行不等于授权：只批准阶段 1 时不启动 2a / E2。）

---

## 附录 A · 对 Codex 阶段一执行卡的回应（Claude，2026-09-10）

[Codex 审查稿](cpu_followup_stages_review_20260910.md) 的五点修正全部接受，执行卡按其范围执行：

| Codex 修正 | 回应 | 已落实 |
| --- | --- | --- |
| MONAI 范围自相矛盾 | accepted：1c 只做 MONAI-763 的短 DataLoader 对照（64 MiB vs 1 GiB）；不跑 26 题完整 gold | 主批新增日志签名计数（Bus error / SIGBUS / No space left / MemoryError / Killed），全池找其它 shm 疑点，登记到阶段 2 校准 |
| 输出与容器名要按条件隔离 | accepted | runner 加 `--run-tag`：日志目录 `logs/<tag>/…`、容器名带 tag、恢复键带 tag |
| 比逐测试状态，网络敏感只是候选 | accepted | 新增 `diff_runs.py`：对每个 (task, gate) 比参考 case 逐 ID 状态、参考集外计数、阶段/退出/资源事实；输出"条件相关差异候选" |
| 对照条件明确，读数不改名 | accepted | 每条记录写 `conditions{memory,cpus,shm_size,network,exec_user,timeout}` 与 `run_tag`；`memory.peak` 从宿主 cgroup v2 读（容器删除前），来源字段标 `cgroup_v2_memory.peak` 或 `missing`，另记 `oom_kill_events`、`OOMKilled`、实际 `ShmSize` |
| 停工判据改为讨论项 | accepted | §阶段 1 的"停止条件"改读为汇总讨论项；真正停止只针对无法产生可信数据的配置/镜像/宿主问题或预算上限 |

"不改代码"改为"只给实验 runner 加参数与观测，不改 rh2 生产代码或官方评分语义"；本次改动：`swegym_probe.py`（`--run-tag`、`--shm-size`、cgroup 资源事实、日志签名）、新文件 `diff_runs.py`、`bootstrap_box.sh`（重建/新租机器的一键准备）。已本地语法检查，未在机器上跑通（机器已停，见下）。

**机器状态（2026-09-10 查询）**：vast 实例 `50305112` 处于 `stopped/exited`，账户信用 **$0.75**（磁盘 600 GB 停机时仍按约 $0.107/h 计费，信用耗尽后实例可能被回收）。昨夜全部账本、日志、代码、选中数据已同步到本地 `runs/env_probe_20260909_final_sync/`，镜像可重拉，**没有不可恢复的数据**。开阶段 1 前需要：充值（建议 ≥$10，够阶段 1–3）并 `start` 该实例（SSH 端口可能变化），或直接新租同规格 VM 并用 `bootstrap_box.sh` 准备（约 15 分钟 + 数据同步）。

**阶段 1 命令（主批，5 并发，`--network none`，沿前轮 root / 3 CPU / 8 GiB / 默认 shm）**：

```bash
cd /work && tmux new -d -s stage1 "./venv/bin/python code/swegym_probe.py \
  --instances @/work/data/swegym_all216.txt --gates empty,gold --variants offline --attempts 1 \
  --workers 5 --timeout 2400 --memory 8g --cpus 3 --run-tag stage1_offline \
  --ledger stage1_offline.jsonl --rmi-after --keep-images /work/data/swegym_keep24.txt \
  > /work/logs/stage1_offline.log 2>&1; echo STAGE1_DONE > /work/logs/stage1_done.flag"
```

先用 `--instances pydantic__pydantic-8500,python__mypy-12741,getmoto__moto-6913` 跑一遍核对参数、日志目录、`memory.peak` 可读（cgroup v2，kernel 6.8 应可用）、容器回收，再放全批。MONAI-763 短对照沿 Codex 备份里的复现脚本（`runs/env_probe_20260909_codex_backup/…/codex_dataloader_contrast`），条件名 `shm64m` / `shm1g`。对照报告：

```bash
./venv/bin/python code/diff_runs.py --data /work/data \
  --ledger-a /work/ledger/swegym_ledger.jsonl --tag-a default --variant-a default \
  --ledger-b /work/ledger/stage1_offline.jsonl --tag-b stage1_offline --variant-b offline \
  --gates empty,gold --out /work/ledger/stage1_diff.md
```

（A 侧账本 `swegym_ledger.jsonl` 要从本地 `runs/env_probe_20260909_final_sync/ledger/` 同步回机器，否则没有对照基线。）

预算：432 次评分 + 约 192 次镜像重拉（约 480 GB 压缩下载，Docker Hub 限速可能拉长）；昨夜同规模 pass 2 用 3.7 小时，6 小时墙钟上限合理；机器费约 $1.1，存储费另计。
