# EA69 R17 Coder：原候选的有界 CPU 边界诊断

2026-10-03。原 Coder `gpu1003-coverageea69-r17-coder-a1` 的 **49/49、raw reward 1 保持不变**。CPU-A 原候选窄验实测：正常内容、正常 CSS 名及重复生成均能忽略报告；三个特殊 CSS 文件名在首次与再次生成后均未被 Git 忽略。合理 `safe_append` 对照在相同场景全部通过。当前49键没有覆盖这些实际生成文件，需补最小验收；这不是空行或文本幂等的新要求。

## 实际执行与范围

作业 `covea69-r17-coder-boundary-cpua-20261003-01` 于13:50:57–13:51:09 UTC占用CPU-A slot0，finished/rc0。固定CPU镜像 `9877b37b…`，沿原来源、base与配方；GPU原镜像 `e23fbbed…` 单列，不声称两镜像ID相同。实际UID/GID54321、Python3.7.9、coverage6.1a0、Git2.34.1；2CPU/4GiB/512进程、无网络、无挂载。该作业没有模型求解、正式重评分或重跑旧七候选矩阵。

上传原GPU闭批`baseline.tar`、manifest和完整FrozenPatch。三个对照均先恢复360文件并逐内容SHA/执行位核对；原候选只按FrozenPatch覆盖`coverage/html.py`，最终内容SHA `631eb6014e4b3a3f2a2c88d105acfc3597a0cce4c5778436ec1051c1bd9035fb` 与GPU原件一致。私有`safe_append.patch`保持SHA `4049a09d…`。只增加诊断输入，没有修改候选、原任务面或评分材料。

共21个“对照×fixture”、44次HTML生成：baseline3场景，safe_append9场景，原候选9场景。每场景生成两次，repeat_three生成三次。每个fixture独立初始化Git，隔离系统/用户配置，以`check-ignore --no-index -q`退出值判断，并保留`-v`匹配依据和完整`git status`。coverage使用公开固定两行样本及`timid=True`，不是全项目回归或正式runner。

## 对照结果

| 场景 | 原候选 | safe_append | 解释 |
| --- | --- | --- | --- |
| 正常两行用户内容 | 两次全部报告文件被忽略 | 相同 | 正常正控制通过，评论/custom.tmp规则保留 |
| 空行/CRLF | 全部报告文件被忽略；空行被删除、CRLF归一 | 全部报告文件被忽略；原前缀保留 | 格式差异，不能据此新增逐字节相同要求 |
| 原style.css规则在否定规则之前 | 全部报告文件被忽略；原非空行顺序被改写 | 全部报告文件被忽略；原顺序保留 | notes/style.css初始不忽略、两种修法后来都忽略；追加*也覆盖该例外，不判原候选独有Git失败 |
| 无末尾换行 | 两次全部被忽略，规则分行正常 | 相同 | 没有拼接坏规则 |
| 连续三次生成 | 三次全部被忽略，*.html计数1/2/3 | 三次全部被忽略，追加块也增长 | 重复文本是质量观察，不要求文本幂等 |
| extra.css | 两次全部被忽略 | 相同 | 正常extra_css正控制通过 |
| !custom.css | 两次该生成文件未被忽略 | 两次全部被忽略 | 原候选把文件名写为否定规则 |
| #custom.css | 两次该生成文件未被忽略 | 两次全部被忽略 | 原候选把文件名写为注释 |
| custom[ab].css | 两次该生成文件未被忽略 | 两次全部被忽略 | 原候选把字面文件名写成字符类模式 |

baseline三场景均有生成报告文件未忽略，作为初态负控制。safe_append9/9场景通过，原候选6/9场景通过；这是本轮边界诊断分母，不能替换原49键评分或计算新模型成功率。用户两个附加文件的内容SHA在全部生成后均未改变；格式/顺序观察与规则语义分列。

## 材料结论与后续

特殊文件名是本轮先行边界诊断，现已具有实际证据：现有公开`extra_css`参数成功接受文件、生成报告并复制目标CSS；Git两轮都不忽略该生成文件。这直接违背已公开“所有生成报告文件被忽略”的目标，不依赖逐字节保留或文本幂等假设。现行R17的`test_2_preserve_v1.py`仅正常名与简单原规则，原49/49准确反映现行fixture，但不能代表完整公开目标。

最小补验收应只增加真实Git的字面extra_css文件名场景，并保留正常extra.css正控制、合理safe_append及原候选反例。公开目标、源环境、原FP不变；空行/CRLF/已有规则顺序/文本增长不变成新的评分门槛。未发布任何新评分材料，未追改原分数。新Qwen沿原claimed请求继续；回传后可对原FP补验收，无需重复求解。无关GPU继续。作者结论待非作者针对本轮原件核查，不复审全部旧轨迹。

作业退出0，自有容器已移除且label回读为空，共享镜像未清理。21份原件/4,667,553字节已全SHA回收；当前无本题CPU在途。完整身份、逐场景Git证据和归档引用见[作者JSON](candidate_boundary_r17_coder_cpu_author_20261003.json)及[闭批归档](../../../../../../../../../../runs/category2_repair_20260929/coveragepy_owner_cpu/ea69_r17_coder_boundary_cpu_v1/archive_receipt.json)。本轮不授训练资格。
