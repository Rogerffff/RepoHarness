# Moto7584：两模型首轮收口

2026-10-03。R13当前v3材料的Coder与Qwen各首次一次均原分1，安装／测试0，正式1F／19P共20参考完整。题主两份补丁与完整轨迹均分析完成：application端点存在性检查先于重复订阅返回，删除后再订阅不绕过检查，已保护有效及其它协议保持。当前无必要题面、评分或环境修订；每模型仅一次，不能证明稳定或训练资格。

| 模型 | 修法与验证质量 | 实际轨迹与成本 |
| --- | --- | --- |
| [Coder](coder_a1_analysis_20261003.md) | 一项源码改动、三个自测及总结进入FP；最后两份严格ClientError断言自测通过。早期观察程序的宽泛catch／print与公开19项不替代正式20项。 | 33回合／32工具，7标错＋1隐藏空测试；输入687224／输出5205，solver71.133秒。多次导入及错误测试路径纠错，无多工具batch。 |
| [Qwen](qwen_a1_analysis_20261003.md) | FP只一项源码，同Coder完整AST相等；inline修前／后观察支持修法，但不抛时仍只打印ERROR，严格性不足。正式20项完整通过。 | 15回合／14工具，0标错但有1隐藏不存在路径；输入394279／输出2853，solver53.708秒。单次源码Edit，实际串行，SNS184尾段与19／104自测重叠。 |

配对请求 `swe-moto7584-endpoint-r13-20261003-v1`，SHA `bfd638718181356e230c432844ddc494fb51903f48dcad46505f2ce7512dd34d`，材料 `moto7584-endpoint-v3`。两臂2537baseline entries、prompt原字节、材料身份、实际actor／grader镜像及模型／评分预算相等；均code8、setup300。各自engine／adapter部署及现场capture单列，未重复全部权重或GPU内存hash。这支持当前配对，仍不能推一般模型排名或稳定成本优势。

总回执 `runs/ordinary_gpu_probe_20261002/migration_20261003/swe-moto7584-endpoint-r13-20261003-v1_pair_execution_receipt_v1.json`，SHA `f55a45806b98e6e5176a1ff69bf7b13b80cad1382eed4695c473bdfca6672d86`；原件不改。两个独立依赖封存包含398及180成员，重叠不能相加为实验数量。单臂原件paired_request_closed=false与机械semantic空保留，当前题主收口及总账确认单列。

本题首轮收口，普通未启动追加暂缓；继续Moto5960、6408、6185三个剩余Qwen首次及必要分析／修复。本题没有活CPU作业，不自行退租、停机或改变共享GPU。
