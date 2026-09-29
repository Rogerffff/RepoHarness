# 旧主张核对（读历史后）：aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2

- 角色：R2E 私有主审；2026-09-25。本文在 `analysis_before_history.md` 保存之后写成，不改动那份初稿。
- 读过的历史材料：`history/.../refs.json` 列出的 8 项全部读过：
  - 本题的 `findings.md`、`screening_record.json`、`facts.json`；
  - `known_issues.json` 中本题所属的 4 个问题族；
  - `decisions.md`（按 E06 / E09 / E10 查找相关条目）；
  - `results_20260924.md`；
  - `repros/aiohttp__6183….py`；
  - `packages/p1/README.md`（只读与本题相关的段落）。
- 为核对旧主张而打开的原始证据：
  - `runs/r2e_env_repair_20260924/p1/{dev_probe,dev_probe_posthoc2,dev_probe_posthoc3}/aiohttp__6183…/dev_probe.json`
  - `runs/r2e_rf_20260923/reconcile_all/reconcile.json` 中本题的两行
  - `runs/r2e_rf_20260923/remote/prepared_r2e/prompts.jsonl` 第 5 行
  - `runs/env_overnight_20260916/M3/facts/618335186f22/facts/initial.diff`
  - `rh2/src/repoharness2/grading/manager.py:377-393`（`FrozenDeltaSource`）
  - 工作树 `Makefile`
- 协调者 09-25 的事实更新（本人没有独立核实）：正式 actor 已改用派生镜像，`.venv` 解释器前缀与 R2E 提示措辞一并改了，待 A 线审查；devcheck 就是按这个正式任务面跑的。
- 判定的含义：
  - **确认**：旧主张成立，并有新的决定性证据；
  - **推翻**：旧主张被证据否定，可以是全部否定，也可以是部分；
  - **过时**：当时成立，后来被新事实取代；
  - **未核实**：本次没有取得决定性证据。

## 1. 逐条对照

| # | 旧主张（来源） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| 1 | "环境支持本题的解题与判分"，分类 `solver_condition`（findings 结论） | **确认**（限环境层面） | 评分侧 noop 两次都是 45/47、gold 两次都是 47/47，日志去掉时间戳后逐字相同。devcheck（正式任务面，agent 54321）中导入、`python -m pytest`、C2/C3 都能跑。环境层面的判断与我一致；题意与测试层面的问题（I1–I3）是历史没有审的范围，不构成对这条的推翻 |
| 2 | "处置暂记 `unknown`，只差 R13"（findings） | **过时** | 同一份 `screening_record` 后来把 R13 改为 pass，`disposition.state` 改为 `environment_qualified`（review_notes 09-23）；`results_20260924.md:16` 也是这样记的 |
| 3 | R-f 的 noop 为 0、gold 为 1；与 5 份参考日志对账结果为 agree（findings；R15） | **确认** | `reconcile.json` 中本题 noop 与 gold 两行都是 `agree=True`，reward、差异集合、观测映射三项都相等；M3 的 gold 两份日志各 47 passed，sha256 与 `run_refs.json` 一致 |
| 4 | R03 "题面描述准确，示例用 mock transport，**照写即复现**" | **部分推翻** | 旧复现脚本第 35 行写的是 `chunks = [c[1][0] for c in write.mock_calls]`，已经把题面示例的 `[chunk for chunk in write.mock_calls]` 改掉了。题面原句里的元素是 `mock._Call`（长度为 3 的元组），真值恒为 True，所以按原样写的 `assert all(chunks)` 在 base 下不会失败（静态推断，未执行）。另外，"提前 EOF"只在 chunked 写出器下出现，这个配置旧脚本是自己另写的 B 段，不在题面示例里（题面示例设了 Content-Length）。"bug 确实存在"这一点成立（devcheck 的 C2/C3 与旧脚本的 A/B 输出逐字相同），"照写即复现"不成立。我的记录因此在清单 23 上记 issue（I2） |
| 5 | 公开复现 A 写出 2 次空块，B 正文开头就是零长块（findings；R09；p1 dev_probe 的 `REPRO_OUTPUT`） | **确认** | 旧输出 `A: … [b'', b'', b'KI,I\x04\x00']` 与 `B: chunked body=b'0\r\n\r\n6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`，与 devcheck 的 `mcve_c2_writes.out` / `mcve_c3_chunked.out` 逐字相同；在私有对照中应用 gold 后两者都修好 |
| 6 | R16：目标键 ↔ 题面"deflate 下写出空块" | **确认，但不完整** | 映射成立：noop 失败都发生在 `assertTrue(all(chunks))`（test_1.py:474、:438）。历史没有检查标题描述的"提前 EOF"有没有隐藏键覆盖。**新发现 I1**：没有任何键覆盖"压缩在最后 + chunked 写出器"。因此只在 `_write_length_payload` 跳过空块的 P1 预计能拿 47/47，但 C3 失败（静态推断；协调者已安排真实评分） |
| 7 | "缺口：无影响判分的缺口"（findings） | **部分推翻**（按题意与测试口径） | 在环境与判分正确性的口径下成立：noop/gold 可以解释，没有 infra 失败。但 I1 意味着一个不完整的修复也能得 1，这是影响奖励正确性的测试缺口 |
| 8 | R04：脏改动属于基线，正式链的 `FrozenDeltaSource` 按基线 census 求 delta，不会被卷进候选补丁 | **确认，但需补充** | `manager.py:377-393`：评分输入是相对基线清单的逐路径冻结条目，应用方式是直接写文件。候选没有碰这 4 个文件时确实不会卷入。**补充 I3**：如果候选把这 4 个文件还原到 HEAD，这就是一条相对基线的修改，会在评分时重放。`initial.diff` 显示还原后是 `asyncio.async(`，它在 Python 3.9 下是语法错误，于是 `import aiohttp` 失败、隐藏测试全部收集失败、得 0（静态推断）。而 Claude Code 的 gitStatus 会把这 4 个文件显示为 `M`（devcheck `messages_000.json`），会诱导候选去还原 |
| 9 | R05 / 问题 3：兼容改写在 3.9 下报 `TypeError: create_task() got an unexpected keyword argument 'loop'`，`test_client_functional.py` 基本全部失败，`protocol.py` 不受影响 | **确认** | 我初稿里这是静态推断，现在有执行证据：posthoc2 的 `REPRO_OUTPUT` 根因行就是这条 TypeError；`initial.diff`（sha256 `46bd9947…`，与工作树清单一致）是 4 处 `asyncio.async(` → `asyncio.create_task(`，都保留了 `loop=` |
| 10 | 问题 1 / R05：包没装进 venv，只能在 `/testbed` 下导入；裸 `pytest` 收集报 ImportError；`python -m pytest` 或设 `PYTHONPATH=/testbed` 都正常 | **确认**；findings 里"cwd /testbed"的说法**过时** | posthoc3：`python -m pytest` 收集 47 个，rc 0；裸 `pytest` rc 2，报 `ImportError while importing test module`；设 `PYTHONPATH=/testbed` 后正常；`/testbed` 之外的脚本报 `ModuleNotFoundError`。`known_issues` 已把说法更正为"`/testbed` 须在 sys.path 上"，findings.md 仍写"cwd /testbed"。**补充**：旧记录写"make .develop 没有留下 editable 安装，原因未查"。本题工作树的 `Makefile` 只有 `develop` 目标（第 10 行），而 `install.sh:4` 调用的是 `make .develop`，没有对应规则可执行，这可以解释本镜像为什么没装进 venv（静态推断；其它 4 张 aiohttp 镜像没有核对） |
| 11 | 问题 2：venv 没有 pip，uv 不在 PATH | **确认** | devcheck `env.out`：`/testbed/.venv/bin/python: No module named pip`；旧探针 `WHICH_uv=MISSING` |
| 12 | 公开测试噪声族：aiohttp 0.x 两题整目录 `tests/` 会被收集错误中断；本题相关文件 `tests/test_http_protocol.py` 47/47 | **确认，并补充** | devcheck 与私有对照中 `test_http_protocol` 都是 47 passed。**补充**：`tests/test_wsgi.py` 加 `tests/test_web_response.py` 在 base 和 gold 下都有 3 个与本题无关的 cookie 失败（`Max-Age=0` 残留、`name=""` 带引号）。这个基线历史里没有记录，解题者做回归对比时需要知道 |
| 13 | R07：隐藏测试在根目录与工作区都不存在；`/rh2_private` 对 agent 拒绝访问 | **确认**（正式任务面下重新取证） | devcheck preflight：`RH2_PREFLIGHT_HIDDEN_TESTS=ok`（该检查覆盖 `/r2e_tests`、`/testbed/r2e_tests`，以及 `/rh2_private/r2e_tests` 是否可读） |
| 14 | R10 / `solver_conditions.network`："none（`--network none` 仍保留回环）" | **确认**无出网；网络形态的描述**过时** | 正式任务面不是 `--network none`：容器接在专用网络上，只有模型 relay 能连通（`NET_relay=CONNECTED`），外部 DNS、禁止目标、直连上游都被拒（`prelaunch.json`）。本题不需要网络，结论不变 |
| 15 | R12：峰值 171 MB，测试约 1 s | **确认** | 4 行评分账本的 `mem_peak_mb` 在 171–178 之间，`test.seconds` 在 0.72–0.89 之间 |
| 16 | R13：noop、gold 各同条件跑 2 次，reward 与差异集合一致 | **确认** | 我对 4 份 eval log 去掉时间戳后比较，noop 两份、gold 两份分别逐字相同 |
| 17 | R14：每次评分都是 fresh 容器，探针前后 git status 都是 7 行 | **确认**（部分） | devcheck 的 `post_run_facts`：`RH2_GIT_STATUS_LINES=7`；账本 `cleanup.removed=true`。并发没有研究（15：not_checked） |
| 18 | R17：git 卫生（HEAD 没有子提交，refs、remotes、reflog 都是 0），派生镜像里没有修复 | **确认**（正式任务面下重新取证） | devcheck 的 `git_sanitize`：`REFS_REMAINING=0`、`REMOTES=0`、`REFLOG_ENTRIES=0`、`UNREACHABLE_OBJECTS=0`；preflight `GIT_HISTORY=ok` |
| 19 | R01、R02、R08 pass；R06、R11 not_applicable（47 键全部 PASSED，没有资产） | **确认** | 哈希、base、导入路径 `/testbed/aiohttp/__init__.py`、47 键全部 PASSED |
| 20 | R18：没有资源配方或材料修订 | **确认** | `revisions.json` 为 `[]`；`run_refs.current_material.env_recipe/resource_recipe` 都是 null |
| 21 | R19 / R20：流程与证据命令的记录；"导入需 /testbed"这一条件对 5 张 aiohttp 镜像的适用范围 | **未核实** | 超出本题范围；我没有复跑，也没有核对其它 4 题 |
| 22 | E09：提示写 conda、解释器前缀默认 conda，是 A 线的接缝，只留证据 | **过时**（据协调者告知） | 协调者 09-25：正式 actor 已改为派生镜像、`.venv` 前缀和 R2E 提示措辞，待 A 线审查。devcheck 的 `activation_check` 显示 `ACT_EXPECTED_PREFIX=/testbed/.venv`、核对 ok。**新的提示文本本人没见到**：devcheck 的 user 消息被换成了 devcheck 指令，系统提示里没有提示文字 |
| 23 | `disposition.state=environment_qualified`，范围是"当前材料 + r2e_derive_v1 + 默认 rollout profile" | **确认**（环境侧状态） | 与本次静态处置互不冲突：环境资格成立，但题意与测试层面有 I1–I3，所以静态处置记 `needs_review`（静态候选待 actor 验证）。`environment_qualified` 不应被理解为测试能正确区分所有修复 |

## 2. 本人相对初稿的改判与理由

- **S1、S2 从"共享阻塞"降为"已实施、待 A 审"。** S1 是正式 actor 仍用来源镜像，S2 是提示写 conda/pip。依据是协调者的事实更新，以及 devcheck 就是按正式任务面跑的。清单 29 因此由 issue 改为 pass，并注明依据 devcheck、正式改动待 A 审。我没有见到新的提示文本，所以清单 3 仍记 unknown。
- **S3 缩小。** R-f 的 `prompts.jsonl:5` 渲染出的任务文本与 `user_prompt.txt` 逐字相同：1248 字符，代码块完整。这说明任务正文的渲染可以确认；仍然缺的只是正式链里组装后的完整消息，即提示加正文。
- **兼容改写的 TypeError、裸 `pytest` 收集失败，由静态推断或"环境卡转述"升级为执行证据**（历史 posthoc2 / posthoc3）。
- **I1、I2、I3 与暂定处置不变。** 历史没有触及 I1 和 I3；I2 与 R03 冲突，我保留 I2，理由是旧复现脚本自己就没有按原样照抄示例断言。

## 3. 与历史的主要分歧（摘要）

1. **I1 漏测**：历史的 R16 只核对了"空块"这个映射，没有审标题所说的"提前 EOF"有没有键覆盖。我认为没有覆盖，部分修复 P1 可以得 1（静态推断，真实评分已由协调者安排）。
2. **I2 与 R03**："照写即复现"不成立：示例断言按原样恒为真，示例配置也不是标题描述的那条路径。
3. **I3 是对 R04 的补充**：候选不碰脏改动时不会卷入 delta；但候选如果还原脏改动，就会被重放，导致导入失败、得 0。
4. 其余环境结论（导入条件、无 pip、无出网、兼容改写、公开测试噪声、gold/noop 可解释、可重复）都**确认**；另外补充了 `test_web_response` 的 3 个基线失败，以及 `make .develop` 目标名不匹配这一静态解释。
