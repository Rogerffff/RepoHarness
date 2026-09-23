# iterative__dvc-4166 — 独立原件初判

2026-09-21；Batch02 fresh reviewer；`scope=static_review`、`state=needs_review`、`intended_use=development_diagnostic`。本稿在阅读主审/公开审查/历史质量结论前冻结。

**初判：base 的目录末尾 `/` 匹配缺陷及 gold/noop 分离有直接历史 RH2 证据；gold 的目录类型处理与此路径相符。冻结奖励没有直接核题面七组 blacklist/negation 原例，而且新增“目录”测试存在弱断言。可保留静态诊断候选，但优先做原例和目录/普通文件对照，不能将 63 passed 解读为完整证明题意。**

路径约定：`ROOT=.`；`P=ROOT/runs/swegym_quality_batch02_20260921_v2/public/iterative__dvc-4166`；`Q=ROOT/runs/swegym_quality_batch02_20260921_v2/private/iterative__dvc-4166`；`R=ROOT/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-4166`。源码行号相对 `P/base/`，log 行号指实际 eval.log。

## 阅读门禁与身份

已读共用 reviewer 角色卡、记录模板、actor 环境卡、质量协议；本题 P 的 prompt/bundle/环境说明/identity、Q 的 patch/gold/grading/validation/refs/environment_record，及下述源码/运行原件。已见 environment_record 的 `verified_environment_pair`、checks、report 等运行摘要；未打开 analysis/history 链接。未读取 results 既有文件、主审/公开读者输出、I2/history、B1/B2 聚合或其它题材料。另两道同仓指定题由此上下文独立复核，但没有其主审结论。

S2 public/grading/validation 各精确第 131 行与本包 JSON 相等。base=`520e01f11305aba1994df354adef86e6d90180de`；artifact/candidate.patch 与 Q/gold.patch 字节一致，test.patch 与两个 eval_script 嵌入正文一致。两侧 recipe 的五个审计文件哈希均与 environment_record 一致，before/after 的测试命令段不变。

将全部 423 个公开 base 文件与 gold/noop baseline_manifest 哈希比较，422 个一致，仅 setup.py 不同。gold log:205–217、noop log:161–173 展示相同环境修复：`moto==1.3.14.dev464` → `moto==1.3.14`。这属于回放基线，非候选投影修改；业务 dvc/ignore.py 与旧测试的 base 身份相符。

本轮未执行 DVC/PathSpec/pytest/安装、Docker、SSH、联网或模型；只作文件、日志、JSON/哈希读取。结论分**静态源码推断**和 **09-19 历史真实 RH2**；没有当前 CPU/局部执行/actor 实测。

## 公开目标和调用链

题面称 `.dvcignore` 在全排除后重新包含 scripts 失败，给六个失败尝试和一个已有效组合：

| 题面规则 | 本次直接断言 |
|---|---|
| `*` + `!scripts` | 无 |
| `*` + `!/scripts` | 无 |
| `/*` + `!/scripts/` | 无 |
| `/*` + `!/scripts/*` | 无 |
| `/*` + `!/scripts/**` | 无 |
| `/*` + `!scripts/` | 无 |
| 原称有效的 `/*` + `!/scripts` | 无 |

不能简单把“用户尝试过”转换为“七组规则必须完全等价”：父目录被排除时重纳入后代的语义本身需要判断。公开源码 `dvc/ignore.py:7,32–42` 采用 GitWildMatchPattern，旧 unit 有顺序覆盖/否定规则，提供了规则解释的公开入口；但本题没有公开精确期望文件集或要求换匹配库。没有查网络答案。

关键路径：DvcIgnorePatterns.__call__ 对 files 和 dirs 都用同一 `matches(root, name)`（45–49）；matches 计算相对路径、在非 Unix 正规化后交给 ignore（51–73），后者顺序匹配并更新最后结果。目录名字没有 `/` 类型标志。`CleanTree.walk:233–241` 将过滤结果原地写回 dirs/files，控制 os.walk 是否递归；`_parents_exist:202–231`、`_valid_dirname:175–183`、isfile/open/exists 同样经此过滤。`BaseTree.walk_files:34–38` 只枚举文件，不能观察是否遍历过空目录。

gold 在 __call__ 传 is_dir=True，对目录同时尝试 path 与 path+`/`，保留模式组的覆盖顺序；文件只匹配 path。该设计能使正向 `subdir/` 在父目录阶段生效，使 `!should_ignore` 不能挽救被剪枝父目录下的文件；也具备处理目录否定末尾 `/` 的路径。没有从这一静态推断推导所有原例已经通过。

## 新增/修改断言全量清单与反向依据

实际执行选集是 `pytest -rA tests/func/test_ignore.py tests/unit/test_ignore.py`。test.patch 改写 unit 参数矩阵，新增五个 function 节点（一个三参数测试及两个函数），删除两个旧 unit 函数。下列逐项展开，没有以“新增 41 项”代替读断言。

unit helper `mock_dvcignore` 用 mock tree.open 读入模式文本；每个参数统一调用 `ignore_file.matches(dvcignore_dirname, file_to_ignore_relpath) == expected_match`。因此这 41 项全是**文件匹配**，没有 is_dir=True 的输入。下表 n 对应最终 nodeid 的 `patternsN`；T=应忽略，F=应保留。它们都是 P2P，两个前导空格节点在冻结参考/当前 parser 中合并为一个键，详见后文。

| n | 路径；规则列表 → 期望 | 反向规格/覆盖解释 |
|---|---|---|
| 0 | `to_ignore`; [`to_ignore`] → T | 普通字面匹配，已有契约。 |
| 1 | `dont_ignore.txt`; [`dont_ignore`] → F | 名称不完全匹配，已有。 |
| 2 | `to_ignore`; [``, `to_ignore`] → T | 空行不影响规则。 |
| 3 | `#to_ignore`; [`\#to_ignore`] → T | 转义 # 字面。 |
| 4 | `#to_ignore`; [`#to_ignore`] → F | 注释不匹配。 |
| 5 | ` to_ignore`; [` to_ignore`] → F | 实际是**前导**空格，旁注写 trailing spaces；题面未单独规定，未在本轮验证 Git/PathSpec 一致性。 |
| 6 | ` to_ignore`; [`\ to_ignore`] → T | 转义前导空格；同上规格界限。 |
| 7 | `to_ignore.txt`; [`to_ignore*`] → T | 单星文件匹配。 |
| 8 | `to_ignore.txt`; [`to_ignore*`, `!to_ignore.txt`] → F | 后置否定生效；与题目方向有关，但不是目录 blacklist 原例。 |
| 9 | `to_ignore.txt`; [`!to_ignore.txt`, `to_ignore*`] → T | 后置排除覆盖先前否定。 |
| 10 | `!to_ignore.txt`; [`\!to_ignore.txt`] → T | 转义 ! 字面。 |
| 11 | `file`; [`/file`] → T | 根锚定命中。 |
| 12 | `data/file`; [`/file`] → F | 根锚定不命中后代。 |
| 13 | `data/file`; [`data/file`] → T | 含中间 / 的根相对路径。 |
| 14 | `other/data/file`; [`data/file`] → F | 不任意后缀匹配。 |
| 15 | `/full/path/to/ignore/file/to_ignore`; [`to_ignore`] → T | 既有绝对字符串输入的末尾匹配。 |
| 16 | `to_ignore.txt`; [`/*.txt`] → T | 根文件星号。 |
| 17 | `path/to_ignore.txt`; [`/*.txt`] → F | 根限定不穿越 /。 |
| 18 | `data/file.txt`; [`data/*`] → T | 一个路径段星号。 |
| 19 | `rel/path/path2/to_ignore`; [`rel/*/to_ignore`] → F | 单星不跨多个目录。 |
| 20 | `file.txt`; [`file.*`] → T | 扩展名字面/星号。 |
| 21 | `file.txt`; [`fi?e.t?t`] → T | 问号一个字符。 |
| 22 | `fi/e.txt`; [`fi?e.t?t`] → F | 问号不匹配 /。 |
| 23 | `file.txt`; [`[a-zA-Z]ile.txt`] → T | 字母范围。 |
| 24 | `2ile.txt`; [`[a-zA-Z]ile.txt`] → F | 范围外拒绝。 |
| 25 | `rel/p/p2/to_ignore`; [`**/to_ignore`] → T | 前置 ** 跨目录。 |
| 26 | `rel/p/p2/to_ignore`; [`**/p2/to_ignore`] → T | ** 后路径组合。 |
| 27 | `rel/path/path2/dont_ignore`; [`**/to_ignore`] → F | ** 不改变末尾名称约束。 |
| 28 | `rel/p/p2/to_ignore`; [`rel/**`] → T | 尾部 ** 任意深度。 |
| 29 | `rel/p/p2/to_ignore`; [`p/**`] → F | 中间 slash 模式根相对。 |
| 30 | `rel/path/path2/dont_ignore`; [`rel/**`] → T | ** 包含另一后代名称。 |
| 31 | `rel/p/to_ignore`; [`rel/**/to_ignore`] → T | 中间 ** 的较浅层。 |
| 32 | `rel/p/p2/to_ignore`; [`rel/**/to_ignore`] → T | 中间 ** 多层。 |
| 33 | `rel/path/path2/dont_ignore`; [`rel/**/to_ignore`] → F | 后缀名称仍限制。 |
| 34 | `rel/path/path2/dont_ignore`; [`path/**/dont_ignore`] → F | 根路径不匹配。 |
| 35 | `to_ignore.txt`; [`/***.txt`] → T | 非特殊连续星号。 |
| 36 | `path/to_ignore.txt`; [`/****.txt`] → F | 根锚定多星不穿 /。 |
| 37 | `path/to_ignore.txt`; [`****.txt`] → T | 无锚定的名字匹配。 |
| 38 | `data/file.txt`; [`data/***`] → T | 非 ** 特例的单目录内容。 |
| 39 | `data/p/file.txt`; [`***/file.txt`] → F | 三星不替代跨目录 **。 |
| 40 | `rel/path/path2/to_ignore`; [`rel/***/to_ignore`] → F | 中间三星不跨多层。 |

`data/sub/file` 对 `data/*`、`data/p/file` 对 `data/***` 的行在 patch 里是**注释掉的案例**，没有执行/计分。末尾 slash 的 comments 指向 func 测试，但不能替代实际参数内容。三项不变 unit `test_should_ignore_dir[.git/.hg/.dvc]` 都断言 DvcIgnoreDirs 从 dirs 中只保留 dir1/dir2，属于合理元数据目录回归，已读。

新增 func 的所有关键断言：

| 测试/冻结身份 | 输入、断言与映射 |
|---|---|
| `test_ignore_file_in_parent_path[data_struct0-pattern_list0-result_set0]`，P2P | 根 .dvcignore=`subdir/*\n!not_ignore`，树为 `dir/subdir/not_ignore`，要求该文件仍可枚举。**弱点：`subdir/*` 含中间 /，相对根锚定，与 `dir/subdir/...` 不同；此案例并不充分证明先排除再重纳入。** |
| 同函数 `data_struct1...`，P2P | 根模式 `subdir\n!should_ignore`，树 `dir/subdir/should_ignore`，结果空集；保护父目录排除优先。 |
| 同函数 `data_struct2...`，唯一 F2P | 同一树，模式变成 `subdir/\n!should_ignore`，结果空集；核心测试目录 trailing slash 的剪枝，noop 留下 should_ignore，gold 空集。 |
| `test_ignore_sub_directory`，P2P | `dir/.dvcignore="doc/fortz"`；两个嵌套目录各有文件，要求保留 `dir/a/doc/fortz/a` 和 .dvcignore；保护相对模式 anchoring。虽然注释解释目录末尾 /，**实际模式没有末尾 /**。 |
| `test_ignore_directory`，P2P | `dir/.dvcignore="fortz"`，被命名目录及其 nested 对照都为空；只断言文件集仅 .dvcignore。没有文件或 dirs 观察，因此即使遍历空目录也能得到同结果，不能证明目录被过滤。 |

删除的 unit `test_ignore_from_file_should_filter_dirs_and_files` 原先分别断言 dirs/files 集合；删除的 `test_ignore_order` 原先用 `!ac*, a*, !ab*` 得到 `{ab}`。新文件否定顺序参数保留了部分后者语义，前者的目录/文件混合断言没有等价的非空目录类型对照。移除不是新的评分要求，但应计入覆盖变化。

相关 func P2P 全部已读：忽略单文件及切换 cwd、Unicode、忽略/未忽略文件 rename/remove 的 mtime/size、两种位置收集 .dvcignore、Git branch 规则、subrepo 隔离、空行。`_files_set` 只调用 tree.walk_files。fixture 追到 tests/dir_helpers.py 的 tmp_dir/gen/Repo.init，Git 分支测试额外需要本地 git；conftest 及 remotes 的导入链已抽查，不把模块导入等同远端服务实际调用。

## 需求覆盖、合理替代路线与剩余风险

| 公开要求/合理回归 | 覆盖结论 | 证据/下一验证 |
|---|---|---|
| 全排除后重纳入 scripts | 部分：文件否定与父目录规则有测试，七组原例无直接文件集断言 | 在固定 PathSpec 版本上建立含 scripts 文件、scripts 子目录及 sibling 的树，逐组解释/验证。 |
| 目录 `/` 与同名普通文件应区分 | F2P 只覆盖正向目录排除后的父目录行为；同名文件反例缺失 | 用 `subdir/` 同时测试目录与普通文件；再用 `/*` + `!/scripts/` 检查否定目录。 |
| 后置规则覆盖、anchoring、glob 规则 | unit 文件矩阵较充分；仍不是目录版本的矩阵 | 该边界对合理实现须保持；不要求复制 gold 的方法签名。 |
| 不破坏其它 tree 操作 | 历史选集通过一些 walk/stat/subrepo 行为；open/isdir/exists 的全部交互未验 | 相关调用链已读，需以具体疑点补窄复现，不全仓穷举。 |

合理替代设计可以在调用匹配器前给目录附加目录分隔标志而保持 `matches`/`ignore` 的原签名，或保留目录专用 matcher；没有测试要求 `is_dir` 参数名、具体 helper 名或 gold 的循环结构。未发现这类替代结构会被新增断言直接误拒的证据。前导空格 n5/6 的规则来源较弱，且注释与输入不符；若更换 matcher，应先做实际语义对照，不能静态认定 Git 行为应当复制这两个期望。

有自然部分实现值得 CPU 区分：将**正向**末尾 `/` 模式去掉 `/` 再编译、保持否定模式原样。这可能修复唯一 F2P，却让目录专用规则也排除同名普通文件，并未修好 `!/scripts/`。现有矩阵没有相应正反类型断言。这里只给原因明确的候选，不声称它已得 reward=1；不为凑反例构造测试识别/硬编码代码。

gold 本身局限：它有目录路径/文件路径区分、保留顺序，本轮没有从调用链发现确定新回归；是否完整满足七组原例仍未知。`ignore(path)` 签名变成需要 is_dir；在本题 base 中应通过 matches 调用，未把内部签名变化单独升级为公共 API 破坏。没有运行项目或读取外部 PathSpec 实现，不作未核实的 regex 细节断言。

## 历史 RH2 运行与冻结计分范围

| 原件（相对 R） | 核实事实 |
|---|---|
| `gold/ledger.jsonl:1` 与 `gold/eval_logs/evallog_replay-er19-dv1-iterativ_ce06dec1.eval.log` | log SHA256=6a9ef505…6ab7a 与 run_refs/ledger 一致；:256–268 官方两文件恢复/应用成功；:409–423 离线 wheel 安装；:623 记录 PathSpec=0.8.1、networkx=2.3+rh2.1；:639–644 执行两个文件并收集 63；:956–1019 全部 63 passed；F2P 1/1、P2P 58/58、reward=1。 |
| `noop/ledger.jsonl:1` 与 `noop/eval_logs/evallog_replay-er19-dv1-iterativ_de73b04d.eval.log` | SHA256=7689ee1d…9affd7 一致；:595–600 同选集；:638–642 F2P 实际结果 `{dir/subdir/should_ignore}`，期望空集；:1013–1018 1 failed/62 passed、rc=1；F2P 0/1、P2P 58/58、reward=0。 |
| 两侧 recipe/诊断/projection/frozen/stage/driver 原件 | 离线先固定 `pathspec==0.8.1 networkx==2.3+rh2.1`，再 editable `[all,tests]`；安装失败命令为空、rc=0；gold 只投影 dvc/ignore.py、noop 空；官方两文件恢复成功；head=base；清理成功，无 driver 残留。 |

派生镜像 `sha256:cfcef64300c96ff4e7dfd2c92bdf6025f9213df5e9574db72103174371b0107a`，Python 3.9.19/pytest 7.4.4，grader=`rh2grader/54322`、2 CPU/4 GiB、deny_all、64 MiB shm、可写 conda 前缀；workspace 导入 `/testbed/dvc/__init__.py`，env_qualification=absent。apply_user=agent/54321 是回放贴 patch 的身份，不证明正式 actor。

**63 执行节点、62 parser 键、59 奖励参考必须分开。** gold log:980–981 的两个 `[ to_ignore-patterns5-False]` / `[ to_ignore-patterns6-True]` 真实节点都通过；当前 `rh2/src/repoharness2/envpack/swegym_parsers.py:44–55,93` 对行做空白 split，只留下共同键 `tests/unit/test_ignore.py::test_match_ignore_from_file[`，该截断键正好在冻结 P2P 中。它丢失逐节点身份；这次两个都是 pass，不能凭别名就说历史 reward 错误，失败组合与摘要顺序的影响需另测。

`test_dvcignore_in_out_dir`、`test_match_nested`、`test_ignore_external` 实际执行且 gold/noop 都过，但不在冻结 F2P/P2P；其它所有本选集关键断言的体已读。当前评分依冻结参考，普通完整 pytest 中这三项单独失败不会仅因 rc=1 自动得到 reward=0；全局收集/启动故障另按 manager 判定，不能混成“执行即受奖励保护”。

## 开发需求和交付边界

| 操作/资产 | 公开依据 | 历史可见事实/当前缺口 | 最小后续验证（未执行） |
|---|---|---|---|
| 导入工作区 DVC 与 PathSpec | ignore.py:7；setup.py:49–82 | grader 导入正确、PathSpec0.8.1 已固定；actor 公共镜像是否同版本未知 | agent shell 输出 id/cwd/PATH、解释器、dvc.__file__、pathspec 版本。 |
| 运行本地目录规则复现及窄公开测试 | tests/func/test_ignore.py、unit、dir_helpers | 所有必要数据均可在临时本地目录生成；Git branch/subrepo 用本地 Git；无任务所需外网服务/模型权重 | actor 跑两个公开文件并逐条原例打印文件集与目录可见性。 |
| 安装/准备依赖 | `[all,tests]`、conftest/remotes 导入链 | 派生环境离线 wheels + moto metadata 调整成功；不能据此宣称原公开 image 已修 | 准备时固定这些版本与 wheels；核 actor 是否需要 editable install 及实际写权限。 |
| 交付 source 修复 | dvc/ignore.py 及调用者 | gold source 可投影，无需改官方测试或外部资产 | 候选投影后重复原例/参考；仅 source delta 应生效。 |

当前 `prepared_task_face.py:312–355` 的 `test_globs=()`；精确官方恢复文件仅 `tests/func/test_ignore.py` 与 `tests/unit/test_ignore.py`。tests/conftest 等不会因“测试名字”自动全部恢复，旧 public_hints 的概括不能当当前机制；合理 source 修复不需要改测试，未因此提出指令例外。没有额外路径排除建议。

正式 rollout 取 public bundle 的 image/digest；本次两侧 grader 使用的是上面 local_build 镜像。actor profile 是 agent/54321，实际 shell 激活（包括 `/root/.rh2_bash_env` 与隐藏 /root 的关系）、依赖资产、工具/消息、资源与 Git 可见历史未验；不能从 patch apply 身份或 grader 的 prefix 写权限代填。P/base 无 .git 是静态导出事实，不是实际无答案线索的证明。

## 八方面范围和下一步

| 方面 | 已查与未查 |
|---|---|
| 公开需求 | 七种模式逐条记录，区分用户猜测与匹配语义；实际 actor 消息未捕获。 |
| 材料/初态 | 精确 S2/base/patch/运行匹配；moto 基线差异已核。 |
| 测试测要求 | 全部新增/修改/删除断言、F2P 与相关 P2P 已展开；原例直接覆盖、空目录弱断言与 root 路径错位已标。 |
| 误拒合理解 | 未见对 gold 实现结构的强绑；空格规则来源保留疑点，未假装已证明。 |
| gold/回归 | dirs/files 区分、顺序、walk/exists/open/父目录调用链已读；没有穷举所有 patterns/平台。 |
| actor 开发条件 | 必需入口/本地资产/依赖明确；只有历史 grader 成功，当前 actor 未验。 |
| 交付/评分 | 精确恢复/source 投影、参考集合与 parser 别名均核；没有新安全审计或规则扩大。 |
| 关系/用途 | 与同审 3576/1681 目标不同，未证同问题派生；已看隐藏测试/gold，不作公开 solver，不估模型效果。 |

唯一优先下一步：同一固定依赖环境中对 base/gold/正向去末尾 slash 的部分实现，建立包含 scripts 非空子目录、兄弟路径、同名普通文件的本地树，逐条跑七种原例与目录专用正反对照，再跑冻结选集并记录真实节点/参考 reward。先判断原题目标与 reward 区别，再决定是否补行为断言或澄清规格；不要为了让所有示例“看似成功”破坏父目录排除语义。之后仍须正式 actor CPU 验收。

token/费用工具计量未知，记 null；无本轮项目 CPU 执行。所有三题初稿完成后按包门禁暂停，未开放前不读主审/公开审查/历史质量结论。
