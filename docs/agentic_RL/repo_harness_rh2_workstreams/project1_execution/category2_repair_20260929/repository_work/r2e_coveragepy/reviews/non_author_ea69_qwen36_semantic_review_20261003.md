# EA69 Qwen3.6 首臂：独立候选语义窄核

2026-10-03。**候选确实覆盖已有用户 `.gitignore`，固定 073–075 验收的原 reward=0、48/49 与源码一致；但实际 solver prompt 未交付新增的内容保留要求。因此发现本题公开目标交付缺项，不能将该 0 无条件归因为纯模型失败。** 环境、评分器误拒或测试绕过没有本轮证据。下一次普通派发应先补公开要求；保留已授权验收与本臂原分数，不自动重跑。

本核查者不是材料作者或 fresh 公开读者。只读取本地 baseline.tar、原 FrozenPatch、实际 prompt、必要轨迹及正式失败，使用内存解码/SHA/AST 对拍；未执行 SSH、Docker、安装、模型、Git 候选或项目测试。仅写本报告与同名 JSON。父线程承担完整执行、七维、效率和总账；本报告不授训练资格。

## 源码行为与唯一失败

原 FrozenPatch 仅修改 `coverage/html.py`、`tests/test_html.py`；完整内容摘要与冻结记录相符。与 baseline.tar 内原文件对拍，源码唯一新增是 `HtmlReporter.make_local_static_report_files` 中的路径赋值与 `with open(gitignore_path, "w")` 写入 `"*\n"`（候选 231–234 行）。去除这两条 AST 语句后，整个源码 AST 与基线相同。

该方法由成功报告调用，在数据检查、index 与静态文件输出阶段之后执行。新目录中 `*` 规则可忽略报告，正式真实 Git 节点已通过；无数据流程在调用前抛错，正式无数据节点也通过。但 `"w"` 会先截断已有文件，每次成功生成都把其内容变成 `*\n`，没有保留已有规则的分支。

正式原日志 27–48 行直接证明这一行为：先创建含有效用户规则的 `.gitignore`，生成一次报告后，原 `b"# User-owned rules\ncustom.tmp\n"` 已不存在，读到的只有 `b"*\n"`。失败发生在 `r2e_tests/test_2.py:80` 的保留断言，还未到该循环后面的实际 Git 检查。唯一失败键为 `HtmlGitignoreTest.test_existing_gitignore_is_preserved_and_report_ignored`；不能写成“本臂重复报告或已有目录 Git 忽略两项都已实际失败”，因为失败在首次保留检查就中断。

48/49、testRC=1、`tests_failed`、infra=null 是原评分事实，符合当前已授权私有目标。候选没有使用 encoding；公开 spy 参数限制与此失败无关。源码仅完成了当前目标的一部分。

## 公开测试全部改动与污染路径

`tests/test_html.py` 只在 `HtmlDeltaTest` 新增 `test_html_gitignore_created`（候选 154–160 行），检查文件存在并被 `FileWriteTracker` 记录为写入。去除此一方法后，整个模块 AST 与 baseline 相同；原 46 个测试、断言、mock/helper、imports、setup/cleanup 都未变化。新增测试没有核既有内容、重复报告或真实 Git 忽略，所以它不足以证明完整验收目标。

没有改 conftest、共享 fixture、runner、expected 或隐藏测试，没有插入全局补丁或伪造正式输出。隐藏 `test_1.py` 导入的是未改的 `tests.coveragetest`/`tests.goldtest`/`tests.helpers`；`test_2.py` 导入未改的 `tests.coveragetest`，都不导入被改的 `tests.test_html`。正式 runner 仍运行 `r2e_tests`，新增公开节点不在 49 键范围；可信 setup 恢复3份材料、4个受保护文件齐全，hidden tree与runner身份符合旧CPU固定版，runner前后摘要不变。因此公开测试修改没有改变本次正式分数，未见测试污染或绕过。

原 `patch_hygiene.test_files_modified=false` 与实际 FrozenPatch 测试路径不一致，不能据此宣称候选没有测试修改；diagnostics 明确列出 `candidate_test_like_paths=["tests/test_html.py"]`。这项字段局限沿执行核查保留，不改原报告。

轨迹必要事实：13次工具调用中2次 Edit分别修改上述两个文件。公开原测试输出46通过；brief中的兼容命令实际输出46通过、2警告；添加自测后输出47通过。两条pytest命令使用 `| head -100`，不可单凭管道返回码说pytest正式退出0；本报告依输出记录自测结果，正式testRC另读。模型自写的额外内容查看脚本出现f-string反斜杠SyntaxError后修正，只是开发脚本问题。所有自测均从新临时目录生成，未覆盖已有 `.gitignore` 场景。最后“修复完成”的模型总结不能覆盖正式失败。

## 新发现：验收目标没有实际公开交付

实际 `solver_prompt.txt` 与 `attempt/prompt.txt` 的交付SHA为 `b5b1c227c22bbaa04d20fb298a6013fb2e7060df3fc6f4b895b37596daf22e29`。其中原 ISSUE 只要求输出目录含 `.gitignore`、所有生成内容被Git忽略；没有明确既有文件覆盖策略。其后固定brief SHA `475e3ee69e2e28b4812c1b464a1c9e8381011e9f4959551e05c162387823e2e9` 只讲环境和open替身参数转发，没有保留用户内容的任务要求。

保留目标已获授权，且 073–075 私有评分明确核它；该目标仍有效。但 owner card、inventory、私有测试、候选和旧CPU审查属于host材料，不能当作solver已收到要求。本题 revision draft仅改隐藏测试与期望映射；旧CPU审查也明确原 ISSUE 覆盖策略未规定、brief不提供私有要求，**没有任何补公开保留要求的传递证据**。旧CPU核准证明控制矩阵、身份、开发命令与运输有效，却漏列“授权目标须明确交付”的准入缺项。这一遗漏需在当前记录纠正，旧CPU通过不能自动证明完整任务面已交付。

当前样本有明确覆盖行为，但公开任务只说创建忽略规则；该候选满足了新目录忽略这个公开主要求。不能用没有交付的附加条件把它写成无歧义的公开任务失败，也不能因此取消授权保留验收、让覆盖型gold变正对照。

**受影响范围：仅本题 R6/073–075 的49键评分面配当前原statement和brief，以及采用同一交付内容的后续普通探针。** 原公开statement SHA `87f805dad9c0268639721aa5e02df3a6b430ade43e91344f641eefd47d242cdf`，hidden tree SHA `d9860e3e4c82c0d005cc5fdb3027ac0b489128eec2ffafdb306fc33d991c3430`。不是共享环境或无关题的阻断。

## 具体补材料方案与最小验证范围

建议用现有 `statement_text_replace`、`target=problem_statement` 正式补 Expected Behavior，新编号由发布者分配。公开补充可直接写：

> If the output directory already contains a .gitignore file with user-provided content, preserve that content while ensuring that all generated HTML report files are ignored by Git. This must remain true when the report is generated again.

只公开行为要求，不暴露私有节点、原用户规则字节、gold/正对照、append实现。保留073–075隐藏测试与49键期望原字节。更新statement before/after SHA、public bundle、prepared prompt、delivered SHA、修订清单/manifest与owner request。若先走brief追加，也必须明确标作任务行为要求并冻结新SHA，不能伪装成中性环境建议；正式statement修订更清楚。

当前无需新增CPU动作或自动模型重跑。补公开材料后，按影响做：

1. 窄核公开新增目标与既有验收一致；按现行流程由未接触私有材料的干净公开读者核可理解性。本审查者不能充当该读者。
2. 重prepare并核新public lineage。hidden tree、runner、expected、base、recipe不变时复用已验七候选矩阵和相应CPU镜像事实；发布者按实际身份确认，不机械重跑全矩阵。
3. 一条同版CPU公开交付／空候选往返窄验：真实首 `messages_000` 含保留要求及兼容说明，49键评分面、baseline/image/overlay、运输和清理身份完整。不能把旧首请求替换成新版证据。

父线程/题主需将当前版本本题缺项记入阻断，防止未执行臂继续沿遗漏公开条件派发；本核查不改board，也不发其他线程。本臂原分数及原件保留，可用于“旧公开目标交付缺项版本下”的诊断和候选源码分析；不能直接作为完整公开要求下的模型能力失败、无修订版本的benchmark成绩或训练资格。下一臂及是否重试由修订后的固定申请决定，不能为0而重跑。

原件路径、逐文件SHA、源码AST核对、限制与待办均见[同名JSON](non_author_ea69_qwen36_semantic_review_20261003.json)。旧CPU报告按固定版复用执行事实；完整GPU执行核查为 `runs/ordinary_gpu_probe_20261002/reviews/coveragepyea69_qwen36_a1_execution_review.md/json`。
