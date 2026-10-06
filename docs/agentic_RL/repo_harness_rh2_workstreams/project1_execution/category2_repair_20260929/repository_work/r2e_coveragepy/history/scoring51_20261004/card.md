# ea6906b0：保留规则内容并忽略HTML报告

2026-10-03。**R17 Coder原49/49、raw1保留；CPU-A对原候选的真实Git窄验确认三个字面CSS文件名未忽略。正常用户内容/再次生成通过，格式和规则顺序变化未证明候选独有Git失败。最小评分补验收草稿已通过三对照单项验证，尚未发布；新版Qwen沿原claimed请求继续题目调查，不把旧评分视为完整语义正确率。** [正式非作者报告](../../reviews/non_author_ea69_r17_coder_boundary_cpu_review_20261003.md)已核查通过；旧Qwen只属旧题面，不改绑。不授训练资格。

当前目标是保留已有用户`.gitignore`内容，并让首次及再次生成的报告文件被Git忽略。题面不限定append、encoding等合理实现；本轮不新增逐字节相同或文本幂等要求。

## 当前Coder边界诊断与最小补验收

[原七维分析](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/model_analysis_coder_r17_a1_20261003.md)和[原非作者语义报告](../../reviews/non_author_ea69_r17_coder_semantic_review_20261003.md)保留原SHA/时间点。新证据以[CPU边界报告](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/candidate_boundary_r17_coder_cpu_author_20261003.md)、[当前收口](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/candidate_boundary_r17_coder_cpu_closeout_20261003_v2.json)为准：原Frozen/360文件基线固定，CPU9877…、UID54321、Python3.7.9、coverage6.1a0、Git2.34.1。21个对照×fixture/44次报告，safe_append9/9场景全部忽略，原候选6/9；!custom.css、#custom.css、custom[ab].css各两次生成后quiet RC1并出现在git status。原候选未修补，没有模型重求解或正式重评分。

正常两行内容、正常extra.css、无末尾换行、连续三次报告均通过。空行/CRLF被改写、原同名规则顺序移动及*.html增长属于已观察内容/质量差异。notes/style.css从不忽略变成忽略在safe_append和原候选都发生，不据此判原候选独有语义错误，也不新增字节或文本幂等门槛。三个特殊CSS则是既有公开extra_css选项实际复制的报告产物，确实未达到公开“所有生成文件被忽略”的要求，现行49键没有覆盖它们。

[最小材料提案](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/generated_css_material_revision_proposal_20261003_v2.json)只在test_2增加一个真实Git字面extra_css测试（含正常extra.css正控制与两次生成），expected旧49键全部不变、草稿新增1键至50。公开题面、源码环境及模型候选不变。[新增单方法CPU验证](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/literal_css_criterion_draft_validation_20261003.json)：safe_append通过；baseline与原候选按预期失败，原候选失败点为!custom.css。这不是新50键正式成绩，未发布新修订号或回写原reward。

两作业均finished0、自有容器0，分别21份/4,667,553字节和27份/4,372,188字节已全SHA回收。当前没有本题CPU在途；正式非作者报告已完成，确认本轮原件及最小草稿范围；不等于新50键正式评分。GPU已经确认新版Qwen沿原请求继续调查，无重复提交/重求解或无关停发。原probe终态核收后，再依现有活动指针规则提交普通publish；新评分材料发布后只对原FP关联补验收。等待时本题仅缺Qwen与新材料发布/实际消费补评分，不重跑旧完整矩阵。

## 当前R17验收与GPU交接

正式r2e-mr-093补题面，073/074/075及49键保留。statement SHA `39b6b28abc08b21a76a71d8908a7e37a00040cbfc3f9d92ee12bc37b3b6a194f`，R17 manifest SHA `76aee53151d3b58758d00a9feb5a901b720b4b430f37d2057ed07c1ef0ce2fa6`。[fresh公开读者](../../reviews/fresh_ea69_statement_preserve_reader_20261003.md)、正式发布及consumer身份核对通过，原neutral brief字节未变。

CPU-A同来源同配方实际prepare/public窄验均rc0结束。完整新版题面和brief精确交付给真实CC首请求，公开HTML兼容命令46通过、2条warning；空FrozenPatch原正式评分41/49、reward0，全部49键与R6 noop一致，测试rc1、执行/驱动rc0，无infra/partial。基线360项、排除路径4850项、运输往返、镜像和退出均核。87原件/6,982,615字节闭批SHA核；actor/grader/relay/任务网络和prepare残留0，18210/18211实际可绑定。见[作者历史快照](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/cpu_acceptance_r17_v1.json)、[后续收口](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/cpu_acceptance_r17_closeout_v1.json)和[非作者实际核查](../../reviews/non_author_ea69_r17_actual_cpu_review_20261003.md)。核查者沿用非作者上下文，不是fresh公开读者；未新增SSH、Docker、模型或项目测试。

评分材料、runner、expected、源镜像、base及recipe按固定SHA核不变，旧七控制矩阵复用，不全量重跑。actual CPU actor/grader同镜像ID `sha256:9877b37b29ed7b187c7382fe8f2eb9b6f99d08d2129fc66134289d28943d71ec`，GPU执行者自行核实际GPU镜像，不代填CPU身份。

[新固定GPU输入](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/probe_request_r17_20261003_v1.json) SHA `8334dc5a3ba8cd5e769d8ca1dd99fba0ab6b402538a7a3cccd67adbf6bcc92b0`，request `r2e-coveragepy-ea69-r093-cpu-r17-20261003-v1` 已claimed并实际通知GPU。按统一probe-wide-v1，两个既有模型各一次新a1；solver只读固定公开面与中性brief，gold/正负对照均host私有。当前无CPU在途；原公开交付验收仍有效，后来候选边界与草稿单方法已实际完成，当前状态见上文。

## 历史R6修订与证据

私有R-b只转发open的`*args, **kwargs`，保留文件记录及HTML断言；R-c保留两条原断言，新增内容保留及真实git status检查。允许跟踪`.gitignore`本身，不指定文案或open参数。正式49键从原46键替换036/037后形成。见[材料变更](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/material_changes.diff)、[结果清单](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/results_manifest.json)和[非作者材料核查](../../reviews/non_author_ea69_material_review_20261003.md)。

R6实际公开CC首请求含原题面，UID54321、Python3.7.9和工作树预检正常；原公开HTML46通过。原FileWriteTracker.open不接受encoding，单进程仅转发open参数的[兼容命令](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/devcheck/public_filewrite_compat_v1.py)保留相同写文件记录，真实CC再执行46通过。原[开发说明](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/public_devbrief_20261003.md)只含环境及替身事实，不修改HTML实现或评分预期。生成报告退出0不等于修复通过，初态仍无.gitignore。原空FP正式noop41/49见[读回](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/public_delivery_r6_check.json)。

七控制完整结束：safe_append、safe_append_encoding各49/49=1；gold、CA、CC各48/49=0，失败为已有规则保留及效果键；CB47/49=0还错报告忽略，RE47/49=0还错无数据时不创建目录。实际材料、runner、镜像、候选SHA、完整段及清理均匹配。见[逐键矩阵](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/formal_matrix_r6_check.json)、[R6作者快照](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/cpu_acceptance_r6_v1.json)及[非作者CPU核查](../../reviews/non_author_ea69_cpu_review_20261003.md)。原gold无条件覆盖用户内容，保留为负对照，两safe_append为host-only正对照；不为gold删要求。

## 旧模型样本的解释边界

旧Qwen open(w)覆盖内容，唯一保留键失败；但实际solver/attempt prompt及brief未交付已授权preserve目标，旧CPU审查漏列此公开准入缺项。原0/48-of49保留，不能无条件归因纯模型能力失败。旧[固定请求](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/probe_request.json)已安全cancelled/ACK，新版不复用旧Qwen作为a1。见[原七维分析](../../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/model_analysis_qwen36_a1_20261003.md)及[非作者语义核查](../../reviews/non_author_ea69_qwen36_semantic_review_20261003.md)。

新版执行回传后仍由本题主审候选语义、原评分、公开测试全部差异及消耗，再决定必要修复。CPU桩/控制候选不计模型样本；`grading_materials_identity`仍为null，不授训练资格、不证明正式训练typed actor租约。[当前接续点](../../resume_checkpoint_20261003.md)；历史依据见[续接清单](../../../../r2e/r2e_inventory.md)及[旧准入卡](../../../../../r2e_lifecycle_20260929/results/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/probe_card.md)。
