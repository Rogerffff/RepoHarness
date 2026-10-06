# Conan14177：公开说明 v2 兼容修订

2026-10-03。原 brief v1 的公开测试文件名命中冻结 code7 的 `test_patch` 字符串扫描，实际入口在模型前拒绝。它不是私有测试或答案泄露的发现，原正式 CPU 验收不被推翻；原请求和说明保留原字节。

新 [brief v2](solver_brief_20261003_v2.md) 使用标准命令 `python -m pytest -n0 -rA conans/test/unittests/tools/files -k patches`，明确“收集公开文件工具目录，再按已有节点名筛选相关回归”。这不是编码或拆字符串隐藏材料；公共扫描、原 issue、评分及 CPU 材料均未改。

[干净公开读者](../../reviews/non_author_14177_brief_v2_fresh_public_reader_20261003.md)未发现中性、目标保持或隐私边界阻断。题主从完整公开目录按文件／节点名核对，静态筛选范围仍为原模块13个测试函数。目录收集会先导入其它公开模块，不能承诺避免其导入失败；本轮未执行pytest收集或Conan。

本地实际调用冻结 code7 的 `load_inputs`：v1仍按原规则拒绝，v2通过。完整原issue进入新prompt，材料身份、consumer脚本SHA、13参考与正式R11一致；没有调用manager、Docker、服务或模型。此项检查只证明输入构造兼容，不替代GPU实际交付／镜像／执行验收。原15候选、195状态、211原件及两份CPU独立核查按同源同评分范围复用，不重跑。

[摘要与绑定](public_brief_v2_delta_20261003.json)链接拒绝原件、局部检查、公开读者及CPU证据。[新固定请求](probe_request_20261003_r11_briefv2_v1.json) ID为 `swe-conan14177-r11-briefv2-20261003-v1`；预算仍为两模型各一次的 `probe-wide-v1`。原请求已在模型前安全取消，实际GPU队列／容器为空，模型尝试0；题主已核回执及现场原件SHA并ack，活动指针切换至新ID。新请求已登记并直接通知GPU，尚无本题模型结果；旧输入／失败／安全取消记录继续保留。
