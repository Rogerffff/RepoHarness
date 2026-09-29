# iterative__dvc-4166 — 历史核对与差异

2026-09-21。协调者核对并封存历史前稿后，明确开放 `runs/swegym_quality_batch02_20260921_v2/history/iterative__dvc-4166/refs.json` 及其本题引用。历史前稿 SHA-256 `cd9e2abcd3d44083df019a88124f095fcb2c0ac8d1a0febce6bb0a37e2db54ce` 保持原字节。本文件追加证据，不回写初判。全部为静态读取/元数据核对，未运行项目、旧脚本、parser、测试或新 CPU。

路径缩写沿用 `analysis_before_history.md` 的 ROOT、P、V、B、R、G、N。以下新增缩写：

- `H=docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_2/records/iterative__dvc-4166.json`，SHA-256 `c1ce801b9e89b1e684dbaebd8ddccb3665d603e74b2806ba843a27da213de66e`，refs 唯一历史记录。
- `S=runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-4166`。已沿 H 的精确 `{gold,empty}/offline/a1/` 指针找到原件，未用旧 smstat/deps_scan/L2 汇总代替，也未用新实验代替检索。
- `SG=S/gold/offline/a1/test_output.txt`，SHA-256 `b914d0d47045e0f9f35dac147c410e689e23313a2934622034b0b8cb12484ae6`，1687 行；`SE=S/empty/offline/a1/test_output.txt`，SHA-256 `7a178a48324771a29609530499616c83167f69077f6e341987cbe4aa4bf53d7c`，1681 行。本文 SG/SE 行号只指各自这份原件。
- 两个 `eval.sh` 同 SHA `853e9f67b16310a2d801aae691e3d54c8e1646540baeef6e1b87aa952d951097`。gold/empty `status_map.json` SHA 分别为 `13479a4ad8af490e0bbe53e134afa94b410feb2e5fe6288226b15ae8d6e960f5`、`38cc332bb0ebb21c2b951dce03095a17d450f7b6ccc9e58e1576f59b185a1124`。旧 gold `patch.diff` 与本题 gold.patch 字节哈希相同。
- H 精确引用的 raw 文件 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl` 仅提取本题 **145 行**，instance_id 核对相同，原始行字节 SHA `9adf06a555c1874d54f0cf075fcf31be6fe5c82074d63538da48b35354b65592`。没有读取其它题的 raw 内容。
- H 所引 `scripts/collide.py` 在 docs 下同 L1_dvc_2 目录找到，SHA `2210c0c8f38cb12b596274990fcc1918e38903e5b9f70d175e713ccde6692f39`。只读其代码，未执行、未打开其 ASSIGNMENT 或多题输出。它是诊断脚本，不是 grader parser。
- 协调者封存后另行明确给出当前 parser 指针：`rh2/src/repoharness2/envpack/swegym_parsers.py:44–55,93`，整文件 SHA `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`。已读所指函数和 DVC 映射；这是当前源码证据，不冒称旧镜像内同一文件已做字节 attestation。

## 逐项核对旧主张

| H 中旧主张 | 结论 | 决定性证据与本次解释 |
|---|---|---|
| gold/test 与上游 #4166 一致、无文件遗漏 | 确认，限补丁材料 | 只读 H 指定 clone 的提交 `253a0eae1374ff0bc81046507714353af977d8f3`，subject 为 `Add more tests according to gitignore (#4166)`，父提交 `8964967af06b7861537d9ad5bfd5001114e8e032`，修改三文件。去除 diff 路径/索引/hunk 定位头后，gold/test 的补丁正文分别与当前两份 patch 相同。不能从上游一致自动推出目标完整性或全部回归正确。 |
| base 丢失目录类型，F2P 确实失败 | 确认 | base ignore.py 的目录调用不带类型；SE:1334–1372 为实际 F2P 断言，返回 `dir/subdir/should_ignore` 而非空集合；SG:1631 同参数通过。与当前 N:606–644、G:972 一致。 |
| 题面完全没提尾斜杠；题意与评分方向部分相反，真正修了另一件事 | 推翻过强表述，保留欠明确 | 公开题面已直接包含 `!/scripts/`、`!scripts/` 两组尾斜杠尝试。raw 本题 hints 明确比较 `/*`+`!/dir/`+`!/file/` 与 `/*`+`!dir/`+`!file/`，称 DVC 返回空列表而 Git 保留 `data/dir/file`、不保留普通 `data/file`。这把题面与“目录专属匹配”直接联系起来。该 hints 不在当前 problem_statement/public_hints，不能倒灌成 actor 已知要求；公开目标仍欠目录树和精确预期，但“完全依赖外查规范/修了无关问题”不成立。 |
| 七组题面模式均未直接进入 F2P/P2P | 确认 | 完整测试输入表已在封存稿 §2；唯一 F2P 走目录排除而非原例的目录重新包含。raw hints 加强了目录/普通文件成对验证的依据，却没有使该对照变成现有计分保护。 |
| 两个带空格 nodeid 合并 | 确认并缩小初稿未知 | SG:1639–1640、当前 G:980–981 均列两条完整节点；expected 仅一个 `...test_match_ignore_from_file[`。当前 parser:52–55 用 `line.split()`、取 `test_case[1]` 为键逐行赋值；93 指定 iterative/dvc 使用它。两个节点都会映射到同一键，后遇日志行覆盖前遇行。旧 status_map 实际也只保留一个该键。 |
| patterns5 永远不参与判分、整对判别力归零；已足以证明遮蔽漏洞 | 不采纳绝对结论 | 源码证明按日志顺序覆盖，不证明混合 PASS/FAIL 时的摘要顺序固定为 patterns5 再 patterns6。现有 gold/empty/noop 两项均 PASS，尚无混合状态原始运行；不能声称已出现错误 reward。至少丢失独立节点身份；不能将“一项信息丢失”扩大为“所有对照判别力归零”。旧稿称尾随空格也不准确，实际参数是前导空格。 |
| gold real=62（59 PASS/3 FAIL）、empty=58 PASS/4 FAIL | 确认其测试键计数，补充实际执行及杂键 | SG:468 收集 63，1681 为 60 PASS/3 FAIL；SE:424 收集 63，1675 为 59 PASS/4 FAIL。62 是合并空格节点后的测试身份数。两个原始 status_map 还含来自安装错误的 `Could: ERROR:` 和 `No: ERROR:`，因此整个 map 有 64 个键；旧 real 不能冒称全部 map 或 pytest 实际案例数。当前 repaired RH2 为 63 实际 / 62 解析 / 59 参考，三者继续分开。 |
| 安装 rc_install=0，故环境可运行 | 末尾码确认；“安装干净”不成立 | SG:371–403 有 PyYAML 包下载失败、远端 Git DNS 失败、两个不存在 requirements 文件；eval.sh:14 串联并有 `|| true`，15 只取最后命令 RC。SG:442–445 的 0 不抹掉前面错误，pip 还打印 root 警告，SE 临时目录为 pytest-of-root。旧 Stage1 不能证明 actor/54321 可开发。当前 R 的修复安装原件是另一份明确配方、不同身份条件，不能混写成同一次安装。 |
| gold 有 networkx/Python 3.9 及 pathspec 重复命名组异常 | 确认历史事实；对当前修复配方已过时 | SG:497–518 是 networkx 从 fractions 导入 gcd；943/1357 是 regex `ps_d` 重定义。SG:1678–1680 对应 `test_dvcignore_in_out_dir`、`test_match_nested`、`test_ignore_external`；SE 同三项失败。当前 G:962/966/967、N:957/961/962 三项都 PASS；R 的 pathspec 0.8.1、networkx 2.3+rh2.1 与安装完成证据覆盖了该旧症状。不是当前仍有“三个坏死测试”，也不代表 actor 已享有修复。 |
| 三项由于旧崩溃而被静默排除出 P2P | 原因链未核实，保留报告级主张 | 原件证明三项旧失败、当前通过且从未在当前 frozen 参考表中；没有本题参考生成/删改过程的原件，无法从一次旧失败反推谁因何排除了它们。它们当前实际执行不等于冻结参考已扩大。 |
| 建议 networkx>=2.4，并重算全部 DVC P2P | 不直接采纳 | 本题 base setup.py 明确 networkx<2.4；当前修复保持 2.3 系列的兼容 wheel。换大版本与全量重算参考需要单独版本/语义依据，不是本审默认修复。原题/test/gold/reward 未改。 |
| P2P 主要为 41 个新增参数、不是本次改动保护 | 修正 | 实际参数 41，但对应 40 个 P2P 身份；部分参数来自 base，不能说 41 全新增。base 通过的断言本来就可以保护本次修改后的旧行为，不能因其非 F2P 就否认回归价值。空目录 files-only 断言无区分力与另一个“注释有尾斜杠、实际没有”问题，需逐项评价，不能由规模判断。 |
| 把 parent 参数 0/1、sub_directory/directory 一并纳入 F2P | 推翻 | 这四项在旧 empty 与当前 noop 已 PASS（SG/SE 的对应摘要；当前 N:965–968），已是 P2P，不符合 fail→pass。不能为了增大 F2P 数量重新定义它们，也不据 F2P 仅一项判题坏。 |
| 局部替代实现可接受 | 静态支持，未执行替代解 | 新 F2P 检查文件集合，不检查 is_dir 名字；但已有 collecting 测试会检查过滤器集合/类型。没有运行合法替代候选，不把“在 __call__ 补 / 就一定过所有情况”写成已验；同时不能把接近正确语义的窄实现自动算作错误解。 |
| 4066/4125/4166 必须同侧 | 部分元数据确认；强制分组不采纳 | 沿 H 精确指针，只读 commit 元数据，`3a469f2e93b8b15f631ece356792acf95b57b3fa` 的 subject 为 `dvcignore: ignore empty (None) patterns (#4066)`；对当前 base 的 ancestry 查询 RC=0。本题 base/参考中确有 blank-line 行为。未读其它任务质量结论、没有另补 4125 来源证据；正常祖先包含先前修复不等于重复同一题。是否同侧取决于拟测泛化和完整任务关系，不从同文件或祖先关系机械决定。 |
| 题面无 gold 代码，所以泄漏检查 pass | 仅确认有限公开字段，实际泄漏仍未知 | raw hints 是维护者诊断脚本/预期结果，公开 bundle 未含此字段；本主审现已暴露。尚未检查真实 actor Git 对象、镜像残留、网络与实际消息，不能将无原文匹配升级为完整防泄漏通过。 |

## 对封存前判断的增量

确认并加强初稿的目录类型保护缺口：隐藏 raw hints 的同名文件/目录对照直接说明所需区别，但不改变其对 actor 的可见性。确认当前源码的空白切分/逐行覆盖行为，撤去“未读 parser 源码”的未知范围；仍保留真实混合状态摘要顺序和奖励表现未执行。

旧配方的依赖故障、root 执行线索、安装中途错误和 status_map 杂键已由原件证实，属于旧 Stage1 条件，当前 repaired pair 的干净安装/三项恢复不得反过来抹去历史事实。原始问题存在、材料与上游对应、当前 gold/noop 差异有意义这些初判未变。题面全部原例未直接保护、自然“去掉尾 /”候选尚未验证、actor 环境未知、独立 reviewer 尚未复核，也未变。

当前建议继续 `needs_review / static_review`、`development_diagnostic`，额外排除为空。唯一优先后续行为实验仍是封存稿 §3 的 base/gold/尾斜杠去除候选三方矩阵；历史记录已找到，不需要用新 CPU 替代原件检索。parser 身份问题已有静态源码依据，另存为来源适配待审事项，不擅自重生成 expected 或把未执行的遮蔽实验写成完成。

本轮没有沿旧记录的 L2、多题 smstat/deps_scan 汇总读取其他题结论。其存在只作定位线索，不采用汇总数量/排名。本题历史原件已完整定位到所需 log/status_map/eval/patch，不是 report-only；仅参考排除的因果链、4125 关系等无明确原件支撑的旧主张仍保留报告级/未核实标签。H 的 24 minutes 是旧审查者自报，不转为本轮成本观测。
