# iterative__dvc-1681 — 历史差异记录

2026-09-21。协调者确认历史前稿 SHA-256 `ee3922e793b83325eb87bcf7b2588e0332e826993f210494f97381e76c857bf0` 后，明确开放本题 history refs。本文件追加历史核对，不回写封存稿。结论仍为 `needs_review / static_review`，用途 `development_diagnostic`。

## 1. 本次新增证据与边界

沿 `runs/swegym_quality_batch02_20260921_v2/history/iterative__dvc-1681/refs.json` 读取唯一旧记录：

- `H=docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-1681.json`，SHA-256 `22a3ebd4054342cbc36c439204b9c8a6a0beeb3c9352d4540812033d0f6fdd1f`。
- H 的明确 Stage1 指针可直接定位，未以摘要代替运行原件。`L=runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-1681`；`LG=L/gold/offline/a1/test_output.txt`，SHA-256 `5ff25882cd0aecc86e3df682b7faa497df791d0e08b8ce73db60063214e7235f`，1393 行；`LE=L/empty/offline/a1/test_output.txt`，SHA-256 `47bd28176388d7b4d02ab7bcb6fdd3f1a3fd47c57dce44bdccf11a0486e88a83`，1316 行。下述旧日志行号仅对应这两个 SHA。
- 两侧 `eval.sh` 全 90 行已读，SHA-256 均为 `e243100c4258fcb303ee265edc3e3ac92d026ff91c13d2e3d1147057742dd42c`。两份 status_map 全读：gold SHA `546365e87a606b3b0bf2d6801d0ac95073f606c0fb922832e3bfc391ee3d7839`、empty SHA `2e78820773c74bbc9be3c4b7bbb441888cca2bfe68acd336d9dd8a0756601858`。gold/patch.diff 全读，SHA `f275fc350e4cd4326b1f2bf7e0e432ef248b55322b95b2793b9328ef6d772ba4`，与当前本题 gold 原件相同。
- H 的 raw 缩写经限定查找定位为 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl` **第 126 行**，只输出并阅读 instance_id 为本题的记录；该行含末尾换行 SHA-256 `d4f617bee89d9146a30ca40e1098a0d7428ed93c4c77e7d9a56f4f8dc4b32fc0`。其 gold/test 文本均与已封存调查的原件逐字相同。没有再遍历整个导出包或重复逐 blob 核验。
- 沿 H 的本地只读仓库 `runs/env_overnight_20260916/repos/dvc` 核本题提交元数据：本题 merge `a36d77272367bf2872799040686b9807caf08c90` 第一父节点即给定 base，标题为 `Stage checksum with default wdir fix`。相对 base 只改 stage.py 和两份官方测试；忽略 Git index 行及 hunk 后函数上下文标签后，hunk 行号和内容均与材料相同。未修改 checkout、运行源码或执行 Git 写操作。
- raw hints 指向 `38536903e101b7449e65fc668c4b19519e61869c`。已读其 stage.py diff，确认它是 base 的祖先，提交为引入 wdir 的 #1658；该 diff 同时引入实际对象绝对 wdir、dumpd 原样字段、写盘相对化及 `_compute_md5` 的字面 `.` 过滤。因此 hints 确实提供精确定位线索，不是修复补丁。

修复配方的 `R/G/N/B/V/O` 缩写沿用封存稿 §0；G/N 的 SHA 与旧 LG/LE 不同，不交叉使用行号。旧日志实际细读安装关键段、setup、收集与结果、失败栈、updater 标记；完整文件 hash 不表示逐行读完所有 captured output。原始旧 eval、status_map、patch 和 H 全读。其余只新增核对公开 base 的 `tests/test_add.py:141–149`、`tests/test_repro.py:88–108`、`tests/test_run.py:617–665`，用途是核旧建议的具体名字与断言；没有机械扩大测试范围。

未读 H 指向的 prescan、其它题调查、批次报告或独立 reviewer 初稿/结论。跨题断言不因旧记录已有标签而采纳。全程仅静态文本、JSON、哈希及 Git 对象读取；没有新 CPU、候选、测试、安装、容器、SSH 或模型执行。

## 2. 旧主张逐项对照

| H 的旧主张 | 判定 | 决定性证据与本次解释 |
|---|---|---|
| 默认 wdir 在真实 create/load 路径变为绝对值，dumpd 与 dump 表示不同导致旧 checksum 回归。 | 确认，限定作用域 | 封存稿 §1、base stage.py:439–451/494–577；本次 hints 精确祖先 diff 再次支持因果来源。不是所有手工 Stage 构造的 wdir 都绝对；Mock 已相对输入的单测本来会通过。 |
| 题面不指定必须改 dumpd；仅在 `_compute_md5` 规范化的路线可能被新增内部断言拒绝。 | 确认静态疑点；“已证合法解被判 0”未核实 | 原 test patch 的内部表示断言和 base 消费者支持此疑点，旧记录没有替代补丁或运行原件。LG/LE 只运行 gold/empty，当前 R 也只 gold/noop。必须先证明替代路线对旧样本、真实非默认目录、缓存和状态行为完整，才能称误拒。旧实验描述的 KeyError 也非此场景必然结果：保留原 dumpd 会有 wdir 键，实际空补丁是 AssertionError。 |
| 把内部断言删掉，后半段 load 后 unchanged 已是充分行为验收。 | 推翻“单删即足够”的修订建议 | base tests/test_stage.py:99–116 后半段原已存在；当前创建、当前保存的 checksum 可以自洽地保留相同错误表示。它没有固定旧版 md5。LE:451–457 与 N:542–548 都先在新增表示断言中断，不证明末尾旧兼容断言本会失败。应先用外置固定旧格式探针判别，不能直接改原题。 |
| 两项正反 wdir 单测可挡住无条件删除 wdir。 | 确认特定错误形态；缩小保护范围 | 它们确实拒绝 `_compute_md5` 对已给定 `..` 也无条件删除，但两项均 Mock dumpd。真实 dumpd 把所有 wdir 写为 `.` 的自然部分实现不受这两个 Mock 入口保护；只是静态疑点，未有该候选得分。封存稿 §2–3 的新发现保留。 |
| P2P 12 条且其中 8 条 schema，dump 的八个调用者无任何回归覆盖。 | 前半确认；后半过度概括 | 13 个实际案例及 12 个 P2P 已逐个核。TestReload 在 P2P 内真实 add/load/dump，F2P 则真实 Repo.run，二者已经执行部分调用路径。相关非默认目录、move、is_cached 等具体行为仍未冻结；不能把“未分别覆盖每个调用点”写成“所有调用点零覆盖”。 |
| gold 核心方向正确，同时去掉 dump(fname=None)，所有内部调用无参。 | 确认局部源码结论；完整正确性仍待验 | 封存稿 §4 与本题 upstream diff 一致。当前 13 项通过；已搜索的内部调用不传 fname，但外部 API 兼容未知。保留 fname 的解不因与 gold 不同而扣分，官方测试也没有强制签名相同。不是已证 gold 错误。 |
| gold 13 passed、empty 12 passed/1 failed，F2P/P2P 可全部对上。 | 确认历史真实执行 | LG:1374–1391、LE:1297–1314，失败点 LE:451–457。旧 F2P 与当前同为内部 dumpd 断言。这个历史运行结论已查原件，不是 report-only；未从这些文件额外推断旧 reward 值。 |
| 安装与测试正常、环境干净、无依赖漂移症状。 | 推翻旧“安装干净”；当前修复条件已另证 | LG:357–372 Git 依赖下载失败且 `true`；406–411 botocore==1.35.9 无匹配及缺失 test-requirements；412–437 editable 安装因 setuptools 构建依赖失败。eval.sh:14–15 未启用 fail-fast，最后 pytest 安装成功覆盖前面的 RC，LG:449–452 仍写 install rc=0。LE 有相同错误。当前 R 先 pin awscli/PyYAML/colorama/rsa 并逐步检查错误，G:387–438/531–551 成功；不能用旧末尾码证明干净，也不能把旧失败移植成当前失败。 |
| 两文件纯本地，无网络/外部服务。 | 功能资产范围确认；“无网络相关行为”过强 | 目标测试不需云桶或 XML 下载；旧安装却请求 Git/PyPI 并因 DNS 失败。LG:585、LE:467 开始出现 updater daemon spawn，打印的环境未设 DVC_TEST；当前 G:1234/1252 也有同类尝试。没有成功远程访问证据。没有 SKIPPED 不等于无网络副作用。 |
| status_map 无 caplog 污染，参考全部匹配。 | 参考匹配确认；遗漏非测试污染键 | 两份旧 status_map 的 13 个测试身份确实匹配，但另有 `Could: ERROR:` 与 `No: ERROR:`，对应安装错误句 LG:406–407/426–427、LE:365–366/385–386。污染来源是安装文本，不能误称来自 caplog；H 的 pass 没有披露这一事实。当前 R 两份 diagnostics 与 13 个摘要身份完全相等、outside=0；仅说明该对运行未见同类多余键，不代表 parser 对任意日志安全。 |
| tests/unit/stage.py 名字不匹配默认 test_ 文件规则，必须显式选择，不能只按文件名排除。 | 确认；本题未因此漏收集 | 旧 eval.sh:88 与当前选择器都显式点名两文件，LG:475/478 与 G:566/569 实际收集全部 3 项 unit；两份官方文件恢复也已核。这是规则边界提醒，当前不是收集失败，不新增文件排除。 |
| 建议 tests/test_run.py -k wdir、TestRunWorkingDirectoryAsOutput 和 TestAddFileInDir 可补足非默认目录。 | 需更正/不足，不执行 | base 中没有 TestRunWorkingDirectoryAsOutput 类；实际为 TestCmdRunWorkingDirectory。`-k wdir` 并非该类全部方法的可靠选择（test_cwd_is_ignored 不含 wdir）。TestAddFileInDir:141–149 只断言 stage/deps/outs 数量与 relpath，没有非默认 checksum 断言；即便执行也不能据此证明已挡住抹平真实 wdir。TestReproWorkingDirectoryAsOutput 名字存在，本文仅查至108行而未审核完整行为。保留封存稿唯一三路外置实验，不追加机械命令。 |
| 1877/2254 的 base 包含本修复，因此同文件历史序列应同侧划分。 | 本次未核实；同侧结论不采纳 | H 没给两题精确 base/patch 或同一需求证据，仅引 prescan。未打开其它题/聚合。已确认本题 #1658 引入与 #1681 修复链，不能据共享 stage.py 或修复在后继历史中出现，自动证明重复题/等价目标/划分泄漏。交协调层按精确提交与暴露路径另核。 |
| hints 含 bisect 回归提交链接，公开题面未包含。 | 确认暴露差异；不自动判公开目标不完整 | raw 第126行精确链接及本地祖先 diff 已核。公开代码自身可定位问题；不提供 hints 不等于缺少完成需求的必要信息。主审现在已接触 hints 与上游修复，不可作盲解者，也没有把这些信息交给公开角色。 |

## 3. 对独立前稿的影响与最终静态建议

封存稿的主要判断未改变：公开缺陷和源码因果成立，修复配方的 gold/noop 分差有真实原件；主要争议是内部 dumpd 表示是否不必要地限制合法修复，及 Mock 边界未保护真实非默认目录。历史记录与我们独立疑点相合，但没有提供已执行的替代/部分实现，证据等级不能升级。初稿未读取的旧 Stage1 现在已补齐；旧安装错误、安装文本污染键、updater 行为及 hints/提交关系得到原件确认。

不接受旧记录的直接删断言方案、全调用者零覆盖表述、把单测保护外推到所有 wdir 路线或未经精确依据的跨题同侧结论。当前修复配方确实完成安装和测试；这不验证实际 actor 的 agent/54321 权限、消息层级、conda 激活、资源或开发反馈。旧 pip 日志有 root 警告及 HOME=/root，也不能把它当当前 actor 证据。

唯一优先后续语义实验仍是封存稿 §3 的 **base/gold/仅在校验输入规范化 wdir** 三路对照：保留原官方13项和 reward，另用固定旧 YAML checksum、小型旧格式状态、真实非默认目录及真实数据变化的外置探针判别。只有行为完整却仅因新增内部表示断言失败，才形成合法路线被拒的实证；若替代实现未完成旧行为，则收回合法性推断。没有执行该实验，没有替换原测试或制造新版本。

最终保留 `needs_review / static_review`、`development_diagnostic`，`additional_exclusions=[]`、`revision_refs=[]`。独立 reviewer 产物由协调者另行封存，本主审未读；一致/分歧及最终准入均待协调者核对。未知总容器墙钟、agent tokens、human_decisions 保持 null，不把旧自报22分钟或局部测试时间当当前可观测成本。
