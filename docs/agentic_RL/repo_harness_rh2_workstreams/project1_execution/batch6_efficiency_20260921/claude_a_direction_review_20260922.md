# 第六组方向检查（Claude A）

2026-09-22 / Claude（A 线分叉）。**状态：检查意见与建议，未实施。** 对象：[第六组 README](README.md)（四项决定、E1–E5、§3 依赖供应）、[B 线补充](grading_environment_b_review_20260921.md)、[A 线讨论稿](grading_environment_options.md)。本轮读了相关源码、既有账本与精读，做了一个只读性质的本机 Docker 探针（§2.3），没有改生产代码。

## 0. 结论

- **四项决定、"当前继续独立评分"：同意，没有方向性异议。**
- **E1–E5 方案成立**，三点补充：优先级建议 E3 先做；E1 针对的"重复 chown"是小头，真正的大头是第一次 chown 触发的整树 copy-up；E2 建议直接用 coreutils 批量，不用容器内 Python。
- **§3 受控依赖供应总体同意**，有两点不同：
  1. 缺一个我认为必需的部件——**按题目时间截止的包索引视图**（同时解决答案泄漏和版本漂移，§4.2）；
  2. **首版不建议调换评分阶段顺序**（Codex 推荐"先安装、后注入私有测试"）。调换会破坏"root 不在候选代码之后执行候选可写位置的东西"这条现有不变量，而它要防的泄漏在"只通包索引、只能下载"的出口下基本不存在（§4.3）。
- 需要你决定的事项 3 项，见 §5。

## 1. 已核对的事实

| 项 | 核对结果 | 位置 |
| --- | --- | --- |
| I25 三处权限初始化 | 属实。可信初始化 `chown -R` 一次；`bringup` 预建用户再一次；vendored slime `ensure_agent_user` 第三次。后两处是 `id agent \|\| useradd … && chown -R …`，shell 按 `(A \|\| B) && C` 结合，用户已存在也照样 chown | `sandbox_profile.py:1021–1031`、`bringup.py:488–495`、`rh2/src/slime/agent/sandbox.py:375–384` |
| I26 逐文件起进程 | 属实。census 脚本对每个文件起 `sha256sum` 与 `cut` 两个进程；基线、运行后、grader 基线重建三处共用同一脚本 | `baseline_census.py:61–96`、`patch_exporter.py:146–`、`manager.py` B4 重建 |
| I23 tape 反复展开 | 属实。同一份数据依次变成 `base64 → list[int] → bytes（落工件）→ tuple（逐轮常驻）→ list → list → torch.tensor` | `projection.py:140–184`、`generate.py:906–1026,1476–1521,1383–1396` |
| I24 forward 条件 | 属实：`not skip_actor_forward_only and (not use_rollout_logprobs or get_mismatch_metrics)` | fork `miles/backends/megatron_utils/actor.py:625–627` |
| rollout 网络 | 每个 attempt 一张隔离 internal 网络，唯一出口是本 run 的 egress relay；relay 是通用 TCP 转发，除模型代理外已支持"环境声明的内部服务"（`InternalService`，`RH2_SANDBOX_INTERNAL_SERVICES`） | `sandbox_profile.py:30–35,252–269,456–458,863–910` |
| grader 网络与阶段 | `--network none`；顺序为 root 可信 setup（激活 conda、git 恢复并应用 test patch）→ root 保护官方测试并把 `/testbed` 与 conda 环境前缀 `chown -R` 给候选用户 → 候选用户一次 exec 内跑安装段＋测试段 | `sandbox_profile.py:582,520,1298–1360`、`manager.py` `_run_eval`、`prepared_task_face.py:100–163` |
| 题目创建时间 | SWE-Gym 行里有 `created_at`，目前归为 `pipeline_meta`，不进任何 bundle | `envpack/ingest_swegym_lite.py:17,57` |

## 2. E1–E5：同意，三点补充

### 2.1 先把收益量级说清楚

216 题旧账本（431 次评分，[汇总](grading_cost_from_existing_ledgers.json)）按总和看：测试段（安装＋测试）16,974 s，占 75%；启动核对 455 s、基线重建 1,865 s、trusted setup 2,423 s、清理 755 s。各阶段中位数：固定开销四段相加约 12.4 s，测试段 20.5 s；其中 fresh 评分特有的部分（启动、基线重建、delta、清理）相加约 7 s。中位数之和不等于总时延的中位数，这里只看量级。

**推论**：相对 600 s 的执行预算，E1/E2/E4 能省的是个位数百分比，单独不会改变吞吐。值得做的理由是并发下的稳定性（进程风暴、写入风暴），不是单次耗时。这与 README "收益不按理论倍数相加"一致，只是希望预期更明确。

### 2.2 优先级：建议 E3 先做

Codex 建议 E1/E2 先做。我建议 **E3（路由 tape 紧凑表示）排第一**，理由是它同时影响稳定性和吞吐，其余切片只影响固定开销：

- 转换发生在 adapter 的事件循环上，期间其它会话的请求与取消都在等。按清单里的历史探针（16K 行约 172 ms/轮）做条件估算：64 个并发会话、每会话约 10 s 一轮 → 每秒 6.4 轮 × 0.172 s ≈ **1.1 s 的阻塞/秒**，单线程事件循环会饱和，表现为模型调用排队、GPU 空等。32 并发、15 s 一轮时约占 37%。**这是估算，不是实测**；E3 的 Brief 应先量"每轮关键路径总阻塞"（含 64 MiB 级响应体的 JSON 解析与 base64 解码，不只是 list 转换），再定只改表示是否足够。
- 常驻内存按 I23 的下限估算可到百 GiB 量级，长上下文多并发时是能让作业死掉的那一类问题。

其余顺序建议：E5 的配置与测量清单（八卡作业前必须就绪）→ E2 → E1 → E4（首次训练的评分次数远不到需要裁剪历史的规模）。

### 2.3 E1：重复 chown 是小头，第一次的整树 copy-up 才是大头

overlay 文件系统上，改属主会把文件**整份内容**复制进容器可写层。本机探针（`swebench/sweb.eval.x86_64.scikit-learn…` 镜像，overlayfs；x86 仿真，耗时不具代表性，只看字节数）：

| 操作 | 可写层大小 | 说明 |
| --- | --- | --- |
| 容器刚启动 | 4 kB | |
| `chown -R /testbed`（244 MB） | **257 MB** | 整个仓库被复制一遍 |
| 再 `chown -R /testbed` 一次 | 257 MB（不变，约 1 s） | 这就是 E1 要消除的"重复"，只有遍历成本 |
| `chown -R /opt/miniconda3/envs/testbed`（882 MB，25,326 个文件） | **1.19 GB** | grader 每次评分都做（D3=A 的 `candidate_writable_prefixes`） |

也就是：每个 rollout 容器约写 0.25 GB，每个评分容器约写 1.2 GB，纯粹为了改属主。代码注释里记录的 run6 事故（8/8 个 django rollout 在 60 s 的 chown 超时）就是这个成本在并发下的表现。E1 按现范围实施后，这部分原封不动。

**候选做法（记为 E1+，需要 B 线配合，先测后定）**：在 B 的派生镜像构建阶段一次性建好 agent 用户并预置 `/testbed`（及需要可写的环境前缀）属主，成为镜像的一层；每次执行只做只读核对（`find /testbed ! -uid <uid> -print -quit` 为空即通过，不触发 copy-up），不再 chown。这保留了 README 要求的"不能用'用户存在'代替目录权限已正确"。grader 目前用另一个 uid（54322），要同样受益需要让两侧候选用户 uid 相同或共用属组——fresh 容器里没有 agent 留下的状态，uid 不同本身不提供隔离（若以后采用同容器评分，这一点要重新评估），但这是 profile 参数变更，需 B 确认。同一次测量建议顺带量"每容器上传/解压/安装 CC"的耗时与写入量（I25 已列，未测）。

E1 原范围（去掉两处重复）仍可照做，改动小、风险低。vendored slime 那一处按 pin 约定处理，Brief 里单列。

### 2.4 E2：直接用 coreutils 批量，不用容器内 Python

`find … -print0 | sort -z | xargs -0 sha256sum` 加 `find -printf` 取类型、执行位、软链目标，就能把每文件两个进程降到每批一个，输出格式不变。不建议 README 提到的容器内 Python 候选：运行后 census 面对的是模型写过的环境，而依赖供应方向会让解释器环境对 agent 可写；root 拥有的 coreutils 是更小的信任底座，也不依赖镜像里有没有合适的解释器。软链目标摘要可以在宿主侧算。文件名含换行或反斜杠时 `sha256sum` 的输出转义规则要在等价性测试里覆盖（现实现按行读取，本来就不支持换行文件名，不借此扩大支持范围）。

### 2.5 E4、E5

同意，无补充。E4 注意 B 的重放 driver 在每次 `grade()` 返回后读 `container_records[-1]` 取候选事实，历史裁剪要保证最近一条完成记录在被取走前还在。

## 3. 评分路线：同意保留独立评分

补充两点。其一，fresh 特有开销在旧账本里约 7 s 量级（§2.3 的 copy-up 已含在 trusted setup 段内，不另加）；真正的大头是测试段里的安装/构建，同容器只有在 agent 已经正确重建时才省得掉。其二，为了以后能便宜地做这个决定，现在只需记三样东西，都不需要新系统：agent 侧实际安装了什么（§4.4 的访问日志）、评分侧安装秒数与测试秒数（已有 `install_seconds` / `test_seconds`）、delta 是否触及构建相关文件。

## 4. 受控依赖供应

### 4.1 同意的部分

两侧共用一个包索引/下载缓存、各容器各自安装、不共享可写 site-packages；出口由网络拓扑限制而不是 `PIP_INDEX_URL`；首版只支持 Python 包，Git/任意 HTTP/conda/apt 按题目例外处理；安装取包与测试运行的网络分开；包源不可用与候选安装错误分开归因。

**rollout 侧不需要新拓扑**：README 让 Claude "先核现有 relay 到固定内部服务的接法"——已核，relay 本来就支持环境声明的内部服务，包索引只是再加一个 `InternalService`，容器内访问 `http://rh2-egress-relay:<端口>/…`，其余地址仍然在路由层不可达。

### 4.2 补充（我认为必需）：按题目时间截止的索引视图

README 的设计里，缓存服务对所有题目呈现"今天的 PyPI"。这有两个问题：

1. **答案泄漏。** 能访问 PyPI 就能 `pip download <被测项目>`，拿到含修复的后续版本源码再 diff。这和 `git log --all` 读未来提交是同一类泄漏，我们已经用 git-sanitize 堵了 git 这一路，开包源等于从另一路重新打开。这不是假想：Qwen3-Coder-Next 报告在 RL 后期观察到 agent **学会**重建 remote、用 clone/curl 取历史（[精读 R3 §4.2.4](../../../../harness_improve/external_paper_references/reading_notes/R3_qwen3_coder_next.md)）；SWE-bench 官方 [issue #465](https://github.com/SWE-bench/SWE-bench/issues/465) 记录了同类行为。训练中这种行为会被 reward 直接强化。
2. **版本漂移。** 缓存只省下载，不冻结解析结果：未锁版本的新依赖今天解析到最新版，对 2019–2023 年的仓库经常装不上或行为不同；同一题不同日期评分也可能不同。SWE-rebench v2 把包源漂移列为自身局限。

**一个机制同时解决两者**：索引服务按 URL 路径提供"截至某时刻"的视图，只列 `upload-time` 早于题目 `created_at` 的文件；rollout 与 grader 对同一题用同一个截止时间。被测项目含修复的版本必然晚于 PR 创建时间，自然不可见；新依赖解析到当时的版本，两侧看到同一个包宇宙。过滤必须在服务端：镜像里的旧 pip 没有相应选项（pip 26.0 才有 `--uploaded-prior-to`），而且客户端参数由 agent 控制，不能当边界。现成部件有 [pypi-timemachine](https://github.com/astrofrog/pypi-timemachine)（URL 形如 `/snapshot/<时间>/`，基于 PEP 700 的 upload-time，自述为 alpha 质量）和 devpi-timemachine 插件；也可以是可信侧一个一两百行的过滤器。代价：每题一个索引 URL，`created_at` 需要进入环境规格（不进模型可见的题面）；个别镜像里预装的包晚于截止时间时，新装依赖可能出现解析冲突，按题目例外处理。

### 4.3 不同意见：首版不调换评分阶段顺序

README §3.2 推荐"应用候选修改 → 联网安装 → 撤出口 → 注入私有测试 → 测试"。我建议首版**保持现有顺序，只把候选段拆成两次 exec，安装段联网、测试段前断网**：

```text
启动（挂在只通包索引的隔离网络上）→ 基线重建、delta 应用          （同现状）
→ root 可信 setup + 保护官方测试                                  （同现状，先于任何候选代码）
→ exec① 候选安装段（可经 relay 取包）
→ docker network disconnect（此后只有 loopback）+ 探针确认
→ exec② 候选测试段（离线，与今天一致）→ 后观测、评分、清理         （同现状）
```

理由：

- **调换要防的泄漏在这种出口下基本不存在。** 出口只有一个只能下载、按时间过滤的包索引，没有上传通道；候选安装代码即使读到私有测试，也没有路径把内容送到以后的 rollout。而且私有测试在测试段本来就对候选代码可读（测试以候选用户运行），调换并没有让它更保密。
- **调换会引入一条真实的新风险。** 现在 root 的可信 setup 发生在任何候选代码执行之前，所以 root 可以放心地 `conda activate testbed`、在 `/testbed` 里跑 git。调换后，root 必须在候选安装代码跑过之后再恢复/注入测试，而此时 `/testbed`（含 `.git/config`、`.gitattributes`）和 conda 环境前缀（含 `etc/conda/activate.d/*.sh` 激活钩子）都已归候选用户所有：root 再激活环境或再跑 `git checkout`，就是以 root 身份执行候选可写的脚本/配置（`core.fsmonitor`、smudge filter 等），F2 对官方测试的保护可以被绕过。README 自己也指出了这一点；要真正解决，得把测试注入改成宿主侧预先物化文件再写入、容器内完全不跑 git 和环境激活——这是对 B 线可信 setup 与评分材料的重做，属于 T0 级改动，换来的保护却很有限。
- README 提到的"部分安装依赖 test patch 改动"在保持顺序时自然不成问题。

残余风险（建议接受并记录）：缓存命中与否的时间差理论上可作为评分侧到后续 rollout 的隐蔽信道，需要策略跨回合蓄意配合，不为此设计。

### 4.4 建议的首版形态

```text
rollout 容器 ─(attempt 隔离网络)─► egress relay ─► 模型代理（已有）
                                        └────────► 包索引服务（新增内部服务）─► pypi.org / files.pythonhosted.org
grader 容器 ─(安装段同样经 relay；测试段前断开)─┘
```

- **包索引服务**（可信侧，每宿主一份）：时间截止过滤 + 下载缓存。缓存层可评估 devpi-server（6.20.x，维护活跃，按需缓存、把文件链接改写到自身）；**待探针确认**它的 JSON 索引是否透传 `upload-time`，据此决定过滤层放在它前面还是自己实现。只开放下载入口，不建用户、不开放上传。
- **配置方式**：在 root 可信初始化里写 `/etc/pip.conf`（索引 URL、trusted-host），同时设 `PIP_INDEX_URL` / `UV_DEFAULT_INDEX` 环境变量。只靠环境变量会在 `env -i`、tox、子进程清环境时丢失。
- **每 attempt 的访问日志**：索引服务按来源网络记录"这次执行取了哪些包"。这是首版最有价值的产出之一：直接回答 B 线的问题（模型到底会不会装、装什么），也能在零分审计时标出"rollout 装了 X、评分环境没有 X"这类环境缺陷，而不必先建三路对照。
- **失败归因**：安装段失败时由 manager 从可信侧探一次索引服务；不可达 → infra / reward=None，可达 → 按现状继续测试（安装退出码仍只进诊断）。
- **agent 侧安装落点**（B 线范围，需一起定）：conda 环境前缀对 agent 不可写时，`pip install foo` 会自动落到用户目录（pip ≥ 20 的行为），通常可用；但重装被测项目自身（`pip install -e .`）会因旧安装归 root 而失败。这与 §2.3 的 E1+ 是同一个问题的两面——在派生镜像里一次性把属主处理好，两边都解决。

### 4.5 归属

网络拓扑、relay、索引服务、grader 的网络挂接与断开归 A；候选脚本拆成安装/测试两段、`created_at` 进入环境规格、agent 侧安装落点与代表题归 B。`manager._run_eval` 与 `prepared_task_face.py` 两线都会碰，网络 Brief 里按函数列清先后。

留给网络 Brief、与 B 一起定的一个开放点：评分侧联网是对**所有**评分生效，还是只在候选改了依赖声明时生效。前者行为统一，但评分环境变了，需要 B 对题池重跑一次 noop/gold 对照；后者影响面小，但评分链多一条分支，且"是否改了依赖声明"只能靠文件名启发式判断。我倾向前者。

## 5. 需要用户决定

| # | 事项 | 我的建议 |
| --- | --- | --- |
| 1 | 包索引是否采用**按题目时间截止**的视图（§4.2） | 采用。不采用时，至少要在服务端按题目屏蔽被测项目自身的包名；但那样不解决版本漂移 |
| 2 | 评分阶段：**保持现有顺序、安装段联网、测试段前断网**（§4.3），还是按 README 调换为"先安装、后注入私有测试" | 首版保持顺序。调换留待出现具体需要时再议，届时连同宿主侧物化测试文件一起设计 |
| 3 | 是否让 B 线评估 **E1+**（派生镜像预置属主、两侧候选 uid 对齐，§2.3） | 先做一次目标机测量（首次 chown 耗时与可写层字节、CC 安装耗时），数字支持再交 B 评估；不阻塞 E1 原范围 |

首版来源范围只含 PyPI（pip/uv）我按 README 的建议默认执行，不单列决定；如果你希望首版就包含 conda 或 GitHub，请指出。

## 6. 方向确认后的安排

E3 窄 Brief → E5 配置与测量清单 → E2 → E1（含 §2.3 的测量）→ E4；依赖供应另起短设计，先做两个半天级探针：devpi 是否透传 upload-time、`--network none` 之外的"先挂后断"在目标 Docker 版本上的行为。各片独立交付、Codex 独立检查。

## 附：外部做法对照

| 来源 | 网络/泄漏处理 | 对本设计的含义 |
| --- | --- | --- |
| MAI-Thinking-1（[精读 R1 §6](../../../../harness_improve/external_paper_references/reading_notes/R1_mai_thinking_1.md)） | 默认隔离；必要联网走缓存代理 + 域名允许列表；限网以防搜到公开 PR | 方向一致；未披露如何处理包仓库里的后续版本 |
| Qwen3-Coder-Next（精读 R3） | 保留网络以装依赖、查文档；用命令启发式拦"仓库链接 + 网络关键词"；观察到 agent 学会取历史 | 启发式拦截不如拓扑限制可靠；泄漏行为会被 RL 学到 |
| Nemotron 3 Ultra（精读 R2） | 物理重写 git 历史；运行时命令过滤拦远端 git 与 GitHub 下载 | 同上 |
| SWE-bench 官方 harness、SWE-rebench v2 公开 CLI | 评测容器有网络（后者 `--network host`） | 我们"只通按时间过滤的包索引"比来源基准更严，不存在因断网偏离官方评测的问题 |
| R2E-Gym | 训练不提供互联网 | 纯离线可行，但新依赖题无法评分 |
| pip 26.0 `--uploaded-prior-to`、[pypi-timemachine](https://github.com/astrofrog/pypi-timemachine) | 按上传时间过滤的现成机制 | 支持 §4.2 的可实现性；客户端选项不能当边界 |
| [devpi-server](https://github.com/devpi/devpi) | PyPI 按需缓存镜像，6.20.3（2026-06） | 缓存层候选，upload-time 透传待探针 |

## 7. 对 Codex 复核的回应与用户倾向（2026-09-22 追加）

[Codex 复核](codex_direction_review_20260922.md)的四条修正我核对后全部接受，上文相应表述以本节为准（上文不回改）：

| 我原来的说法 | 修正 |
| --- | --- |
| §2.1"E1/E2/E4 单独不会改变吞吐" | 过强。600 s 是预算上限不是收益分母；真实执行时长、存储是否拥塞、grader 是否成为供样瓶颈都没有数据。只能说"旧账本里这些阶段通常是秒级"，不预报加速，也不预报无加速 |
| §2.3"overlay 上改属主会整份复制" | 只对未开 metadata-only copy-up 的配置成立。本项目自己的记录里就有目标机证据：开启后 dvc 的 chown 约 180 s → 11 s，随后又因 metacopy/native-diff 与 `docker commit` 组合把文件内容变成全 0 而撤回通用开关（[评分接线记录](../swe_grading_wiring_20260915.md)）。我漏看了这段 B 线历史。本机 0.25 / 1.2 GB 只是该探针条件下的事实；E1+ 按 Codex 的四点执行：目标机诊断时顺带记录存储模式与首次/重复 chown 成本，rollout 与 grader 可以各有自己 UID 的派生层（不必合并 UID），delta 重放后新文件的权限仍要单独处理，不借机扩大 agent 可写范围 |
| §4.3"只能下载，没有信息外发路径" | 不正确。GET 路径与查询参数本身就能携带数据，是否到达上游取决于服务如何校验与转发。没有证据表明发生过泄漏，但文档不能承诺"私有材料可见后无出站信息" |
| §4.4"安装失败后探一次索引，不可达即 infra" | 证据不足：服务可能失败后恢复，也可能候选编译失败之后才抖动。健康检查只作诊断，归因沿用安装日志里确证的取包错误与阶段事实，判不了的保持未确定 |

另外两处是我方案里的实质缺陷，同样已核对属实：

- **grader 不能直接挂 rollout 的 relay。** `relay_listen_map()` 恒含模型代理端口，挂上去候选代码就能碰到模型代理。grader 需要只开放包服务一个目标的窄接法。relay 还会抹掉来源身份，"按来源网络记账"行不通，要由宿主为每个 attempt 绑定索引入口。
- **不能把一次 Bash 拆成两次 exec。** `prepared_task_face.py` 明确保证安装段与测试段同一 shell；真实的 MONAI-763 配方开头就 `export OMP_NUM_THREADS=4 …`，拆开后测试段读不到（Codex 的真实 Bash 探针：同 shell 0/0，拆开 0/1）。

### 7.1 用户选择一：我改为同意 1A

用户倾向 Codex 的 1A（默认不提供被测项目自身的远端发行包，第三方依赖不按题目日期截断）。**核对 Codex 的反例后我同意，撤回"时间截止视图是必需的"。** 决定性的事实是：MONAI-763 的 `created_at` 是 2020-07-15，而 B 已验证的修复配方装的是 2022-08 发布的 `nibabel==4.0.2`。也就是我们验证过的环境本来就不是"题目当年的依赖世界"，在它上面套一个 2020 年的索引视图，新装依赖会解析到与现环境不兼容的旧版本，挡住的合法安装可能比堵住的泄漏多。我担心的泄漏入口（下载被测项目的后续版本）由 1A 直接堵住。

1A 要成为真实边界，网络 Brief 里需要落实三件事（都属实现细节，不需要用户再选）：

1. **仓库 → 发行包名的对应表，含同源的其它发行名。** 题池只有 11 个仓库，可以手工维护；注意不同名的情形：`facebookresearch/hydra → hydra-core`（同仓库还有若干插件发行包），`Project-MONAI/MONAI → monai` 与每周构建的 `monai-weekly`。按 PEP 503 规范化后匹配。
2. **按 attempt 绑定、候选改不了。** 屏蔽必须按题目生效而不是全局并集（dask、modin 的题需要装 pandas，全局屏蔽 pandas 会误伤）。做法是宿主为每个 attempt 登记一个不可猜的索引入口（写进 root 拥有的 `/etc/pip.conf`），服务端按入口查该题的屏蔽名单；索引页和文件下载都要过这条规则，未过滤的父索引不对容器暴露。这个入口同时解决了访问日志按 attempt 归属的问题。
3. **不声称可复现。** 1A 不解决版本漂移；正式作业要写清固定了哪些配方/供应版本、哪些依赖仍动态解析，并记录实际取得与安装的版本。

### 7.2 用户选择二：保持现有顺序（2A），机制按 Codex 的修正调整

用户同意保持现有顺序。落到实现上，我把 §4.3 的"拆成两次 exec"改为**同一 shell 内加一道可信闸门**，这样安装段的 `export`、工作目录、shell 选项全部原样保留，总期限、tee 日志、收口事实也都还是一次 exec：

```text
（同一个候选 shell）安装段 … echo RH2_PHASE_END=install
→ 脚本在此等待 root 目录下的闸门文件出现（候选用户无权创建）
→ manager 看到安装段结束标记后：断开包服务网络 → 探针确认已无出口 → 以 root 创建闸门文件
→ 脚本继续跑测试段
```

候选提前伪造结束标记只会让自己的安装提前断网；manager 断网失败则不放行并按 infra 处理，不会出现"带着网络跑正式测试"。同时按 Codex 的表述明确接受：私有测试已可读时，候选仍可向包服务发请求。可选的廉价收敛手段留给 Brief 评估：服务端只转发规范化后且确实存在的项目名、丢弃查询参数，把可携带的信息压到很低。

### 7.3 接下来

E1–E5 不依赖上述两项选择，先起 E3 的窄 Brief；网络短设计在用户把选择一从"倾向"确认为决定后再写。
