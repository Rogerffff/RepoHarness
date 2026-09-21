# iterative__dvc-9395

base c75a5583b384，目标是让 repro --pull 恢复本次复现所需的缺失数据源，并保留运行缓存恢复。静态建议 needs_review/static_review，限 development_diagnostic。

| 需求/旧行为 | 依据与测试 | 覆盖/证据 |
| --- | --- | --- |
| 缺失源文件恢复 | prompt:9–11；F2P missing_data_source | 本地remote、真实cp；noop失败→gold通过 |
| 缺失运行缓存仍避免重算 | 修改F2P test_restore_pull | 产物/lock存在、禁止cmd_run；三次checkout耦合内部方式 |
| dry不下载/检出 | CLI、Stage.run、StageCache.restore | 现有dry P2P不带pull；gold新增路径无dry保护 |

已逐项读全部修改、fixture、2 F2P/27 P2P及相关调用者；核材料身份、初态、合理路线、gold、开发需求和交付边界。09-19派生配方固定pygit2 1.14.1，grader离线安装成功；gold真实30过，noop3失败/27过。额外import测试已失败转通过，却不在29项参考；parser计31不等于执行31。

最重要的静态疑点是gold在dry前拉run-cache并fetch/checkout，可能改变文件；另在无需下载、未配remote时也先拉run-cache，预计新增NoRemoteError。二者未运行验证。精确checkout三次可能拒绝按需恢复的合理路线。旧报告所称历史“次数误拒”，原失败栈实际停在缺bar，未到次数断言；旧pygit2永久失败说法也已过时。

八方面尚未验实际actor消息/解释器/权限及配方消费、真实镜像泄漏、上述回归的运行结果和完整exp调用者；不按同文件推题族。无新增排除，gold源码可提交，官方恢复仅两测试。唯一下一步是固定本地remote的base/gold pull+dry快照及dry=False正对照，详封存分析；CPU未执行，独立reviewer已收口。主审已见gold和旧候选，不能当未暴露solver。


复核收口：独立复核确认dry/no-remote为历史前分别发现的静态疑点，未执行。旧候选在reproduce缺bar，未到次数断言。封存主稿/历史稿的GL/NL行号错误由review.md正确位置取代；最终引用以review为准。公开旧checkout两次与私有三次不同，actor旧测试失败须按行为解释。 详细依据与处置分歧见 review.md；未回写封存前稿。
