# 8511：当前CPU结果

2026-10-03。R14正式三候选实际 **0／0／1**，公开actor固定桩通过；[非作者原件核查](../../reviews/non_author_8511_cpu_review_20261003.md)已通过，[固定GPU探针请求](probe_request.json)已真实发送；GPU实际公开wheel可读权限和部署仍须核查，不授予训练资格。

正式作业 `pyd8511-formal-20261002232906-r14-f1f09` 每候选执行全部173参考。noop原repr F2P失败、172 P2P通过；gold解决原repr，但恰好新增的必填字段、隐藏字段、工厂字段三类继承P2P失败；narrow的1 F2P及172 P2P全过。安装完整、测试失败为普通tests_failed，镜像/Python3.8/core2.14.5/源码与受保护有效测试核对通过。本run三评分器均关闭，容器/网络零残留；398原件已回收。

公开actor作业 `pyd8511-actor-20261002234027-r14-3deca` 使用已核精确派生镜像；UID54321、Python3.8.19、core2.14.5、源码导入/可写检查通过。只执行原公开示例（复现已知repr错误，rc1且TARGET_EQUALS False）和原已存两项测试（2 passed）；三命令均完整，实际首桩消息包含原题面与hints，清理零残留，32原件已回收。未交付新私有断言或gold；它是控制桩，不是实际模型，也不证明正式训练typed actor租约。

固定版本：`cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`，manifest SHA `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`。输入／逐行／原件清单见[剩余四题CPU记录](../../cpu_acceptance_20261003/remaining/results.json)。首次双槽繁忙75保留，未运行题目，不计0分。完整452文件baseline运输及全部430原件获独立核查通过，baseline环境字段null的适用限制保留；冻结发布成员及历史评分不回写。
