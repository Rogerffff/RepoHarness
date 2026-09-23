# iterative__dvc-4166 — 独立复核收口

2026-09-21。**优先列为受限 `development_diagnostic` 静态候选**，保留 `needs_review / static_review`。本小包中它的局部修复与可见目录类型问题联系最直接；冻结F2P检查真实文件集合，未要求gold的新参数名。参数身份碰撞是已定位问题，文件/目录边界存在具体部分实现假说，但均不等于已经观察到错误奖励，也不妨碍先用受限诊断实验检验其影响。不是正式训练/评测准入或actor就绪判断。

全部三题 reviewer_initial 已在协调者统一开放其他角色产物之前封存。本题初稿 SHA-256 `a11c093dea629368e315e003c34209897338ec3b058173ae62d05279a7f168a2` 保持原字节；本次只新增review.md。主审主要结论获支持，下文修正其一个具体覆盖解释。

## 证据定位

权威根 `ROOT=${REPO_ROOT}`；`I=ROOT/runs/swegym_quality_batch02_20260921_v2`，`P=I/public/iterative__dvc-4166`，`V=I/private/iterative__dvc-4166`，`B=P/base`，`O`为本报告目录。`R=ROOT/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-4166`。

- `G=R/gold/eval_logs/evallog_replay-er19-dv1-iterativ_ce06dec1.eval.log`，SHA `6a9ef5059178cc9503e8ff7172d9a68cf086f2f964af68e6e4193ef61f06ab7a`。
- `N=R/noop/eval_logs/evallog_replay-er19-dv1-iterativ_de73b04d.eval.log`，SHA `7689ee1dc5e2000b10d0e4bbef1dfe546e5993de9381f578717c18f2299affd7`。
- `H=ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_2/records/iterative__dvc-4166.json`，SHA `c1ce801b9e89b1e684dbaebd8ddccb3665d603e74b2806ba843a27da213de66e`，由本题history/refs.json指向。
- `S=ROOT/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-4166`；旧 `LG=S/gold/offline/a1/test_output.txt` SHA `b914d0d47045e0f9f35dac147c410e689e23313a2934622034b0b8cb12484ae6`，`LE=S/empty/offline/a1/test_output.txt` SHA `7a178a48324771a29609530499616c83167f69077f6e341987cbe4aa4bf53d7c`。下述行号绑定各自原件。

初稿已核S2三份第131行、base `520e01f11305aba1994df354adef86e6d90180de`、两个patch及实际run/recipe/投影身份。本次未重复逐blob完整性工作。

## 主审决定性主张与新增修正

| 主张/位置 | 复核判断与原件支持 |
| --- | --- |
| 题面六种失败尝试不必都变成相同递归包含效果（public_read:30–44，analysis:41–47） | 同意。目录自身可达、子项否定、根相对及递归范围不能混同。公开文本已出现 `!/scripts/` 和 `!scripts/`，旧H“完全没提尾斜杠”不实；题目并非只能靠隐藏规范才能定位。 |
| base丢失dirs/files的类型，gold让目录匹配同时考虑尾斜杠（analysis:45,150–154） | 同意。`B/dvc/ignore.py:45–73` 已有dirs/files却同样调用matches；gold传目录信息并保留规则组顺序。WorkingTree/GitTree有自己的类型/遍历上下文，不能只靠当前磁盘isdir代替。未发现已知内部ignore调用遗漏。 |
| 唯一F2P为父目录 `subdir/` 被排除、子文件否定不能穿越（analysis:59） | 同意。`V/test.patch:28–40`；N:638–642 的实际集合多出 should_ignore，G:972通过。它与目录类型根因有关，不能因使用排除而非题面否定写法就称“方向相反”。 |
| parent参数0证明允许进入父目录并由后规则重新包含文件（analysis:57,133） | **需要收窄。** patch:19–21创建 `dir/subdir/not_ignore`，patch:39把ignore放仓库根；正规则却为 `subdir/*`。matcher按ignore根构造 `dir/subdir/not_ignore`（ignore.py:30,54–60）；按现有带中间斜杠的根锚定约定，该正规则不命中此路径。故其通过证明文件可见，不能证明文件先被排除再由 `!not_ignore` 救回。此问题在独立初稿已指出，非历史提示导出；是静态输入/断言分析，未改测试或跑变体。 |
| sub_directory与empty directory两例的覆盖弱于注释（analysis:60–63） | 同意。实际pattern为 `doc/fortz` 和 `fortz`，均无尾 `/`；empty dict只建空目录，而_files_set→walk_files仅枚举文件。空目录是否被剪枝对该文件集合无影响。不能把注释当目录专属匹配实证。 |
| 41个匹配参数均按默认文件路径调用，未直接验证is_dir=True（analysis:65–117） | 同意，初稿已逐条展开所有实际参数和删除的旧断言。Mock只代替ignore文件I/O，真实regex匹配仍执行；不是Mock直接给答案。现有规范/顺序回归有用，不能因base已通过就说它们与修改无关。 |
| 去掉规则尾 `/` 的自然部分实现可能通过（analysis:144–146） | 同意为具体未执行假说。把换行前的终端 `/` 当作可删除的格式差异，会使F2P的 `subdir/` 退化为已通过参数1的 `subdir`；现有其它实际规则未提供同名普通文件的尾斜杠反例。不能据此写已获reward、确定绕过或必须修题。 |
| parser碰撞、实际/解析/参考分别63/62/59（analysis:121–138，delta及JSON check19） | 同意。修复日志保留patterns5与6两个完整ID，冻结只有 `...test_match_ignore_from_file[`；当前parser按空白split并以字典后写覆盖。两项目前都PASS，未看到错误reward。 |
| 历史环境故障与当前配方分开（analysis §5、delta） | 同意。旧gold实际60过3败，修复gold63过；不是把62个解析键误作实际测试数，也不能延续旧“gold环境干净”或“当前3项仍坏”的说法。 |

### 数目、冻结奖励与碰撞的实际影响

当前命令运行19个func案例、41个匹配参数、3个默认忽略目录案例，共63。两个前导空格参数合成一个解析身份，得到62；再排除3个非冻结func身份，冻结为F2P1 + P2P58 = 59。其中P2P为43个unit身份与15个func身份。`test_dvcignore_in_out_dir`、`test_match_nested`、`test_ignore_external`虽然在G/N都执行通过，仍未进入冻结列表；不能把它们升格为已有计分保护。

当前 `rh2/src/repoharness2/envpack/swegym_parsers.py:44–55,93` 的 `line.split()` 与字典赋值解释碰撞；这是当前源码，不是对旧镜像parser字节的认证。旧H断言patterns5“永远丢失/永远不计分”过强：需要看实际日志最后出现哪个状态行，混合PASS/FAIL时摘要顺序也可能变化。现有两期材料都只有两项同时PASS，没有混合状态运行，不据其顺序虚构某条失败必然被遮蔽。

同时，正常完成pytest的一个**非引用案例**失败不自动使冻结F2P/P2P奖励为0；完整执行与参考评分是两层。当前RH2 scoring/manager对有效段及全局错误另处理，collection/超时/不完整日志等不能与普通测试失败混为一谈。旧LG的3项失败与其报告RESOLVED_FULL并不单独构成判分矛盾，更不能反推这3项当初为何没被放入P2P。

## 八方面收口与历史纠正

| 方面 | 已核范围和保留条件 |
| --- | --- |
| 公开目标/初态 | 六失败加一成功模式及父目录语义边界；无需把六例全判同义。公开接口与源码足以开始正常开发。raw隐藏对照支持目录/文件区别，但不回灌成actor必须已知的额外约定。 |
| 需求—断言双向映射 | 初稿已展开5个新增func案例、41参数、删除旧测试、3默认目录案例、全部冻结身份及另外执行3项；本次新增纠正参数0的reinclusion解释。数字统计完整不等于语义覆盖完整。 |
| 合理替代/自然部分实现 | 局部修复可在目录边界加标记或传类型，不被新增参数名锁定；内部collecting P2P有既存类型/集合约束，大幅重构仍须兼容。终端斜杠去除是有依据的部分实现假说，未执行。 |
| gold/调用者/回归 | gold修正直接根因，WorkingTree/GitTree、CleanTree路径查询、mtime/size调用链及有关回归已查。公开原模式及tree测试没有本次新运行；一般未覆盖边界不全部升为候选前置门。 |
| 环境/资产/开发 | 固定pathspec0.8.1/networkx2.3+rh2.1、moto release环境差异及editable安装有原件。本地文件/Git足够；远程fixture导入依赖与真实远程服务需求不同。兼容wheel内部未审，但不妨碍把已见运行作为限定条件证据。 |
| 投影/恢复/控制 | gold只投影ignore.py，noop空；官方恢复两个test.patch文件。当前默认test_globs=()，非“所有测试都会还原”；两次候选保护成功不是全部配置/依赖/恶意候选防篡改证明。额外排除为空。 |
| 关系/版本 | S2、base与两期精确run对应；本次只读本题提交253a0eae…的ignore.py修复对象，内容与gold一致。没有读取4066/4125题目、聚合或推导强制同侧。主审对那些关系的保留正确。 |
| 暴露/用途 | 门禁前环境摘要可见，门禁后读本题H、raw hints和修复提交；本报告已私有暴露，不能交solver。没有真实actor泄漏检查或未污染保证。 |

旧原件进一步确认：LG:371–403含联网/缺文件安装失败，eval.sh:14–15串联命令与 `|| true` 只记录末尾状态，LG:442–445仍RC0。LG:515–518的fractions.gcd ImportError、943/1357的ps_d重定义，以及1678–1681的3败摘要均真实存在。LE:1671–1675是同3项加唯一F2P，共4败/59过。两份status_map各64键，含62个测试键和Could/No两个安装文本键。

修复G:639/644/956–1019和N:595/600/951–1014则为63过与62过1败，ledger为reward1/0；依赖故障症状在这对grader原件中消失。recipe同时改变若干条件，不能把每个改善都声称经过单因子因果实验。旧建议升到networkx>=2.4与base上界<2.4冲突，当前兼容2.3配方另有原件。旧建议把已经双侧通过的若干新增案例改称F2P不成立；未授权重建参考或改reward。

真实执行身份是rh2grader/54322，公开image与派生镜像分开；apply_user=agent/54321不是开发会话。actor的解释器、public工具消息、源码/包权限、资源及导入仍未知；这些是模型开发启用条件，不是本次静态候选全部否决的理由。

## 唯一优先后续实验

**固定当前修复配方做 base/gold/终端斜杠规范化候选的一组三方CPU对照。** 保留原63项执行和冻结59身份/reward；外置小矩阵对普通文件 `subdir` 与含叶文件的目录 `subdir` 分别应用 `subdir/`，再对非空scripts目录比较公开 `/*` + `!/scripts/` 与已知有效 `/*` + `!/scripts`。记录目录及文件可见性、官方各完整nodeid和分数，不只看总reward。

这比立刻扩全仓或改全部参考更能回答：缺类型的自然修复是否得到同分，以及gold是否保留目录专属否定语义。若候选没过原参考或并未破坏外置行为，就收回此具体错误接受推断。七组题面尝试的其余差异可作为输出观察，不能预设必须全部相同，也不设成另一个前置实验。参数碰撞仍单列已知限制；不在本轮为验证它人为改测试、改parser或增设第二实验门槛。实验未执行，没有新候选产物。

## 本次阅读范围

已读O五份开放产物、H全文、本题history refs、两份旧eval.sh安装/选择段、两份status_map、旧日志上述关键段；raw第145行本题hints（行SHA `9adf06a555c1874d54f0cf075fcf31be6fe5c82074d63538da48b35354b65592`）；本题本地历史commit `253a0eae1374ff0bc81046507714353af977d8f3` 的metadata与ignore.py diff；复看公开ignore.py匹配段、func测试全175行和test.patch新增func段。初稿已经完整列出的参数与fixture不重复展开为另一个清单。未读H链接的L2碰撞汇总、deps_scan、prescan、其他题或B1/B2聚合/CPU队列。

没有执行项目代码、测试、安装、Docker/SSH、联网、付费模型或当前CPU；只做文本/JSON/哈希及明确Git对象只读操作。没有修改base/mirror、主审稿、初稿、官方patch、奖励。结论由“独立源码静态判断 + 两期历史原件”支持；未执行假说和actor未知保持原等级。
