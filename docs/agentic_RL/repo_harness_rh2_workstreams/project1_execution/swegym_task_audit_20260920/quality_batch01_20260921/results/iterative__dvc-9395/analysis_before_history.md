# iterative__dvc-9395：history 前静态分析

2026-09-21；主审 investigate_dvc。历史未开放时保存本稿，后续不回写。本轮只静态读源码/日志及用标准库核元数据；没有运行项目、安装、容器、SSH、模型或反例。

## 引用与暴露

R=.。P=R/runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-9395；Q=对应private/iterative__dvc-9395；源码路径默认相对P/base。O为本文件目录。
T=R/runs/env_recipe_repair_20260919/dvc_tail_v1/tasks/iterative__dvc-9395；GL=T/gold/eval_logs/evallog_replay-er19-dvc_tail_v1-_66688534.eval.log；NL=T/noop/eval_logs/evallog_replay-er19-dvc_tail_v1-_d7bf896d.eval.log。两账本为T/{gold,noop}/ledger.jsonl:1。

已读本题public_read、公私有bundle、test/gold patch、validation、source/run refs。environment_record只展开环境字段、观察与recipe引用，接触verified_environment_pair标签、DVC_pygit2问题标签；未展开/跟随其analysis/history。共用协议和字段定义沿已读版本。没有读9395旧报告、其它题原件/结论、manifest、主计划或method_adjustments。前题知识不作本题证据。

P和Q均base=c75a5583b3840ba90a8e800a0f42c1cb120916db，tree=865bc0582bc98990dc7eface03520a6c6335a6fa；base_identity称608跟踪条目、无gitlink/LFS/.git，本轮不重建tree。source_refs指定三份S2 JSONL各第146行，与本题bundle内容相等。两原始日志hash与run_refs、两角色十份recipe审计文件hash与environment_record均一致。gold SHA256=4a5017f1dfa6375041fd1a4ce055a5bcc1a7bedc221ccada2cc0732044667d4a。

## 1. 公开目标、初态、开发入口

prompt:3–11要求repro --pull恢复“本次repro需要”的缺失文件，明确普通无cmd的.dvc数据源不能依赖用户事先pull。已有运行缓存恢复需保留；不能将标题的all解释为无条件恢复全仓无关对象。CLI commands/repro.py:27–40传入pull、dry等，:129–145规定pull默认false、dry只打印不执行。公开旧测试test_repro_changed_data/test_repro_data_source要求尊重用户修改，test_repro_dry要求不改变输出，test_non_existing_output保留不加pull的缺失错误。

初态源码：repo/reproduce.py按目标选图、_get_steps按依赖/frozen/单项确定顺序；Stage.reproduce先changed，再Stage.run。stage/__init__.py:576–584对无命令源和frozen仅检查工作区存在，utils.py:140–143缺失抛MissingDataSource。普通有命令阶段StageCache.restore:201–213只在pull且非dry时拉取对象/checkout，而且restore不会先下载已不存在的本地run-cache记录。NL:698–746实际缺foo失败；NL:1433–1480在本地run-cache删除、cmd_run被mock时缺bar失败。二者与新增行为对应，不是安装失败导致分差。

public_hints属于harness指令与待验环境声明，非产品规格；实际消息与shell未捕获。只改非测试源码足以表达本题合理修复，旧“所有测试都恢复”解释不能概括当前规则。

## 2. 每个新增/修改测试、fixture与断言

test.patch只触碰tests/func/test_repro_multistage.py、tests/func/test_run_cache.py。全部变更已逐行读，测试名称中的mising是原件拼写。

| 测试/参考身份 | 设置、调用与全部关键断言 | 实际测到/未测到 |
| --- | --- | --- |
| test_repro_pulls_mising_data_source；F2P | dvc_gen写foo内容foo并dvc add；push到local_remote；stage.add建立cp foo bar且依赖foo；删foo和其cache_path；唯一assert dvc.reproduce(pull=True)为真 | 真实文件、缓存、DAG、shell；源必须恢复才可正常cp。没有直接核foo/bar字节、源修改/目录/dry/多个分支；返回非空不是完整内容oracle |
| test_repro_pulls_mising_import；新增但不在F2P/P2P | erepo_dir中创建并提交DVC foo；本仓dvc.imp本地路径foo；push；建立同一cp阶段；删导入foo及缓存；唯一assert reproduce(pull=True)为真 | 本地外部repo导入恢复真实执行；没有remote云依赖。该项在原始30项中执行并失败转通过，但来源29项参考不包含它 |
| test_repro_pulls_intermediate_out；新增且列P2P | 写fixed，create-foo=echo foo > foo依赖fixed，copy-foo=cp foo bar；先reproduce create-foo并push；删foo/缓存；assert reproduce(pull=True) | 现有命令产物恢复；no-op已过。没有mock“不运行create-foo”，所以重新执行echo也可满足当前断言，不能称其已验证避免重算 |
| test_restore_pull；修改F2P | 旧run_copy生成foo→bar。push变为run_cache=True；spy StageCache.restore和dvc.output.checkout，patch cmd_run；删bar、lock、output缓存，新增删run-cache目录；reproduce选定copy-foo-bar | 真实远端run-cache记录恢复、禁止重算、产物存在；新增需求有题面旧能力/自动缺失恢复依据 |
| 同上全部最终断言 | 解包仅一个stage；restore恰一次(stage,pull=True,dry=False)；cmd_run未调用；checkout次数从2改为3；bar存在；assert not foo.unlink()；lock存在 | foo.unlink返回None，所以该句主要要求foo原本存在并删除它，不核内容。bar存在/lock与禁止重算有公开意义；精确三次checkout属于内部机制，题面无该次数要求 |

fixture/helper已追：tests/conftest.py导入dvc.testing.fixtures、dir_helpers、scripts/remotes；autouse日志/UI/clean_repos与session isolate已读。isolate:176–210在临时HOME写Git身份并设置pygit2全局搜索路径。dvc/testing/fixtures.py:36–86用缓存模板构建tmp_dir与Repo，上下文关闭；local_remote:176–178→make_remote:125–129→make_cloud/make_local→本地TmpDir并设为默认remote。TmpDir:148–174将gen→dvc.add，:186–203写remote配置；普通测试无scm时初始化no_scm；erepo_dir=make_tmp_dir(scm=True,dvc=True)，因此import试验才用本地Git提交。run_copy（tests/dir_helpers:62–76）调用python copy.py，依赖含foo与copy.py；copy_script实际使用shutil.copyfile/copytree（scripts.py:3–19、37–41）。remove（utils/fs.py:62–72）删除文件/目录，ENOENT容忍。mocker未用于三个新multistage测试体，只作fixture参数；不能称它们mock了恢复行为。

P2P的params样例还追到tests/func/test_run_multistage.py:220–226常量。测试收集需dvc-ssh（tests/remotes/__init__.py:1）和pygit2（conftest:206–208）；自动dvc.testing.plugin导入pytest_virtualenv等。func子目录无conftest。第三方dvc_data/scmrepo等实现未随包提供，未逐行查其安装源码；本轮不借此断言其checkout会覆盖修改文件。

## 3. 需求—断言双向映射与回归范围

完整打开两个官方测试文件：base multistage:1–399、run_cache:1–185，加test.patch全部新增，涵盖2 F2P、27 P2P、额外import一项。不是仅从数量推覆盖。

| 公开要求/旧行为 | 依据 | 对应断言/保护层 | 覆盖与实际证据 |
| --- | --- | --- | --- |
| 所选图的完整缺失数据源恢复到工作区 | prompt:9–11；Stage.run:580–584 | F2P missing_data_source的真实cp和非空返回 | 核心正例；NL失败→GL通过；仅单文件/默认图 |
| 远端run-cache记录与对象恢复，避免重算 | prompt:4–11；旧test_restore_pull | 修改F2P禁止cmd_run、bar/lock存在、restore调用 | 核心正例；NL失败→GL通过；具体三次checkout过严疑点 |
| 导入数据源恢复 | Stage.is_data_source:241–257；prompt只明确狭义source | 新import测试的真实流程 | 历史执行保护，但不在来源参考；不等于评分保证该行为 |
| 中间输出恢复 | 题面已有能力 | 新intermediate_out（P2P）的成功返回 | base/gold均过；不能区分下载与重算 |
| 旧缓存记录保存/复用/多个版本和stage | run_cache文件:13–158 | push_pull、restore、save、memory_for_multiple_runs、memory_runs_of_multiple_stages | 读取全部具体断言，历史参考均过 |
| nocache区分与dry不保存 | run_cache:54–87 | do_not_save_on_no_exec_and_dry；out_type三参数 | 保护无pull的dry和不同cache策略；没有dry=True,pull=True组合 |
| 图顺序、frozen、下游、循环、缺stage | multistage:15–120、295–309 | frozen、downstream、cyclic_graph_error、non_existing_stage_name | 参考均过；主要不带pull，不能覆盖gold新增分支 |
| cmd/dep/out/lock/参数变化 | multistage:122–361 | changed_cmd、added/moved deps、added outs、overlap/nonexist、deleted_lock、multiple_params | 已读全部输入/断言，参考均过；未覆盖pull和已修改source组合 |
| 多命令顺序和失败停止 | multistage:364–399 | 两组True/False参数化 | 具体foo/bar内容与异常均有保护；in_order最后无条件写列表，两种参数并未真实区分最终cmd形式 |
| dry不产生下载/检出副作用 | CLI:138–145；Stage.run:573–603；StageCache.restore:201–213；公开test_repro_dry | 来源参考dry测试不带pull | gold新增路径无dry保护，具体静态回归疑点 |
| 无需恢复时、无remote仍可repro --pull | “missing and necessary”；Stage.reproduce:424–429跳过unchanged | 无参考组合 | gold在选图后无条件stage_cache.pull(None)，预计新增NoRemoteError |
| 用户已有source修改应保留 | test_repro.py:270–284、671–685 | 公开旧测试，无pull且不在参考 | gold用stage.changed（包括modified）触发pull，可能提示/阻碍正常repro；下层外部checkout未展开，未定实际结果 |
| CLI/exp共享调用者 | commands/repro.py:13、27–40；experiments/run.py:29–42、81–84 | 公共CLI默认参数测试已读，不在参考 | API测试没有真实CLI/完整exp流程覆盖 |

反查：F2P不指定新helper名、日志字符串或固定源码，真实本地文件主要有行为意义；但restore一次和checkout三次仍强制内部轨迹。尤其GL:3607、3614明确第三次流程中的预拉取面对“bar无hash、不创建”，随后正常run-cache checkout与commit relink才完成产物（output.py:699–711、713–752）。若只恢复数据源、先取run-cache记录后让现有restore恢复有命令stage，则可保留业务结果且没有这次无效checkout。它是合理非gold路线，可能被精确3拒绝；尚未构造/执行，故不能宣布已证误拒。

可能蒙混的部分实现：只给普通is_data_source阶段加pull并补run-cache，保留import错误，可能仍满足来源2+27但让额外执行import失败；或只针对已测单文件恢复而漏目录。尚无候选原始评分证据，不能把“参考不含import”直接宣布它必然reward=1或平台忽略test_rc，需实际校准。相比这些合成候选，gold已有dry路径疑点更值得优先。

## 4. gold逐项审查和唯一优先对照

gold全部改动是repo/reproduce.py：增加PLR0912 lint豁免；选图后if pull就stage_cache.pull(None)；每个stage在_reproduce_stage前if pull and stage.changed()就repo.pull(stage.addressing,allow_missing=True)。无新增依赖/未交付helper，也没有改测试/原始参考。核心正例历史确实修复，gold保留选图步骤，没有全仓checkout业务输出；但全局run-cache transfer:237–257扫描远端runs，并非仅本次所需记录。帮助文案仍描述旧范围（commands/repro.py:134–135），是文档未同步，不必单独判坏题。

高置信静态疑点 A：两个新增pull路径都不看dry。StageCache.pull:264–266无dry参数，transfer会复制远端runs；repo.pull:35–53会fetch并checkout，链上repo/checkout、Stage.checkout、Output.checkout也未自动感知外层dry。旧StageCache.restore有not dry保护，gold在它之前执行了有副作用动作。因此公开dry契约可能回归，即便原参考全绿。现有证据是控制流，不是本轮运行复現。

独立疑点 B：无remote但已有数据/无需恢复时，base Stage.reproduce可直接skip；gold顶层stage_cache.pull(None)先走DataCloud.get_remote_odb→get_remote:60–98并抛NoRemoteError。HTTP远端的run-cache transfer:224–231亦有不支持分支，不能由需要对象pull自动推导必须支持run-cache。至少无remote无缺失输入有清晰的源码回归预测；运行结果待验。

用户修改source的风险 C保留为未知：stage.changed包含modified，gold无条件先pull并checkout，Output._checkout把外部PromptError转ConfirmRemoveError；尚不知不同缓存/交互条件下是否会提示、失败或还原，不能写成已证数据覆盖。目录部分缺失与同时用户修改的策略也未由题面完全约定。

唯一优先CPU对照（建议未执行）：固定本题base、dvc_tail_v1配方、agent身份与本地remote，按新增missing_data_source设置一个foo内容“foo”的.dvc源及copy-foo消费者，push后移走foo和其本地缓存；远端不变。并行概念上的两个fresh复本分别为base/gold，先记录foo/bar、.dvc/cache与runs、dvc.lock存在性/字节，再调用reproduce(pull=True,dry=True)。预期两个版本均不能恢复foo、生成bar或下载run-cache；若gold恢复foo而base保持缺失，就确认gold的新dry回归。再在各自新的同初态复本用dry=False作正对照：base报缺源、gold恢复并完成，排除输入/环境未配置。保持本地remote可读，杜绝网络可达性混淆；若需要定位，可spy调用但最终判据是文件/缓存快照，不以mock数量作新oracle。同一运行入口先核sys.executable、dvc.__file__和权限，补actor缺项。不把该建议称已执行，不启动其它独立实验；B/C与mock次数仍各自保留待审。

## 5. 历史原始运行和评分/执行分开

两账本:1记录同一个派生镜像sha256:e64191bff363b956d9f4fc6f2abde42eecbcc21cbf4fe47a01b7404f942f457b、dvc_tail_v1:iterative__dvc-9395，grader rh2grader/54322、2CPU/4GiB、deny_all、PID512、shm64MiB、tmp1GiB，可写conda前缀。不是public image digest，actor是否消费此配方未知。candidate.apply_user=agent/54321只是补丁应用身份，不是solver开发证据。

- 初态：NL:132–136干净base；GL:132–204仅gold改动。projection包含dvc/repo/reproduce.py；官方只恢复两个测试文件（GL:205起、243–255；NL:203–215）并成功应用test patch，没有普通源码混入恢复。
- 安装：recipe.before/after与recipe.json显示固定pygit2==1.14.1、安装实际extras all/tests，保留安装退出码；GL:394–409、616–634和NL:354–369、576–594确认从本地wheel目录完成editable安装，install RC0。conftest确实依赖历史pygit2常量。旧安装/pygit2问题在本次grader条件中已覆盖，不是当前失败。build-backend/setuptools-scm与dvc-data等依赖仍须真实actor预备。
- 执行：GL:641–652、NL:601–612的命令都是pytest -rA tests/func/test_repro_multistage.py tests/func/test_run_cache.py，Python3.9.19/pytest7.4.4，收集30；NL完整summary:4046–4076为3失败/27通过，RC1(:4080)；GL:3626–3656为30通过，RC0(:3660)。
- 逐ID对账：来源F2P2+P2P27=29；全29在两日志出现，P2P均过；额外第30项是missing_import（NL:4074失败，GL:3644通过）。参考未缺席/未skip；这三个集合不能互换。
- parser计数：两账本num_parsed_tests均31，比实际30多1，段外0。原日志有non_existing_stage_name预期错误上下文“Could not find”（GL:709–747、NL:1750–1788），但未读/运行共享parser确认多余键来源，故只记录未解释的计数差，不虚报31个真实测试。参考映射核对未见受影响。
- 候选生效：两账本import=/testbed/dvc/__init__.py、version2.56.1.dev27+gc75a5583b.d20260919；gold diff与F2P目标差异一致；cleanup removed=true。无本轮新执行，也无重复稳定性或真实模型证据。

原始日志按初态、patch注入、安装关键行、三失败栈、目标测试captured输出、完整summary/退出定点读取；没有逐行阅读约四千行日志内每个无关P2P的debug/progress，也未审全部第三方安装包。哈希核对是整文件，内容阅读范围按上句，不混同。

## 6. actor开发需求、交付与关系

| 需求 | 公开依据 | 可复用证据/缺口 | 最小后续验证（未执行） |
| --- | --- | --- | --- |
| 核心入口与当前checkout导入 | commands/repro、repo/reproduce、Stage.run | 已定位；grader导入本源码 | 实际agent shell打印解释器、dvc/dvc_data/dvc_objects来源；真实消息与工具配置另核 |
| 历史Python/依赖/插件 | pyproject:22–67、90–109、122–140；conftest | grader离线配方成功；actor解释器/包写权限未验 | 窄collect-only及test_restore_pull，不能依赖公网pip |
| 本地数据/remote/缓存 | TmpDir、local_remote、run_copy脚本 | 少量文件均可本地生成；不需云账号、GPU、外部数据 | 实际UID对workspace/tmp/cache建立/读写/重命名，运行public_read本地CLI原例 |
| shell/Git | 新测试cp/echo；import的erepo_dir与isolate | grader这些fixture已执行；非import核心可no_scm | shell/Python/cp可用；import扩展才需Git及临时身份；不需启动SSH/Docker服务 |
| 网络四阶段 | pyproject包依赖、当前recipe；业务local_remote | 准备时需固定包/wheel；本题解题/候选安装/测试可用预置包与本地remote | actor是否能读离线资产未知；不申请不必要公网 |
| 编译/提交 | gold纯Python；pyproject backend/version；官方test paths | 无新增编译代码；源文件被投影、两测试恢复 | 无额外排除；若需要editable关联须在有权限和后端已备条件下验证；不改不可提交系统包当解答 |

dvc/testing作为普通源码提供fixture，是本题开发/运行入口之一，不能因名称含testing统一排除；但本题gold不必改它。未审平台控制面完整安全、实际镜像未来Git/缓存/挂载；静态包无.git不能证无泄漏。exp run共享_common_kwargs已定位，完整实验队列/执行器未查。无具体同题派生关系证据，不按与前题同仓库归族。本主审已见gold和隐藏材料，只用于development_diagnostic。

## 7. 八方面结论与处置

公开需求、材料/初态、全部断言/fixture及参考、合理替代路线、gold/调用者回归、开发环境需求、投影恢复边界、关系/暴露八方面均有上文记录。未知主要是实际actor、真实消息、dry/no-remote/用户修改的运行结果、精确checkout次数是否实际误拒及parser多1的身份。无必要硬造错误补丁：gold自身dry控制流已给出足够有区分力的窄实验。

暂定needs_review/static_review，development_diagnostic。与5839不同，本题存在gold引入未被参考保护的具体dry回归疑点，不能仅凭gold30过声称实现完整；同时记录no-remote风险、内部三次调用约束和import参考缺席。历史需单独开放后才能核对；前稿封存后不回写。

