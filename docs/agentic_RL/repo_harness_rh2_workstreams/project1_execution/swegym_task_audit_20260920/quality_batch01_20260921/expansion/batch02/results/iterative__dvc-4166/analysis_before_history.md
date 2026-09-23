# iterative__dvc-4166 — 历史前独立静态分析

审查日期：2026-09-21。角色：私有主审。建议暂定 `needs_review / static_review`，用途 `development_diagnostic`。本稿在本题 history 开放前形成；封存后不得回写，后续历史差异另写 `old_findings_delta.md`。

本题有可定位的目录匹配缺陷，现有原始运行也显示明确的 gold/noop 差异：修复配方下，唯一 F2P 由失败变为通过，58 个 P2P 引用未报告失败。需要进一步核对的具体问题是：目录尾斜杠的“仅匹配目录”边界未被实际断言区分，两条带前导空格的单测身份合并为一个截断引用，以及真实 actor 的环境与消息仍未验证。这些是分开的质量与使用条件，不能由一次 grader 成功一并消除。

## 0. 范围、来源与可复核身份

本文路径缩写均相对于权威根 `ROOT=${REPO_ROOT}`，不是当前 worktree：

- `I=runs/swegym_quality_batch02_20260921_v2`；`P=I/public/iterative__dvc-4166`；`V=I/private/iterative__dvc-4166`；`B=P/base`。
- `B1=docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921`；`O=B1/expansion/batch02/results/iterative__dvc-4166`。
- `R=runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-4166`。
- `G=R/gold/eval_logs/evallog_replay-er19-dv1-iterativ_ce06dec1.eval.log`，SHA-256 `6a9ef5059178cc9503e8ff7172d9a68cf086f2f964af68e6e4193ef61f06ab7a`，1026 行。
- `N=R/noop/eval_logs/evallog_replay-er19-dv1-iterativ_de73b04d.eval.log`，SHA-256 `7689ee1dc5e2000b10d0e4bbef1dfe546e5993de9381f578717c18f2299affd7`，1021 行。

全文 G/N 的行号仅指上述各自 SHA 的原件。两个 log、ledger、diagnostics、recipe/audit 文件均直接读取本题精确引用对应的本地原件，未以环境汇总代替。`/work/env_recipe_repair_20260919/...` 引用对应此 ROOT 下 `runs/env_recipe_repair_20260919/...` 存档。只做文本读取、JSON 解析、文件哈希/比较和本稿写入；没有导入或执行 DVC/pathspec、运行 pytest/安装/容器/SSH/模型，也没有生成候选或改动源码、输入、测试、gold、reward。

已遵循并读过 `B1/roles/investigator.md`、`B1/record_template.md`、`B1/actor_environment_card.md`、`B1/../quality_review_protocol_20260920.md`，以及明确引用的 `project1_execution/environment_screening_definition_20260915.md`、`environment_screening_checklist_20260915.md`。未把角色卡例题当成本题证据。已读本题独立封存的 `O/public_read.md`，SHA-256 `0c7a35bc5352768f266ed95bfdeb00ed6b07f0e5683269fc4f714600eb282204`。本稿结合其公开解释后自行核原件，不是另一份公开盲读。

`V/source_refs.json` 指向 S2 ingest 的 `public_bundles_v0.jsonl`、`grading_bundles_v2_v0.jsonl`、`validation_bundles_v0.jsonl` 各第 **131 行**；只提取这三条指定行，分别与本题 public/grading/validation JSON 解析值比较一致，没有扫描相邻题。`grading.test_patch` 与 `V/test.patch` 相同；`validation.golden_patch` 与 `V/gold.patch` 相同；problem_statement 字节哈希与 bundle 声明一致。全文没有读本题 `I/history/iterative__dvc-4166/refs.json`，没有沿 private environment 中的旧 analysis/history 链接读旧结论，也没有读批次报告、manifest、method_adjustments 或其他题结论。已见 private environment 内嵌的运行/修复汇总和这些链接的存在，不能称为完全未接触汇总。

| 原件 | SHA-256 / 身份 |
|---|---|
| `P/user_prompt.txt` | `87f265d9911b740930988863b259fd51dd51882a651a0d2f3e133af69fc90c4b` |
| `P/public_bundle.json` | `19dc2da9cdae2fd34b306c1d10771f8b714366dd83287493afacfb0252f517b8` |
| `P/base_identity.json` | `a4b9bb0832661abae8b352f1ccad3420653052e09a751dfc542c01f3adaaf787` |
| `V/grading.json` | `2073235e1537cc021d7c8c98fb283c432a6067907cdf937049c4ced7f720ca30` |
| `V/test.patch` | `8947418a215b3d1ad5c8b682560755d0fb8285c52d49b9d36ae55416d9adea83` |
| `V/gold.patch` | `092d48c27ce32921855206a1d1608d653edaed3e3878be1dac5984747d3a3e03` |
| `V/environment_record.json` | `3177e0fb45f496dec9b5292d286ca83cf2c36a79f17c8ed0e3d678fb7213b24f` |
| `R/gold/ledger.jsonl:1` | `0af876dd6a6fbe1cf24997d37a1d7b3433d65b9aa6561787691c0bc179a91341` |
| `R/noop/ledger.jsonl:1` | `99b89e053dade54e2d5acb3a5e26c15ec2a04a6ab85b1fedb210970179f8852b` |
| gold diagnostics（与 G 同 stem） | `c06aba5cd11ed7746ce2963d45cbf012c776293a446032de24edd498e30040d8` |
| noop diagnostics（与 N 同 stem） | `e06976ee41bdfdd4d676a92f83d9562d9e015e170a633a791c1aaab6d8f883f1` |

base commit 为 `520e01f11305aba1994df354adef86e6d90180de`，声明 tree 为 `e9b82d895e5aa01606d2f0d12b424b87125dc364`。base_identity 记录 423 个 blob、1429005 字节，无 symlink/LFS 未物化项/gitlink，无导出 `.git`。这些完整性计数是导出元数据，本审未重建 Git tree 身份；关键读取文件的哈希另核。公开镜像 digest 为 `sha256:f32dbb8cd78ee8146529185f79532b3e3dca61c06a10c4ede6ca48ba26b15041`，不能与后述派生 grader 镜像混称。

## 1. 公开目标、已有能力与初始故障

`P/user_prompt.txt:3–46` 报告先排除全部再重新包含 scripts 时若干 `.dvcignore` 写法失效。六组失败尝试是 `* / !scripts`、`* / !/scripts`、`/* / !/scripts/`、`/* / !/scripts/*`、`/* / !/scripts/**`、`/* / !scripts/`；这里斜线两侧表示两行规则的分隔，并非规则文本。用户说 `/*` 加 `!/scripts` 两行有效。题面没有目录树、触发命令、实际/期望文件列表、平台或依赖版本。

合理目标是让目录相关的忽略与否定规则按既有规则顺序、路径根位置和遍历语义工作，修复有尾斜杠的目录匹配，并保持已有成功例。不能由“六组尝试失败”推导六组都应递归重新包含 scripts 内容：排除父目录后的子项否定、`*` 与 `/*` 的作用范围、重新包含目录与重新包含其所有后代，本来可能不同。公开读稿也指出这种需求边界；私有测试新增的父目录剪枝说明与这个解释一致，但该说明不是 actor 必须事先知道的隐藏目标。

base 已经实现 `.dvcignore` 读取、pathspec 的 GitWildMatchPattern 转 regex、否定规则按顺序覆盖、相对根路径和非 Unix 路径归一化（`B/dvc/ignore.py:25–73`）。`__call__` 同时收到 `dirs` 与 `files`，却都只将无目录标记的 basename 交给相同的两参数 `matches`（45–49）。匹配层由此丢失调用者已经知道的文件/目录区别，这是具体缺陷入口，不是需要新建忽略体系。

`DvcIgnoreFilter` 在遍历时读取当前 `.dvcignore` 并原地改写 dirs/files（116–137）；`CleanTree.walk` 同样原地过滤底层 walk 返回的 dirs（233–241），使已被排除的父目录不再递归。`CleanTree.exists/isdir/isfile` 通过 `_parents_exist` 与 `_valid_dirname/_valid_filename` 复用这一过滤体系（161–231）。因此故障涉及遍历与路径查询的一致性，并非单个显示层问题。`B/dvc/ignore.py` 实读全 250 行，SHA-256 `998e87ebd8b3f87ac23f3b7e768cdb87b4f067be6f9478152a44ba0bfbc92460`。

## 2. 所有修改断言、fixture/helper/Mock 与参考集合

官方 patch 只改 `tests/func/test_ignore.py` 与 `tests/unit/test_ignore.py`。已读 patch 全 267 行、两个 base 测试文件全文、相关 fixture/helper 和参考 ID 全表。没有以 F2P 数量代替断言审查。

### 2.1 新增的五个功能案例

| 案例 / patch 行 | 输入、断言与保护范围 |
|---|---|
| parent 参数 0，15–40，P2P | 创建 `dir/subdir/not_ignore`；根规则 `subdir/*`、`!not_ignore`；断言 `_files_set("dir", dvc.tree)` 恰为 `{dir/subdir/not_ignore}`。允许进入未被整目录排除的父目录，再由后规则重新包含子文件。 |
| parent 参数 1，15–40，P2P | `dir/subdir/should_ignore`；规则 `subdir`、`!should_ignore`；断言空集合。无尾斜杠的父目录排除应剪枝。 |
| parent 参数 2，15–40，唯一 F2P | 同一树与空集合断言；规则改为 `subdir/`、`!should_ignore`。目录标记必须使父目录真正被排除；子文件否定不能绕过该父目录。 |
| `test_ignore_sub_directory`，43–61，P2P | 建立 `dir/doc/fortz/b` 与 `dir/a/doc/fortz/a`，在 `dir/.dvcignore` 写 **`doc/fortz`**，保留后者与该 ignore 文件。实际检验中间斜杠的根位置；注释谈 `doc/frotz/`，但执行输入没有尾斜杠，拼写也为 fortz。不能把注释算成目录专属匹配断言。 |
| `test_ignore_directory`，64–70，P2P | 创建两个空目录 `dir/fortz`、`dir/a/fortz`，规则为 **`fortz`**；仅断言文件集合包含 `dir/.dvcignore`。`TmpDir._gen` 的空 dict 确实只建空目录；`walk_files` 根本不枚举目录。因此两个目录即使未过滤，该文件集合也一样，不能证明目录被排除。 |

`tmp_dir.gen` 没有伪造匹配结果：`B/tests/dir_helpers.py:120–145` 递归创建目录和文本/字节文件；空 dict 调 makedirs。`tmp_dir` fixture 使用临时目录并切换 cwd（250–266），`dvc` fixture 返回其初始化的真实 Repo（275–276）；是否创建 SCM 由请求 fixture 决定（90–108）。`B/tests/func/test_ignore.py:127–128` 的 `_files_set` 将 `tree.walk_files` 结果转集合，`B/tests/utils/__init__.py:22–23` 只把反斜杠换成 `/`。`BaseTree.walk_files`（`B/dvc/scm/tree.py:34–38`）只消费每层 files，不消费 dirs。故上表对空目录断言的限制是从完整 helper 链得出。

### 2.2 参数化单测：41 个实际布尔断言

`mock_dvcignore`（base unit:9–14）使用 MagicMock tree，仅以 `mock_open(read_data="\n".join(patterns))` 替代 ignore 文件 I/O；真实构造 `DvcIgnorePatterns`，真实调用 `.matches(dvcignore_dirname, file_to_ignore_relpath)`，断言其结果等于 expected_match。它没有替换 regex、匹配器或直接塞入答案，也没有要求 gold 的 `is_dir` 参数名/新增实现。所有这些调用均按默认文件路径语义，没有显式传目录类型。

以下表中 `patternsN` 对应原始 pytest ID 的 N，路径以 Linux 展示；反斜杠是规则中的转义字符；`T/F` 为期望匹配布尔值。没有省略任何实际参数项。

| N | 路径 | 规则列表 | 期望 |
|---|---|---|---|
| 0 | `to_ignore` | `to_ignore` | T |
| 1 | `dont_ignore.txt` | `dont_ignore` | F |
| 2 | `to_ignore` | 空行；`to_ignore` | T |
| 3 | `#to_ignore` | `\#to_ignore` | T |
| 4 | `#to_ignore` | `#to_ignore` | F |
| 5 | ` to_ignore`（前导空格） | ` to_ignore`（前导空格） | F |
| 6 | ` to_ignore`（前导空格） | `\ to_ignore` | T |
| 7 | `to_ignore.txt` | `to_ignore*` | T |
| 8 | `to_ignore.txt` | `to_ignore*`；`!to_ignore.txt` | F |
| 9 | `to_ignore.txt` | `!to_ignore.txt`；`to_ignore*` | T |
| 10 | `!to_ignore.txt` | `\!to_ignore.txt` | T |
| 11 | `file` | `/file` | T |
| 12 | `data/file` | `/file` | F |
| 13 | `data/file` | `data/file` | T |
| 14 | `other/data/file` | `data/file` | F |
| 15 | `/full/path/to/ignore/file/to_ignore` | `to_ignore` | T |
| 16 | `to_ignore.txt` | `/*.txt` | T |
| 17 | `path/to_ignore.txt` | `/*.txt` | F |
| 18 | `data/file.txt` | `data/*` | T |
| 19 | `rel/path/path2/to_ignore` | `rel/*/to_ignore` | F |
| 20 | `file.txt` | `file.*` | T |
| 21 | `file.txt` | `fi?e.t?t` | T |
| 22 | `fi/e.txt` | `fi?e.t?t` | F |
| 23 | `file.txt` | `[a-zA-Z]ile.txt` | T |
| 24 | `2ile.txt` | `[a-zA-Z]ile.txt` | F |
| 25 | `rel/p/p2/to_ignore` | `**/to_ignore` | T |
| 26 | `rel/p/p2/to_ignore` | `**/p2/to_ignore` | T |
| 27 | `rel/path/path2/dont_ignore` | `**/to_ignore` | F |
| 28 | `rel/p/p2/to_ignore` | `rel/**` | T |
| 29 | `rel/p/p2/to_ignore` | `p/**` | F |
| 30 | `rel/path/path2/dont_ignore` | `rel/**` | T |
| 31 | `rel/p/to_ignore` | `rel/**/to_ignore` | T |
| 32 | `rel/p/p2/to_ignore` | `rel/**/to_ignore` | T |
| 33 | `rel/path/path2/dont_ignore` | `rel/**/to_ignore` | F |
| 34 | `rel/path/path2/dont_ignore` | `path/**/dont_ignore` | F |
| 35 | `to_ignore.txt` | `/***.txt` | T |
| 36 | `path/to_ignore.txt` | `/****.txt` | F |
| 37 | `path/to_ignore.txt` | `****.txt` | T |
| 38 | `data/file.txt` | `data/***` | T |
| 39 | `data/p/file.txt` | `***/file.txt` | F |
| 40 | `rel/path/path2/to_ignore` | `rel/***/to_ignore` | F |

patch:166–167 的 `data/sub/file.txt` + `data/*` 与 238–239 的 `data/p/file.txt` + `data/***` 是被注释掉的条目，不是执行案例，不计入覆盖。patch:110–113 注释谈 trailing spaces，执行输入却为 leading space，不能按注释扩张事实。没有任何执行单测规则以 `/` 结尾，也没有同名普通文件与目录的成对断言。

patch:78–94 删除 base 的 `test_ignore_from_file_should_filter_dirs_and_files`（两项集合断言），255–267 删除 `test_ignore_order`（三规则 `!ac*`、`a*`、`!ab*`，只保留 ab）。顺序仍有参数 8/9 的正反覆盖，但原三组切换案例不再实际执行；不是把两个被删除测试也算作回归通过。base 旧参数组被扩展和重排，而非仅追加。未改的 `test_should_ignore_dir[.git/.hg/.dvc]` 三项断言经过 DvcIgnoreDirs 后 dirs 恰为 dir1/dir2，属于另外三个 P2P 身份。

### 2.3 58 个 P2P 的完整归属与另外执行的案例

P2P 中有 40 个 `test_match_ignore_from_file` 身份，代表上述 41 个参数案例：N=5 和 N=6 只出现同一个不完整引用 `tests/unit/test_ignore.py::test_match_ignore_from_file[`，其余 39 个参数有各自完整身份。加上 `.git/.hg/.dvc` 三项，共 **43 个 unit P2P 引用**。功能部分的 **15 个 P2P 引用**如下；各自的断言均已阅读。

| 功能 P2P | 实际保护 |
|---|---|
| `test_ignore` | 普通过滤及切换 cwd 后相对路径结果（base:21–28）。 |
| `test_ignore_unicode` | Unicode 文件名忽略（31–35）。 |
| `test_rename_ignored_file` / `test_remove_ignored_file` | 忽略文件改名/删除不改变目录 mtime 摘要和 size（38–47、60–69）。 |
| `test_rename_file` / `test_remove_file` | 非忽略文件改名改变 mtime 摘要但不变 size；删除同时改变两者（50–57、72–79）。`get_mtime_and_size` 用路径到 mtime 的字典摘要，不仅靠墙钟间隔判变。 |
| `test_ignore_collecting_dvcignores[dir]` / `[dir/subdir]` | 忽略父目录后，不收集其内部 `.dvcignore`；断言 ignores 数为 3，默认目录过滤器、外层规则、DvcIgnoreRepo 类型均存在（89–109）。此处会约束既有集合/类型组织，纯外部等价的彻底重构未必保留这些内部表示；不要求本题必须重构它。 |
| `test_ignore_on_branch` | 当前工作树与另一 Git 分支的 ignore 内容不同，切换 Repo.tree 后文件列表应随 GitTree 变化（112–124）。 |
| `test_ignore_subrepo` | 父库忽略规则使子目录 foo 不存在；初始化子库并遍历其提交时，子库自己的 tree 又能看到 foo（154–168）。 |
| `test_ignore_blank_line` | 空行不改变其它有效规则（171–175）。 |
| `test_ignore_file_in_parent_path` 参数 0/1 | 上表两种子项否定/父目录剪枝，2 个引用。 |
| `test_ignore_sub_directory` / `test_ignore_directory` | 上表根位置与空目录文件集合，各 1 个引用，限制如已说明。 |

参考合计为 **F2P 1 + P2P 58 = 59 个身份**。`pytest -rA tests/func/test_ignore.py tests/unit/test_ignore.py` 实际运行 19 个功能案例 + 41 个匹配参数 + 3 个默认目录案例 = **63 个案例**。功能文件中 `test_dvcignore_in_out_dir`（输出目录含 ignore 文件应抛 DvcIgnoreInCollectedDirError）、`test_match_nested`（多层普通文件名/后缀过滤）、`test_ignore_external`（仓库外路径不套用内部规则）另外三项均实际执行、在两份日志中通过、原件断言已读，但 **不在冻结 F2P/P2P 列表**，不能称为三个新增计分回归保护。

G:644/956–1019 与 N:600/951–1014 证明实际收集和结果；G:980–981、N:974–975 明确包含两条不同的前导空格案例。两个 ledger/diagnostics 均记录 `num_parsed_tests=62`，而引用只有一个截断的 `...from_file[`，与这两项碰撞相一致。当前两项结果同为 PASS，不影响观察到的 gold/noop 对比；未读全局 parser 源码、没有合成状态实验，不能断言哪项覆盖哪项、混合 PASS/FAIL 时会怎样或已经发生奖励绕过。但不能把 58 个 P2P 写成 58 个独立完整参数节点，更不能宣称这两项被分别冻结保护。

## 3. 合理替代路线与自然部分实现

合理修复不必采用 gold 的具体签名。可以在目录调用边界传递类型或形成目录专用匹配路径，再保留规则组的先后覆盖和不带尾斜杠规则的效果；也可以采用能等价表达目录标记的匹配结构。已有 `.matches(root, name)` 的文件调用与根位置、转义、通配和否定语义要保留，默认目录过滤/子库边界与 GitTree 也要可用。新测试没有直接窥探 `is_dir`、正则内容或方法调用次数。就局部实现而言，未发现只认 gold 结构的私有硬约束；已有 collecting 测试的内部类型断言则使大幅重构有兼容义务，不能说任何外部等价路线都一定被接受。

从全部输入中可形成一个具体、自然的部分实现假设：在规则编译前把规则终端 `/` 去掉，当作“规范化目录写法”。唯一 F2P 的 `subdir/` 会变为本来已通过的参数 1 的 `subdir`；其余本题执行规则没有终端 `/`，因此静态看它可能通过整个现有验收，却错误地把目录规则也用于同名普通文件。它还可能掩盖题面部分有尾斜杠的重新包含案例。这是对“丢掉类型区别”的具体假设，不是编造一个与题意无关的硬编码解。

该候选没有被实现或执行，**没有“已骗过 reward”结论**。判断其风险的证据是规则全集、父参数 1/2 的输入差异和缺少普通文件对照；不能用常规覆盖不全自动判题坏。此处最有区分力的后续 CPU 建议只有一项：在隔离副本、固定同一配方下对 base/gold/上述尾斜杠规范化候选做三方对照，先保留官方参考原样跑，再用审计外置矩阵分别放置普通文件 `subdir` 与含叶文件的目录 `subdir`，用 `subdir/` 验证只排除目录，并覆盖公开的 `/*` + `!/scripts/` 与已成功的 `/*` + `!/scripts`。同时记录原始文件/目录可见性与官方 reward，避免仅看分数。实验尚未授权且本审未运行，也不改官方题目、测试或 reward。

## 4. Gold、调用者与相关回归

gold 只改 `dvc/ignore.py`：目录列表改传第三参数 True；`matches` 增加默认 `is_dir=False` 并继续透传；目录匹配同时检查无尾斜杠 path 与 `path + "/"`，文件维持原循环。每个规则组仍按原顺序更新 result，故后匹配覆盖前匹配的框架不变。静态上它修复丢失目录标记的直接原因，且保留两个参数的既有 matches 文件调用。内部 `ignore(path)` 改为 `ignore(path, is_dir)`，仓库内搜索仅找到本类内部调用，未发现已知仓库调用者遗漏；未证明外部用户从未调用该内部方法。

已沿调用链读取：`Repo.tree` setter 将 WorkingTree/GitTree 包为 CleanTree（`B/dvc/repo/__init__.py:136–144`）；WorkingTree.walk 直接采用可剪枝的 os.walk（`B/dvc/scm/tree.py:70–79`）；GitTree 使用 Git 对象 mode 区分目录/文件，并在 yield 后仅递归剩余目录（`B/dvc/scm/git/tree.py:63–67,113–129`）。因此类型应取自遍历上下文，不能仅凭当前磁盘 `os.path.isdir` 推定另一个提交中的节点。gold 利用已有 dirs 参数，符合这两个调用者。`CleanTree._parents_exist` 的各父目录检查也经同一过滤路径受益。

`B/dvc/utils/fs.py:33–60` 的目录 mtime/size 计算通过 tree.walk_files/tree.stat；gold 不直接改摘要，但忽略边界改变会影响追踪与缓存。功能 P2P 已提供有限的改名/删除回归。另已读 `B/tests/func/test_tree.py` 全 243 行，其中 GitTree walk（138–180）及子库 CleanTree exists/isdir/isfile（226–243）是相关回归；它们不在本次两文件命令内，不能把阅读当作本次执行通过。公开七组模式未在原日志逐项重现，也没有新 CPU 验证 gold 对全部原始尝试的结果。

关键源码哈希：`B/tests/unit/test_ignore.py` 为 `67cff53e0626e13934a1b74461d5d2648c8e56859fc1aadd9fc067282b6c48ed`；`B/tests/func/test_ignore.py` 为 `0b11d0098c2e97b3cc1f454cba2fbccdbb3e144545b45854aff75cf0be8f9602`；`B/dvc/scm/tree.py` 为 `f91b811d6838dd9b2d58ef4c42cad91be09d468ef17a292d266a78064e2166c1`；GitTree 为 `b97f9abc1dec274d101de2e2eff5925bd917ed8dfcf51ec3d89d4d7c14ff25d7`。

## 5. 具体开发条件、配方原件与运行边界

| 条件 | 需要它的具体操作、已见事实与未知项 |
|---|---|
| Python / shell | 公开提示称 `/testbed` 且 testbed conda 已激活；这只是可见字段，未验证实际消息或 agent shell。源 setup.py 的 Python 下限为 3.6、列举分类到 3.8；本题 grading 指定 3.9，原日志实际 Linux Python 3.9.19、pytest 7.4.4。需要 actor 解释器与 pytest 确实指向同一环境。 |
| editable import / 源码权限 | 修复 ignore.py 是纯 Python 编辑，不需要 DVC 自身编译。两次 grader 观察 import `/testbed/dvc/__init__.py`、版本 `1.1.7+520e01.mod`；actor 是否同样可写源码、导入修改后的文件、可以更新 editable 安装未知。 |
| pathspec / networkx / 依赖 | base setup.py 要求 `pathspec>=0.6.0`、`networkx>=2.1,<2.4`；本题 matcher 直接依赖 pathspec 的 pattern_to_regex 语义，单测不是纯自足 stub。配方固定 pathspec 0.8.1 和 networkx `2.3+rh2.1`。不能只让 actor 使用任意更新版后归咎补丁。 |
| 测试收集依赖 | tests/conftest 导入 remotes fixture；其 S3 文件顶层导入 `moto.mock_s3`。本题不请求 S3/SSH 服务 fixture，但收集仍需这些包可导入。base setup.py 含 moto `1.3.14.dev464`；G:205–217 的环境差异是改为 `1.3.14`，两次 grader 的环境源与导出 base 存在这项区别。 |
| 文件系统与 Git | 功能测试写临时文件、创建 .dvc、切换 cwd；branch/subrepo 案例需要本地 Git 初始化/提交/读取 tree。`TmpDir` fixture 已具体展开。无需真实云桶、外部项目数据或联网服务；预置依赖与测试期间联网是不同阶段。 |
| 网络与预置资产 | 两次 grader deny_all；pip 从 `/opt/rh2/build-wheels` 取本地 wheel，离线可执行是这份派生环境的结果。原 before 脚本含远程 Git、宽泛安装、`|| true`，不能把其联网/容错行为称为当前修复脚本。未获本地兼容 wheel 内容的精确导出引用，未审 `networkx+rh2.1` 内部补丁。 |
| 资源与时间 | grader policy 为 rh2grader/54322、2 CPU、4 GiB、PID512、shm64 MiB、tmp1 GiB、conda prefix 可写；两次 `mem_peak_mb` 记录约 343/485。共享 actor 默认还含 home256 MiB，但未有本题 actor 实测，不能把 policy/峰值当作 actor 资源验证。 |
| 测试与工具可见性 | public allowed_tools 为 bash/edit，并有窄测建议；实际 Claude Code 请求、工具定义、system message 和 actor/54321 的 shell 未捕获。actor 可自行测试公开 base 用例，不需要私有 patch。共享“禁止改测试”提示是否实际应用仍未知。 |

本题两个 `R/{gold,noop}/recipe/recipe.json` 字节相同，SHA-256 `ac685569d4a94fcfc4ec65dd1fe39a89cb970fe52e0d02ca280b8774d4cc601d`，内部配方摘要为 `92609c19e87f84aca299d9e2a8c11fc8e2e5350177266565876269e484a1a15d`。前后脚本直接 diff 仅替换 install 段：先 `python -m pip install --no-deps pathspec==0.8.1 networkx==2.3+rh2.1 || return $?`，再 `python -m pip install -e '.[all,tests]'`，保存其退出码并打印 DVC/pathspec/networkx 版本，最后返回该码。candidate/eval 的 pytest 选择没有改动。当前 recipe 是诊断环境输入，不是已验证的 actor 配方。

两侧 audit 文件哈希分别相同：candidate before `04cfd25db022691fc95cab7ce6acfde3bcf373cf2131d077cc05c9148e42273c`、after `0c9f9d453d4652f04241bdaa7ec7879169c593e5ddc7e3bdccbe2d9ea53dea05`；eval before `bce28db08c06842c02778475b54d1c82253456cde0be65c633b3b259a92a6539`、after `f880e235080d8d5de6c4d9922cc0a5477d12cf138e041279b13e0cdf8382c111`。实际派生镜像均为 `sha256:cfcef64300c96ff4e7dfd2c92bdf6025f9213df5e9574db72103174371b0107a`，与公开镜像 digest 不同。

G:408–424 显示 pathspec 0.12.1 被卸载并改为 0.8.1，networkx 2.3 改为 2.3+rh2.1，本地 wheels 完成安装；G:609–629 显示 editable wheel 构建/安装成功、版本打印及 install RC 0；对应 N 安装结尾为 570–585。两份 ledger 的 `install_failed_commands=[]`、install RC 0 与已读关键日志吻合。没有把任意历史安装“末尾 RC=0”直接当作本次成功，而是检查当前 recipe 和当前原件。

| 既有原始运行 | gold | noop |
|---|---|---|
| run_id / attempt | `er19-dv1-iterative__dvc-4166-gold` / 1 | `er19-dv1-iterative__dvc-4166-noop` / 1 |
| install 秒 / RC | 8.371 / 0 | 8.658 / 0 |
| 测试阶段秒 / RC | 8.319 / 0 | 9.686 / 1 |
| pytest 原始结果 | 63 passed，2 warnings，G:1019 | 1 failed、62 passed，2 warnings，N:1014 |
| F2P / P2P 报告 | 1/1；0 fail / 58 | 0/1；0 fail / 58 |
| reward / resolution | 1.0 / RESOLVED_FULL | 0.0 / RESOLVED_NO |
| 解析身份 | 62，outside 0，missing/skipped 空 | 同左 |
| `mem_peak_mb` / cleanup | 342.906 / removed true | 485.395 / removed true |

N:606–644 的失败不是 collection error：真实得到 `{dir/subdir/should_ignore}`，期望空集合；G:972 相同参数通过。测试工具版本为 `swebench-4.1.0+swegym_parsers@242429c1`。两份 diagnostics 的 compile_probe=null、env_qualification=absent、resource_facts=null、install_probe=absent。这些运行属于原始历史工件的静态复核，**本审没有执行**。candidate apply_user=agent/54321 只是补丁应用身份，实际 grader policy 是 rh2grader/54322，不等于 actor 已完成测试或安装。

后续若授权验证 actor，最小检查应先用实际 actor 登录环境核对 id/解释器、关键依赖版本和 dvc import 路径，再用其可见 base 运行 `python -m pytest -q tests/unit/test_ignore.py tests/func/test_ignore.py`；必要时仅补读公开 `tests/func/test_tree.py` 的相关节点。该建议不承诺隐藏 F2P 对 actor 可见，也不要求全仓测试/远程服务全部可跑；上述命令本审未执行。

## 6. 候选投影、官方恢复与输入规则

gold ledger 的 included_paths 仅 `dvc/ignore.py`，ignored_paths/unsupported_shape_reasons 为空，classification=projectable；noop included_paths 为空。gold 记录的 frozen_patch_digest 为 `a6d2eb5f54ead0def28448f1973ce87cadd670748675aefff71cd81cf998aa17`，不是原始 gold.patch 摘要，二者不混用。G:162–202 实际 diff 为目标修复，205–217 的 setup.py moto 变化属于环境差异，不能算作 gold 的第二个候选文件。

G:218–268 先从指定 base 恢复两份官方测试文件，再应用官方 patch，两个 apply 均 clean、RESTORED=2、预期/实际文件数均 2、缺失/异常为零、SETUP_OK=1。noop 相应 checkout/apply 在 N:177–187，diagnostics 同样证实恢复 2、apply RC 0。两份 diagnostics 的 control_surface 记录 protected_files=2、protected_dirs=6、PROTECT_OK=1、缺失/异常空、writable_prefixes 完成；runner_digest 前后相同且 integrity_changed=false。这支持这两个实际候选上的恢复/保护路径，未测试恶意候选，不能扩大成所有依赖、配置、fixture 与消息都已防篡改。

公开 hints 的“所有测试修改都会恢复、永不计分”解释比本题原件证明的范围更广。当前能证明的是这两个官方文件的恢复，以及这次候选投影接受了 ignore.py；没有按所有测试文件名统一排除的证据。旧“不得改测试”操作指令若实际发给 actor，应按当前消息适用；本题已有不改测试的合理修复路线，未见其限制完成局部修复。若其未实际发送，也不能自行假定所有测试编辑会投影/生效。该矛盾记为共享输入/运行条件，不据此判原始题目无效。

未发现本题需要额外路径排除的具体证据，建议 `additional_exclusions=[]`。不因文件名、gold 路径、`.dvcignore` 的配置性质或一般篡改可能性机械增补规则；也不把本审提出的外置诊断矩阵并入官方测试或修改奖励。

## 7. 关系、暴露与可迁移结论的限制

本题原始 issue、base、test patch、gold 和 source row 身份一致；已经存在的源码和公开测试足以定位到目录类型与遍历，隐藏验收不需要提供给解题者。没有看到本题原件中的答案明示，但导出包无 `.git` 只描述本导出，真实 actor 镜像是否包含未来提交、环境提交、残留补丁或历史日志仍未知；不得声称实际无泄漏。

本私有调查已接触 gold、隐藏测试、reward 与既有运行，产物只能用于诊断/审查，不可回流给公开角色或当成未污染 actor 输入。公开读稿在此次私有阅读前独立封存；本审没有把私有信息发给公开读者。此主审此前按授权完成了 3576，保持对其材料的记忆，但没有把其历史结论、相同文件名或同一项目关系当作 4166 的证据；也未调查/读取 1681 或其它题来建立关系。没有证据支持本题与其它题合并、排除或分组，跨任务重复/训练暴露结论均未定。

## 8. 历史前判断与未决项

1. **目标与初态有实质联系。** 题面在否定/目录模式上有歧义，但 base 明确丢弃目录类型，唯一 F2P 的真实失败也与此相符。不是空任务或单纯依赖安装题。不得要求六个用户失败尝试都变成同一种递归包含行为。
2. **当前证据支持局部 gold 有效，不能替代完整目标证明。** 原始 gold/noop 运行与 patch、关键调用者一致；未逐项运行公开例，也未验证所有 GitTree/路径查询边界。部分 P2P 是有价值的既有行为保护，空目录测试的弱断言只影响其自身证明力。
3. **一个具体的语义保护缺口待复核。** 尾斜杠去除的自然部分实现可能利用“无普通文件对照”通过，需用第 3 节唯一三方矩阵建议区分；目前为静态假设，不能先写成已证作弊或必然错误奖励。
4. **参数身份的质量问题已可静态定位。** 两条前导空格案例有不同原始结果节点却共享一个截断冻结引用，实际 63、解析 62、参考 59；本对照中两项都通过，不虚构实际判分错误。后续应查此精确节点的源适配/解析保真，不直接改原始测试和 reward。
5. **开发条件应绑定具体配方与身份。** repaired grader 使用兼容 wheel、pathspec pin、moto 环境变化、editable 安装；这些不是 actor 已具备的事实。实际 agent/54321 依赖、权限、导入、工具和消息未知；没有 actor 证据前不标可直接投产/未污染评测。
6. **当前只建议 needs_review/static_review，development_diagnostic。** 不因 P2P 数量、一般空白或未执行新 CPU 自动判坏；也不在旧历史开放前沿链接找结论。新 CPU 成本为未发生；完整容器墙钟、agent tokens、人工决策成本未获可靠数据，后续记录用 null，不能把局部 install/test 秒数相加充当全成本。

## 实际阅读与未阅读记录

已实际读：本题公开四文件、私有七文件与 source/run refs；本题 source 指定三行；独立 public_read；两份 ledger/diagnostics 全文；两个 recipe 及 candidate 脚本全文、candidate/eval 前后安装差异；log 的安装、setup/restore、失败栈与 63 案例结果范围。G 主要逐行范围为 140–299、380–426、606–648、952–1026，另有按关键标记定位；N 主要范围为 593–646、945–1021，另检查 restore/install/version/RC 标记。哈希读取整份日志不等于逐行阅读整份日志；没有声称完整理解安装输出中的每个传递依赖。

源码实际读：ignore.py 全文；两个 ignore 测试全文；scm/tree.py、scm/git/tree.py、tests/func/test_tree.py 全文；Repo 初始化/tree setter 40–155；utils/fs 中相关 mtime/size 函数；setup.py 45–176；tests/conftest、func/conftest、remotes/__init__、tests/__init__；remotes/s3 顶层导入；dir_helpers 的初始化、gen/scm_gen、chdir/branch、make_tmp/tmp_dir/dvc/scm fixture 段；tests/utils 的路径归一化 helper；CONTRIBUTING（仅外链）与 setup.cfg。做过仓库内 matches/ignore/CleanTree 调用定位。初次误查不存在的 `tests/utils.py` 后已沿实际 package `tests/utils/__init__.py` 核实；部分合并工具输出截断后，对关键 log/patch 段分段补读，没有把被截断内容视为已阅读。

未实际读：本题 history refs 或旧质量报告正文；任何批次汇总/manifest/method_adjustments；原始测试插件/parser 的全局实现；兼容 wheel 内部代码；真实 actor 镜像/消息/轨迹；在线 gitignore 文档（patch 注释中的网址只按注释阅读）；其它题的原件来推导本题关系。未执行项目、测试、安装、容器、候选或新 CPU。当前只写本题本稿，历史阶段其它三个文件尚未开始。
