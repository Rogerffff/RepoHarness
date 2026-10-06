# 6043 静态短卡

目标是best-effort确定且递归整理JSON Schema。base `d476599cdd956284595034d7d9fd046569a0574c`。建议 `needs_review/static_review`、`development_diagnostic`：可执行目标存在，但有公开契约冲突与覆盖缺口。

| 要求/旧行为 | 依据/断言 | 判断 |
|---|---|---|
| 递归整理映射键 | 题面；唯一F2P仅将alias字段序改为Crackle,Snap | 缺根、嵌套、$defs和批量出口顺序验证 |
| schema字段保序 | docs/usage/models.md:964；旧test_by_alias | 与新增字母序断言冲突，保字段序的合理解有误拒风险 |
| 列表与引用语义 | tuple六参数、enum/examples、批量/模式P2P | 有语义护栏；保prefixItems位置合理，不能因gold不排列表就判错 |

完整读gold三个hunk、递归helper、单/批量model和TypeAdapter调用者，抽查决定性P2P。gold正常JSON树递归排所有dict键、list仅递归保位置，因此会把z,a字段改a,z；这是静态可证的旧行为变化，是否被新要求授权待裁决。未穷审全部303项语义。旧pilot转述properties-only fake满分，本次未读其原实验，仍按静态覆盖缺口记录。

原install-v1两次安装RC0；noop305 passed/1 failed/1 xfailed，gold306 passed/1 xfailed；303个expected P2P均PASS。初态pyproject/pdm.lock非干净、派生image/安装/恢复均见前稿。实际actor消息、工作树、资产/权限/依赖/网络/资源unknown；合法非测试源码可投影，未证明全部控制面安全。跨题重叠/actor答案暴露未核，审查者已见私有及两份历史材料。

唯一优先下一步：先裁决properties是否继续保留声明序，再使公开要求和断言一致；CPU重跑不能决定契约优先级。不自动剔除，也不提前补新评分要求。无本次实验或题目修改。独立reviewer未读/结果未知；完整证据见前稿与历史差异稿。
