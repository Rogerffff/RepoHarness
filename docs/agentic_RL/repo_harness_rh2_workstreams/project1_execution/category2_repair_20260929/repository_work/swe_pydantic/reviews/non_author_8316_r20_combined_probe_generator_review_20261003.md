# 8316 R20组合探针生成器：非作者静态窄核

日期：2026-10-03。结论：**未发现此次窄适配的决定性静态阻断，可保留为待实际核收后的生成入口**。这不是CPU/GPU资格审查。新R20十九行results、公开actor和最终非作者CPU报告当前均未到位；本次没有执行生成器，snapshot/request均未生成。

我已有私有题卡、controls及R14原件上下文，不是fresh公开读者。只做本地标准库源码、差异、AST、JSON、SHA及当前来源绑定检查，没有SSH、Docker、任务tests、安装或模型，也没有重新核旧759份原件。仅写本审查MD/JSON。

## 核查对象与版本

生成器 `runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/generate_8316_r20_combined_probe_request_v1.py`：17230字节，SHA `be43af74234d30a56a968edac487326e429c4fbf1fc6b1a8619a7b2113e6b985`。完整读该文件，并对照已核8567组合生成器（15422字节，SHA `14207ee4e1aacb11357d523055909cc02d1653833ca6ba10202260c0e8c02a27`）。

适配的主要变化是分开旧/新results及meta、五行/十九行切片、R20consumer与registry、不同wrapper/input身份、reset900/policy观察以及GPU精确镜像兼容说明；未加入CPU/模型运行或外发逻辑。35项本地材料断言通过，36件当前来源文件已绑定。AST解析只是语法/结构检查，不是执行验收。

## 五行与十九行的组合

旧results来自 `remaining/results.json`，新results来自 `8316_r20_resume/results.json`；只在内存中合并attempts，不回写两份原件。每个指定job+task+kind须唯一。旧部分作业固定R14 job、formal_v2 namespace、returncode1、stopped_needs_analysis及原error；其release/manifest取old_meta。新formal和actor的release/manifest取R20 meta，不能用R20身份包装旧五行。

旧formal input/wrapper分别固定 `bea70edd…` / `b127f730…`；新formal input固定 `58765caa…` 且与本机新输入SHA相同，wrapper与当前已核新runner匹配；actor亦分别核新actor input和wrapper。当前这些来源SHA与前次R20输入审查一致。新formal namespace明确限定 `formal_8316_r20_resume_v1`。

旧五行名称须完整为noop/gold/keep_digit/scan/w_example_only，旧部分独立审查须声明可复用、旧w_acr_max8为infra/null且清理无残留。新formal十九行名称须等于旧完整candidate的[5:]，组合后必须保留全24行顺序、各行预期reward、passed及每个check。每条组合记录附job与source_release；完整attempt另保留manifest/input/wrapper/原件等身份。因此旧五行继续属R14，不会改成“全24在R20通过”。

当前真实旧五行及reward0/1/1/1/0、旧meta及状态已核对应，旧失败仍是保护300秒infra/null且install/test未开始。新十九行的预期0不是实际结果，当前没有新results可核。新final review还必须明确旧infra/null保留，不能机械把第六行历史null改0；即使后续新w_acr_max8得到0，两次attempt也分别保存。

spec比较将旧实际spec的budgets替换为900/120/1800，再要求新完整spec相等。旧实际已核预算为300/120/1800，当前保存新prepare也满足该比较，因此在本题固定旧原件下允许的唯一变化是reset300→900。新十九行逐个读取单条真实ledger并核reset900和固定policy SHA；其余预算与request/request_input的完整核对沿用新runner的passed/checks条件及最终非作者原件审查，不能只凭这两个ledger字段授予资格。

## 新actor与最终报告

新actor必须returncode0、无error、published_public_actor_diagnostic_passed，核新input/wrapper、实际公开交付、私有新测试未活动、f939精确容器/2CPU/4GiB及清理。生成器不单独断言actor namespace；新wrapper的输出路径限制已经将它限定在本R20 namespace，最终实际审查仍应核job路径和namespace，不能混用旧actor。

公开首消息的证据链是新actor runner实际读取 `messages_000.json`，检查首请求中的user内容包含render后的公开prompt、problem_statement与public_hints，再记录actual_request SHA和actual_public_delivery。生成器只消费这一结果标记，**不重新解码首消息或查完整角色边界**；这些必须由最终独立CPU/actor报告检查真实原件。当前actor不存在，所以输出文案“已核实际首消息”等只能在未来资格条件满足后成立。

最终review JSON要求job、actor_job、reused_formal_job、formal_jobs顺序、combined_candidate_order、旧infra/null保留、cpu_review_passed、ordinary_gpu_probe_ready_within_review_scope、R20source/manifest全部吻合；MD和JSON都绑定进入snapshot/request。当前静态输入报告的CPU/GPU字段是false，不能代替该最终报告。生成器是固定已审结果的入口，不是独立CPU审查实现；实际完成后题主仍须读核最终报告和来源绑定。

## R20公开/评分来源与GPU边界

本次独立核R20 manifest中四份bundle、producer manifest及8316 registry的大小/SHA和唯一8316记录。registry是运行注册格式，题卡revision是提案格式；两者整体字典不相同不构成失配，已核其v3 revision/base、有效补丁字节与SHA、public digest及E10安装资产/内容一致。public/grading canonical digest、环境join、144参考与当前保存spec一致；request仍保留原题面和公开hints、当前参考分区，没有扩题。

镜像来源固定base digest、公开八wheel URL/SHA与CPU f939准备原件，GPU实际ID仍为null；需再次检查UID54321/54322对wheel可读，不能继承旧0600安装失败或以CPU宿主ID冒作GPU实测。Q12可读层核收只说明相邻题已有共享修复证据，不代表本题GPU安装或候选已验。

新增preparation_budget_policy声明正确：**R20政策仅匹配CPU f939精确镜像；GPU实际镜像不同则必须由共享发布者提供对应版本兼容支持并核实际spec/ledger，禁止任意覆写900**。该说明是执行者的待核条件，当前生成器没有提供兼容实现，也不会因此自动启动GPU。缺兼容支持时先停在发布/执行者审查，不把已核CPU预算外推到GPU。

## 写入及后续范围

所有CPU/actor/final-review资格断言在首次输出写入前；当前缺新results会更早停止，不能凭静态报告创建快照。AST只发现snapshot和target两个输出，不写旧results、原分、失败工件或共享代码。预存在snapshot/request时拒绝覆盖；两份文件由连续write_text保存，沿用原生成器方式，并非双文件原子事务。若后半写入失败留下半封包，应按原件保留和人工核收处理，不把半封包记成合格请求。

后续仅在新十九行及新公开actor真实完成、最终非作者报告完整核收并由题主读核后运行生成器；随后再读实际snapshot/request的全部字段、字节及来源绑定，再交执行者。当前CPU恢复、组合整矩阵通过、实际actor核收、GPUready和训练资格全部为false。此次没有新增决定性静态阻断；旧输入审查不回写，随后hold历史guard增量另用独立报告核查。

