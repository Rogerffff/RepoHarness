# Dask8801 首 Coder 候选与原执行非作者窄核

2026-10-03。原候选身份、操作重放和执行封包通过窄核；原正式分是 **None / infra_failure**，不能计模型失败，也不能据公开自测认定目标完成。可见诊断语义保持`needs_evidence`，待本次同原FP CPU日志与新鲜独立判定。`qualification=None`，未授自动训练reward。

本reviewer不是候选作者；复用已有Dask7656、7305、9378、7138上下文与证据核查方法，本题此真实候选首次读。只核封闭原件、静态候选和原执行；不重审29/59矩阵、不复用420裁决。没有新CPU/GPU、tests/model、SSH或Docker；没有修改原件、共享源码或模型补丁。报告仅首次写H/reviews，不向sealed closed追加。已读源码的本reviewer不冒称按v3盲判要求的新鲜语义裁决者。

## 闭包与材料

[闭包manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/gpu1003-dask8801-coder-a1_closed_manifest_v1.json) SHA `eba8b49c23fb6ff22fea8ed2cbd2cbf87ab1bf851bbac09844fb790e781dc021`；[v3映射回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/sync_receipt_v3.json) SHA `f812022ab41928264b9297358a7964294209a3925d3ce293f8180b60894d156c`。528件、52,779,768B逐SHA/size及528映射闭合；无错误。包内其他题历史只核闭合，不展开私有语义。原job为`queue_v31/results/gpu1003-dask8801-coder-a1`；另一模型arm未闭合。

[GPU owner_request](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/prepared_dask_pandas_four_code8_v1/dask8801/host_evidence/owner_request.json)与[当前题主请求](../tasks/dask__dask-8801/probe_request.json)逐字相同。实际prepared采用R16 `dask8801-behavior-semantic-v7-compat1`：[公开view](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/prepared_dask_pandas_four_code8_v1/dask8801/prepared/rollout_task_views.jsonl)的题面8563B/162CRLF，SHA `0b3ffb734d5e9f1eac09848d407b0f040913075359563f7717d5f3efb1ce166c`；[实际prompt](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/attempt/prompt.txt)8668B，SHA `da676ad7d775266c4e31d755ea6d534a8d75ff7b351484d7eff521ba7c063e7c`。[首条真实HTTP user请求](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/services_v29/coder/gateway/gpu1003-dask8801-coder-a1/requests.jsonl)逐字包含完整题面。[私有view](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/prepared_dask_pandas_four_code8_v1/dask8801/private/host_grading_views.jsonl)的test patch与[当前有效patch](../tasks/dask__dask-8801/effective_test.patch)逐字相同，SHA `a0d2794fb43dc920f7dbc00078975b9334a3040d873aa56971256f04f3dd360c`；2F+43P=45参考与actual diagnostics逐组相符。私有测试/诊断/分析没有进入公开prompt。[revision导航](../tasks/dask__dask-8801/revision.json)保留旧pending状态，实际消费依据prepared/registry/input_check，不把导航旧状态当作运行未消费。

公开要求坏YAML或非空非映射在直接加载/完整import时失败，指名坏文件并真实解释内容问题；不可读文件忽略。空/注释/null/空映射有效；其余假值非映射可空配置或准确诊断后拒绝。[v3 prompt](../tasks/dask__dask-8801/semantic_judge_prompt_v3.txt)要求逐份本次受信事实与可见异常独立判定，不能用源码/隐藏原因/控制标签補证。本报告不产生真实候选fresh语义pass/fail。

## 原FP与工具重放

原FP规范SHA **`739f20878faca8da44f55b164596413fe411b9a1054e4d9c227212bc0dabd7a1`**；FP文件SHA `74f1d11153705668c72ab331251d31d343291c35362e6230f043ee4fc3a7ef8a`。原baseline规范SHA **`aff22965ee08670e719a8ae2c026cf1f78ef93e201356921845b61ada0262aea`**。[baseline.tar](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/attempt/frozen/baseline.tar)463常规成员仅安全逐成员读、不解压执行，每件内容digest与manifest一致。基线HEAD `9634da11a5a6e5eb64cf941d2088aabffe504adb`。实际actor及grader资源绑定原config **`sha256:695d2cc28e303a0224c1109fe245f7296c6290d480124fa4fd4cc2ad072124b1`**，manifest `sha256:21e77aea7025bad694a5c600ed6d4b372c80c83bc319fafa2fedb23d9ff48483`。

[完整289行轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/attempt/trajectory.jsonl)L36 Edit→L40成功，只改`dask/config.py`；L101/123写及重写`test_yaml_fix.py`，L171写`test_realistic.py`，L193写`test_import_with_invalid_config.py`，L228写`final_test.py`，成功结果L105/127/175/197/232。L263删四临时文件，L267完成。全部Edit/Write在内存重放后精确得到[FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/attempt/frozen/frozen_patch.json)唯一生产条目20371B，内容SHA `b703567bdf999d7da1c85637596e81aa5123cccc6f82173e8f449ead135c05da`。独立解析[diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/attempt/candidate/dask__dask-8801.diff)唯一hunk应用到原成员，字节同FP；两个轨迹副本逐字相同。

最终源码L182–194把None转空映射，Mapping保留，其余非映射抛含path/type/repr的ValueError；OSError忽略不变。五假值拒绝是当前允许分支，不能据此判回归。静态未覆盖路径在L182：`yaml.safe_load(f.read())`解析错误先于新增检查，未新增YAMLError文件上下文处理。损坏YAML属于当前题目标，轨迹没有自测；这项缺口须本次CPU可见封包核，**不从源码预判真实fresh语义fail**。

[正式projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/grading/projection.json)只含`dask/config.py`，classification为projectable，private/excluded pathset未改。没有看到评分绕过、正式测试污染或隐藏材料访问。[原eval log](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/grading/eval_logs/evallog_gpu1003-dask8801-coder-a_cc10ae51.eval.log)L1091–1135显示官方test文件从固定HEAD恢复、当前patch clean apply、`RH2_SETUP_OK=1`；临时自测清理未删官方测试。

## 自测与说明

| 轨迹 | 真实范围 |
| --- | --- |
| L75→79 / L88→92 | 两原公开collect_yaml节点分别1P。 |
| L145→149 | 原公开test_config.py 43/43通过，0.12s，含两权限项；不是本次私有2F。 |
| L101→110→114 | 混合坏配置遇bool.yaml正确拒绝，打印`Test failed!`；脚本的成功期望写错。 |
| L123→132→136 | 重写为字符串文件直接入口，打印`Test passed!`。 |
| L171→180→184 | 字符串坏配置被拒绝而打印失败；前一try已return，后面的refresh没有执行。 |
| L193→202→206 / L228→237→241 | 两次新进程字符串坏配置import例打印成功。 |
| L158→162 / L215→219 / L250→254 | 正常import成功；没有损坏YAML诊断自测。 |

**[P2] 最终全面自测表述过宽。** [L285/L289最终说明](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/attempt/trajectory.jsonl:285)称43/43现有测试通过属实；`comprehensive tests`及invalid config全面获帮助性错误的概括超出证据。两脚本把期望拒绝标为失败后，验证收窄到字符串直接入口/两个字符串import例；损坏YAML、五假值两入口、13–23正式匿名诊断输入及45参考均未验证。失败脚本只是`return False`而未`sys.exit`，Bash不报错不等于自测成功；也不能把这些失败标签当候选新回归或正式评分绕过。完整目标待实际正式行为与fresh裁决。

## 原执行与恢复边界

[attempt](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/attempt/attempt.json)求解56.406s，CC L289自然`success/end_turn`、harness exit0；24turns、23工具调用（3Read/1Edit/14Bash/5Write）。24网关请求均200、无stream_error，实际model_sent `Qwen3-Coder-30B-A3B-Instruct`；输出5743tokens，输入请求合计551024tokens。宽预算10800s/240turns/196608context/65536输出请求/1024gateway requests，已见输出无预算截断。[实际服务采集](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/diagnostics/QUEUE_V31_gpu1003-dask8801-coder-a1_before/capture_receipt.json)、config与HTTP绑定一致；engine/adapter前后ID/StartedAt相同、restart0。checkpoint revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`；没有本次全权重重哈希或GPU内存权重认证。

[原正式report](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/grading/report.json)是`failed_to_grade / infra_failure / reward=None`，原因`grading_control_surface_protect_timeout_after_300s`。[diagnostics](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/grading/eval_logs/evallog_gpu1003-dask8801-coder-a_cc10ae51.diagnostics.json) trusted setup段300.509969s，control_surface/candidate/observations为null，test未开始；eval log止于恢复测试与`RH2_SETUP_OK=1`。45参考逐组null，安装/正式测试/诊断封包均未开始。[实际manager源码](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/code_v8/rh2/src/repoharness2/grading/manager.py:3436)L3436–3440将控制面保护绑定setup timeout；这是准备基础设施失败，不是候选测试失败。

实际task config无recipe/derived_image覆写，spec_builder返回原builder。请求规定原安装`python -m pip install --no-deps -e .`，本次未执行。diagnostics记录script digest `sha256:835811ced3255278f9fd36b35e68ae6deee2791ed710367d832e4d9954af67e5`、supply=null；manager L3590–3595为single-shell候选安装/测试分支，本次未启动。[原result/status](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/queue_v31/results/gpu1003-dask8801-coder-a1/result.json)确认原FP直接消费且baseline rebuild通过。

actor container/network/relay清理无残留、quiescence residual0、gateway revoked/drained且active0；grader创建1/删除1，open/supply/failures均空。terminal attention/exit3保留原infra失败。[29资源采样](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask8801-coder-a1/gpu1003-dask8801-coder-a1_closed_resource_v1.jsonl)actor峰值所见914,898,944B/pids43，grader1,619,120,128B/pids9；所见memory.max/oom/oom_kill及pids.max均0，diagnostics另记OOMKilled=false。最后过滤范围容器列表空；采样间隙未知，不声称全GPU无其他作业或所有时刻精确峰值。

同原FP/baseline/当前材料/source的运输没有发现静态阻断。已知阻断是prepare300超时；仅setup900恢复需实际采集验收。本报告未读在途CPU、未核恢复worker、不保证900足够、不套7305五键环境。后续原始行为分与诊断语义分别验收，真实可见封包交新鲜独立上下文，不能复用R16控制420结论。

仅单个首Coder样本，另一既定Qwen arm未知。普通薄探针没有正式训练actor、miles receipt或训练消费接线。原None保留，未来环境恢复或行为1也不自动授qualification/reward。后续报告另存，不覆写本次或GPU原件。逐证据SHA与字段见[non_author_8801_coder_a1_candidate_review_20261003.json](non_author_8801_coder_a1_candidate_review_20261003.json)。
