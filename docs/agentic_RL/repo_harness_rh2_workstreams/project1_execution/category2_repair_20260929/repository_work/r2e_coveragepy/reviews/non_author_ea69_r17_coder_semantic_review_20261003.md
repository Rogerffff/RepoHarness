# EA69 R17 Coder a1 非作者原件与语义核查

2026-10-03。**原件、正式评分和运输核查通过，原reward1（49/49）保留；候选未完整满足广义公开内容保留目标。** 常规已有两行内容及两次生成后的真实Git检查实际通过；空白/换行/同名规则保留和特殊CSS文件名仍有源码可见缺口或待实测风险。不能把49键成功写成全部公开语义正确，也不能直接把这个候选缺口判成整题材料或环境不可运行。

范围仅`gpu1003-coverageea69-r17-coder-a1`，材料R17、073–075+093。本核查者已经接触本题私有评分与旧候选，不是fresh public reader。只读本地原件并做SHA、归档内存解码、diff内存回放和固定纯parser重放；没有运行项目测试、目标实现、SSH、Docker、模型或安装。旧报告与原件不回写。全部引用的路径、SHA、工具输入及结果定位见[JSON](non_author_ea69_r17_coder_semantic_review_20261003.json)。

## 三层判定

1. **正式分成立。** 闭包506文件、48,458,118字节逐项一致。固定parser SHA`339b7c80…`从原eval完整测试段独立产出49个PASSED键，与expected、执行回执逐键完全一致，无缺失/多余/状态差异。原footer为`49 passed in 1.27s`，testRC0、entryRC0、harness0、非infra。install明确SKIPPED且RC为null，不能写成安装成功0。
2. **常规目标已实测。** 同SHA评分fixture实际运行真实Git：新报告被忽略；既有内容`# User-owned rules\ncustom.tmp\n`在连续两次生成后仍完整包含，报告产物均不被Git枚举。现行测试明确排除`.gitignore`本身，不据此追加新的验收要求。
3. **完整公开目标仍有候选缺口。** R17实际prompt明确要求保留用户已有内容并确保再次生成仍被Git忽略。源码的文本过滤/重写不能完整保留任意内容，特殊extra_css模式未经转义。现行49键不足以核销这些边界，属于候选质量缺口和疑似评分覆盖盲区；边界目标运行尚未完成。

## 实现与语义

原基线HTML路径没有创建`.gitignore`。候选仅新增`HtmlReporter._create_gitignore`并在静态文件/extra_css复制后调用。列举五个静态文件、index、status及extra_css basename，用`*.html`覆盖按flat_rootname生成的页面；每次成功报告都会调用。去除新增方法和调用后AST与原基线相同，无数据异常路径保留。

候选`coverage/html.py`第225–244行用`r`文本读取、`splitlines()`，过滤空白行以及strip结果与生成文件名相同的用户行，再以`w`写入LF连接的新内容。源码直接可证空行被删、CRLF归一、同名规则被移除再排序加入；正常两行fixture通过不能证明任意用户内容保留。第229–240行保留旧`*.html`后再次追加，该规则逐次增长；这是质量观察，文本幂等没有在本轮变成新硬要求。

第206–207、235–236、279–280行把extra_css basename原样写为Git模式。`!custom.css`、`#custom.css`、`custom[ab].css`等合法文件名可能成为反向规则、注释或字符类模式，而复制出的CSS仍是原文件名，不能确保被Git忽略。这是依据配置/复制/规则路径的静态推导，本轮没有这些输入的真实Git或目标运行；不得写成已观察失败。常规extra.css和现行preserve fixture未覆盖该边界。

## 工具轨迹与测试控制

完整363行轨迹有29个工具，Bash19、Read3、Edit4、Write3；每个tool_use都有tool_result，3次is_error，无工具超时。生产源码只改两次，之后没有生产修正。三次失败均需区分：

- L149自测用exec字符串，实际无可报告数据；改为导入并调用真实文件后成功。这是自测设置问题。
- L219的preserve自测把已有`.gitignore`写在临时根目录，报告却在htmlcov，fixture目录错误，不能作为正确输出目录的候选反例。L232后继只打印新文件，没有修正并重跑已有内容/再次生成，因此模型后来宣称完整保留超出开发证据。
- L293要求动态页面文件名直接出现在规则文本，忽略了`*.html`表示。L306改为静态文件名和glob子串是合理格式调整，不自动判作弊；但子串存在不证明Git真实忽略。

公开验证包含1、1、5、7、10项重叠运行，最后完整HTML46点与test_report3点成功。末两次qq返回没有summary footer，46/3依据完整点数与公开源码集合；不虚构终端摘要，不把重复运行相加成独立项。三个临时自测脚本没有真实Git，也没有有效的保留/再生成回归。

原FP只有`coverage/html.py`一项，内容SHA`631eb601…`、regular/100644，没有`tests/test_html.py`或其它tests、runner、fixture、conftest改动。临时`test_gitignore.py`、`test_existing_gitignore.py`、`verify_fix.py`均删除，没有进入FP；baseline既有install.sh/run_tests.sh不是模型新增。评分trusted setup恢复并保护原评分树，只应用原FP源文件。未发现候选评分控制或助手遗留污染；排除路径集变化如实保留，不宣称运行环境完全未变。

## 交付、身份与往返

solver_prompt与attempt/prompt、prepared base prompt加未改brief的公式精确一致，SHA`19aa60c7…`。首真实网关请求一个user text精确含全新statement和brief；statement SHA`39b6b28a…`、brief SHA`475e3ee6…`，没有gold、私有候选或私测泄露。Coder没有执行compat命令，因其open未传encoding，原公开替身可用；R17 CPU的encoding marker+46项compat证据按版本复用，不计作此次模型工具调用。

公开bundle`53deb1de…`、环境`8fb9b7e1…`、私有评分`46de14f5…`，base`7fd1ea39…`；实际GPU actor/grader镜像为`e23fbbed…`，配方`85b488e5…`、hidden树`d9860e3e…`、runner`8285765f…`、expected`b3482977…`一致。与CPU-A镜像`9877b37b…`按source/recipe/material兼容证据复用，不能改写成同一镜像ID。CC2.1.205、agent UID54321，解释器/testbed导入与预检通过；Python3.7.9、pytest6.2.5、coverage6.1a0、pip无模块。

原FP canonical`591da512…`、基线canonical`7d9fea8c…`独立重算匹配。baseline.tar为4,198,400字节、360文件，逐内容SHA和Git模式核对通过；install/run原POSIX0664对应非可执行Git100644，不称逐位0644。5212行原基线census与grader重建逐字节相等，排除路径运输往返成立。审阅diff在内存应用到原基线后精确得到FP内容；diff供审阅，实际评分输入仍原FP。

actor停止/静止屏障残留0、gateway revoked/drained且active0、容器/relay/网络label残留空；grader created1/removed1/open0、无cleanup failure。原件完整无partial，stderr空。闭包只核当前Coder终态，不核销另一模型。

## 预算、消耗与用途

实际Coder为Qwen3-Coder-30B-A3B-Instruct，固定revision`b2cff646…`，BF16/TP1，采样0.7/0.8/top_k20/repetition1.05、reasoning_parser null。actor/grader code_v8、adapter code_v4、gateway services27；没有宣称整个运行树同版。依据保存的实际runtime配置/HTTP读回及只读模型挂载，不重新逐SHA全部大权重文件或核显存内容；gateway checkpoint_identity_verified原false及code_snapshot_id、grading_materials_identity原null、qualification absent保留。

probe-wide-v1为196608 context、65536输出、240回合、10800秒、1024请求、first_byte1800秒、adapter_idle14400秒；grader whole3600/setup300/apply120/test1800秒。30次生成请求实际max_tokens均65536，CC modelUsage的32000元数据不能替代wire实值。30次生成+1次count_tokens均HTTP200，累计input800415/output6971、cache0、请求输入峰33583/响应输出峰914；累计输入包含重复上下文。solve72.704秒、CC wall69.149/API60.668秒、gateway生成响应累计59.993秒、actor开始至清理135.291秒。CC非API残差8.481秒不是纯工具时间，gateway时间不是纯GPU推理。CC别名估价4.17635USD，未核账单。

14份有限资源切片中只取本题实际容器：8个actor样本所见memory.peak最大1,152,385,024字节、pids.peak23、OOM0；3个grader样本134,008,832字节。后者与正式grader峰值347.699MB不同来源/采样范围，不互相替代；采样间隙未知，共享GPU读数不归因本题，不称196K峰值已实测。

本结果可用于R17 Coder首臂版本化普通基座诊断、原分记录及质量分析；不授完整语义正确或训练资格。旧R6矩阵只在固定私有payload/source/recipe/runner范围复用；旧公开缺项Qwen不与此臂配对。新R17 Qwen尚无本范围回执，请求继续等待，不作pair ACK、不自行追加采样、重评分或取消在途。

题主已备未提交候选边界计划：保留本次原FP/基线，定向比较普通内容、空行/CRLF、已有静态规则、无末尾换行，并对特殊CSS逐产物查真实Git状态及再次生成。该窄验对判断是否补验收有必要，但本报告没有启动CPU/GPU，也没有改题面或评分。独立核心判断完成后比对作者draft，三层结论和轨迹解释一致；作者派生记录未替代原件。

## 主要证据SHA

| 引用 | SHA256 |
| --- | --- |
| `closed_manifest`（完整路径见JSON） | `89cc9350a26f8b0892964046bac6d7478299c31e9dabbe14f82b507909ebe3da` |
| `execution_receipt`（完整路径见JSON） | `cc298ce986d4c0ab4f34be0b2767560e324bd8c15f55d80c12f58d36ce024e22` |
| `frozen_patch`（完整路径见JSON） | `85c2211228edd88e9012924fc118c7e3cc1e814859a6b3ac2cda26d86367e388` |
| `baseline_tar`（完整路径见JSON） | `2138be5b5c3d196c08bfaeb4d46dc51a8c1018895eab712aec977c28bdb8c64a` |
| `baseline_manifest`（完整路径见JSON） | `fc422c66fa64f59a4038aa0f2ae76cd1b5b21dcd2176b412d0d501eaa09fe259` |
| `trajectory`（完整路径见JSON） | `356e9b596e5aa57eb6aca6c5ff65df26c060cb7bf11def1568e4cb6c21f9a3f3` |
| `solver_prompt`（完整路径见JSON） | `19aa60c71f97c59184b24f99cccdfee77fa7745bc201e7e7bd67066259f05d24` |
| `eval_log`（完整路径见JSON） | `6d6fec8c395686bc5d8a906aa77fe619bdbd2e182e5559310cec9b04bfa9d63f` |
| `grading_diagnostics`（完整路径见JSON） | `b7c0f731281c5f421cd47d6cc542acbbc241fb57059c6a1f36da352f3377ce6e` |
| `gateway_requests`（完整路径见JSON） | `fea9a5e19a46337089381cf667562953979a596f4970b85d304c0bd1735793b6` |
| `result`（完整路径见JSON） | `4c7c6aa2f21bb21cb0ac7b7cdd37deb67a8061a8ed6af221a48787c1bacc1266` |
| `author_draft`（完整路径见JSON） | `fa44cb129abb608fe58c6b9a971ddae3e6077691ae84376d46fb045315f8cd12` |
| `boundary_plan`（完整路径见JSON） | `8144bea096177d244b54f8aba2ac73c59ace23651c53ee2e0be105635242977e` |

其它所有引用SHA、完整49键、29工具输入/结果行号与结果内容摘要身份均在JSON固定。
