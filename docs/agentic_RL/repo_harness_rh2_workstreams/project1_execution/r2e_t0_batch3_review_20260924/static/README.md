# R2E 固定材料独立复核：Production Tracer

2026-09-25，Codex 独立子审。对象是 `r2e_static_prep_20260924` 与 `runs/r2e_static_prep_20260924/v1/`，范围止于环境收尾到静态审查的材料边界。已读仓库 `AGENTS.md`、审查标准、最新 B 线记录与材料准备说明；未做 48 题题意或评分质量审查。

**结论：当前 v1 材料通过限定验收，可以进入静态审查。** 有一个非阻塞工具 P2：原 `verify` 不检查工作树实际字节，且空镜像输入可返回成功。本轮独立探针已直接核对当前 v1 全部文件，因此该缺陷不否定本轮材料。33 题缺安装脚本等未跟踪文件已准确披露，不要求为了静态阅读补拉 33 张镜像。

## 1. 真实入口与所有权

`prepare` CLI → `load_trusted_r2e_ingest_outputs` → 当前三份 bundle（48 个同集主键）→ 公开行与当前 `render_user_prompt` → base 原始 blob → M3 `initial.diff` → 镜像未跟踪文件 → `public/`；当前评分/验证面、修订单与来源测试 → `private/`；调查记录路径 → `history/`。此工具不进入训练消费链。

这是协调者运行的单次离线 Python 进程；同步调用 git 读对象/应用差异，无后台线程、队列或长期状态 owner。协调者拥有新版本输出目录；`prepare` 拒绝覆写已有目录。原 `verify` 会写回所指定目录的 `material_check.json`，因此本次**没有在 v1 上执行它**。

独立探针不调用原导出/差异/verify helper：直接读取当前正式 trusted 入口与 JSONL，重算 v1 实际文件；未改文件按 Git blob 对象摘要核对，12 题差异在内存逐 hunk 校验旧上下文、行数与 index hash，再比较结果。没有运行题目代码、fetch、Docker、SSH，也没有重建或写回 v1。

## 2. 不变量与实测

完整逐题/逐镜像结果见 [probe_result.json](probe_result.json)，可复现脚本见 [probe_materials.py](probe_materials.py)。

| 边界 | 独立核验结果 |
| --- | --- |
| 输入身份 | 当前 trusted 摄入入口通过；公开/评分/验证面与三类目录主键均为同一 48 题。代码摘要、ingest manifest `adbd27a1…`、修订单 v3 `0e47ad41…` 与固定核验记录一致；文档和 v1 两份 `material_check.json` 逐字节相同。 |
| 公开面与提示 | 48 份原行及其行摘要与当前摄入面一致，48 份提示逐字等于当前 `render_user_prompt`；每题公开目录只有规定的五项。提示未冒充捕获的真实模型请求。 |
| base 与脏树 | 49,932 个 base blob 均核对；48 题 M3 HEAD 均等于 base。12 题共 38 个修改文件、7 个删除文件独立重放成立，7 个 `pyproject.toml` 确实缺席。19 个 gitlink 均为记录的提交与空目录。 |
| 工作树守恒 | 49,932 base blob − 7 删除 + 67 未跟踪文件 = 49,992 个文件/软链；实际路径与 manifest 精确相等，无额外文件。67 项为 48 `run_tests.sh`、15 `install.sh`、3 aiohttp 脚本和 1 `datasets` 软链。 |
| 私有面 | 120 个隐藏文件均与当前评分面摘要和原文/修订单/M3 副本一致；48 份 gold、expected、run_tests 与当前行及摘要一致；20 条修订单完整对应；原始 expected 按修订重放后与当前 expected 相同。 |
| M3 与镜像文件证据 | 48 `run_tests.sh` 摘要与 M3 原记录一致。15 份 image_hashes 的 19,795 项记录包括 19,785 个现存文件/软链、7 删除和 3 gitlink，全部与 v1 实际文件吻合。36 处 mode 差异均为镜像 0664、导出 0644，无执行位变化。 |
| 缺失说明 | 33 缺 `install.sh`、6 缺 `datasets`、2 缺 `process_aiohttp_updateasyncio.py`，共 41 项，都在逐题 manifest 中明确且实际缺失；没有用其它题脚本代填。 |
| 链接与阅读边界 | 46 个软链全部可解析，最终目标都在本题工作树内。公开文件逐项可归因于冻结公开行、中性事实、base/M3 和已公开的构建文件；未发现新增 gold、隐藏测试、expected 或历史 findings 混入。 |
| 历史与证据定位 | 48 份 history refs 都指向存在的记录/findings/提案；私有 refs 的 12 次“本地缺失”实际是路径带 `#L…`，去掉行锚点后文件均存在，无真实证据文件缺失。 |

脏树覆盖包括 pandas 7 题、aiohttp Makefile 三题及旧 Python 源码兼容改写两题；镜像比对覆盖 pandas 全 7 题，以及 aiohttp `1c1c0ea3`、`240da100`、`61833518`。另外两个 Makefile 类题有完整差异重放，未冒充经过镜像实测。

## 3. 必须保留的证据限制

15 份 image_hashes 只证明其记录的镜像与**公开工作树**一致，不证明 15 张都采用当前完整环境配方。与已归档最新覆盖表比较：coveragepy `016af5f6`、datalad `58ba5165` 两份 image ID 相同；aiohttp `240da100`、`61833518` 两份是来源镜像；其余 11 份是较早派生镜像 ID。逐题两组 ID 已列入 `probe_result.json` 的 `images`。

这个限制不阻塞当前材料：后续 `material_v2.sh` 只改 `/rh2_private/r2e_tests`；`env_v1.sh` / `env_v2.sh` 只在 `.venv` 安装所列 wheel。这些位置都不属于此次导出的公开树，公开文件已有独立 base/M3 与实际文件证据。当前配方是否真正构建与评分通过，应引用本批环境/评分证据，不能引用这里的 15 份摘要替代。

中性环境说明只取 Python 版本、pip 是否存在、cwd/pytest、xvfb、git 身份和包版本等事实，没有拼接包含隐藏键或历史结论的备注。numpy `2f4a9650` 所写 4 GiB / `/tmp` 1 GiB 是解题侧默认条件；12 GiB / 6 GiB 是已记录的 grader 逐题配方，二者没有互相冒充。公开的来源 `run_tests.sh` 已在镜像工作树中存在，不据此新增“必须隐藏来源入口”的审查闸门。

公开/私有/历史路径的分发仍是同一文件系统上的阅读约定，不是系统隔离。源题面本身是否泄漏答案、测试是否充分，都留给正式质量审查。

## 4. 非阻塞 P2：verify 可在实际文件损坏时给出成功

- **当前行为与可达性**：材料说明的重建流程真实调用 `prepare_materials_r2e.py verify --out …`。该 CLI 在 [prepare_materials_r2e.py](../../r2e_static_prep_20260924/prepare_materials_r2e.py:415) 枚举 image_hashes，在第 418–419 行只读取保存的 `man["files"]`，不读取对应工作树；第 450–452 行写回结果，并对空集合使用 `all()` 返回 0。标签为 `production_reachable`；实际 CLI 的合成输入反例已复现，未宣称当前 v1 已损坏。
- **违反的不变量**：作为“把镜像记录与导出工作树逐文件比对”的验收入口，应证明当下被交付的文件一致，不能只证明两份历史摘要彼此一致；缺失全部镜像输入不能记为完整成功。
- **证据/复现**：[probe_verify_cli.py](probe_verify_cli.py) 在本审查目录内建立临时单文件夹具，调用真实 CLI 三次：健康输入 rc=0；只改实际 `worktree/file.txt`、保留旧 manifest 后仍 `OK` / rc=0；指定不存在的 image 目录仍 rc=0，并将结果写为空对象。结果见 [probe_verify_result.json](probe_verify_result.json)。临时夹具结束即清除，v1 和历史核验文件未改。
- **影响与分期**：以后的文件漂移或 image 输入路径写错会被误报通过。本轮全量实际文件已有独立探针补证，因此不阻塞开始静态审查。建议 owner=材料工具维护者，gate=下次重建或再次依赖此 CLI 作验收前修；无需重跑容器或 48 题评分。
- **最小修复**：verify 重算工作树文件集合与摘要，核 manifest 自证后再与镜像记录比较；无 image 输入时明确失败或记录为未验证，不能给总成功。保持单进程、单次失败即退出即可，不新增 owner、retry、恢复状态或训练拒绝逻辑。无需删除整个核验能力，也无需扩大到全池镜像复跑。
- **验收条件**：健康夹具通过；只改实际文件字节、增删文件或改变软链时返回非零并定位差异；空 image 输入不报成功；当前 v1 独立核验结论保持可重现。

复现命令（仓库根）：

```sh
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_t0_batch3_review_20260924/static/probe_materials.py
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_t0_batch3_review_20260924/static/probe_verify_cli.py
```

## 5. 停止条件与标准复盘

本角色的 48 manifest/公开边界、12 dirty、15 imagehash 核对已完成，到此停止。两个聚焦探针运行成功；不是 pytest 计数，无 skipped / xfailed。crash/cancel/timeout/retry/restart/queue-full 的训练故障注入不适用于本次只读离线材料边界；本次覆盖的 artifact 故障是实际文件与摘要漂移、镜像输入缺失。

适用维度为 A/D/E/F/G/H/I/M/N：来源与目录边界、真实 CLI、冻结版本、诊断与依赖身份。B 的 reward/训练分布、跨线程生命周期及训练挡板本次不变，交主审相应角色。发现的 P2 已由 E/G/M 覆盖，无需新增审查维度或闸门。当前通过仅为静态材料可读、可追溯、没有新增私有材料混入，不代表任何题已获准入池。
