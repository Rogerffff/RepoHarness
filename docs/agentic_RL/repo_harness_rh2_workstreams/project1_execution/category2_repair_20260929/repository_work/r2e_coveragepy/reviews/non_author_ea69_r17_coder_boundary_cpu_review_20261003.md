# EA69 R17 Coder 原候选 CPU 边界非作者核查

2026-10-03。**新闭批证据核查通过；三个特殊extra_css文件名已实测证明原候选遗漏“所有生成产物被Git忽略”的公开目标。** 原R17正式49/49、reward1保留，常规六fixture通过；格式观察不自动变成新硬要求。新增单方法验收草稿范围合理，safe正控通过、原FP与基线预期失败，但尚未正式发布，也没有重算完整50键评分。

本核查者已有本题上下文，不是fresh public reader。只读本地新闭批及固定源材料，核SHA/bytes、归档和结果一致性；没有启动CPU/GPU、Docker、SSH、模型、项目测试或重评分。完整引用与SHA、逐fixture/逐轮观察见[JSON](non_author_ea69_r17_coder_boundary_cpu_review_20261003.json)。没有重审旧506件。

## 原件、环境与真实Git

边界job `covea69-r17-coder-boundary-cpua-20261003-01` finished/rc0，21文件、4,667,553字节逐SHA/bytes通过；输出tar内4份结果与保存文件逐字节一致。CPU-A实际镜像9877b37b…，2CPU/4GiB/512、network none、无mounts。root只负责复制/采集，探针及Git实际UID/GID54321、Python3.7.9、coverage6.1a0、Git2.34.1。诊断从GPU原360路径baseline恢复三臂，每臂逐SHA/可执行位验证，单独Python进程从各自源码树导入；原FP、baseline tar/manifest与GPU闭批逐字节一致。候选html SHA631eb601…，原FP文件85c22112…、canonical591da512…，候选未经修改。CPU/GPU镜像ID及Git版本不同，适用性按既有固定source/recipe证据复用，不称同一镜像。

runner调用真实git，固定cwd与隔离系统/全局excludes；`check-ignore --no-index -v`仅保存解释，`-q`返回0才作为ignored真值，避免把反向规则verbose输出误判为忽略。路径通过参数数组和`--`传递。每轮独立保存`git status --porcelain --untracked-files=all`，失败CSS在状态中确实出现。源码样本用真实文件路径compile/exec并启用timid收集，各轮coverage100，产物存在；不存在无数据假失败或字符串冒充Git检查。所有stage的b64/text/SHA、quiet状态、generated集合及聚合布尔值一致。

诊断只查顶层生成文件，排除`.gitignore`与预置用户custom.tmp；此报告的CSS/静态/页面/status都在顶层。notes/style.css是用户子目录观察，不计作生成产物。job rc0说明记录完整，不等于候选所有fixture通过。

## 实际边界结果

| 臂 | fixture／生成轮次 | 所有生成产物被忽略 |
| --- | --- | --- |
| baseline | 3／6 | 0/3，预期负控制 |
| safe_append | 9／19 | 9/9，每轮通过 |
| 原Coder FP | 9／19 | 常规6/6通过，特殊CSS3/3失败 |

总计21个fixture-arm、44次生成、370个生成路径/轮次检查，不能称21条正式评分测试。候选`!custom.css`、`#custom.css`、`custom[ab].css`各两轮都只有对应输出CSS未被忽略，quietRC1且gitstatus列出`htmlcov/<name>`；其余当轮产物ignored。safe使用同一配置和样本，三种特殊名每轮全部ignored。原实现把basename当Git模式，分别变成反向规则、注释或字符类模式，既有静态风险现已得到目标运行证据。

这是现有公开extra_css配置允许的合法路径，复制成功后文件就是报告产物。R17 statement已经明确要求所有生成报告文件被Git忽略、再次生成仍保持；因此属于候选实际行为失败和现行49键覆盖缺口，不需要另加格式要求才能成立。

空行/CRLF归一、原非blank行顺序变化与重复`*.html`在本批确实可观察，但仅记为格式/内容观察，不自动追加逐字节保留或文本幂等硬要求。existing_static_order中notes/style.css初始未ignored，safe/model之后都ignored，用户文件字节均不变。safe追加`*`本就覆盖该例外，不能判model独有行为失败。常规已有内容和无末尾换行的报告忽略均通过。

## 新验收草稿的独立检查 addendum

`test_2_generated_css_v2_draft.py`仅新增`HtmlGitignoreTest.test_generated_extra_css_literal_names_are_ignored`，删除该方法后的AST与旧test_2一致；草稿和CPU实际输入逐字节相同。`expected_generated_css_v2_draft.json`完整保留旧49键状态，只新增该方法PASSED为第50键。

新增方法循环普通extra.css与三种特殊名，各用独立输出目录和普通已有两行.gitignore；成功收集覆盖后设置现有extra_css，核复制文件存在，逐生成产物调用真实quiet check-ignore，重复两次。它不检查`.gitignore`文本格式，不限制`*`、转义、append、encoding等实现选择，也不新增字节/幂等标准，属于公开目标的最小行为补验收。

criterion job `covea69-r17-coder-criterion-cpua-20261003-01` finished/rc0，27文件、4,372,188字节逐SHA/bytes一致，输出tar8文件与保存结果一致；同CPU镜像/资源/UID，清理无残留。safe方法rc0，走完4种文件名各2次生成；原FP rc1，在`!custom.css`首轮quietRC1断言失败；baseline rc1，在普通extra.css场景的coverage_html.js未ignored处失败。失败原日志明确是行为断言，不是收集或infra；safe日志是成功点数和rc，不虚称有完整summary footer。

单方法遇首失败停止，所以不能说此单方法为原FP跑完#/[案例；三种特殊名每两轮反例来自前面的独立boundary记录。本轮只运行新增方法三对照，**没有运行完整50键正式评分或验证新发布后的grader镜像/隐藏树身份**。

## 当前用途与最小后续范围

支持将该草稿和expected50正式登记为新的不可变评分材料版本，绑定新test_2/hidden树/expected及grader消费身份，并按新增方法和材料消费做窄验。现有public statement已经覆盖目标，可以保留；runner与旧49要求不需为候选改写。新材料未发布前不能称50键评分已验证，不回写原R17分、不用修过的候选替代原FP，也不需重跑旧506件和全部历史CPU矩阵。

本报告确认的阻断是“完整公开目标/完整验收已核销”的声明仍不成立，不是任务环境不可运行。保留原49/49、raw1及旧报告；新Qwen继续按已有请求等待回执，不自动取消、作pair ACK或停发无关GPU。不授训练资格。

两个jobs、探针均正常退出；诊断stderr为空，容器finally remove成功、job label残留0。shared_images_untouched是原runner限定操作范围及cleanup记录，未扩展成全机镜像审计。既有R17源/配方/公开交付/原49正式通过按先前报告复用，本轮没有重新审其全轨迹。

## 主要SHA

| 证据 | SHA256 |
| --- | --- |
| `boundary/archive_manifest.json` | `01a91a190ea1d480b9bbac4eacad131bfe04a63d0ceb5faa5d4f4e4d0b6a70f2` |
| `boundary/inputs/boundary_probe.py` | `b1a19d8535035f91ead2be9c9cb29dceb1cfbd17f28e01e34a57246a508d2c6f` |
| `boundary/cpu/results/original_coder.json` | `b2f261bed5723f38db42dfd7ffdfe14c2821a43be71ef9149a3fbd80c1240056` |
| `boundary/cpu/results/safe_append.json` | `bc05c755c4a20acd8e64b301e319d701667518fe308450fb56c56eaa65ba2fbf` |
| `criterion/archive_manifest.json` | `bcaac4061ea193079f28fb00e7eafe20e60955953bced72a8d61691e7133770d` |
| `criterion/inputs/criterion_probe.py` | `eabf029c19368c1450ef1de2d790537f9cd016dc4fbcff10d3f74c13d7780fb4` |
| `criterion/cpu/results/criterion_validation.json` | `790a08f6bb2533cc715058b032f5fe865dde65aaf3562f284c0b3325513d6c7b` |
| `criterion_draft` | `4ff56808d8b38aa22242e8d28f4b7fe00160729bd8f7f3ad4ac33b2e7f82b9f3` |
| `criterion_expected_draft` | `7d70216586c39e2f98457b9b2cce26931325305d20a0ece2253a8d9dc80fc950` |
