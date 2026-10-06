# Moto5960：原镜像 noop 已返回，安装供应阻断

2026-10-03。固定 R13／matrix v2 作业 `moto5960-cpu-6a6dd8d309c3` 只执行 noop，正常收尾，45 件原件已逐 SHA256／长度回收核对。**原始得分 0，三个 F2P 都失败、155 个 P2P 都通过，但 make init 实际退出 2，CPU 未验收。** gold／omit_keys_only 尚未执行；旧 R5 反例得分仍未知，不根据 noop 预报旧误判或模型能力。

测试实际收集 159 项，原 getmoto parser 形成 158 个唯一 key；这是原参数名含空格造成的一次合键：`test_set_attribute_is_dropped_if_empty_after_update_expression[use attribute name]` 与 `[use expression attribute name]` 均实际 PASSED，映射到同一 `[use` key。该 key 属原 P2P，两个实际参数节点均成功；不能只据 parsed 总数验收，也没有修改 parser 或删除节点。完整三个 F2P 和155个P2P均有实际状态，无缺失或跳过。

三个失败为 `test_gsi_projection_type_include`、新增 `test_gsi_scan_projection_keys_only_all_items`、`test_lsi_projection_type_keys_only`。新增 scan 的输出明确仍含 payload alpha/beta，期望只含表／索引键；其实际失败不是收集或安装异常。原两项分别报告多出 nonProjectedAttribute／someAttribute。pytest 实际 RC1、包装 exec RC0，正式开始／结束 marker 与真实退出匹配。

PEP517 build isolation 离线找不到 `setuptools>=40.6.0`；日志有 make init失败和独立 `RH2_INSTALL_RC=2`。安装段完整约9.047秒，不代表成功；测试使用镜像已有SDK继续，实际22.480秒。新环境供应交付前停止后续两臂，保留原raw0与安装失败原件。拟仅复制历史三件离线wheel并设置供应ENV，目录0755／文件0644，原make init、项目层、test patch、3F／155P和预算不变，实际镜像／环境身份另登记。

原source实际ConfigID `sha256:c67dbd356fcaa937ebff4b3fe0d78e4ea78211888233a4e5f07da95eddfe079d`，source manifest `sha256:4b71766331736b51bd74bb86cdb5e4e21040a7816e01fbb5d914526d33ef8944`，与原准备及正式R13消费者匹配。可信测试恢复、HEAD/base和脚本/材料身份均匹配；原CLI footer、候选移除和本job标签容器／网络查询正常。正式题级非作者原件结果窄核仍待安排，作者读回不替代独立验收。

证据根 `runs/category2_repair_20260929/moto_cpu_20261003/moto5960-cpu-6a6dd8d309c3_evidence/`。archive SHA256 `b80edd66cfb9b7695ce215be57f0f69869177131125854236aa95747a8ebe14c`，transport manifest `8ae5b4af9c8ad27056637c985e1b8817b2c41bf436905e3d1d62484b8ccb9755`。唯一评分日志SHA256 `5b45ececd156bcada1f8120b8e4741f75d905e3ed1c9c87523b8a4540e5780ce`／49370B；逐参考作者读回为上一级 `moto5960-cpu-6a6dd8d309c3_author_raw_readback_v2.json`。本次没有公开CC、模型、训练资格或typed actor租约结论。
