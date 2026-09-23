# getmoto__moto-6408 对照复审

结论：同意主审维持 `needs_review / static_review`、用途 `development_diagnostic`。精确原复现被gold修复且已有历史运行支撑；唯一归属和其它标签保留没有完整验收。新manifest分支的删除错误是邻接旧缺陷，gold把非代表旧tag也带入该路径；不是已证“base正确、gold新破坏”的回归。选一项目的manifest存在/不存在的受控状态对照作为主CPU建议，未执行。

独立性：本人initial SHA256=`04158158ea294a9dbd133a39f5f729716a1315d83856aec94121b7806bd18795`。root于2026-09-20T22:03:11.721133+00:00确认整包封存并明确放行后，才读取本题public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json和本题history/refs.json指定唯一旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_3/records/getmoto__moto-6408.json`。不追该旧记录的stage1、包级问题、全局索引、维护者hints或外部AWS说法。environment_record先前已有gold/noop摘要暴露，不能称结果盲审。initial保持原字节；未导入/执行项目、测试、安装、网络、Docker/SSH、模型或配额操作。

路径：ROOT=.；P=ROOT/runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-6408；V为对应private；E=ROOT/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6408。原件SHA和逐项阅读范围沿封存initial。

## 同意、分歧与旧结论处置

| 主张 | 复审判断 | 证据与限制 |
| --- | --- | --- |
| 标签移动应使查询切换到第二manifest，并保留两图的其它标签 | 同意 | 题面明确目标manifest，P/base/moto/ecr/models.py:601–605声明唯一性，304–313及旧多标签/删除测试支持保留剩余tag。不能把题面仅比较不等当成允许任意变动。 |
| helper未在题面定义，构成私有依赖缺失 | 同意delta撤回 | helper在公开tests/test_ecr/test_ecr_helpers.py:31–44；测试imports可定位，全部helper已读，仅本地随机/标准库hash。题面缺导入可由正常开发调查补齐。 |
| 新F2P覆盖原精确序列，未完整验唯一性 | 同意 | 完整新增49行及全部两条assert已读，两次都是first,*_后只比较manifest。没有images长度、failures、describe标签集合或旧独立tag回查。名称only_on_one_image不代替断言。 |
| 仅排序或整图删除来源就可得满分 | 收窄，认同主审未执行限定 | 这些是针对明确漏测的具体部分实现预测。没有候选原运行，不能将静态可蒙混路径或旧记录“预期满分”升格为已证RH2奖励漏洞。 |
| gold已有目的分支能够正确迁移并保留其它标签 | 同意，区分观察层级 | gold先batch_delete旧tag，再给目标update_tag；原序列两图均多tag，只有原归属被解除。完整状态正确是源码推断；原96节点全过只实证其中已测行为。 |
| 新manifest分支会删掉新图 | 同意强静态路径，明确非新增回归 | append B后全局batch_delete遍历A和B；A多tag故保留对象、只摘tag，B单tag则整图删除。代表tag场景base即错；非代表tag场景base保留重复归属，gold改成员匹配后转为新图被删。两版表现不同，但base并非正确基准。 |
| gold第一hunk没评分，因此只含第二hunk就是不完整解 | 不接受该逻辑作为充分证据 | 缺某个gold hunk不等于违背公开行为；应以具体归属要求判断。第一hunk相关邻接分支值得测，但完整gold也没有正确处理上述状态。只含第二hunk的真实得分尚未核。 |
| 同模块95个P2P通过，证明全面无回归 | 拒绝全面结论 | 原95个参考全部通过可确认；已展开相关函数不等于展开95个函数，更不覆盖所有put/delete组合。原公开single-tag新manifest测试不能替代multi-tag新manifest分支。 |
| 黑盒断言不强制内部实现，合理非gold路线可行 | 同意但不写全体实现必过 | 可先确定目标、只从其它对象摘tag，再创建/更新目标，保留旧last-tag删除策略。未发现helper/Mock形状限制；未运行替代实现。 |
| 旧install rc2、无子模块、无派生、ready_for_probe或17分钟成本 | 不沿用或限定 | 最新本题原make init实际完成；Terraform gitlink存在但与ECR路径无关；无全局关系核验、没有本轮模型成本。状态与用途按本轮限定。 |

本人与主审核心初判一致，未出现需推翻业务诊断的分歧。主审的唯一主实验曾列base/gold/合理实现三者；本复审把合理实现视为结果有歧义时的可选延伸。先用base/gold就能区分精确原序列、邻接旧错误和新旧错误表现，无需为了启动诊断强制制作第三候选，更无需机械凑两份错误补丁。

本人独立阶段完整展开的相关P2P比主审列举范围更宽，包括按digest删、digest+tag一致/不一致、多图删除和mutability配置等；这增加对已读分支的静态核查，没有把剩余策略/生命周期等函数体补成全读。全部F2P1及P2P95名单与原结果已核，实际函数清单详见initial。测试随机manifest未观察到碰撞或不稳定；不能仅凭random判题坏。题目未要求扩大到所有IMMUTABLE、manifest等价JSON或真实AWS删除语义。

## 已有观察与静态推断分账

G原日志=`E/gold/eval_logs/evallog_replay-er19-iw1-getmoto__8717daf0.eval.log`；N=`E/noop/eval_logs/evallog_replay-er19-iw1-getmoto__0fdceeeb.eval.log`，SHA沿initial已重算。原命令G:689/N:659均`pytest -n0 -rA tests/test_ecr/test_ecr_boto3.py`；G:695/820收集并通过96节点，N:665/848为96节点、1失败95通过，失败在新增目标manifest等式。执行节点96、解析键96、冻结F2P1+P2P95分别核对；没有参数空白别名碰撞、缺席或skip。G/N退出码0/1和reward1/0有各自原账，奖励差由具体冻结F2P状态支持，不把pytest总退出码当奖励定义。

只读重新查看historical baseline.tar.gz的parser:44–56及scoring:225–270，仍按marker内摘要和冻结键计分；没有导入它。ECR当前96节点不存在6185/5960那类合并，不能把别题的键风险挪来当本题已观察故障。没有新跑候选、错误补丁或扩展断言；来源唯一性漏测及B被删路径仍为静态证据，旧记录/主审一致不提升为运行观察。

主审initial曾给mem峰值附MiB，delta已明确撤回单位推断。本复审保留原字段resource.mem_peak_mb=204.816/228.629、resource_facts=null；不换算或据此给actor资源打pass。

## 唯一主CPU建议与环境边界

一个受控实验，两种初始化：固定不同manifest A/B、来源A含独立tag与moving，分别让B已预创建（题面控制组）或尚不存在（邻接组），其余操作保持一致。在精确base/gold分别执行同一个put迁移，记录put返回、batch_get(moving)完整结果数量/manifest/failures、describe两图标签集合，以及来源独立tag是否仍可读。预期控制组base重复归属、gold正确；新目的组base/gold在moving是代表tag时均可能返回已被删的B。优先保持moving是代表tag，以直接核旧缺陷；非代表tag只作为必要的同实验扩展解释gold匹配范围。全部预期未执行，不以此自动reject题目。

该诊断可以使用固定grader环境；正式actor验收不自动成为它的前置。若还要量化原评分对缺口是否敏感，应在独立输出中保留原F2P/P2P结果，不能悄改冻结reference/reward/expected。按实验观察再决定是否需要一种有明确因果目的的候选或另版补充断言；本轮没有实施修订。

历史install_wave1无recipe/materials/reference binding覆盖，原spec仍make init/Python3.12/pytest -n0 -rA。Dockerfile的COPY/ENV不是安装成功依据；G:517–679及N:487–649两轮editable实际build/install记录才是。pins setuptools72.1.0/wheel0.43.0/packaging24.1；派生image=sha256:9ea5a5f571d9feda40bda0d0be2c1242c409a457c7ff38827deb9b937a4e85c4；scripts_digest=sha256:fa4f2ffa96bcbb4c953d5b8470b4e0927a859647b803cc0788f80b1c76fb305a。原status只保存最后gold命令，noop依据原launcher和日志，不声称status捕获两次。

原prepared仍指/work，未来重放须另建重定位summary/manifest、核当前目标机镜像和historical baseline code-root及依赖，以新run_id/输出保存；原wheel payload/context未保留，当前资产可用性未知。本轮不动原件。原policy字段为cpus=2.0、memory_bytes=4294967296、pids_limit=512、shm_bytes=67108864、tmpfs_bytes=1073741824、deny_all、rh2grader/54322；candidate apply=agent/54321，env_qualification=absent。它们及历史本地import均不等于正式actor；实际模型消息、UID/HOME/cwd/PATH/解释器/权限、工具和镜像消费另待共同验收。

官方恢复保护仅tests/test_ecr/test_ecr_boto3.py，test_globs=()；helper不因文件名像测试就自动排除，additional_exclusions=[]保持。合法业务源码可交付；未修改任何源/tests/gold/reference/reward/expected。

## 同包关系证据升级与暴露范围

root对照阶段提示后，本人只在已分配三题原公开包核读：6408的P/base/moto/dynamodb/models/table.py:487–504完整保留6185 gold的attr参数、递归传key及table_key_attrs条件；同文件839–842保留5960的deepcopy+index projection方案，但已经改为`results = [index.project(r) for r in results]`，并非5960 gold逐字相同。6185公开base同文件846–850则逐行保留5960 gold核心。升级仅为“晚题公开base包含早题实现或后续演变”的可见源码事实；6408本题目标是ECR，不能据DynamoDB代码承接认定任务重复、Git祖先关系、真实solver看过答案或已有泄漏。此补充不回写initial，不沿用旧全局索引的无派生结论。

八方面沿initial完整成立；本次新增阅读为自己main/public五份报告、指定唯一旧单题记录、ECR models.py:565–621/707–760、冻结parser/scoring上述片段，以及己方三题精确DynamoDB源码/gold关系片段。未读其它题/聚合，未查真实AWS规范、全量SDK/core、正式actor、重复稳定性或模型成本。用途维持开发诊断。
