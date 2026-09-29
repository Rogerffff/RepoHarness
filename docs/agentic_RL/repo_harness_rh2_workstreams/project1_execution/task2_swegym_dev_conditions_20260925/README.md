# 任务二：已审 SWE-Gym 题的开发条件与修复（执行计划）

2026-09-25 / Claude（B 线主线程）。负责人：Claude B 主线程。任务二和[探针接线](../base_probe_chain_fixes_20260923/b_wiring_handoff_20260924.md)都由本线程负责（用户 09-25 决定）；任务一交给 Codex。上游页是[09-25 交接页](../environment_batch_20260925.md) §2.2，执行方法按[共用开发验证流程](../actor_development_validation.md)。**本页是计划，还没有运行任何东西。** 结果写在本目录，交接页只放链接和摘要。

## 1. 目标与交付

**Codex 完成复核（09-25）：**[独立结果与四项窄修](codex_completion_review_20260925.md)。21 题开发验证的主要结果成立；下一模型批前先修失败导出误送 noop、清理失败仍派发，另处理网关终局识别和初态 dirty 文件再编辑的导出接缝。已知超窗 400 与真实模型冒烟尚未核销，不要求重跑全部 21 题。

**Codex复核（09-25）：**[计划复核与六项落实要求](codex_plan_review.md)。可先做Dask入口；题级配方/材料、夹具的devcheck判据与实际资源、既有模型前提、旧checks以及批跑收口按该页分期补齐。下文是作者原计划，修订回应由Claude继续维护。

目标：为下一轮 GPU 探针准备"开发条件已在真实解题身份下验证"的 SWE-Gym 题，并补齐首轮题的环境缺口。

次晨交付一张逐题表，每题标四种状态之一：

- **可进探针**：写明版本（镜像 / 配方 / 材料）、用途和限制；
- **仅静态判断**：还没在 actor 条件下跑过；
- **待 CPU**：命令已写好但没跑，或跑出了需要再查的问题；
- **需决定**：涉及题面 / 测试修订，属于 T0。

每题附证据目录。另列需要移交 A 线的通用问题。"脚本写好"不算验证完成。

## 2. 共同入口：真实 CC + 桩端点跑开发命令

开发验证必须在"准备交给 Claude Code 的身份和 shell"下取得，不能用 root 或 grader 的结果代替，也不再用首轮的诊断变体 `bash_env_v1`。

做法：复用 A 线的 [`acceptance_startup_2.py`](../../../../../rh2/experiments/base_probe_fixes_20260923/acceptance_startup_2.py)。它已经走正式的容器、relay、网络、可信初始化、激活文件、启动前核对和 `ClaudeCodeDriver.run`，只有模型端点换成桩（`stub_anthropic_endpoint.py`）。我会给它加一个 `devcheck` 场景：桩从每题的命令清单依次发出 Bash 调用，最后 `end_turn`。这样每条命令都由真实 CC 2.1.205 在 agent 身份（UID 54321）的子 shell 里执行，输出保存在宿主轨迹里。

- 共用入口只有本线程一个实现者，逐题只写命令清单（`commands/<task>.json`）和配方；
- 桩按请求全局计数，每次运行用独立端口或串行执行，不并发共用一个剧本；
- 桩的 `count_tokens` 恒回 0，而且直连桩会绕过 Qwen adapter。所以这条入口只验证开发条件，不验证计数、提醒、EOS 和溢出——这些归探针接线（§6）另验。

**先用 Dask8597 打通**：原条件下跑一次，确认入口、轨迹和逐命令结果都能取回，再批量用。

## 3. 每题怎么做

1. **固定输入**：题号、公开镜像 digest、配方版本、base commit；在镜像里记录 `git -C /testbed status --porcelain`，结果为空也要记。
2. **写命令清单**：依据题卡里的开发需求，至少包括：
   - 打印解释器和包来源，确认导入的是 `/testbed` 里的代码；
   - 跑题面原例；
   - 跑相关的公开窄测试，要看到实际执行的数量，只收集不算；
   - 至少一条走公开入口（CLI 或公开 API）的命令；
   - 题目需要的构建、资产或服务。
3. **原条件先跑一遍**，逐条命令记退出码和执行数量，并归类为：目标 bug、环境阻断、无关的既有失败、零收集或 skip、未检查。
4. **只修环境阻断**：派生镜像只加公开开发依赖（pin 加 wheel 的 sha256），不带 gold 或隐藏测试。修完后复跑**同一份清单**。base 仍应暴露目标 bug，不要求全绿。
5. **需要时做私有对照**：另起一个私有容器，把 gold 应用上去跑同样的命令，确认失败来自 bug，不是环境问题。这个容器不交给求解者。
6. **影响评分侧时**：如果修订改了 grader 也会用的依赖，补一次真实 RH2 noop/gold。

## 4. 题目与顺序

### 4.1 首轮 8 题的环境缺口（先做，量小、证据现成）

| 题目 | 已有缺口 | 计划 |
| --- | --- | --- |
| Dask8597 | actor 的 pytest 8.3.2 跑不了旧的 `pytest.warns(None)` | 用 grader compat_v1 的公开依赖（pytest 7.4.4）做 actor 派生；看相关测试是否真正执行、框架 TypeError 是否消失。不删断言 |
| Moto5134 | actor 的 boto3/botocore 1.35.9 与 grader sqs_v1 的 1.28.57 不同；base 上 3 个 SQS 测试失败 | 核对后把兼容版本迁到 actor；看 Events/Logs/SQS 的本地 mock 能否执行，不开放真实 AWS |
| DVC6954 | CLI 能复现题面，但公开功能测试缺 `GIT_OBJ_COMMIT`（pygit2 路径） | 先查该版本 scmrepo / pygit2 / libgit2 的约束，不直接套用别题的 pin |
| Conan15422 | 镜像 cmake 3.22.1，跑不了要求 ≥3.23 的 functional 路径 | 按公开要求固定 CMake 版本；看生成的预设能否被真实 CMake 消费 |
| DVC5839、Moto5752、mypy17071、mypy11236 | 首轮只有 `bash_env_v1` 下的证据 | 在正式入口下各复跑一次原清单，确认结论能迁移（mypy 两题需重建 install_wave1 派生） |

### 4.2 21 个候选里尚未求解的 13 题（主体）

按准备难度排序，前面的先做：

| 组 | 题目 | 已有条件 | 主要风险 |
| --- | --- | --- | --- |
| A：已有 install_wave1 pins | mypy15184、mypy10174、mypy16869、mypy10424、moto6408、moto5960 | 配方可直接重建，wheel 有 sha256 | actor 是否能导入工作区代码；mypy 的类型数据与临时目录可写 |
| B：dvc_install_v1c 配方 | dvc4166、dvc1681 | 已有配方 | 首轮 DVC 两题都出过 actor 专属问题（pathspec、pygit2），不能假定同仓配方可用 |
| C：需先定配方 | pydantic8511（pins 未定）、mypy10308（材料需修订） | 部分 | 先补配方或材料，再验证 |
| D：需重编译 | pandas56849、pandas48106、pandas53958 | pandas_meta_v3 | actor 必须能从 checkout 重建 C 扩展；构建耗时和资源最大，放最后 |

每题的"题意 / 覆盖诊断"（各题 `cpu_queue.json` 里的 priority 1 项，例如 mypy10424 的短路候选、mypy16869 的精确文本断言、pandas56849 的警告文案）**排在开发条件之后**，用固定 grader（`replay_grade.py`）做，今晚能做多少做多少。

### 4.3 首轮题的题意 / 覆盖对照（机器空闲时穿插）

直接执行已经写好的检查脚本（`rh2/experiments/base_probe_20260922/checks/`）：

- Conan15422：固定候选的三处缺口；
- Moto5134：评分选集外的 archive 回归；
- Moto5752：BeginsWith 的对照；
- DVC6954：负数参数的工作流；
- DVC5839：CLI 数值。

另外补写 mypy17071 的短路候选 C1，并用 RH2 评分。只产出事实，题面或测试怎么修订留给你决定。

### 4.4 19 个先诊断项

今晚不主动铺开。只在 4.1–4.3 完成后择优做：优先已经设计好三路对照的 Moto5406（地区 ARN）和 Moto6114。

## 5. 机器

需要一台 **x86_64 的 CPU 机，不需要 GPU**，要求如下：

| 项 | 要求 | 理由 |
| --- | --- | --- |
| CPU | **32 vCPU** | pandas 三题要从 checkout 重编译 C 扩展；同时并行跑多题的 pytest 和派生构建 |
| 内存 | **64 GB**（最少 48 GB） | pandas 编译峰值；约 4 个题目容器并行 |
| 磁盘 | **500 GB** | 按已记录的镜像大小估算（见下）。这是估算，不是承诺 |
| 系统 | Ubuntu 22.04 或 24.04，**能跑 Docker**（优先 KVM VM，cgroup v2），出网正常（Docker Hub、PyPI、npm、GitHub） | 正式启动路径要起容器、建内网和 relay |
| 形态 | 能暂停更好；不能暂停也行，我会在收口时回传证据，并提醒你销毁 | — |

**磁盘估算。** 历史记录里的 SWE-Gym 镜像解压后每个 7–11 GB。本批约 21 题（13 题 + 首轮 8 题），公开镜像约 170–230 GB。派生层大多只加几个 wheel，体积很小，但 pandas 重编译和构建缓存会再占几十 GB。拉取镜像时还需要临时空间。500 GB 大约留出一倍余量；若只有 300 GB，我会分批拉取、用完即删，速度会慢一些。

这台机器同时用于探针接线的 CPU 验证（真实 CC + 桩端点 + 本地 adapter），两件事共用，不需要另租。

## 6. 探针接线（同一线程，并行推进）

按 [A→B 接线交接](../base_probe_chain_fixes_20260923/b_wiring_handoff_20260924.md)和 Codex 09-25 复核的收窄意见修改：

- `qwen_adapter_server.py`：按最新顺序装配：
  1. `install_count_tokens_wire`
  2. `install_parse_wire`
  3. `install_turn_terminal_publisher`
  4. `assert_parse_wire_installed`
  5. 构造生产子类
  6. `bind_count_tokens_adapter`

  在 `adapter_config.json` 里如实记录各包装是否装上。溢出 400 等 A 线提供共用函数，在此之前记 `overflow_400: false`。
- `solve_attempt.py`：
  - 改为逐次注入执行环境，改用宿主日志目录读取轨迹；
  - 接上下文窗口参数，窗口与 adapter 的 `max_context_tokens` 必须取同一个数；
  - 工具白名单和关闭自动记忆已经由 `bringup` 追加，不重复加。每次运行从真实请求里回读实际生效的条件。
- `model_gateway.py`：上游 `stream_error` 后调用 abort 的逻辑已经存在；需要补测"HTTP 正常结束、但缺少 SSE 终局事件"这一分支。

验证：在 CPU 机上用受控的桩上游跑本地 adapter，覆盖正常结束、断流、窗口注入三种情况。真实模型的冒烟测试等租 GPU 时再做。

## 7. 纪律

- 带过 gold 的容器和私有对照不交给求解者；求解输入只有公开材料。
- 旧结果不回写。修前、修后分开记录，不混成同一条件。
- 凭据只从 git-ignore 的文件读取；机器地址只写在 `CLAUDE.local.md`。
- 结构化结果写进 `runs/task2_swegym_dev_20260925/`（git 忽略，放原始证据）和本目录的 `results.md`（逐题表）。
