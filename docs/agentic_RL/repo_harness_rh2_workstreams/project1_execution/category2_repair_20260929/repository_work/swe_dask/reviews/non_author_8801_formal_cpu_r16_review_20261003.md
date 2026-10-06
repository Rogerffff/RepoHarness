# Dask8801 R16 实际正式 CPU 与新鲜结果绑定：非作者复核

复核日期：2026-10-03（SGT）。本轮范围复核通过，未留存本次实际结果的阻断项；`gr_csafe_loader` 的固定 fixture 解析器待核项已关闭。结论适用于 `dask8801-formal-cpu-c-20261003-v2-q01`，修订为 `dask8801-behavior-semantic-v7-compat1`。

本轮独立重算实际行为、验证新鲜裁决出处及结果绑定，并未重新裁定自然语言或授训练资格。来源准备与当前公开 actor 的[既有 188 项报告](non_author_8801_current_public_actor_r16_review_20261003.md)及原件保持固定；本报告新增正式 CPU 的完整 29 行范围。机器可查的逐项断言、身份和引用见[本轮 JSON](non_author_8801_formal_cpu_r16_review_20261003.json)。

作业于 `2026-10-03T04:00:22Z` 自然结束、rc0。运输清单 306 件、7,202,870B，无排除；已逐件重核 SHA256、大小、路径唯一性、非 symlink 与目录闭合，并将清单、queue、state、run、ledger 和对应 eval log 精确绑定。所有消费原件均属于清单，固定本地配置与封存 v2 payload 相同，来源设置 300s、执行 120s、测试 1800s，qualification 保持 `null`。未从本机新增 CPU、Docker 或 SSH 调用。

全部 29 行都实际执行 `python -m pip install --no-deps -e .`，安装 rc0，测试段完整，候选命令无失败，清理均记录 `rm:ok` 与 removed=true。测试失败 rc1 保留为行为结果，不包装成安装故障或运输故障。每行都有原 2F + 原41P/新增2P 的45个唯一参考，共 1,305 个参考状态，1,294 pass、11 fail、0缺失；原始行为分重算为20行1、9行0。冻结测试 patch、真实安装/测试段、有效 grading 及受信 setup 身份均对应固定输入。

| 候选 | 通过参考 | 原始行为分 | 新鲜裁决条数 | 最终诊断状态 |
| --- | ---: | ---: | ---: | --- |
| `noop` | 44/45 | 0 | 0 | 行为失败 |
| `gold` | 45/45 | 1 | 23 | 诊断目标通过 |
| `reasonable_named_values` | 45/45 | 1 | 23 | 诊断目标通过 |
| `wrong_missing_file_reason` | 45/45 | 1 | 23 | 诊断语义失败 |
| `rv_enum_types` | 44/45 | 0 | 0 | 行为失败 |
| `wr_null_raises` | 44/45 | 0 | 0 | 行为失败 |
| `wr_perm_fatal` | 44/45 | 0 | 0 | 行为失败 |
| `wr_wrong_reason` | 45/45 | 1 | 23 | 诊断语义失败 |
| `wrong_file` | 45/45 | 1 | 13 | 诊断语义失败 |
| `wr_zip_misalign` | 45/45 | 1 | 23 | 诊断语义失败 |
| `wr_zip_misalign_orempty` | 45/45 | 1 | 13 | 诊断语义失败 |
| `wr_all_files` | 45/45 | 1 | 23 | 诊断语义失败 |
| `wr_dir_named` | 45/45 | 1 | 23 | 诊断语义失败 |
| `oserr_fatal` | 43/45 | 0 | 0 | 行为失败 |
| `noreason` | 45/45 | 1 | 23 | 诊断语义失败 |
| `parsererror_only` | 45/45 | 1 | 23 | 诊断语义失败 |
| `import_swallow` | 44/45 | 0 | 0 | 行为失败 |
| `rv_import_warn` | 44/45 | 0 | 0 | 行为失败 |
| `wr_import_only` | 43/45 | 0 | 0 | 行为失败 |
| `chain_cause` | 45/45 | 1 | 23 | 诊断目标通过 |
| `gr_attr_wrap` | 45/45 | 1 | 13 | 诊断目标通过 |
| `ok_aggregate` | 45/45 | 1 | 23 | 诊断目标通过 |
| `ok_object_value` | 45/45 | 1 | 23 | 诊断目标通过 |
| `ok_map_settings` | 45/45 | 1 | 23 | 诊断目标通过 |
| `ok_dictionary_typeerror` | 45/45 | 1 | 23 | 诊断目标通过 |
| `ok_yamlerror_subclass` | 45/45 | 1 | 23 | 诊断目标通过 |
| `gr_csafe_loader` | 45/45 | 1 | 23 | 诊断目标通过 |
| `ok_falsy_empty` | 45/45 | 1 | 13 | 诊断目标通过 |
| `wrong_falsy_extra_settings` | 44/45 | 0 | 0 | 行为失败 |

两条权限负例 `wr_perm_fatal`、`oserr_fatal` 都实际失败于 `test_collect_yaml_permission_errors[file]`。前者其余44项通过，后者另有1条F失败；没有将这些P失败改写为默认通过。9条行为失败均保留 `fail_behavior`，不因缺少后续语义输入而升格。20条行为分1的候选都留存完整 API/完整 import 封包与 stderr 边界：16行23条、4行13条，共420份新鲜匿名输入，每行10个兼容分支必在场。另有 `wr_perm_fatal` 也产生完整 import，共21个原始 import 封包；其余8条行为失败的提前退出不冒称完整 import 采集。

全部29份 FrozenPatch/baseline/projection按冻结契约校验，基准为 `9634da11a5a6e5eb64cf941d2088aabffe504adb`，基准配置 SHA 为 `689e71ce770ee620c1e1c9ddaa72d12c1639c93d5d9c1c12f0be0e99c2d631ee`。noop 无条目；其余28份固定 patch 仅修改 `dask/config.py`，在内存中应用于原配置后逐字等同实际 FrozenPatch 内容。实际 clean base、无远端/不可达对象、未改排除路径集、public/runtime及材料身份全部相符。未执行或修改候选源码。

身份范围仍须保留：来源 inspect 实际配置 ID 为 `sha256:695d2cc28e303a0224c1109fe245f7296c6290d480124fa4fd4cc2ad072124b1`，对应 manifest digest `sha256:21e77aea7025bad694a5c600ed6d4b372c80c83bc319fafa2fedb23d9ff48483`；29行 ledger 的 `image_id_actual=null` 和 `resource_facts=null` 原样保留。冻结 producer 的策略与执行调用使用 UID54322，也包含 prelaunch 检查，但这306件原件未保存新的可信 grader `id -u` 原文。因此本轮不能借用 actor 的 UID54321，或候选诊断中的 owner字段，宣称获得正式 grader 的独立实测身份。

420份匿名输入均从本次实际日志重建：核材料身份、run/eval、ledger/log SHA、固定 prompt/config SHA与完整 payload SHA，没有沿用旧校准裁决。三批各140条恰好覆盖420个唯一 ID；逐 ID、合法 schema、引用在该输入的可见原文中、输出集合与逐候选结果引用全部核对。实际裁决为313 pass、107 fail、0 uncertain；合并后29行是11条诊断目标通过、9条诊断语义失败、9条行为失败。这里复核的是来源与引用完整性，不以作者期待标签重新推导裁决；作者报告中的控制匹配字段未作为本次通过依据。

三份实际 provenance 的140条输入、input/output/prompt/config SHA与大小、无父历史及禁读声明，与[严格外部交叉核](<../../../../../../../../runs/category2_repair_20260929/swe_dask/actual_semantic_judges_r16_20261003/actual_fresh_provenance_crosscheck.json>)和[实际 dispatch 观察](<../../../../../../../../runs/category2_repair_20260929/swe_dask/actual_semantic_judges_r16_20261003/dispatch_actor_binding.json>)逐字段相符。观察中的任务为 `/root/dask8801_actual_semantic_a/b/c`、`fork_turns=none`，精确后端模型和 effort 保持 unavailable。该证据是裁决者声明与编排者实际工具观察的交叉核，不能称为独立身份认证。

本轮发现并已定向通报初版聚合工具边界缺口：`finish_8801_actual_semantics_r16_20261003.py`（SHA `4243e419add541abfcf0f503c18cb76e5f5ffb70ab07d46acc394219feb87271`）只检查 provenance 存在并记录 SHA，未消费其内容，`fresh_context` 字段也由工具写固定值。初版脚本和已生成诊断原件未回写。本次实际结果由新增严格外部工具及本轮独立逐字段复核补足，未发现输入/输出错绑；这项补核不能等同于原聚合工具已经自行验证 provenance，后续批次不能仅依赖该字段。

`gr_csafe_loader` 的等价核依据实际 FrozenPatch 中的 `yaml.load(..., Loader=yaml.CSafeLoader)`、[实际日志](<../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask8801-formal-cpu-c-20261003-v2/remote/run/gr_csafe_loader/eval_logs/evallog_replay-dask8801-formal-c_e8e847c2.eval.log>)中的23条完整封包和10条拒绝分支，而非候选名称或23份裁决 pass。固定的11类诊断/兼容 fixture、5类空文档/空映射及1个有效映射共17组字节，分别经本机 SafeLoader/CSafeLoader 纯解析：两条语法错误的失败类别一致，9类标量的精确类型/值一致，空文档/comment/null/`---`返回None、`{}`和命名映射返回dict。实际两条 C 语法消息分别对应未闭合flow结构和第2行非法tab；它们与本机 C 消息逐字相同，而与 SafeLoader 的位置/措辞不同。实际非映射消息中的类型也逐条吻合，完整 import 的坏str仍真实非零。有效CPU测试中 SafeLoader独立拒绝两语法fixture、空配置和权限用例都通过。

上述纯解析使用 Python3.12.13/PyYAML6.0.3（libyaml=true），来源 actor 运行探针是 Python3.9.19/PyYAML6.0.2；未新增正式CPU解析器版本探针。因此本轮关闭的是这一组冻结 fixture 下的解析器等价待核项，不推及所有 YAML 输入、解析器版本或措辞鲁棒性。[原诊断报告](<../tasks/dask__dask-8801/formal_cpu_diagnostic_readback_r16_20261003.json>)仍保留当时的 pending 字段，此新复核记录其有限关闭，不修改历史原件。

另以15个内存反例核缺失/重复/未知 ID、非法 shape、引用错绑、未完成行为、空结果、服务故障和 uncertain：分别进入 needs_evidence/needs_review，实际 fail保留对应失败状态，未默认变成 pass 或0。所有本轮1,008条断言通过；这是本机复核断言数，不是新增CPU测试次数。

本轮固定证据 SHA：

| 证据 | SHA256 |
| --- | --- |
| [运输清单](<../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask8801-formal-cpu-c-20261003-v2/remote/readback_manifest.json>) | `ecba4e10ce6c86fafd96a32b68c4bb932ae708243102be37433613bbd467a2bf` |
| [发布清单](<../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe40_dask8801_v1/manifest.json>)（1369成员身份保留，本轮重核消费producer） | `f98eddad0c75df00e8e8352d52819d602a06d5e5ccb8d40feacb8c2658a2b80a` |
| [行为原报告](<../tasks/dask__dask-8801/formal_cpu_behavior_readback_r16_20261003.json>) | `f580c6b60a60a23c01958f6b6363a0c98583fb03806ce8faad1e0d5a926f28ad` |
| [最终诊断原报告](<../tasks/dask__dask-8801/formal_cpu_diagnostic_readback_r16_20261003.json>) | `18e93e7dcc5c696711bafa8220593260f401c238c24bc3bd1a0d36c86c064845` |
| [外部来源交叉核](<../../../../../../../../runs/category2_repair_20260929/swe_dask/actual_semantic_judges_r16_20261003/actual_fresh_provenance_crosscheck.json>) | `ed2c672b51cbc98333f97f385870f4ab7165cb971161ea9b1424fc5bd47cd88c` |
| [修正读回工具](<../../../../../../../../runs/category2_repair_20260929/swe_dask/finalize_8801_formal_behavior_r16_20261003.py>) | `7d31edc355114a86266f94cefc0d320327928c5e9e600719c8c03e1a63f8af4b` |

当前8563B/162CRLF公开交付已由前一轮实际 actor 独立核；actor为CC2.1.205 scripted stub四请求，无基座推理。本轮未重开公开actor或全链审查，不授探针/训练准入，不授权自动训练reward，也未验证GPU真模型结果。
