# NumPy d805：非作者材料接续核对

2026-10-03。本核查者非材料作者，已接触私有测试、候选和历史报告，**不是 fresh 公开盲读者**。依授权先读公开原题、base 相关代码与测试原件，再读已有报告。只用标准库文本/JSON、SHA-256、AST及内存补丁/编辑块重放；没有执行题目代码、pytest、项目检查、SSH、容器或下载，没有修改原材料。

结论：已有两项非作者报告覆盖同一当前题面、测试及关键候选，足以复用；本次未发现新的身份、source合并、旧断言保留或候选接续错误，不机械重审完整语义。**无新的CPU结果**，父版hybrid=1、新版hybrid=0、K-A5b=0、K-A5c=1仍是待正式核实的预期。

## 公开依据与既有审查身份

先核source公开题面及base，再读 `reviews/public_read.md`、`reviews/static_revision_review.md`。公开报告明确只读public与公开base，未读私有；修订报告明确是非作者静态核查，未运行NumPy/正式评分。它们的实际全文SHA分别为 `5a444e92…`和`5bed10ee…`，与result_manifest引用一致；修订报告绑定测试 `09d0aa6d…`，公开报告绑定题面 `0d6302a3…`，均与当前原件相同。本次有私有暴露，不能替代或冒称那个fresh角色。

base `numpy/ma/core.py:3767`的str路径先截角再转object，`:3827`附近的repr数据来自str(self)，公开arrayprint的threshold是总元素数摘要阈值，edgeitems决定首尾项数。因此测试追加的提高阈值后仍需摘要、首尾501项并显示省略号有公开契约依据。token检查容许linewidth折行；未扩大到多维、性能、structured dtype或所有打印配置。题面Actual的0/49mask/1950–1999能从公开初态 `_print_width=100` 推导；本次未核文本逐字符实跑输出。

## 合并与旧断言

从原始source test SHA `72f865c42fba15679442951d772b9213dc4fc5d4ad16170f486ed6aac7e8deb1`重放publication_handoff的两个合并编辑块，old各匹配唯一，逐字得到当前完整test SHA `09d0aa6d80f85d394fc0a7971e23de8dd43a79d817749f0246693f62898bf67a`。原056单独重放仍得到父版 `14d78a1c74be07bf5e62a81c5383b3d408dbf597f6a54d3bfe48ac5e6d9516c7`。

只有 `TestMaskedArray.test_str_repr` 函数AST改变，其他函数未删/未改。056目标内原八个assert调用逐个保持相同，本轮增加两项；打印设置仍由既有try/finally恢复。source expected实际229键，SHA `4ed3f5bcaea6016adb71885f0befe9dd1e056d460d7e6410e9a40fc84be11dd6`，与revision_draft.expected_after逐键相同，没有expected变更。题面三个编辑块从公开source重放得到当前problem_statement逐字原件；没有新增测试常量/候选泄漏。

发布交接正确使用原始before SHA，合并替换056而非在同target叠加，并单独登记statement target；正式文件路径/ID仍由发布者补齐。交接记录首release已是v14/v13且本题056不变；这是作者/协调者接续记录，本核查没有远端回读，不能代证实际宿主release。发布时应以当时最新冻结版合并、保留其他题，不回退到v11。

## 关键候选与运行边界

K-A5c实算SHA与计划一致。超过阈值时取原宽度、threshold+2、2*edgeitems+2之较大者，截取长度仍大于摘要阈值和首尾总项数；未超阈值则不预删元素。这支持本轮一维场景的合理正路线，沿用既有非作者报告的明确边界，不称完整正确性证明。hybrid固定截取1500项在n3000/t2000下截取后不触发摘要；K-A5b在edgeitems501时长度等于1002而无省略号，与新断言冲突。两项静态预期有代码依据，不能用局部推导替代229键评分。10行矩阵的9份非空候选实际SHA全部符合计划；父材料检查另列，两代结果不得混记。

已有两报告对helper、候选可应用性和实际solver题面交付的未完成范围说明充分，本轮不重复其项目验证。新正式评分、决定性断言执行、行为核查和actual solver消息依既有计划收口，旧v8只覆盖旧范围。

## 实际SHA-256

| 工件 | SHA-256 |
| --- | --- |
| `private/test_1.py` | `09d0aa6d80f85d394fc0a7971e23de8dd43a79d817749f0246693f62898bf67a` |
| `public/problem_statement.txt` | `0d6302a3be3a39d0828c4fc5cf3b9e4d70ce6099b9bc61f6cf4275aad276225e` |
| `publication_handoff.json` | `39da39f09a6b056002a3aaf4436df24721fd49f14e7570cb111f9feadee7463f` |
| `revision_draft.json` | `73d2625e995441103df52d924a99aff179fe35c851fe827ceeed64081835d7f2` |
| `acceptance_matrix.json` | `84497dc26f88794a75aa16663bdf41ecc4ded0104c2f1b0440218bb7a2669196` |
| `reviews/public_read.md` | `5a444e92504f47e04fcfdae3096a819a2edee226256b5faada8e9c647ce2575f` |
| `reviews/static_revision_review.md` | `5bed10ee8622648c65d49cee3e07fe66fc71508772b50251d4ff388d4e5cb7ea` |
| `private/candidates/numpy_d805_KA5c.patch` | `c343ac75de6e122550efb9c93d2e0d88596afe5c8cfd6270f48eade8a7050ffa` |
| `private/candidates/numpy_d805_hybrid.patch` | `fcd140019c87d7ecc92591f3a6f0ce687e94c8853112cb37a43fb1846a2b9a4b` |

仅新增本报告；既有两报告、材料、候选、历史证据和共享生产入口均未改。
