# Moto5406：将既有地区回归测试纳入正式验收

2026-09-30。沿用户已授权的SWE修订机制逐题扩展。实现基线为 `runs/category2_repair_20260929/frozen_d6_monai4583_v1/code_v1`，691文件库存摘要 `638b56aeea2ec06e4f87224784957f35f0c37a128212cc82e1d8723038926373`。只复制到 `runs/category2_repair_20260929/d6_moto5406_implementation_v1/code_v1` 后修改，root审查后再按逐文件摘要接入共享树。

材料位于 `swe_materials/moto5406_next/`；manifest摘要 `d5ca5786f42ef1a25463b28e89ba101a7e2062229294fc3e143fe22459f5fb83`。新增的既有公开节点为 `tests/test_dynamodb/test_dynamodb_create_table.py::test_create_table_standard`，在base与gold通过，恒East2错误候选失败。原1F2P、26P2P顺序保持，新增1P2P形成28项。原test_patch保持逐字不变，不制造测试补丁替换。

## 本片实现范围

1. 增加封闭的 `append_swe_existing_p2p` 操作及本题独立登记，revision为 `moto5406-existing-east1-p2p-v1`。绑定题目、仓库、base、原材料父身份、公开身份、原test_patch摘要、唯一路径/节点及原文件摘要。不能接受任意shell、路径、-k表达式或参数化选择器。
2. 原vendor命令完整保留，再追加一个空格与固定节点。原安装 `make init` 不变。新文件必须纳入可信原件恢复、普通文件/SHA核验、测试保护及候选改动过滤，不能只往P2P列表追加却不真正执行。
3. actor与replay使用同一正式构造。新身份和资格绑定必须生效；旧资格、旧新prepared混配拒绝。原reference分区和诊断保留，原材料可精确恢复。不得修改manager、parser、奖励或安全边界。
4. 从原216输入生成新版本；相对已验MONAI4583版本，仅本题grading/environment变化。所有public/validation及其余215行保持字节，五道已验修订的身份、脚本和诊断保持。生成器须可重放到同字节输出。
5. 验证真实边界：错task/node/file/SHA/base/parent/pin、遗漏/重排/重复/交集，恢复/保护次序、单脚本与split脚本、资格及原版本兼容。测试中先确认负例进入目标校验路径，避免仅被其它校验提前挡住。

## 尚未关闭的公开题面问题

根复核发现原公开示例create/describe使用 `mock_Foundational_AMI_Catalog`，期望ARN却为 `test_table`。已有公开actor命令曾统一名称，不能冒作原题面原样可复现。根已另备最小R-f草稿：仅将两处create/describe名称统一为题面原有的 `test_table`，不改地区或添加私有知识；独立新公开读者待查。**本片先完成评分修订，尚不能据此交第1类。** 题面正式版本与实际交付由后续明确补充承接，不准在运行器临时改prompt绕过版本机制。

## CPU验收与交付

root统一远端执行，每次1个本任务actor/grader，和同机探针合计不超过2。原不可变镜像先实际inspect；资源沿历史2CPU/4GiB/PID512/shm64MiB、setup/reset900、apply120/test1800/whole1800/cleanup120，网络不改。正式noop/gold/constant应0/1/0，28项真实执行、安装完整成功、实际源码与保护文件、退出码、日志和两层清理均核。真实CC桩端点只收公开材料；同次原冻结工件送新grader，保留完整baseline和excluded census。

保存代码/材料/镜像/配方、历史与新结果、独立审查和未闭环问题。未验题面修订前仅算评分子片完成；CPU通过也不等于训练准入或公共评分信任闸门通过。不提交推送，不覆盖历史，不热换另一线程在途快照。
