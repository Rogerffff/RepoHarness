# coveragepy 暂停检查点

2026-10-03。**已安全暂停，等用户明确恢复。** 停止新增作业、探针请求、发布／部署和常规跨线程通知；无自动重试器／后续派发器，无活动子agent，不起新agent。原5dbb非作者子agent已完成。

两份暂停前已启动的有界作业均自然退出0，未强杀、未改旧工件：

- `cov016a-matrix-r6-cpub-20261003-01`：原14行整组矩阵结束，原件130文件已保存；包装器记录14行符合预期。暂停后没有继续逐键作者核对、CPU非作者核查或探针提交。
- `covea69-public-r6-cpub-20261003-01`：公开CC桩v2及既有评分／往返结束，原件53文件已保存；没有接续EA正式矩阵。

自有两作业及派生builder标签下容器／网络均零残留，gateway18190／stub18191空闲，见[pause_cleanup_20261003.json](pause_cleanup_20261003.json)。首次016摘要保护失败的原status／stdout／stderr也已保存，未执行CC或评分。已启动包装器全部结束，没有自动接续。

固定版本与最近证据：

- 5dbb保持R5 `cat2-cpu-r2e078079-swe7-git-20261003-v1`（manifest `80ee228d…`）：CPU及非作者核查通过，已提交GPU请求保持冻结，尚无模型结果；见[probe_request.json](probe_request.json)。不新发请求或确认链。
- 其余保持R6 `cat2-cpu-r2e080087-swe8-git-20261003-v1`（manifest `ab0a3a13…`）：prepared15／8／49键及三派生镜像已核；016、F5公开交付已完成作者核对，F5其余15候选未启动。EA公开交付原件刚保存，完整作者核对／正式矩阵仍未做。
- 最近原件：`runs/category2_repair_20260929/coveragepy_owner_cpu/remaining_r6_v1/016a_formal_matrix01/` 与 `ea69_public_e2e02/`；题级身份和既有核查见[preparation.md](preparation.md)及各题`cpu/`。CPU桩／固定候选均不计模型结果。

**恢复后的唯一下一步：先核对016这份现有正式矩阵的逐键、版本身份、退出与清理，完成作者CPU结果收口，再按重新对齐的分工安排必要核查。** 当前真正暂停依赖是用户恢复与分工对齐，没有新增技术阻断。模型准入／回传仍由统一执行者负责，现有请求不在本线程重跑。
