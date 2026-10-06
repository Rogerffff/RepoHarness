# Pillow 3a61 / a682：非作者材料接续窄核

2026-10-03。本核查者非材料作者，已接触私有测试、候选和历史报告，**不是 fresh 公开盲读者**。依授权先读公开原题、base 相关代码与测试原件，再读已有报告。只用标准库文本/JSON、SHA-256、AST及内存补丁/编辑块重放；没有执行题目代码、pytest、项目检查、SSH、容器或下载，没有修改原材料。

结论：未发现两题本轮合并、采用工件、旧断言或候选接续中的具体静态错误。采用材料已有聚焦语义审查，本次核身份、完整原件与发布合并，复用相同材料上的既有意见，不再展开全角色链。两题仍为未发布提案与待运行计划，历史私有模拟不等于新正式评分，矩阵标签也不是实测结果。

## 3a61：来源合并与原正式 C1

公开 ISSUE 要求恒等 remap 后 RGBA 调色板保持不变。公开 base `Image.remap_palette` docstring (`Image.py:1854`) 说明交换映射，`:1922` 已维护整数 transparency 索引；公开原测试也核该索引移动及未使用索引删除。因此RGBA模式、remap与整数透明索引的交集有公开依据，不因gold在该交集失败就删去要求。

`3a61_material_proposal.json` 从原始test SHA `17ececcd…`重放三个唯一编辑块，逐字得到云端v2完整文件 `78631c73…`，不是在024产物上再叠加同target。对照v11的024编辑结果，原73键对应文件的所有函数AST完全不变，仅新增 `TestImage.test_remap_palette_rgba_transparency`；原调色板快照、RGBA渲染、交换映射及GIF保存读回断言完整保留。source expected 71键到最终74键只增三个PASSED键，原71键值不变，ANSI键名也保持；它包含025的两个新增节点与本轮交集节点。

采用完整文件`:678`的新测试检查两项及满256项RGBA调色板的恒等/交换、透明索引及渲染。调色板透明项原alpha为40，渲染alpha为0，这分别检查“调色板保持原件”与既有透明语义；不能把修改原palette以烘入透明度当作等价解。满256段保留，能拒绝只在小调色板避开映射异常的G_small。fixture调用使用现存P模式、putpalette、remap和convert，未发现调用错误。

验收计划明确使用原正式 `runs/r2e_actor_20260925/grader_cands/pillow_3a61_C1_rgb_plus_alphas.patch`，实算 `da1193af5bd57ea6dd7a52dc581120d230f40375848e28de8798e9959a6414fa`。云端C1 `c3096361…`只在index行的缩写不同；独立内存应用两份补丁到同一base得到逐字相同 `Image.py`，SHA `8cde01fee71cf1f14f57003d366fe3094b4e3931f4b84e76402c97f4db664d2c`，AST可解析。U11及C1保留为不同合理实现正对照，gold/A1u因已核交集缺陷列为0合理；当前18行候选引用与声明SHA全部相符。已有聚焦复核的U11公开回归意见可按旧证据范围复用。本次未新验证分数，也不补造不存在的W4。

## a682：独立复核 v2 接续

从原始test `ff7a439c…`唯一编辑块逐字重放得到复核者v2 `3573f459…`；只有 `test_removed_transparency` 函数AST改变，没有删函数，原示例的保存、UserWarning与无transparency读回语句按原顺序保留。expected原件与采用文件逐字相同，实际93键，SHA `a465b6c9…`。

`:1089`采用目标仍检不能分配透明色时成功保存且不带透明度，并追加调用者info不变、save_all单帧、同颜色后续可分配、照片、透明色已经在满调色板/照片中的行为。写入真实临时GIF路径，各次open在上下文内关闭，调用与fixture未发现静态错误。公开 `_normalize_mode` (`GifImagePlugin.py:483`) 调用ADAPTIVE转换，base转换及公开 `test_image_convert.py` 对该机制有UserWarning契约；保留warns仅核类别，未新增文案、次数要求。已有审查对调用者状态、save_all与顺序机制的依据充分，可复用同一v2，不以新猜想扩张范围。

16行矩阵与既有聚焦复核停止清单一致。r_kwtuple允许额外处理关键字元组的合理路线，测试未要求该扩展；w_mutate_kept、w_nosaveall、w_order_cache分别有采用版状态、save_all、顺序断言相接，w_filter_leak/q_prestrip仍由保留warning行为区分。所有非空补丁实际SHA和计划声明相同。此前root/UID私有模拟与164格记录仍是历史证据；新agent投递、正式93键及失败原因须实际运行。

## 发布边界

3a61明确替换024/025，a682增加此前没有的hidden target；不追加重复target、不覆盖旧文件。proposal正式ID为null、revised_file为尚未写入的拟发布版本路径，不能把它作为已生效registry消费。交接依赖共享发布者当时最新父版本，须保留其他题条目，完成正式编号、文件、pins/ingest和派生镜像。CPU新宿主身份、正式交付与计划分数仍未由本核查验证。

## 实际SHA-256

| 工件 | SHA-256 |
| --- | --- |
| `3a61_material_proposal.json` | `7df4d26ae533ac61db4c62bc28bbc958e41103babef073fe4ac53fcca835c8d3` |
| `a682_material_proposal.json` | `7eea4ee229c04c5297f901abbc6d7d4de70b0391e9878c11e18b75af59d013b1` |
| `publication_handoff.json` | `446248c1d26b82848f5673058849f5ddba39814b62eab5fab3c34e748fa54360` |
| `acceptance_plan.json` | `df2ec923ca86ba9939b1f769a1f33e5f790d9436c57f55c98c9c7d05d21e13e2` |
| `hidden_test_1_revised_v2.py` | `78631c73aa9599b3b07c157fdc08f94df7e4698685fee9e462d17db321334612` |
| `expected_output_revised_v1.json` | `af126a3c513f11efd3f78a89ff5f601a1c9bf401d078d43d569b2dfcc6650304` |
| `hidden_test_1_review_v2.py` | `3573f459d7e313f7b3ca14ae691fccc9268d82ba079de8c7cdb870abf466274a` |
| `expected_output_orig.json` | `a465b6c99cb3be23e4f9d9a4f602d6caa2ceea228f524532938a535f7401a096` |

仅新增本报告，未回写历史材料或登记表。
