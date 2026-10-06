# P4 包报告：pillow ×7、scrapy ×5（R2E 第一轮环境审查，2026-09-24）

P4 sub-agent，交 Claude（B 线）验收。标记：**已实施** = 本包做了的事；**已验证** = 有命令输出或日志为证；**提案** = 待用户 / 主会话决定，本包未落地。本包没有新的“已决定”，只执行 E01–E10。路径都相对仓库根。

## 0. 结论

- **已验证**：12 题环境层面都能支持解题与评分：派生镜像复核 12/12；探针最小开发条件 12/12（agent/54321、`--network none`、rollout 资源与能力）；noop 0 都来自目标键；gold 1 都达到来源定义；与独立 runner 逐键一致 12/12。
- **提案（T0）**：3 题有材料问题。pillow `2b061b68` 的公开题面与目标测试矛盾。scrapy `9a15fcf8` 的期望会惩罚更完整的修复，已**实测**：一个修得更全的候选被判 0。scrapy `cfed9b66` 有隐藏测试搬迁伪影，题面主体没有能验证的键。
- **解题侧条件（12 题共同）**：venv 里没有 pip，与公开提示“`pip` already points at it”矛盾；无网络，但 loopback 可用；`cwd` 不受限，在 `/tmp` 下也能导入。按题的额外条件见 §2.2。
- **未决**：R13（重复一致性）只有 pillow `3ac9396e` 已通过（3 次运行）。其余 11 题要等中央复跑，读取时复跑只到 22/48、还没跑到 pillow / scrapy，由主会话验收时并入。

## 1. 逐题表

| 题 | 分类 | 处置 | 关键 issue | 证据（`tasks/<iid>/` 下 screening_record.json / findings.md，另列） |
| --- | --- | --- | --- | --- |
| pillow `2b061b68` | material | needs_decision（R13 待并入） | 题面称 `formats=['JPEG']` 打开 PNG 应成功，目标测试要求它抛 `UnidentifiedImageError`；题面所述 Warning/NoneType TypeError 是 pytest 8 拒绝 `pytest.warns(None)` 的产物（复现 REPRO_OBSERVED=0）；2 个期望 FAILED 键是同源死键 | `material_revisions/pillow__2b061b68….md`；gold 日志 `…-all-gold-p_d21a126c` |
| pillow `2d01f7d0` | solver_condition | environment_qualified（R13 待并入） | 2 个期望 FAILED 键是 `pytest.warns(None)` 死键（不改）；公开 Tests/test_file_tiff.py 有 2 个预存失败 | gold 日志 `…-all-gold-p_6fdf1e36`；`p4/targeted_public_tests/` |
| pillow `3a61c9e9` | solver_condition | environment_qualified（R13 待并入） | 仅无 pip | 探针 + 复现 REPRO_OBSERVED=1 |
| pillow `3ac9396e` | solver_condition | environment_qualified（R13 **pass**） | 自定义 runner 输出能被 parser 正确解析（11 键）；pytest 跑公开 Tests/ 有假失败（Pillow 3.1 的 helper 与 pytest 8 不兼容），可用 `python Tests/test_x.py`；`pkg_version="?"` 是因为 Pillow 3.1 没有 `__version__` | `p4/targeted_public_tests/`、`p4/targeted2_cmds/` |
| pillow `4bc64835` | solver_condition | environment_qualified（R13 待并入） | 仅无 pip | 探针 + 复现 |
| pillow `a682ceaf` | solver_condition | environment_qualified（R13 待并入） | 仅无 pip（缺 Netpbm 只让 2 个无关用例被跳过） | 探针 + 复现 |
| pillow `f9d3ee0f` | solver_condition | environment_qualified（R13 待并入） | 仅无 pip | 探针 + 复现 |
| scrapy `75450e75` | solver_condition | environment_qualified（R13 待并入） | 测试 14 s 已归因：每个用例起一次 `scrapy shell` 子进程，约 0.8 s；`test_dns_failures` 1.45 s，**无网络等待** | `p4/targeted_public_tests/`（--durations） |
| scrapy `9a15fcf8` | material | needs_decision（R13 待并入） | 期望里 2 个 FAILED 键是 py3 遗留缺陷；“gold + bytes 解码”候选 7/7 PASSED 却 **reward 0**（实测） | `material_revisions/scrapy__9a15fcf8….md`；`p4/ledger_overfix.jsonl`；`p4/offline_rescore_9a15fcf8.json` |
| scrapy `a95a338e` | solver_condition | environment_qualified（R13 待并入） | 2 个期望 FAILED 键：评分入口的 `-W ignore` 使 `catch_warnings(record=True)` 记不到警告，是死键（不改）；不加 -W ignore 时公开同名用例 4/4 通过 | gold 日志 `…-all-gold-s_9377378e`；`p4/targeted_public_tests/` |
| scrapy `cfed9b66` | material | needs_decision（R13 待并入；推荐本轮不改） | 3 个期望 FAILED 键是搬迁伪影：`test.egg` 没跟着搬；测试以 `'tests.test_middleware.M1'` 自引用，搬迁后指向公开旧模块。题面主体没有活键 | `material_revisions/scrapy__cfed9b66….md`；`p4/image_readout/scrapy__cfed9b66_public_tests_grep.txt` |
| scrapy `e9387529` | solver_condition | environment_qualified（R13 待并入） | 仅无 pip；抓取类公开测试因 Twisted 版本恒失败（与本题无关） | 探针 + `p4/targeted2_cmds/` |

分类口径：E03 把“无 pip”列为 solver_condition。本包 12 题的 venv 都没有 pip，公开提示却说有，所以没有材料问题的题一律记为 `solver_condition`，没有用 `env_ok`；如果主会话要统一口径，可以把“只缺 pip”的 8 题并回 `env_ok`。`disposition.pending_checks=["R13"]` 是本包对 checks_r2e.md §3 形状的扩展，表示除 R13 外都满足。

## 2. 提案清单（均未实施）

### 2.1 材料修订（T0，待用户决定）

| 题 | 问题 | 选项 | 推荐 |
| --- | --- | --- | --- |
| pillow `2b061b68` | 公开题面与目标测试矛盾，并把 pytest 伪影写成缺陷 | A 不改 / B 修订题面（版本化）/ C 隔离 | **C**：本轮隔离，题面修订交给统一的题意筛查 |
| scrapy `9a15fcf8` | 期望 FAILED 键可被合法修复翻成 PASSED，更完整的修复被判 0 | A 不改 / B 隐藏测试删这两例，expected 同步删 / C 评分时两侧对称忽略指定键（改公共契约）/ D 隔离 | **D**：本轮隔离；若全池同类不止一题，再考虑 C |
| scrapy `cfed9b66` | 搬迁伪影造成 3 个死键，题面主体无活键 | A 不改 / B 修复搬迁（补 `test.egg`、改自引用路径，重生成 expected）/ C 删死键 / D 隔离 | **A**：本轮不改；质量筛查再定 B 或 D |

**关键更正（已验证）**：如果只从 expected 删键，RH2 的并集口径（`scoring.expected_map_matches`）会把这两例记成 `unexpected`，gold 也被判 0；上游 `calculate_reward` 要求两侧键数相等，同样判 0。所以删键必须两侧对称，要么隐藏测试不再运行这两例，要么评分时两侧同时去掉。离线重算见 `runs/r2e_env_repair_20260924/p4/offline_rescore_9a15fcf8.json`：两侧对称去掉后，noop 0 / gold 1 / 更完整修复 1。

### 2.2 解题侧条件（E10：只写进 `screening_record.solver_conditions`，是否进题面由任务面定）

| 条件 | 适用题 | 证据 |
| --- | --- | --- |
| venv 无 pip：install.sh 用 `uv venv` 和 `uv pip`；pip / pip3 / uv 都不在 PATH。公开提示却写 “`python`, `pip` … already point at it” | 12 题（pillow 与 scrapy 的 install.sh 在各仓库内逐字相同） | `p4/dev_probe/<iid>/agent_probe.log`（PIP_VERSION、WHICH_*）、`p4/image_readout/<iid>.txt` |
| 无网络：NET_CONNECT_RC=1、DNS 失败；loopback 可用，scrapy 的 mockserver 与复现用的本地 HTTP 服务都能工作 | 12 题 | 同上；scrapy `75450e75` 复现 |
| 公开相关测试在 base 上有与本题无关的预存失败 | pillow `2b061b68`、`2d01f7d0`（`pytest.warns(None)`）；scrapy `9a15fcf8`（py3 bytes，**正是期望要求保持失败的键**） | `p4/targeted_public_tests/<iid>/agent_probe.log` |
| 公开 Tests/ 不能直接用 pytest 判断：写临时文件的用例会假失败；`cd Tests && python -m unittest` 会让夹具路径失效；要在 `/testbed` 下运行 `python Tests/test_x.py` | pillow `3ac9396e` | `p4/targeted_public_tests/`、`p4/targeted2_cmds/` |
| Scrapy 1.1.0dev1 与镜像内的 Twisted 24.11、zope.interface 不兼容，HTTP 下载处理器加载失败，抓取类公开测试恒失败，但本题目标路径不经过下载器 | scrapy `9a15fcf8`、`cfed9b66`、`e9387529` | `p4/targeted2_cmds/<iid>/agent_probe.log` |

### 2.3 资源配方

无。12 题峰值内存 205–523 MB，限额 4 GiB，占 5–13%；默认 profile 足够。

### 2.4 记录不改（参考死键，status=verified 表示原因已证实、不提议改动）

- pillow `2b061b68` / `2d01f7d0`：测试里的 `pytest.warns(None)` 在 pytest 8.3.4 下抛 TypeError。
- scrapy `a95a338e`：评分入口 `-W ignore`。

这三题的死键都不会被合法源码改动翻转，评分一致，不误伤正确解。

## 3. 跨题发现（已验证）

1. **期望键带 ANSI**：pillow `2b061b68` / `2d01f7d0` 的期望键形如 `\x1b[1mTestImage.test_…\x1b[0m`，来源是仓库 setup.cfg 开了 `--color=yes`。`r2e_parsers.normalize_status_map` 对两侧都先去色再比较，所以评分和对账都一致。但 `collate_facts.py` 的 `non_passed_reasons` 在这两题为空，原因是日志行里带颜色码（见 §7）。
2. **自定义 runner（pillow `3ac9396e`）**：隐藏的 `unittest_custom_runner.py` 会自己打印 `short test summary info` 段（格式为 `PASSED test_1::Class::method`），parser 取 `::` 之后的部分，得到 `Class.method` 键：11 个键全部解析，noop 和 gold 都与独立 runner 一致。探针烟测只证明了 “pytest 能跑公开 Tests/”，而这对**相关**文件不成立：`test_file_tiff_metadata.py` 在 pytest 下有 3 例假失败。
3. **gold 触碰路径与 hygiene 不相交**：hygiene 文件是 `r2e_tests/<隐藏文件>` 加 `run_tests.sh`（见 `rh2/src/repoharness2/adapters/slime/r2e_grading_scripts.py`），gold 都只改库源码。日志里的 `RH2_SETUP_EXPECTED_TEST_FILES` 等于隐藏文件数加 1，12 题逐一核过。
4. **泄漏面**：
   - install.sh 是通用安装脚本，不含修复：pillow 7 题的 sha 都是 `c272ac91…`，scrapy 5 题都是 `8a27e412…`。
   - pillow 镜像自带的 `__pycache__`（也就是 R-f 账本里 omitted_cache_count 非 0 的来源）经逐个核对，pyc 头里记录的源码 mtime / size 与 base 源码一致，是 base 源码编译出来的，不是修复版的残留。
   - HEAD 无子提交，也没有 refs、remote、reflog 或补丁残留。
5. **R10**：scrapy `75450e75` 测试耗时 14 s，已确认不是网络等待：`--durations` 显示每例约 0.8 s 的子进程启动，16–17 例合计 13–14 s。
6. **dirty tree 2 行**：12 题探针的 GIT_STATUS 块都只有 `?? install.sh` 和 `?? run_tests.sh`，探针、复现和定向测试前后行数不变（2→2）。

## 4. 未解决项

- R13：11 题为 unknown，等中央复跑并入。本包没有等待，也没有触碰 `/work/envrepair/_rerun2/`，只读取了账本行数。
- scrapy `cfed9b66`：“只改 load_object 的部分解就能拿满分”是**按键集推断**，没有实跑。如果主会话想要实测，可以按 over-fix 同样的方式跑一次 `patch-dir` 候选，约 30 s。
- pillow `2b061b68`：“题面把 harness 伪影当缺陷”可能是同源数据的系统性问题，本包没有扫其它包的题。
- 超出本轮范围、只记录不判定：site-packages 和 `.venv/bin` 在 `/testbed` 里，chown 之后 agent 可写，属于反作弊面。

## 5. 远端产物与本地回传

远端 `/work/envrepair/p4/`（约 1.3 MB）已用 `rsync -azc` 全量回传到本地 `runs/r2e_env_repair_20260924/p4/`：

| 路径 | 内容 |
| --- | --- |
| `repros/`、`repros.sha256` | 12 个公开复现脚本（与 `docs/…/repros/` 同内容）及摘要 |
| `dev_probe/`、`probe_1825.log` | 探针（unit `r2e-p4-probe-1825`，工具 sha 与 `r2e_env_tools.sha256` 一致，parser v1） |
| `targeted_public_tests/`、`targeted_1832.log` | 定向公开测试（unit `r2e-p4-probe-1832`）：用 `run_dev_probe.probe_one` 的容器条件，只把 agent 脚本换成 `tools/targeted/dev_probe_agent.sh`；`run_dev_probe` 以只读方式导入，运行时改 `HERE`，**没有修改 /work/code** |
| `targeted2_cmds/`、`followup_1841.log` | 同一方式跑的命令清单：pillow `3ac9396e` 的 unittest 与脚本方式；Scrapy 1.1 三题 closespider 的失败原因 |
| `image_readout/` | root、`--network none`、`--rm` 的只读取证：install.sh 全文与 sha、`__pycache__` 与源码是否对应、`Image.core` 路径；另有 cfed9b66 公开用例名 grep |
| `overfix/`、`ledger_overfix.jsonl`、`eval_logs/`、`artifacts/`、`rerun_overfix_1848.log` | scrapy `9a15fcf8` 的 over-fix 候选评分（unit `r2e-p4-rerun-1848`，run_id `r2e-envrepair-p4-overfix`，exit_code 0，清理 removed） |
| `tools/` | 上述定向工具（driver、agent 脚本、清单、images.txt、image_readout.sh、run_followup.sh） |
| `offline_rescore_9a15fcf8.json` | 仅本地：离线重算结果，只读既有日志，使用生产函数 `parse_eval_log_r2e` / `expected_map_matches` |

收尾检查（18:49、19:02 UTC 两次）：`docker ps -a` 没有 P4 的容器，也没有 `r2e-p4*` unit；磁盘剩余 45 GB（起步 46 GB）。记录的机械核对：主会话的 `rh2/scripts/r2e_env/check_records.py` 对本包 12 题逐一检查，`problems=0`，退出码 0（19:0x UTC，只读运行）。仍在运行的容器属于 P3 和中央复跑，本包未碰。本包没有构建或删除镜像，没有改动 `/work/replay`、`/work/r2e_derived`、`/work/code`。

## 6. 耗时（与其它包、中央复跑并行，不作校准，E08）

| 段 | 墙钟（UTC） | 合计 |
| --- | --- | --- |
| 探针 12 题 | 18:25:10–18:32:00 | 410 s（单题 26.6–40.3 s，chown 18–36 s） |
| 定向公开测试 12 题 | 18:32:19–18:38:57 | 397 s |
| 跟进：镜像读取 12 题 + 定向命令 4 题 | 18:41–18:44 | 约 30 s + 107 s |
| over-fix 评分 1 次 | 18:48:15 起 | 26 s（grader 各段合计） |

整个包从读材料到写完记录约 1 小时。

## 7. 对流程 / 工具的改进建议

1. **`run_dev_probe._derive` 的 `pip_ok` 判断有误**（本地 v2 仍然如此，见 `rh2/scripts/r2e_env/run_dev_probe.py` 的 `"pip" in PIP_VERSION.lower()`）：输出 “No module named pip” 时也会判为 true。本包 12 题和烟测里的 `3ac9396e` 都被误判。建议改为 `PIP_VERSION.startswith("pip ")`，或者新增 `PIP_RC`。已写入的 `dev_probe.json` 在修复后需要 `--reparse`。
2. **KV 正则丢了 `WHICH_*` 行**：本包探针用的是 v1 解析器，gcc / make / pip 的有无是从 `agent_probe.log` 原文读出来的。主会话已在 v2 修复，并加了 `--reparse`。本包没有对自己的产物重跑解析，留给主会话统一处理。
3. **探针挑的公开测试文件代表性差**：它取字母序第一个 `test_*.py`（pillow 得到 `Tests/test_000_sanity.py`，scrapy 得到 `tests/test_closespider.py`）。这个文件对 R09 的意义有限，还会把无关的依赖问题（Twisted）混进来。建议加 `--public-tests <iid>=<file>` 映射，或者由可信侧挑出与隐藏测试对应的公开文件。另外建议加 `--durations`，并记录去掉 PREFIX 后（求解者视角）的运行结果。本包的定向运行就是这条的原型（`p4/tools/targeted/`）。
4. **`collate_facts.py` 的 `non_passed_reasons` 应先剥 ANSI**：pillow 的日志行形如 `\x1b[31mFAILED\x1b[0m …::\x1b[1mClass::test\x1b[0m`，目前取不到原因行。
5. **新增一条 R06 筛查规则，识别“可翻转的期望非 PASSED 键”**：看 FAILED / ERROR 键的 traceback 落在哪里。落在 `/testbed/<包>/` 的库代码里（例如 9a15fcf8 的 `scrapy/responsetypes.py`），就可能被更完整的修复翻成 PASSED，要标记出来并做 over-fix 实测。落在测试代码里，或者落在 `_pytest/…`、`importlib` 这类测试框架和导入机制里（例如 `pytest.warns(None)` 与搬迁伪影），就是死键。本包的 5 题里只有 9a15fcf8 属于前者。
6. **批量扫描搬迁伪影**：检查隐藏测试里按 `__file__` 找的相对夹具、以原模块路径（如 `'tests.test_x.Cls'`）自引用的字符串，以及 `os.path.dirname(__file__)` 下的非 .py 资产。cfed9b66 是 1 例。
7. **题面与 noop 原因的一致性检查**：题面 Actual Behavior 里写的异常文本，应当出现在 noop 目标键的原因行里。2b061b68 的题面写 Warning/NoneType TypeError，而 noop 原因是 `unexpected keyword argument 'formats'`，这种不一致可以自动标出来。
8. **分类口径**：“无 pip”在本包 12 题和 P2 的多题上都成立。建议 E03 明确：只缺 pip 的题算 `env_ok`，再加一个全池 solver_condition 族；或者全部记为 `solver_condition`。本包采用后一种（见 §1）。
9. **facts.json 在本包执行期间被重生成**（18:18 UTC，路径改为相对仓库根，内容不变）。本包的记录生成器两种格式都能处理；其它消费方要留意 `eval_log` 的前缀变化。

## 8. 本包写入的文件

- `docs/…/r2e_env_repair_20260924/repros/<12 个 iid>.py`（**已实施**，写于读取隐藏测试片段、gold 与日志正文之前）
- `docs/…/r2e_env_repair_20260924/tasks/<12 个 iid>/screening_record.json`、`findings.md`（**已实施**）
- `docs/…/r2e_env_repair_20260924/material_revisions/{pillow__2b061b68…, scrapy__9a15fcf8…, scrapy__cfed9b66…}.md`（**提案**）
- 本页；本地 `runs/r2e_env_repair_20260924/p4/`；远端 `/work/envrepair/p4/`

没有改动 facts.json、本目录的 README / checks / decisions / known_issues / dispositions / recipes、`s2_r2e/`、`rh2/src`、`rh2/scripts`；没有 commit、push 或 stash。
