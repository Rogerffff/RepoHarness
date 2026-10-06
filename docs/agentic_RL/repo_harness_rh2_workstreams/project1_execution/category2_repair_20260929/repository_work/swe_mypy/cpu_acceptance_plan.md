# mypy CPU验收与探针交接

2026-10-03 21:33更新（Asia/Singapore）。两题正式CPU矩阵及非作者核查完成，10174原GPU候选的可读wheel窄复验r16已收口。15184两模型首轮实际交付、候选语义与执行观察现已[验收](python__mypy-15184/two_model_first_round_acceptance_20261003.md)，总账returned/ack并清空活动请求，无新增CPU/GPU作业。当前本包无CPU待办或在途；10174原候选新GPU安装/四参考重评分现已[验收](python__mypy-10174/new_GPU_regrade_acceptance_20261003.md)，新增Coder首轮及[两模型题级验收](python__mypy-10174/two_model_first_round_acceptance_20261003.md)完成，总账returned/ack、活动请求清空；无本包CPU/GPU待办。

## 10174：保留已完成验收

第六版实际结果为noop0、gold1、关闭非strict-optional比较诊断的负对照0。四个参考均实际执行和解析，缺席、跳过及未计入参考的执行键均为0；已核安装、源码来源、测试恢复与保护、候选投影、runner完整性及清理。依据为[新矩阵作者回读](python__mypy-10174/revised_cpu_readback_20261003.json)、两份非作者报告及[普通探针CPU条件收口](python__mypy-10174/cpu_probe_acceptance_20261003.json)。

原请求`swe-mypy10174-strict-equality-v1-20261003`和SHA保持不变。GPU方完成消费者兼容冻结及实际派发；题主不因共享新版部署重跑CPU或重复提交。GPU intake不是模型结果，当前未授予训练或留出资格。

本轮Qwen3.6已正常完成，原raw1、四参考及清理原件保留；新问题是GPU派生镜像`32f313…`的editable安装实际Permission denied/RC1，后续pip pytest使段末命令RC0；旧builder明确chmod0600且COPY未改权限，可解释该失败，但旧运行未捕获wheel实际stat，不能将静态构建证据当运行实测。见[安装缺陷记录](python__mypy-10174/gpu_install_issue_20261003.json)。这是当时的安装缺陷快照；后续恢复及Coder实际新镜像结果另记，旧安装失败不改。

窄复验沿cpu-a已验的同source digest、同三wheel SHA且可读的`9d63…`镜像，消费原FP/完整baseline manifest，保持49个cache和50路径正式projection。正式manager重建基线后以UID54322逐条执行原三条pip命令、记录真实rc，核meet/build/checkexpr来源/源码SHA，然后原正式脚本再评分四参考。前置安装是额外窄验，会预热环境；正式eval.log不单独冒称fresh安装。模块probe在前后独立Python进程，不是pytest内跟踪。原FP/runtime、候选与旧GPU成绩不改绑。最终r16唯一有效原候选重评分得1，四参考实际执行/解析且缺席/跳过/段外均0；前置三安装各RC0，正式安装失败列表为空，1建1移无遗留。12次75及r3/r8/r15的owner失败原件保留，r13误通知已更正，均不计候选成绩。安装前已有相同editable元数据，成功安装依据两轮真实pip构建/安装日志；resource_facts为空，包版本仍?，不声称新增HostConfig实测。作者与两非作者核关键原件后的[新收口](python__mypy-10174/gpu_install_revalidation_acceptance_20261003.json)已完成，停止扩跑。GPU实际80418df…可读层已核双UID读取、不变性及清理，见[补证](python__mypy-10174/gpu_identity_and_wheel_supplement_20261003.md)；新GPU原候选完整安装与四参考重评分现已[有界验收](python__mypy-10174/new_GPU_regrade_acceptance_20261003.md)，本次无新模型样本；原请求后来两模型首轮均齐并由题主收口，旧原件和CPU事实不回写。Q12有限运营来源归因另记，不回写旧checkpoint false。旧32f不再新派发；无需旧矩阵或模型重解。

## 15184：正式四候选验收完成

发布请求`swe-mypy15184-nested-v2-publish-20261003`的实际回执已回读，依据见[发布验收记录](python__mypy-15184/publication_readback_20261003.json)。R10 manifest`00ac5c…`、cpu-a950成员/48+216可信读回、grading`3a3c4e…`及environment`de06cc…`均绑定。消费者实际`derive_test_command_for_bundle`精确选五node；vendor元数据前缀仍保留原-k，不把元数据字段误认成实际测试命令。只检查新版本增量，不重做未变的历史审查。

公开bundle摘要必须对应fresh审查输入`77b85678b3f20ef5689e4a9b646518ae1247407ff44b250803563c11dce3ea7e`；有效nested_v2补丁摘要为`e6d5eb0ef39aeeb08a945d3ce6aeb340a7f8b4fd56e599247dbef3b99bf4e532`。base没有`check-assert-type-fail.test`，该文件由官方补丁创建；新有效补丁保留原三case正文，仅追加一个嵌套F2P。不能把它当作base已有文件恢复。

两题已恢复11份去重wheel并核历史SHA，见[资产记录](install_assets_20261003.json)。15184沿固定base digest、9个wheel和COPY-only派生配方，实际CPU镜像ID为`sha256:76b5b2646a9eb134e6349ee8e214bb84eb6030c34a234e167351acdec5dd8c54`。这些pins不是完整依赖锁，仍需核本次安装、解释器、/testbed源码、HEAD和dirty初态。

| 候选 | 原材料实测 | R10新材料实测 | 实际触发的行为 |
| --- | --- | --- | --- |
| noop | 0 | 0 | 三个F2P失败，两个P2P通过 |
| gold | 1 | 1 | 五参考全部通过，顶层/嵌套消歧正确，有效断言继续成功 |
| gold＋全部assert_type报错 | 1 | 0 | 仅新增有效断言P2P失败，正确的int/Literal断言也被错误报告 |
| 仅顶层类型名限定 | 1 | 0 | 仅新增嵌套F2P失败，仍显示List[C]/List[C]而非List[a.C]/List[b.C] |

原正式四候选每项执行/解析三参考，见[原矩阵证据](python__mypy-15184/original_cpu_readback_20261003.json)。私有窄验只证明新case区分base/top_only与gold；always_reject也能通过该失败case，因此必须同时保留有效断言P2P。首草案小写list造成gold失败的原件保留；v2依据公开base的suite配置改为List，见[校准证据](python__mypy-15184/nested_guard_cpu_readback_20261003.json)。

正式参考为原F2P2/P2P1＋新增嵌套F2P1＋已有`testAssertType` P2P1，共五键、F2P3/P2P2。节点含.test文件层。另四项开发case及actor控制检查的六项公开case不计入正式参考。`-k`子串不能使更多case被悄悄执行后混算；分别核收集、实际执行、解析、参考外执行和缺席/跳过。

本次通过cpu_slot首次获槽，使用`runtime_cpu_v2`及R10冻结源码，在远端新建prepared。四候选在一个作业内串行，grader实际UID54322、2CPU/4GiB、deny_all；各候选和grader共八个容器正常移除，open/supply/cleanup failures均空，所有CLI、slot和wrapper退出0。未重跑未变的镜像准备、actor控制或历史矩阵。

已保存并核完整安装输出、命令边界、失败ERR trap和阶段完成记录；实际editable安装为base对应1.4.0+dev，源码来自/testbed，runner前后摘要一致。冻结日志没有每条成功安装命令的独立数值rc，ledger包版本仍为`?`，不补造证据。负对照均因预定断言真实失败被拒，没有安装/补丁/未执行或解析缺失。原件包含源码投影、测试保护/恢复、清理、driver和slot退出码及全部输入SHA，见[作者回读](python__mypy-15184/revised_cpu_readback_20261003.json)；归档SHA`c7f4f34886a1284f185092fa8a4dd5ac702d0177e0e92240d349c5f2eecaa9e9`。

## 公开交付与增量收口

15184公开新例在base/gold和真实CC控制路径已复现；有意构造的类型不匹配在gold仍应退出1，只需将C/C诊断正确限定为a.C/b.C。helper退出0不替代真实mypy退出码。

固定公开输入的fresh静态审查已通过，字节未变则复用。旧真实CC控制prompt只证明开发命令入口；现15184两模型首条solver任务block已逐字节核实，SHA `2efeb37e86cb65e228a92d9623c73c31286bf5eaccacbff2935def2bd75ec8de`，实际含新版题面/中性brief。私有测试、gold、负对照及审查仍只在可信评分/审计面，不能由控制入口推导真实交付。

正式五参考矩阵完成后，两位非作者已独立回读15184新增原件、消费者变化和版本身份，分别形成[运行链增量报告](reviews/non_author_15184_r10_execution_trace_20261003.md)及[反证增量报告](reviews/non_author_15184_r10_falsifier_20261003.md)，没有新增finding。两角色已见gold/私有上下文，非fresh；旧报告仍按10174请求固定SHA保留。题主核关键原件并写入[CPU条件收口](python__mypy-15184/cpu_probe_acceptance_20261003.json)，其SHA为`2d02acc3f7a079f019c869d31ce7edb54d9ab07149ee323e57216a0713bf0c18`。该收口只具备普通GPU intake的CPU条件，不授予训练或留出资格。

15184[独立GPU请求](python__mypy-15184/probe_request_20261003.json)`swe-mypy15184-nested-nominal-v2-20261003`的固定SHA `623bc39612a9812e92b3c5ec218480e916e3c4dae219c4e4f17d7e85056e993e`不变，两模型各1次、预算`probe-wide-v1`均完成。题主已核两臂实际镜像、公开交付、安装、五参考、原FP/投影及语义并合并非作者审查，见[配对收口](python__mypy-15184/two_model_first_round_acceptance_20261003.json)。Q13运营来源40请求与Coder实际服务25生成均支持有限归因，精确GPU驻留权重身份仍未知。总账request revision5已ack，task revision13活动请求清空；无新增CPU或本题GPU作业，普通追加采样按覆盖优先暂缓。原10174请求、SHA及旧原件不变。

请求returned后先核原始回执，再按总账revision执行ack及清空活动请求。发布回执不自动消除CPU评分缺口；模型成功或失败都由本线程继续分析、必要时修订并重新固定材料。排队、raw reward及CPU环境通过均不代表题目完成或获得训练资格。
