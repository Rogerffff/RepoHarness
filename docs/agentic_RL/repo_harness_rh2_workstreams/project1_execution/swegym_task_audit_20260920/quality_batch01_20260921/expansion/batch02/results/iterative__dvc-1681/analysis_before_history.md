# iterative__dvc-1681 — 历史前独立静态分析

2026-09-21，私有主审。暂定建议为 `needs_review / static_review`，用途 `development_diagnostic`。本稿在本题 history 门禁关闭时形成；封存后不回写，历史差异另存。

公开问题可以从现有源码定位到 stage 元数据中的工作目录表示不一致。修复配方的真实原件显示 gold 13 项通过，noop 只失败唯一 F2P；但该失败实际停在新增的 `dumpd()["wdir"] == "."`，尚未走到末尾的状态检查。这留下一个具体的实现约束疑点：仅在校验输入处规范化、保持内部字典表示的合理路线可能被拒。两项工作目录校验单测 mock 掉 `dumpd()`，也不能证明真实非默认目录经过序列化后仍参与校验。以上与 actor 环境未验证分开记录，不把单次 grader 成功写成完整目标证明。

## 0. 阅读范围、身份与证据定位

权威根为 `ROOT=${REPO_ROOT}`，没有使用继承 worktree 的内容。下文相对路径缩写：

- `I=runs/swegym_quality_batch02_20260921_v2`；`P=I/public/iterative__dvc-1681`；`V=I/private/iterative__dvc-1681`；`B=P/base`。
- `B1=docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921`；`O=B1/expansion/batch02/results/iterative__dvc-1681`。
- `R=runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-1681`。
- `G=R/gold/eval_logs/evallog_replay-er19-dv1-iterativ_ed4fa666.eval.log`，SHA-256 `343e328a61dc9df9083d8c835b3cc861561964c6bf5cdd77bd31923c8477d21f`，1489 行。
- `N=R/noop/eval_logs/evallog_replay-er19-dv1-iterativ_ffddd94c.eval.log`，SHA-256 `da0ebba65221c3983393ac9b2d94a9e2a383b41615632ea7fa17b1b3115dc43f`，1412 行。

G/N 的精确行号只对应上述各自 SHA 原件。已沿本题 run_refs、ledger、recipe 的明确指针读取原 log/diagnostics/audit 文件；`/work/env_recipe_repair_20260919/...` 对应 ROOT 下 `runs/env_recipe_repair_20260919/...` 存档。只有静态文本读取、JSON/行集合比较、哈希和本稿写入，没有执行 DVC、测试、依赖安装、容器、SSH、旧脚本、模型或候选；没有修改源码、clone、输入、gold、test patch 或 reward。

共用角色/格式依据为已读的 `B1/roles/investigator.md`、`B1/record_template.md`、`B1/actor_environment_card.md`、`B1/../quality_review_protocol_20260920.md` 及其明确引用的 `project1_execution/environment_screening_definition_20260915.md`、`environment_screening_checklist_20260915.md`。未把方法例题当本题事实。已读本题独立封存 `O/public_read.md`，SHA-256 `5566c429ac0670f29841ed4655f6730739a6c000cac33ac394433783b9e624e5`；随后自行核验本文使用的源码/测试，不把公开读者的阅读清单算成本主审自己的阅读。

`V/source_refs.json` 指定 S2 ingest 的 public/grading/validation 三份 JSONL **各第 113 行**，只提取这些行，与本题对应 JSON 解析值均相同；未读相邻题。grading 中 test_patch 与独立 patch 文件一致，validation 中 golden_patch 与独立 gold 文件一致；problem_statement 字节摘要与声明 `c89d55f403829a6ad9c9919a5a266426cad9d70d2c27e4011a3834caf145e0cf` 一致。

未打开本题 `I/history/iterative__dvc-1681/refs.json`，没有读旧调查、raw hints 或未来修复历史。`V/environment_record.json` 已授权读取，其中 `verified_environment_pair`、运行摘要及 analysis/history 链接已经可见；没有沿那些链接读旧质量结论或批次 analysis。此前完成 3576/4166 的同一主审保留其上下文，但不把其它题的结论、配方或问题套到本题。未读批次报告、manifest、method_adjustments、其他角色结论（本题封存 public_read 除外）或聚合产物。

| 原件 | SHA-256 / 身份 |
|---|---|
| `P/user_prompt.txt` | `bb306c9d5675b15cc01c495a2eff6c7d67ec0163a0ff43dc6c93bb020e5e35ba` |
| `P/public_bundle.json` | `e287598a694b8a947c7ddabf53999dd53ccc6d4c02a19f4ee040cbc03a75a8b2` |
| `P/base_identity.json` | `0b108e7f5c063a02ef91c1e67d87957bd4ab4f60eed9ab07c5d8ff26af569b7d` |
| `V/grading.json` | `1be435b0fe906765b22d26e85ec0f8e69ef4ff95f31bb663ed9a8292c7030897` |
| `V/test.patch` | `76f79789280e81ab78a1e40385906df6617c20fdce32d89b12ac36b0c1c4b52b` |
| `V/gold.patch` | `f275fc350e4cd4326b1f2bf7e0e432ef248b55322b95b2793b9328ef6d772ba4` |
| `V/environment_record.json` | `f168c5aa02b6da73c95dadae6a01139e44e4326ef962dbc09ecf2c873dcd3e94` |
| `R/gold/ledger.jsonl:1` | `135aa32277f2d1bc4aa074f20b29be5b4b51a83dcdff7f0b24707c460e102dc7` |
| `R/noop/ledger.jsonl:1` | `472015a0390e2a6af5d43f7bb45db0ef14171714e7fe71763b0f46f0cb1730c5` |
| gold diagnostics（G 同 stem） | `57f61eae84d7248a20198f889ed906dc6cd239aed27c4f50218ca9648a2bcc7d` |
| noop diagnostics（N 同 stem） | `c5b2b55d1c5f6cea6a1efdc1010dccc4658bcf0d98cd341b034fa656b50ad7bb` |

base 为 `9175c45b1472070e02521380e4db8315d7c910c4`，声明 tree `611151f60d7a10deead85a9af5e39970369cc7e3`；版本 0.30，grading 指定 Python 3.8。base_identity 记录 220 个 blob、659940 字节、无 symlink/LFS 缺件/gitlink、未导出 `.git`。本审核了关键文件哈希，没有重建整个 Git tree 或把导出统计当作实际 actor 镜像检查。公开镜像 digest 为 `sha256:47f2213bba1f71e6674cef8027d6cd7df892c480bb2a27a58391162a268eee8e`，与后述 repaired grader 派生镜像不同。

## 1. 公开目标与初态

用户在 Arch Linux、pip、Python 3.6.8 背景下报告：旧版 `dvc add` 生成且数据未改的 `.dvc` 文件，在升级后 `dvc status` 错报 `changed checksum`。题面包含具体 YAML：顶层 stage md5 为 `fc2ea87b490d2f382601c489822a1e96`，输出文件 md5 为 `068b1464866e460e58ce216cd82dcf9b`，cache=true、metric=false、path=`plwiki-latest-pages-articles.xml`，没有 wdir。0.28 的状态是既有干净提示，指定 base 附近版本出现错误。正文 `0.3.0`、标题/安装 0.30 与一次 `0.29.0+220b4b.mod` 输出有文字差异，但 base 身份明确，不需要因此停止调查。

顶层 stage 校验与数据文件校验不是同一东西。`Stage.status()` 根据 `changed_md5()` 添加题面的确切字符串（`B/dvc/stage.py:748–769`）；输出自己的状态另报 deleted/modified/not in cache（`B/dvc/output/base.py:114–150`）。CLI 由 CmdDataStatus→Repo.status→Stage.status 展开，普通查询返回码 0 不代表没有变化，quiet 模式才在非空状态时返回 1（`B/dvc/command/status.py:39–63`）。不能通过隐藏字符串、忽略所有 stage 校验、要求重新 add 或默认重写旧 md5 解决本题。

初态证据链完整：`Stage.create` 将运行目录和 stage 路径变为绝对路径（439–451）；`Stage.load` 将缺省 wdir `"."` 相对于 stage 文件目录解析为绝对路径（494–520）；`dumpd` 原样放入 `self.wdir`（524–536）；`dump` 仅在写 YAML 时转相对路径（538–554）；`_compute_md5` 从 dumpd 取字典，却只删除字面值 `wdir == "."`（558–577）。同处源码已经明确说这个删除规则用于兼容不含 wdir 的旧 pipeline。因此故障的工作目录表示根因可从公开代码推得，不需要 gold 或原始大 XML 才能定位。

原文件内容及缓存并未给出，不能原样重跑完整 CLI 状态并证明内容 md5；但 stage 元数据校验的最小检查不需要读大文件内容，可使用公开 YAML 或小型本地旧格式 fixture。实际旧 0.28 环境、所有中间版本迁移政策不在材料内；接受曾由坏版本生成的所有绝对路径哈希，不是本题已明示目标。

## 2. 需求—断言双向映射与全部参考案例

| 公开需求或合理旧行为 | 依据 | 对应验收与边界 |
|---|---|---|
| 旧无 wdir 元数据不应仅因升级变 checksum | 题面旧 YAML；stage.py:567–572 的兼容注释 | F2P 在本版本创建 stage、删除 YAML wdir 再加载，检查 changed=False；没有装载题面固定旧 md5。noop 在新增内部表示断言即停，未实际走完该兼容性部分。 |
| 缺省和显式 `.` 在校验上等价 | 同上、旧 TestDefaultWorkingDirectory | unit 原 test 与新增 default 两项固定哈希相同；它们 mock dumpd，输入已经是目标表示，隔离验证 `_compute_md5` 规则。 |
| 非默认工作目录仍影响校验 | wdir 决定命令 cwd/输出位置；旧 test_run:633–649 | 新增 non_default 单测对 `".."` 期望另一固定哈希，但 mock dumpd，未经过真实绝对目录到相对目录的转换。 |
| 保存/加载不擅自重算存储 md5 | 旧 TestReload | P2P 将顶层 md5 改为 32 个 `1` 后 load/dump，仍应相同；不是验证该 md5 正确或状态干净。 |
| 默认 wdir 写入 YAML 为 `.` | 旧 test_stage、test_run | F2P 保留此既有持久化断言；新增 **内存 dumpd 字典** 同样必须为 `.`，超出只检查持久化/状态结果，可能限制修复位置。 |
| 真正数据/命令/依赖变化继续可检测 | stage.changed/status、输出状态源码 | 本题 13 个案例未直接断言修改真实内容后 status 变脏；公开 test_status/test_run 有相关回归，但未在本次命令中执行。 |
| 固定哈希算法及嵌套 md5 语义保持 | `_compute_md5`、dict_md5、旧 unit test | 原 unit 和新增两项明确固定摘要；摘要用于旧格式兼容，有语义依据，不能仅因“固定字符串”指控过拟合。 |

### 2.1 两份 patch 的全部新增断言与 helper/Mock

`V/test.patch` 全 65 行已读，改 `tests/test_stage.py` 和 `tests/unit/stage.py`，不删除旧案例。功能案例 `tests/test_stage.py::TestDefaultWorkingDirectory::test_ignored_in_checksum` 是唯一 F2P；完整过程与断言为：

1. `self.dvc.run(cmd="echo test > foo", deps=[bar], outs=[foo])` 通过真实 run、shell、缓存/状态路径创建 stage。
2. **新增** patch:8–9，`stage.dumpd()[stage.PARAM_WDIR] == "."`，检查内部字典的具体表示。N:542–548 在此失败：实际是 `/tmp/dvc-test...` 绝对目录。
3. **原有** 从 stage YAML 读 wdir，仍断言 `"."`；然后手动删除 wdir 并写回。
4. **新增** patch:18–20，重新读取 YAML，`assertIsNone(d.get(wdir))`，确认删除后的 fixture 没有可用 wdir。它是测试输入检查，不是另一条独立旧校验复现。
5. **原有** 在真实 `self.dvc.state` context 中加载，断言 `stage.changed()` 为 False。gold 完成该案例，G:1332–1333/1446–1447 的日志显示相同生成 checksum 与未变化状态；noop 因步骤 2 中断，不能把它写成“旧文件校验断言在 noop 下失败”。

两个新增 unit 方法均构造 `Stage(None, "path")`，outs=`[{path:"a",md5:"123456789"}]`、deps=`[{path:"b",md5:"987654321"}]`，顶层 md5=`"123456"`、cmd=`"mycmd"`：

- `test_wdir_default_ignored`（patch:33–48）额外 wdir=`"."`，Mock `stage.dumpd` 返回指定 d，断言 `_compute_md5()` 为 `e9521a22111493406ea64a88cda63e0b`。
- `test_wdir_non_default_is_not_ignored`（50–65）仅改 wdir=`".."`，同样 Mock，断言为 `2ceba15e87f6848aa756502c1e6d24e9`。

这两个名字容易造成误解：它们均是 **P2P**，本 base 的 `_compute_md5` 原本就能正确处理已经相对化的 `.`/`..`；当前 noop 两项 PASS（N:1402–1403）。Mock 仅替代序列化输出，真实哈希、过滤及比较都执行，但恰好绕过 gold 所修改的 `dumpd()`。所以它们保护“规范化后的字典如何哈希”，不证明“真实非默认工作目录如何进入字典”。

fixture 链已具体展开（`B/tests/basic_env.py` 全 116 行）：TestDir 创建小型 foo、barr、code.py 和两个目录，切换到临时 cwd；TestGit 用 GitPython 初始化并提交，遇 GitCommandNotFound 最多重试 5 次；TestDvc 初始化真实 Repo 并开启日志。FOO/BAR 内容长度不同是为避免文件时间戳粒度造成的变更检测误判。没有下载 Wikipedia XML 或使用 GCP_CREDS_FILE；它只在此 helper 中定义，没有被这两个测试模块消费。TestCase 的 assertRaises/Equal/True/False/IsNone 均是真实 unittest 断言。

`Stage.validate` 调 schema，转换字符串后验证 cmd/deps/outs；load_stage_file 使用 yaml.safe_load。`OutputLOCAL.dumpd` 从真实输出对象构建相对 stage.wdir 的路径（57–68），`OutputBase.dumpd` 从 info 拷贝并保留 cache/metric 等（167–185）；`dict_md5` 对递归过滤后的 dict 用排序 JSON 的 UTF-8 字节做 MD5（utils:76–104）。没有 Mock 固定 `_compute_md5` 返回值，也没有通过捕获日志文本伪造通过。

### 2.2 全部 12 个 P2P

| 完整类/方法（文件前缀见表） | 断言内容、覆盖与实际结果 |
|---|---|
| `tests/test_stage.py::TestSchemaCmd::test_cmd_object` | cmd={} 应抛 StageFileFormatError；helper `_validate_fail` 包含 assertRaises。 |
| `TestSchemaCmd::test_cmd_none` | cmd=None 调 validate 不抛异常。 |
| `TestSchemaCmd::test_no_cmd` | 空 dict 可验证。 |
| `TestSchemaCmd::test_cmd_str` | cmd 字符串可验证。 |
| `TestSchemaDepsOuts::test_object` | deps={} 和 outs={} 分别应抛 StageFileFormatError，两次断言。 |
| `TestSchemaDepsOuts::test_none` | deps=None 和 outs=None 分别可验证。 |
| `TestSchemaDepsOuts::test_empty_list` | deps=[] 和 outs=[] 分别可验证。 |
| `TestSchemaDepsOuts::test_list` | 三个条目分别有字符串 checksum、None checksum、无 checksum；deps 可验证，再为前两个加 cache True/False 作为 outs 可验证。 |
| `TestReload::test` | add 返回一个非 None stage；人为改 md5 后 load 非 None，再 dump 保持该值（base:72–95）。不要求重算人为 md5。 |
| `tests/unit/stage.py::TestStageChecksum::test` | 原有 Mock dumpd 字典无 wdir；固定哈希 `e952…63e0b`。 |
| `TestStageChecksum::test_wdir_default_ignored` | 新增 Mock 字典 wdir=`.`；同固定哈希。 |
| `TestStageChecksum::test_wdir_non_default_is_not_ignored` | 新增 Mock 字典 wdir=`..`；另一固定哈希 `2ceb…6d24e9`。 |

表中省略文件前缀的 schema/reload 方法均属 `tests/test_stage.py`，省略前缀的 checksum 方法均属 `tests/unit/stage.py`。所有 12 项在 gold/noop 两次都通过（G:1469–1481、N:1392–1403）。官方命令显式指定 `tests/unit/stage.py`，因此不依赖其是否符合默认 `test_*.py` 发现规则。

实际收集 13 = 10 个功能文件 TestCase + 3 个 unit TestCase。逐个原始 PASSED/FAILED 摘要 ID 与 F2P/P2P 并集作集合比较完全相同，两边都是 13 个完整唯一身份；两份 diagnostics 同样解析 13、outside=0、reference_missing/skipped=[]。本题没有看到参数身份碰撞或额外执行未纳入参考的案例。不把其他题的 parser 风险搬过来，也不因此外推所有候选都安全。

## 3. 合理替代、自然部分实现与唯一优先实验

合理路线至少有两类。第一类统一 dumpd 的持久化语义，运行对象仍保留绝对 wdir，序列化字典相对于 stage.path 所在目录，默认值沿原 `_compute_md5` 规则忽略；这是 gold 的主要路线。第二类保留现有内部 dumpd 表示，在 `_compute_md5` 的输入副本中，将绝对 wdir 相对于 stage 文件目录规范化，已有相对值/缺省值按原规则处理；原 dump 继续正确写相对 YAML，`is_cached` 的旧/新 stage 在相同路径下比较仍可保持一致。这也是独立公开读稿列出的合理范围，并非读 gold 后凭空要求一种新架构。

第二类路线只要保留 dumpd 原约定，就会被新增 `dumpd()["wdir"] == "."` 拒绝，即使旧 YAML 的 changed_md5、状态文本、非默认工作目录和持久化结果已正确。源码中 dumpd 没有“必须相对表示”的独立公开 docstring，仓库内主要消费者是 `_compute_md5`、`dump` 和 `is_cached`；题面没有指定该内部字段表示。因此此新增断言存在具体的实现定位约束疑点。**尚未实现/运行替代候选，不能称为已证误杀**；需要先证明完整行为等价，不能以只修一个示例为正解。

同时存在有依据的自然部分实现风险：把真实 `dumpd()` 的 wdir 一律写成 `"."`。F2P 的默认场景可能通过；原 dump 仍在写文件时用真实 self.wdir 覆盖相对值，所以保存的默认 fixture 和 reload 也可能看起来正常；三条哈希 unit 全部 Mock dumpd，非默认 `".."` 的 P2P 不会发现真实 dumpd 已被错误抹平。此做法会忽略真实非默认工作目录的校验差异，和公开工作目录行为不符。该候选未执行，不能写成已获 reward 的错误解。这里的疑点来自具体 Mock 边界和缺少真实非默认构造，不是因为 P2P 少或一般覆盖空白自动判坏。

唯一优先后续实验建议是 **固定配方的 base/gold/“仅在校验输入规范化 wdir”合法替代候选三方对照**：官方 13 项保持原样；审计外置探针对题面原 YAML 的顶层 md5 做加载校验、对小文件的旧无 wdir/显式 `.` 做干净状态检查，再对真实嵌套 stage 的非默认目录与数据变更检查状态，比较实际行为和官方失败位置。若替代候选行为通过但只因内部 dumpd 断言被拒，才形成具体过严证据；若它漏掉 is_cached/真实目录差异，则收回其完整合法性推断。这个实验也可澄清非默认目录的 Mock 盲区，但本审不另行机械堆叠新实验。所有命令/候选仅是建议，未写入 clone、未执行，也不改原始题目、测试或 reward。

## 4. Gold、调用者和回归边界

gold 只改 `dvc/stage.py`。它把相对于 stage 文件目录的 wdir 计算从 `dump()` 移到 `dumpd()`，让计算校验和写文件共享同一表示；同时把 `dump(self, fname=None)` 改为 `dump(self)`，总写 self.path，移除原 dump 内再计算相对路径的段。没有改 `_compute_md5` 的过滤/排序/hash 算法，也没有把真实 self.wdir 改成相对路径。静态上这直接处理公开链中的绝对路径污染，保留缺省 `.` 省略规则与非默认目录值。

已读并追踪以下具体消费者：

- `Stage.save` 保存 dep/out 后计算 md5，`changed_md5` 再计算比较，`changed()` 还合并真实 deps/outs 状态；`check_can_commit`、`_already_cached` 和 reproduce 都依赖这条路径（stage.py:182–242、272–276、558–617、771–779）。
- `Stage.is_cached` 对旧/新 dumpd 字典删除顶层及输出校验后比较（351–380）。gold 两侧用同一 self.path 对应的位置，相对化应保持该比较的意图；实际 build-cache 回归未在 13 项中执行。
- `Repo.add` 创建/保存/commit 后 dump（repo/add.py:52–64、12–13），`Repo.run` 先 Stage.create/run 后 dump（run.py:34–65）；这连接用户 add 场景与 F2P run 场景，不能只修 CLI 文案。
- `Repo.move` 在需要时更新 stage.path 与 stage.wdir，然后无参 dump（move.py:45–66）；输出路径序列化相对于 stage.wdir，不应被工作目录校验修复破坏。
- repo status/command status 两模块全文已读；数据缺失/变化与顶层 checksum 的状态来源已分清。

仓库内 rg 检索的 stage.dump 调用均不传 fname，包含 add/run/reproduce/import/move/metrics.modify/lock/commit 和 TestReload；没有发现现有内部调用因 gold 删 fname 参数而直接报错。原可选参数确实能按另一个保存位置计算 wdir，gold 缩减这个方法签名；外部调用者/兼容承诺未检查，不能从“没有内部调用”证明对所有使用者无回归，也不能仅凭 API 变化判 gold 已错误。创建中的 path=None 对象尚未赋路径时不应被随意当作正常持久化对象；未找到真实内部在此状态调用 dumpd 的证据。

已读取而**不在本次执行/冻结参考内**的相关公开回归包括：`tests/test_status.py::TestStatus::test_quiet`（数据改变后返回 1）、`test_run.py::TestCmdRunWorkingDirectory`（默认 YAML `.`、嵌套 stage 的 `..`、运行对象绝对 wdir）、TestRunDeterministic 相关段（is_cached/重运行）、`tests/test_move.py` 的跨目录 move 及输出相对路径、`tests/test_utils.py::TestUtils::test_dict_md5` 的嵌套字段过滤。它们为审计选择依据，不冒称已通过，也不要求全仓/所有云远程测试才能判断本题。

关键文件哈希：stage.py（实读全 779 行）`03395fbcf4e983bf0c6095dc524e49c728f64de8bff456fbb9f96522d2b88f59`；utils/__init__.py（全 234 行）`2bcbae9a9a18d4518c6469265fe571ed792f8b858c48aecbeb26f3fd13de4746`；base tests/test_stage.py（116 行）`def7a786bcae0c7d88e8fe31831da7850ab8a42cbd3644604f1729d08daf6b2a`；base tests/unit/stage.py（16 行）`ff5762605458ef12c62da89f4a5c01d27768f5d0dc8cf89002b9da395744097d`；basic_env.py `fdd6c5b57282f1fcc54647da2e16dbb87a716330fcaf5886254ef9c976eaa5f6`。

## 5. 具体开发条件、环境配方与原始执行

| 条件 | 任务用途和证据 | 未知或边界 |
|---|---|---|
| Python、shell、Git | 报告者 Python 3.6.8；grading 3.8；G/N 实际 Linux Python 3.8.19、pytest 7.4.4。fixture 需 Git init/commit；F2P 执行 `echo test > foo`。 | 不把报告者平台当实际 actor；actor 解释器激活、Git 身份和 shell 未验证。 |
| 源码与导入 | 修改纯 Python stage.py，无 DVC 本体编译需求。两次观察 import `/testbed/dvc/__init__.py`，模块版本 `0.30.0+9175c4.mod`。源码导入可能写 dvc/version.py（init.py:21–45）。 | actor 对源码/生成版本文件/解释器 prefix 的权限未知；不是当前桌面导出可直接当运行环境。 |
| 包与收集依赖 | setup.py 核心含 schema/PyYAML/GitPython/networkx；all extra 包含旧 boto3 1.7.4、google-cloud-storage 1.13.0、Azure、SSH 客户端。unit 用第三方 mock；tests/requirements 含 pytest/nose/awscli 等。 | 别的 DVC 版本配方不能直接复用。顶层 requirements 的 boto3 1.9.86 与 setup.py extra 不同；本题修复按实际 metadata 安装并核依赖。 |
| 本地状态与缓存 | TestDvc 生成小文件，State 用 SQLite（state.py:210–225），RemoteLOCAL 建缓存、尝试本地链接/拷贝。 | 需要可写 tmp、repo、home 及兼容文件系统；原 XML/缓存缺失不阻塞元数据级检查，完整原 CLI 数据场景未复现。 |
| 测试导入资源设置 | tests/__init__.py 设 fd 2048、进程 soft limit 到 hard limit；默认项目鼻子测试入口带多进程。 | actor hard limit/配额未核；建议显式串行窄测，不把导入阶段失败归为 checksum bug。 |
| 网络阶段 | 包从 `/opt/rh2/build-wheels` 离线取，grader policy deny_all；目标测试用本地文件和 Git，不需要云桶/Wikipedia 下载。 | Repo 初始化的 updater 可启动后台进程：G:1234/1252 记录尝试启动 updater daemon，不能称无网络相关副作用；不证明实际访问成功。公开源码可用 DVC_TEST 关闭 updater/analytics（updater.py:42–44、analytics.py:205–212）。 |
| 资源 | grader 为 rh2grader/54322，2 CPU/4 GiB、PID512、shm64 MiB、tmp1 GiB；mem_peak_mb 634.945/688.609。 | actor 计划 home256 MiB 等来自共用卡，未有本题实测；无并发/多次重置/重复稳定性证明。 |
| 操作指令和输入 | 公开 workdir=/testbed、allowed_tools=bash/edit，提示仅改非测试源码、窄测，声称 testbed conda 激活。 | 实际 Claude Code 请求、消息层级、工具、actor/54321 shell 未捕获；private grader 成功不补全这些未知。 |

本题 recipe 不采用其它版本的 pathspec/networkx 修复。两份 `R/{gold,noop}/recipe/recipe.json` SHA 均为 `c2268f6361b932e873bf1bae7824d5edabd087a1779f85212cee20299e974188`，内部 recipe_sha256 为 `701c6da6901641e96249f1ff427d2481eb323d00fad0cf24b46cad3ecbaaf4b0`。修订安装顺序：先固定 awscli 1.15.85 / PyYAML 3.13 / colorama 0.3.9 / rsa 3.4.2（失败即返回），再安装 tests/requirements（失败即返回），最后 editable `.[all]`，保存返回码、打印 DVC metadata 版本、返回该安装码。解释为匹配旧 boto3/botocore 与 CLI 依赖；原件决定字段 E13 只是 recipe 记录，不沿它寻找未开放分析。

G:387–410 显示本地 wheels 安装这四项，411–438 的 requirements 解析接受其严格依赖；531–551 显示 editable 构建/安装与 install RC 0，metadata DVC 版本为 `0.30.0`。ledger 观察的模块 Git 版本为 `0.30.0+9175c4.mod`，与分发 metadata 是不同观测字段，不直接据字符串不等判错包。两份 ledger/diagnostics 的 install_failed_commands=[]、log_partial=false，与已检查关键安装段一致。没有将旧 before 脚本串联命令的末尾码当作当前成功证明。

candidate/eval 前后脚本静态 diff 仅改 install 段，选择器仍为 `pytest -rA tests/test_stage.py tests/unit/stage.py`。两侧 audit SHA 相同：candidate before `3e8e718f6698c81d9769ea7e8ac21a09526e2ed8b5824313e4f2eb512fb88f1a`、after `9c71ac98854961f76ba2025bb26091b03556ad50b6045bc2631b4bcd6f64468b`；eval before `ec9ee98f18c33eb0221ffabdb5447a2992dd562b4df46b4590f686b6a983dcfe`、after `9cfd1dd429cdfc73b7b859455de8df0e98906db15caaf3482aa2451c52b2e570`。实际派生镜像 `sha256:d71db46cbc0fdd24b26db0202e326bc9ec9764b07b19704fb293383849220a70`；不是公开 image digest 已原样验过的证明。

| 既有运行原件 | gold | noop |
|---|---|---|
| run_id / attempt | `er19-dv1-iterative__dvc-1681-gold` / 1 | `er19-dv1-iterative__dvc-1681-noop` / 1 |
| install_seconds / RC | 9.678 / 0 | 8.572 / 0 |
| test_seconds / RC | 12.128 / 0 | 11.857 / 1 |
| pytest 原始结果 | 13 passed / 13 warnings，G:1482 | 1 failed、12 passed / 13 warnings，N:1405 |
| F2P / P2P 报告 | 1/1；0 fail / 12 | 0/1；0 fail / 12 |
| reward / resolution | 1.0 / RESOLVED_FULL | 0.0 / RESOLVED_NO |
| 逐 ID 与 reference | 实际/解析/参考均 13，完整摘要 ID 集合相同 | 同左 |
| mem_peak_mb / cleanup | 634.945 / removed true | 688.609 / removed true |

G:563–569、1469–1486 和 N:522–548、1392–1409 直接支持上述执行结论；部分 warning 是旧 Google/pkg_resources/collections API 弃用，不是测试失败。两份 diagnostics 仍为 env_qualification=absent、compile_probe=null、resource_facts=null、install_probe=absent。candidate.apply_user=agent/54321 只指应用补丁，不能改写实际 grader rh2grader/54322 的执行身份。所有这些是**已有运行的静态复核**，本审没有重跑。

后续 actor 开发侧最小建议（均未执行）：在实际 actor 环境核 id、python/pip/Git 版本、dvc import 路径、PyYAML/schema/mock 是否可导入和 repo/home 可写；设置 `DVC_TEST=true`，运行公开原版 `python -m pytest -q tests/test_stage.py tests/unit/stage.py` 或对应 unittest 类。普通 CLI 复现应检查状态内容，quiet 模式才可用 0/1 区分干净/变化。若验证题面 YAML 的 stage md5，可用临时 Repo+Stage.load，不要求下载大 XML；没有数据缓存时不得把完整 status 的所有项都期望为空。建议不是已执行命令，也不向 actor 提供隐藏断言。

## 6. 候选投影、恢复与合法修改范围

gold ledger 的 included_paths 仅 `dvc/stage.py`，noop 为空；ignored_paths/unsupported_shape_reasons 为空，均 projectable。gold frozen_patch_digest 为 `bc2fbf0b5d5014bc72ed548ffb3f745c9bb02bc8b866c857a1aa6bba96a112e7`，不是 gold 原始 patch 的摘要，不混用。G:161–196 的实际 diff 为目标修改；G:147–156 的 init.py 版本变化属于 `git show` 输出 base 提交本身，不是额外候选或环境源码改动。

G:197–247（直接读 checkout/apply 段及 setup 标记）、N:159–206 的对应标记显示两个官方文件从指定 base 恢复后 clean apply。两份 diagnostics：RESTORED=2、EXPECTED_TEST_FILES=2、TEST_FILES=2、APPLY_RC=0、SETUP_OK=1，缺失/异常为零；control_surface protected_files=2、protected_dirs=5、PROTECT_OK=1，writable_prefixes 完成。runner_digest 前后相同、integrity_changed=false。这证明该对照中的官方恢复与投影，不是对任何候选、依赖、配置和插件控制面的全覆盖验证。

原公开 hints 的“所有测试改动都会恢复、永不计分”解释范围过大；本题能证实的是两份官方测试恢复。默认取消测试名通配与具体官方恢复要分别记录，不能由 test 文件名机械拒绝合法改动。若“禁止改测试”操作指令真实适用，本题可通过源码局部修复和临时外置诊断完成，未见必须改测试才能实现的阻塞；若不适用，也不能擅自推定任意测试/helper 都会投影计分。实际消息未知属于共享输入问题，不因此判原题无效。

无本题特定新增排除依据，建议 `additional_exclusions=[]`。没有更改 protected 测试、原始 expected、F2P/P2P 或奖励。本文的替代路线/外置矩阵不是对生产规则的修改授权。

## 7. 关系与暴露

仅核本题 source row、base、gold/test 材料和本题 repaired 运行，未查本题未来 PR/旧历史、其它任务原件或跨题相似度。与同项目其它题是否重复、是否应同侧、是否同修复回移植，均没有新增证据，不能由共享 Stage 文件或环境配方家族推断。

本私有主审已读本题隐藏测试、gold、F2P/P2P、奖励与当前开放的环境汇总，不能作为盲解者。公开角色先独立完成并封存；本审没有把私有发现传给公开角色。真实 actor 仍可能有 Git 对象、预装包、生成物、日志或可访问网络中的材料，导出 base 无 `.git` 不证明其无答案暴露；当前未检查真实镜像/消息/网络，不能声明防泄漏通过或未污染留出。

## 8. 历史前建议与明确未决项

1. **任务有明确公开缺陷入口。** 未变化旧 stage 的顶层校验被绝对 wdir 污染，源码兼容注释支持目标；原始大数据缺失不是元数据调查的硬阻塞。报告版本拼写差异不影响指定 base。
2. **原始分差可信但证明范围有限。** 两份修复配方安装完成、13 个完整 ID 对账，唯一差异在新增内部 dumpd 表示断言；不是 collection/install/解析空集导致的 0。gold 的局部表示修复与源码因果一致，未逐项证明题面旧哈希/完整 CLI 或广泛回归。
3. **最值得独立验证的是合理路线拒绝风险。** 规范化只放在 `_compute_md5` 的候选可能满足公开目标，却被内部字典表示断言拒绝；当前为静态、未执行的合法性假设。优先做 §3 三方对照，不预判测试必须删改。
4. **非默认目录的真实路径保护不足。** 两个新增 unit Mock 排除了待修的序列化入口；“一律写 .”自然部分实现可能逃过这些案例。尚无错误候选分数，不能称已证 false positive；普通覆盖空白本身也不构成判坏理由。
5. **gold 相关边界保持可见。** dump(fname) 签名缩减未发现内部调用破坏；is_cached、真实非默认目录、move/status 数据变化等已选读但未执行。不能把 12 P2P 等同所有调用者均通过。
6. **actor 的开发与输入仍未知。** repaired grader 具体 SDK pins/身份/离线 wheels 已核，不等于 actor 已能安装/测试；也没有真实模型独立求解、资源稳定性或泄漏检验。建议只保留 `needs_review / static_review`、`development_diagnostic`，等历史与独立 reviewer 后再收口。

当前只写本题 `analysis_before_history.md`。历史尚未开放，old_findings_delta/card/screening_record 尚未开始。无新 CPU/模型成本；若后续入结构化记录，未知总容器墙钟、agent tokens、human_decisions 保持 null，不能用旧 install/test 局部秒数充当完整成本。

## 实际阅读记录

已读本题公开四文件、独立 public_read；private grading/test/gold/source_refs/run_refs/validation/environment_record 全包；S2 指定三条 113 行；两份 ledger/diagnostics/recipe；candidate after 全文、candidate/eval before/after 安装差异与选择器；关键 log 段及所有 13 个摘要节点。G 主要逐行范围为 137–218、384–439、527–606、1467–1489，另按 setup 标记、F2P/Computed stage/未变化/updater 关键行定位；N 为 522–554、末尾 1392–1409，另定位 restore/install/版本/RC 标记。日志全文件哈希不代表逐行阅读所有依赖日志。

源码实际读：stage.py 全 779 行、utils/__init__.py 全 234 行、两个 base stage 测试全文、basic_env 全文、repo status/command status/add/run/move 全文、output base/local 及其包初始化全文、dependency base/包初始化全文、setup/requirements/tests requirements/tests __init__/__main__/dvc __init__ 全文；repo __init__:1–150，updater:1–105，analytics:40–77/202–233，state:1–14/205–236，remote/local:1–77。相关回归实读 test_status 全 25 行、test_utils 全 60 行、test_move 全 185 行、test_run:1–105/210–265/600–715；未将这些扩展文件的 fixture 全链或其未读部分算作全面审查。另 rg 定位 dump/dumpd/校验调用者；检索命中不等于全文已审。

未读本题 history/旧调查/raw hints/上游未来提交，未查网络/外部文档、原 0.28 安装或真实原 XML/缓存，未验证 wheel 内部源实现或实际 actor 环境。没有读其它题结论来完成本稿，没有执行项目/候选/测试/安装/容器/SSH/模型，没有改动输入或生产源码。
