# coveragepy 5dbb 题面 A 非作者静态窄核

2026-10-03。审查者：Codex，非题面作者；已见038／039、CE候选与既有公开读者报告，不是fresh公开阅读。只核本包5dbb新题面、修订单、manifest、CPU计划及必要公开源码；未运行项目、SSH、容器、安装或模型，未修改题主／生产材料。

**结论：未发现本轮题面 A 的具体冲突、误拒或接续错误，可以由维护者沿已有授权登记发布。038／039及76键评分保持不变，毋须因题面-only机械重跑全部历史矩阵。发布不等于实际CC题面交付；正式准入仍须核新版本的CC初始请求与材料身份、宿主关键条件及计划中的代表性往返。**

1. `materials/statement_A.txt` 精确补全原例的期望：同slug的两条once警告即使消息不同也只显示第一条，不同slug各显示一次。它未规定集合／列表、去重存放位置或调用私有helper，也没有把slug=None、跨实例、once后的非once混合边界升级成新增验收。公开 `coverage/control.py:336`–`:350` 已把slug定义为警告抑制的识别键并显示在括号中。该新增说明与已决定A和原例相符。
2. 从原 `public_bundle.json.row.problem_statement` 唯一替换得到新题面，前后SHA吻合；与 `rh2/experiments/category3_cloud_20260929/cov5dbbe/revised_statement_A.txt` 逐字相等。已有公开阅读可复用，本人未冒称重新完成盲读或实际运行其报告里的命令。
3. 新 `revision_draft.json` 只有一条statement_text_replace；manifest的replace_revision_ids=[]、publication_files={}，保留038／039。直接核v11中两个revised_file字节：038 test_1.py SHA为 `05bcd4891846016e194d2fea16bcfdf026feb62787ebd3a8f936ca1cbeb994d7`；039 expected SHA为 `fc64a1db6ec518a4088067d2571ad93b90acc6aca21847a3c1f54d06960e316a`，expected确有76键。
4. 定点核038有效测试的once调用：`test_warn_once`验同slug不同消息第二条不显示；新增`test_warn_once_each_slug`验两个不同slug都显示。没有在本轮新评分中追加题面未说明边界。CE3按slug去重、CE1按消息去重、CE4把所有once合为一个的原补丁，与矩阵角色相符；新版正式分数仍由实际运行证明，不能以此静态推导冒称新运行。
5. `cpu_execution_plan.json.public_delivery` 明确从PreparedTaskFace的prompt取得完整题面，核第一条真实stub `/v1/messages` 请求字节，不用devcheck默认通用prompt替代。scenario、公开命令和CE3／CE1补丁SHA已核匹配。脚本化桩／真实CC公开开发检查不是基座模型探针；其结果目前是计划，未执行。
6. r2e-mr-903仅是解析占位，发布时维护者分配最终编号并核最新父版本。公开交付、实际consumer与材料身份及清理证据仍待运行；没有新审批要求。

本轮材料SHA256：

| 文件 | SHA256 |
| --- | --- |
| materials/statement_A.txt | `b2a7f5fb3e3c76a8896ac0f8afb2e9b534bcfbd28baf6ebbe647ddd0857b2415` |
| revision_draft.json | `fe1dd025d6a7e09324a5be79375668b315464b4ff42a1fe3fa3c190904c937ca` |
| cpu_execution_plan.json | `5a91d234471c8030a367ea2f306b696a04a09c8e03a86cf4977cfff2760525ac` |
| cpu_matrix.json | `d2c7ddfda9825311d12c3831e1f8430a58d5af684782836ac19f09ede98d7d91` |
| results_manifest.json | `6a5e265191cd4214a8f097f2b86185a1091e647c09875378698fb74956c0f59d` |

停止条件：新题面与已选A、有效评分材料及接续计划静态一致，没有必须先改的新材料问题。可先发布固定版本；实际CC初始消息／身份、代表性正式往返及清理完成后再谈准入。本轮仅新增本报告。
