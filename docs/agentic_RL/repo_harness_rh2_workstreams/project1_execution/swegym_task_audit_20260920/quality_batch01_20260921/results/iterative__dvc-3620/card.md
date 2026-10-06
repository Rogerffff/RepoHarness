# iterative__dvc-3620

base `e05157f8e05e856d2e9966c30a3150c26b32b86f`。目标是解除 symlink 输出保护时保留缓存权限与数据。建议 `needs_review / static_review`，仅作 `development_diagnostic`；actor 尚未验证。

| 需求/旧行为 | 公开依据 | 验收与范围 |
| --- | --- | --- |
| symlink cache 保持只读 | issue；fs.py 的预先 chmod | symlink F2P 检查源0444、输出非保护，直接覆盖主例 |
| hardlink cache 立即只读 | 相同根因，但公开旧测试允许暂时可写 | hardlink F2P 是合理推广，仍有需求范围歧义 |
| 输出存在、可写、保留数据并断链 | unprotect 的 copy→rename；公开 checkout 测试 | 额外 CLI 查可写却未入参考；7项均未查内容/断链 |

八方面已核：公开需求与旧断言冲突；材料身份和初态；全部修改断言、2 F2P/4 P2P及fixture；无helper/顺序绑定但有硬链接范围疑义；gold及remove/unprotect调用者；依赖与非root需求；投影和官方恢复；用途与暴露。未核实际actor消息、Windows运行、完整回归和跨题同族。

最新 `dvc_install_v1c` 两份账本/原始日志确认：相同修复镜像、rh2grader/54322、离线安装成功；gold **7过**，noop **3败4过**。参考只含其中6项。gold先unlink、失败再chmod，保留复制路径，无新依赖。旧root导致CLI前置失败已过时；旧报告“安装正常、parser无污染、symlink-only也能全过”均不成立。历史缺席参考的具体生成原因未证。

静态限制是硬链接推广、数据后置条件与Windows回退覆盖；未证明误拒或错误解满分，不因此自动排除有限诊断。主审封存时的CPU提案：实际actor入口核身份/导入后，同非root条件对照base/gold/symlink-only，固定非空文本分别建两类链接，核缓存mode/字节、输出存在/断链/内容、修改输出不改缓存，再分报来源得分与额外CLI。CPU能核行为，不能裁定需求歧义；尚未执行。独立reviewer已收口。

详证见本目录前稿与历史差异；主审已见私有测试、gold和历史，不可作为盲解上下文。原件未改，额外排除为空。

复核收口：独立复核保留hardlink合理推广与旧契约冲突的判断差异；协调者采纳数据丢失负对照为首个评分校准，symlink-only只量化范围且不能裁定契约，不设两组必做门。review补核共享moto版本预改；local.py:532–538定位is_protected正确。 详细依据与处置分歧见 review.md；未回写封存前稿。
