# scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67：旧主张核对（读历史后）

- 角色：R2E 私有主审。日期 2026-09-25。初判 `analysis_before_history.md` 在读历史前已保存，本文不改它。
- 已读的历史材料：`refs.json` 列出的全部路径，即 `r2e_env_repair_20260924/` 下本题的 `findings.md`、`screening_record.json`、`facts.json`、复现脚本、`packages/p4/README.md`，以及 `decisions.md`、`results_20260924.md`、`known_issues.json` 里与本题和 scrapy 相关的行。`known_issue_families` 为空。
- **历史的范围**：只有 P4 环境审查（2026-09-24），处置写的是"环境资格（不含题目质量 / 训练准入）"。它没有评估隐藏测试是否测到要求，也没有评估 gold 的语义。所以我在初判里提出的两条质量问题（目标测试过宽、gold 新建了不运行的循环）在历史里**没有对应主张**。这是历史未覆盖，不是历史结论被推翻。

## 1. 逐条核对

| 旧主张（出处） | 判定 | 新的决定性证据 / 说明 |
|---|---|---|
| 分类 `solver_condition`，处置 `environment_qualified`（findings 结论、record.disposition） | **确认**（限环境资格） | 评分可复现：current noop 两次都是 0，只错目标键；gold 两次 17/17；M3 参考 noop 两次 0、gold 两次 1（`facts.json` reference.reconcile）。devcheck 在 agent 身份下的开发条件实测可用。但这不等于题目质量合格，见 §2。 |
| "环境无缺口"（findings 结论） | **部分推翻（补充）** | 公开测试 `tests/test_crawler.py::CrawlerProcessSubprocess::test_default_loop_asyncio_deferred_signal` 在 base 和 gold 下都失败：Twisted 24.11.0 没有 `reactor._handleSignals`，`scrapy/utils/ossignal.py:19` 抛 AttributeError（`DC/orig/captures/pr6_9_pytest.out`；私有 gold 对照 `pr6_9_pytest` rc=1）。<br>这意味着在本环境里，凡是装信号处理器的 `CrawlerProcess.start()` 都会崩；asyncio reactor 下已实测，默认 reactor 按 Twisted 版本推断同样。<br>shell 传 `install_signal_handlers=False`，所以评分不受影响，但 agent 用公开测试验证主线程 asyncio 路径时会被这个失败误导。<br>P4 README 为 scrapy `e9387529` 记过同类的"Twisted 版本导致恒失败"，本题没有记；历史只跑了 `test_closespider.py` 和 `test_command_shell.py`。 |
| 测试 14 s 已归因：每例起一个 shell 子进程，不是网络等待（R10） | **确认** | current 日志 13.35 s / 13.15 s；devcheck 公开 shell 测试 16 例 8.46 s。我没有重跑 `--durations`。 |
| 解题侧条件：无 pip（R05、solver_conditions） | **确认** | devcheck `env.out`：`/testbed/.venv/bin/python: No module named pip`。 |
| issue："venv 无 pip，而公开提示写 pip already points at it"，另有 conda 措辞（E09），status=open | **过时（已被新提示解决）** | v3 公开包 `public_bundle.json` 的 `public_hints` 已改为 ".venv … `pip` may be unavailable"，不再提 conda。devcheck 的 `activation_check.json` 显示解释器前缀是 `/testbed/.venv`。该 issue 可以关闭。 |
| R01：派生镜像 `sha256:2e6e1f3b…`，HEAD = base | **确认，另加注** | 评分运行确实用这张镜像。但本批 devcheck 用的是 `sha256:21da38a7…`，是另一台机器上按同一 tag / recipe 重建的；版本号一致（Python 3.9.21 / Twisted 24.11.0 / pytest 8.3.4 / scrapy 2.7.1）。两张镜像内容是否等价，我没有核对。 |
| R02：noop 0 来自 1 个 mismatched 键，没有零解析 | **确认** | noop 日志第 59 行 FailTest，第 80–81 行 1 failed / 16 passed。 |
| R03：题面示例用的是测试辅助 `execute()` 和 "mockserver 地址"，等价命令能复现 | **确认，措辞小更正** | 站点其实是 `scrapy/utils/testsite.py` 的 `SiteTest`，不是 `tests/mockserver.py`。devcheck C1（`file://`）和 C4（本地 testsite）在 agent 身份下都复现了报错。<br>另有三点历史没记：题面说"raises"不精确（实际是 ERROR 日志，退出码 0）；"within the new thread" 是方向提示；题面没说复用哪个循环（初判 §4(b)(c)）。 |
| R04：gold 只改 `scrapy/shell.py` 和 `scrapy/utils/reactor.py`，与 hygiene 不相交；不需要改其它测试辅助 | **确认，另加注** | 隐藏测试依赖 `scrapy/utils/testproc.py`、`scrapy/utils/testsite.py`（非测试路径，候选可改，评分不重置），还有 `tests/__init__.py` 和根 `conftest.py`。这是通用漏洞面，未测试。 |
| R06：期望 17 键全 PASSED，没有外部资产 | **确认** | `P/expected_output.json`。 |
| R07：site-packages 在 `/testbed/.venv` 内，agent 可写，反作弊面另议 | **未核实** | devcheck 没有测 site-packages 是否可写。按静态推断，`.venv` 被 git 忽略，改动进不了候选 diff，评分侧用的是新容器，所以它不是评分漏洞；但 agent 在解题期间可以改已装的库来"本地通过"，这会误导它自己的验证。 |
| R08：导入 `/testbed/scrapy/__init__.py`；gold 17/17 | **确认** | devcheck `env.out` 与 gold 日志。 |
| R09：公开 `test_command_shell.py` 16 passed；复现 REPRO_OBSERVED=1 | **确认** | devcheck `pr5_6_pytest.out` 16 passed；`pr1_2_cmd.out` / `pr4_5_cmd.out` 出现报错。`test_closespider.py` 没有重跑（与本题无关）。 |
| R10 / R11：无出网；不依赖外部服务；评分容器为 `--network none` | **确认（R11 补一条环境敏感键）；actor 网络条件过时** | actor 现在是隔离网络加 relay，外部 DNS 被拒（`DC/orig/prelaunch.json`：`DNS_EXTERNAL=DENIED`、`NET_forbidden_*=DENIED`），不再是 `--network none`；对本题等价。<br>补充：`test_dns_failures` 依赖评分环境对不存在的主机名解析失败。若换成能解析任意主机名的网络，这个键会 SKIPPED，变成缺键，**所有候选都判 0**。 |
| R12：内存峰值 281 MB | **确认**（引用 `facts.json`，没有重新观测） | — |
| R13：noop / gold 在同条件下各 2 次一致 | **确认，并加强** | 加上 M3 参考，noop 共 4/4 为 0，gold 共 4/4 为 1。初判 §4(e) 说"noop 时序风险没有量化"，据此下调为"很低"。对报错晚一个循环迭代才出现的部分修复（K2），这个风险仍待重复运行验证。 |
| R15：与独立 runner 对账 2 行 agree | **确认**（引用 `facts.json` 的 reconcile，没有重新打开 `reconcile.json`） | — |
| R16：目标键 1 个，noop 原因与题面一致 | **确认** | 同 R02。 |
| R17：`fix_present=no`、HEAD 无子提交、install.sh 通用 | **确认前两项；install.sh 未重读** | devcheck 预检 `RH2_PREFLIGHT_GIT_HISTORY=ok`，prelaunch 显示 `GIT_REFS=0`、`GIT_REFLOG=0`、`GIT_REMOTES=0`；隐藏测试不可读。 |
| R05：gcc / make / git 在 | **未核实** | 本题不需要构建。 |
| 建议："不需要配方或材料修订" | **确认（限环境与材料）** | 我同样不建议做环境或材料修订。但历史没评估的两条质量问题要记入本次记录：①目标测试过宽；②gold 语义不完整。 |

## 2. 历史未覆盖、本次新增（证据层次）

1. **目标测试过宽**（25、32）：只断言退出码为 0，且 stderr 不含那一句文本。静态分析认为掩盖根因的修法（K3）会得 1；待实跑。
2. **gold 新建了一个不运行的循环**（27）：devcheck 私有 gold 对照里 C2 输出 `(None, None, False)`，base 为 `True`（各一次运行）。累计越过 `SCRAPER_SLOT_MAX_ACTIVE_SIZE` 后 fetch 会永久阻塞，这一点只是源码推断，待 E1 验证。
3. **asyncio 路径缺少回归覆盖**（26）：16 个回归键全在默认 reactor 下。
4. **公开测试恒失败**（10）：见 §1 第二行。
5. **题目关系**（5）：本题初态包含 a95a338e、e9387529 的修复，暴露的是那两题的答案。历史没有做跨题比对。

## 3. 我对初判的修改与理由

- **更正 E1 命令的阈值（我的错误）。** 初判 §7 的 E1 用了 `SCRAPER_SLOT_MAX_ACTIVE_SIZE=1500`。但 `tests/sample_data/test_site/index.html` 只有 311 字节，槽位按 `max(len(body), 1024)` = 1024 计（`W/scrapy/core/scraper.py:56`、`:70`），1024 < 1500 不会触发退避，那条命令区分不了 gold 和 base。card 里改为 `SCRAPER_SLOT_MAX_ACTIVE_SIZE=1000`（1024 > 1000），每次 fetch 后加 `print(..., flush=True)` 标记进度，外面套 `timeout -k 5 60`。
- **noop 时序风险从"低、未量化"下调为"很低"。** 理由是 M3 参考的两次 noop 也是 0（共 4/4）。E2（noop 重复运行）从建议降为可选。
- **关闭"提示说有 pip"这一旧 issue。** 理由见 §1，v3 提示已更正。
- 其余判断不变：暂定处置、两条主要质量问题、K1/K2/K3 设计都维持。历史没有提供能改变这些判断的新执行证据。
