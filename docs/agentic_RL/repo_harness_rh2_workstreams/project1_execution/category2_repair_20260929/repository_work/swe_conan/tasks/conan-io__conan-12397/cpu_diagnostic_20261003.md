# Conan12397：新机草案诊断

2026-10-03。**完整cpp键检查与新增Linux原场景均已实际执行，gold通过，两个反例按缺陷被识别。** 这是私有root诊断，不是正式评分或actor验收。有效补丁SHA仍为`7352a2fd18bcaccaa5e35ae5746b2b8a87725fa40c48972adb3b8647c8335e0b`，测试、候选和题面未改。

| 候选 | 实际收集 | F2P通过 | P2P通过 | pytest RC |
| --- | --- | --- | --- | --- |
| gold | 4 | 2/2 | 2/2 | 0 |
| noop | 4 | 0/2 | 2/2 | 1 |
| objcpp_only | 4 | 0/2 | 2/2 | 1 |
| apple_only | 4 | 1/2 | 2/2 | 1 |

objcpp-only在Apple完整cpp键及Linux节点均失败，不能再借`objcpp_link_args`后缀获得通过。Apple-only通过Apple节点、仅新增Linux节点失败。四份日志的16个精确参考逐项核过，无参考缺失、重复或skip；原两项P2P全部保留并通过。仅生成Meson配置，没有安装或执行clang/libc++、Meson或编译软件。

原镜像按manifest`b3192aee6c3565730fece66f36212dc2fd77f13271bb632cbb1be2ba0bb6bd55`拉取，实际image ID为`sha256:d0b6f915791c8c4597dffc2642093dfdc864a90f122544b23561e09ad6ba90a1`。BASE HEAD、原测试与Meson源码、有效测试全文及每份候选应用后的源码SHA全部匹配。四方项目均从`/testbed`导入，pytest6.2.5。

镜像准备job`conan12397-image-20261003-v2`外层RC0；首次请求RC75是槽忙，未启动命令。诊断job`conan12397-draft-diagnostic-20261003-v1`使用原`private_behavior.py`，按run槽持锁、串行四候选、2CPU/4GiB、network none。所有准备命令RC0；四容器rm/query RC0，残留为空。67件输入和回传文件与远端SHA一致。

未重跑原安装前缀，UID0，不代替公开actor权限、D6正式consumer或reward。不把预期0/1/0/0写成正式得分；正式CPU验收仍为空。非作者材料静态窄核已完成，后续依据实际接线和运行差异复核。

原件在忽略目录`runs/category2_repair_20260929/conan_cpu_20261003/`：`diagnostic_audit_12397_v1.json`包含逐ID状态；`diagnostic_evidence_12397_v1/output/`保留原日志；`image_evidence_12397_v1/receipt/`保存镜像拉取；`remote_transfer_audit_12397_v1.json`保存远端摘要及作业回执。下一步是真实actor配置生成与正式材料接入，满足后才提交探针。
